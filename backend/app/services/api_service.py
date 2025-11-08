import requests
from datetime import datetime
import os
from app.core.config import TAVILY_API_KEY, SERP_API_KEY
# For security, use an environment variable for your API key!
#TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")  # set this in your shell/.env file
import logging
logger = logging.getLogger(__name__)

def fetch_tavily_articles(query: str, max_results=10) -> list:
    """
    Fetches articles from Tavily API based on a search query.
    Returns: List of dicts with keys: title, summary, content, link, published, guid, meta_data
    """
    if not TAVILY_API_KEY:
        raise RuntimeError("TAVILY_API_KEY is not set as environment variable.")
    url = "https://api.tavily.com/search"
    headers = {
        "Authorization": f"Bearer {TAVILY_API_KEY}",
        "Content-Type": "application/json"
    }
    json_data = {"query": query, "num_results": max_results}

    try:
        resp = requests.post(url, headers=headers, json=json_data, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", []) 
        logger.info(f" \n\n ******* OUTPUT FROM TAVILY SEARCH IS *********\n\n{data}")
    except Exception as e:
        raise RuntimeError(f"Tavily API error: {e}")

    articles = []
    for item in results:
        articles.append({
            "title": item.get("title"),
            "summary": item.get("content") or item.get("description") or "",
            "content": item.get("content") or "",
            "link": item.get("url"),
            "published": None,
            "guid": item.get("url"),
            "meta_data": item,
        })
    return articles

def fetch_serpapi_articles(query: str, max_results=10) -> list:
    """
    Fetches articles from SERP API (Google Search API) based on a search query.
    Returns: List of dicts with keys: title, summary, content, link, published, guid, meta_data
    """
    if not SERP_API_KEY:
        raise RuntimeError("SERPAPI_KEY is not set as environment variable.")
    url = "https://serpapi.com/search"
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERP_API_KEY,
        "num": max_results,
        "hl": "en",
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        logger.info(f" \n\n ++++++++++ OUTPUT FROM SERP SEARCH IS ++++++++ n\n{data}")
    except Exception as e:
        raise RuntimeError(f"SERP API error: {e}")

    articles = []
    # This part depends on the structure SERP API returns.
    # Here we assume 'organic_results' as main result list
    for item in data.get("organic_results", []):
        articles.append({
            "title": item.get("title"),
            "summary": item.get("snippet") or "",
            "content": item.get("snippet") or "",
            "link": item.get("link"),
            "published": None,
            "guid": item.get("link"),
            "meta_data": item,
            "source": "SERPAPI"
        })
    return articles

# Registry to add more API providers easily in future
API_SOURCE_HANDLERS = {
    "tavily": fetch_tavily_articles,
    "serpapi": fetch_serpapi_articles,
    # "bing": fetch_bing_articles,  # Example for future expansion
    # "my_custom_api": fetch_custom_articles,
}