import feedparser
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime, timezone
from typing import List, Dict, Optional
import time
import logging
import pytz
import json, uuid,os
import re
import html
import app.services.llm_service as llm_service

logger = logging.getLogger(__name__)

# Browser-like headers to avoid 403 Forbidden errors from servers that block bots
RSS_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, application/atom+xml, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
}


def _create_session_with_retries(max_retries: int = 3, backoff_factor: float = 1.0) -> requests.Session:
    """Create a requests session with automatic retry logic for transient failures."""
    session = requests.Session()
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,  # Wait 1s, 2s, 4s between retries
        status_forcelist=[429, 500, 502, 503, 504],  # Retry on these status codes
        allowed_methods=["GET"],  # Only retry GET requests
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def clean_html(raw_html):
    """Remove HTML tags and decode common entities."""
    if not raw_html:
        return ""
    cleanr = re.compile('<.*?>')
    text = re.sub(cleanr, '', raw_html)
    # Optionally decode HTML entities if needed
    
    return html.unescape(text).strip()

def ensure_aware(dt):
    """Force datetime to be UTC-aware. Return None if input is None."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=pytz.UTC)
    return dt.astimezone(pytz.UTC)

def fetch_rss_items(source_url: str, last_synced: Optional[datetime] = None, limit: int = 10) -> List[Dict]:
    """Fetch RSS items newer than last_synced (UTC)."""

    try:
        import re
        source_url = source_url.strip()
        source_url = re.sub(r'%20$', '', source_url)

        # Use session with retry logic and browser-like headers
        session = _create_session_with_retries(max_retries=3, backoff_factor=1.0)
        resp = session.get(source_url, headers=RSS_REQUEST_HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"RSS fetch error: {e}")

    feed = feedparser.parse(resp.content)
    logger.info(f"Number of entries in feed: {len(feed.entries)}")
    # Debug: Save to files for inspection
    save_feed_debug(resp, feed, output_dir="output")    
    new_items = []
    for entry in feed.entries:
        # Parse published date, fallback if not present
        published_str = getattr(entry, "published", None) or getattr(entry, "updated", None)
        #logger.info(f"published str is: {published_str}")
        pub_date = None
        if published_str:
            try:
                pub_struct = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
                if pub_struct:
                    pub_date = datetime.fromtimestamp(time.mktime(pub_struct), tz=timezone.utc)
            except Exception as err:
                logger.warning(f"Failed to parse pub_date for entry: {err}")
                pub_date = None

        aware_pub_date = ensure_aware(pub_date)
        aware_last_synced = ensure_aware(last_synced)
        #logger.info(f"Aware last synced is: {aware_last_synced}")
        # Only include new items if last_synced is set
        if aware_last_synced and aware_pub_date and aware_pub_date <= aware_last_synced:
            continue
        summary_raw = get_best_summary(entry)
        summary = get_final_summary(summary_raw, llm_service.summarize_article)
        new_items.append({
            "title": entry.title,
            "summary": summary,
            "link": entry.link,
            "published": aware_pub_date,
            "guid": getattr(entry, "id", entry.link)
        })

        if len(new_items) >= limit:
            break
        
    return new_items

def save_feed_debug(resp, feed, output_dir="output"):
    """
    Save the raw RSS response and parsed feed entries to uniquely named files in the output directory.
    Args:
        resp: requests.Response object (has .content)
        feed: parsed feedparser object (has .entries)
        output_dir: directory where files will be saved
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Unique identifier for filenames
    uniq = uuid.uuid4().hex[:8]

    # Save raw XML
    raw_filename = os.path.join(output_dir, f"rss_raw_{uniq}.xml")
    with open(raw_filename, "wb") as f:
        f.write(resp.content)
    print("Raw feed written to:", raw_filename)

    # Save parsed JSON
    parsed_filename = os.path.join(output_dir, f"rss_parsed_{uniq}.json")
    with open(parsed_filename, "w", encoding="utf-8") as f:
        json.dump([dict(entry) for entry in feed.entries], f, indent=2, default=str)
    print("Parsed feed written to:", parsed_filename)


def get_best_summary(entry):
    # Try these fields in order of preference
    fields = ["summary", "description", "content", "content_encoded"]
    for field in fields:
        val = getattr(entry, field, None)
        # Handle feedparser's .content (often a list of dicts)
        if field == "content" and isinstance(val, list) and len(val) > 0:
            val = val[0].get("value", "")
        if val:
            cleaned = clean_html(val)
            if len(cleaned) > 30:
                return cleaned
    # Fallback to title if long enough
    title = getattr(entry, "title", None)
    if title:
        cleaned = clean_html(title)
        if len(cleaned) > 10:
            return cleaned
    return None  # No good summary found

def get_final_summary(raw_summary, llm_summarize_func, threshold=400):
    """
    - Cleans HTML from raw_summary.
    - If cleaned summary is long or looks messy, send to LLM.
    - llm_summarize_func(text) is your LLM summarize function.
    """
    cleaned = clean_html(raw_summary)
    # If it's still very long or multi-paragraph, summarize
    if len(cleaned) > threshold or cleaned.count("\n") > 5:
        # Optional: log this for debugging
        print(f"[Info] Summary too long, sending to LLM ({len(cleaned)} chars)")
        return llm_summarize_func(cleaned)
    else:
        return cleaned