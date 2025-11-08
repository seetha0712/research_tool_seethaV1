# app/services/web_scrape_service.py

import requests
import trafilatura
import logging
from app.models import ArticleFullText  
from app.services.llm_service import key_insights, deep_insights_from_content

logger = logging.getLogger(__name__)

def get_full_text(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://google.com"
    }
    try:
        #resp = requests.get(url, headers=headers, timeout=10)
        #resp.raise_for_status()
        #downloaded = resp.text
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
            return text or ""
    except Exception as e:
        print(f"[Scrape Error] {url}: {e}")
    return ""


def fetch_or_scrape_summary(session, url: str, summary: str = None):
    logger.info(f"Fetching summary for URL: {url}")

    # 1. Check if entry exists in DB
    article_text = session.query(ArticleFullText).filter_by(url=url).first()

    if article_text:
        logger.info("Article found in database.")

        if article_text.full_text:
            logger.info("Full text is available in database.")

            # Generate summary if missing
            if not getattr(article_text, 'summary', None) or not article_text.summary.strip():
                logger.info("Summary missing or empty. Generating summary using LLM...")
                try:
                    summary_llm = deep_insights_from_content(article_text.full_text)
                    summary_text = summary_llm["summary"] if isinstance(summary_llm, dict) else str(summary_llm)
                    article_text.summary = summary_text
                    session.commit()
                    logger.info("Summary generated and committed to DB.")
                except Exception as e:
                    logger.error(f"Failed to generate summary via LLM: {e}")
                    article_text.summary = summary or ""
                    session.commit()

        else:
            logger.warning("Full text not found in DB.")

        # ✅ Always return summary from DB or fallback
        return article_text.summary or (summary or "")

    # 2. Not in DB: Try to scrape
    logger.info("Article not found in DB. Scraping full text...")
    try:
        scraped = get_full_text(url)
    except Exception as e:
        logger.error(f"Exception during scraping for URL {url}: {e}")
        scraped = None

    if scraped:
        logger.info("Successfully scraped full text. Generating summary...")
        try:
            summary_llm = deep_insights_from_content(scraped)
            summary_text = summary_llm["summary"] if isinstance(summary_llm, dict) else str(summary_llm)
        except Exception as e:
            logger.error(f"Failed to generate summary from scraped content: {e}")
            summary_text = summary or ""
        article_text = ArticleFullText(url=url, full_text=scraped, summary=summary_text)
        session.add(article_text)
        session.commit()
        logger.info("Scraped data and summary saved to DB.")
        return summary_text

    # 3. Scraping failed (empty or exception): Add fallback DB entry
    logger.warning(f"Failed to fetch or scrape full text for {url}. Logging fallback summary to DB.")
    article_text = ArticleFullText(url=url, full_text="", summary=summary or "")
    session.add(article_text)
    session.commit()
    logger.info("Fallback summary saved to DB.")
    return summary or ""