# app/api/endpoints/paid_search.py
from fastapi import APIRouter, Depends, HTTPException,Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from pydantic import BaseModel
from app.services.api_service import API_SOURCE_HANDLERS
from app.services import llm_service
from app import models, database,schemas
from app.dependencies import get_current_user
import logging
from app.schemas import ArticlePaidOut, UpdatePaidArticleRequest
from app.models import PaidArticle
from app.services.web_scrape_service import fetch_or_scrape_summary
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

class SavePaidArticlesRequest(BaseModel):
    articles: list[ArticlePaidOut]

class PaidSearchParams(BaseModel):
    query: str
    providers: List[str]  # e.g., ["tavily", "bing"]
    limit: int = 10
    offset: int = 0

@router.post("/", response_model=List[ArticlePaidOut])
def paid_api_search(
    params: PaidSearchParams,
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user)
):
    results = []
    logger.info(f"INSIDE PAID SEARCH CALL --- 1")
    for provider in params.providers:
        logger.info(f"INSIDE PAID SEARCH CALL --- 2: {provider}")
        handler = API_SOURCE_HANDLERS.get(provider)
        logger.info(f"INSIDE PAID SEARCH CALL --- 3")
        if not handler:
            logger.warning(f"Provider {provider} not supported")
            continue
        try:
            logger.info(f"INSIDE PAID SEARCH CALL --- 4")
            articles = handler(params.query, max_results=params.limit)
            logger.info(f"INSIDE PAID SEARCH CALL --- 5, articles found: {len(articles)}")
            for article in articles:
                # Summarize and score on the fly
                logger.info(f"INSIDE PAID SEARCH CALL --- 6, article title: {article.get('title')}")
                text = article.get("summary") or article.get("content") or article.get("title")
                logger.info(f"INSIDE PAID SEARCH CALL --- 7, text length: {len(text) if text else 0}")
                if text:
                    try:
                        article["summary"] = llm_service.summarize_article(text)
                        article["relevance_score"] = llm_service.score_article(text)
                        article["source"] = provider.capitalize()  # "Tavily or Serp"
                        article["score"] = article.get("score") or article.get("relevance_score") or 0
                        article["url"] = article.get("link")  # for safety
                    except Exception as e:
                        logger.warning(f"LLM error summarizing/scoring article: {e}")
                #results.append(build_article_paid_out(article, user_id=user.id, query=params.query))
                item = build_article_paid_out(article, user_id=user.id, query=params.query)
                item["is_paid"] = True        # NEW: add flag
                results.append(item)
        except Exception as e:
            logger.error(f"Error fetching from {provider}: {e}")

    # Simple pagination slicing (consider merging and sorting for real-world usage)
    logger.info(f"Total articles before pagination: {len(results)}")
    paginated_results = results[params.offset : params.offset + params.limit]
    return paginated_results

@router.post("/save", response_model=list[ArticlePaidOut])
def save_paid_articles(
    req: SavePaidArticlesRequest,
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user)
):
    saved = []
    for art in req.articles:
        # Check if already saved
        obj = db.query(PaidArticle).filter_by(link=art.link, user_id=user.id).first()
        if not obj:
            obj = PaidArticle(
                user_id=user.id,
                title=art.title,
                summary=art.summary,
                content=art.content,
                link=art.link,
                source=art.source,
                score=art.score,
                meta_data=art.meta_data,
                query=art.query,
                saved_at=datetime.utcnow()
            )
            db.add(obj)
            db.commit()        # <-- commit right after adding (get autoinc ID)
            db.refresh(obj)    # <-- get auto-incremented id
            
        saved.append(obj)
        logger.info(f"Saved or fetched article: {obj.id}, {obj.link}, {obj.title}")
    
    # Convert to pydantic output model + mark as paid
    out = []
    for a in saved:
        base = ArticlePaidOut.from_orm(a).dict()
        base["is_paid"] = True          # NEW: add flag
        out.append(base)
    return out


@router.get("/saved", response_model=list[ArticlePaidOut])
def get_saved_paid_articles(
    query: Optional[str] = None,
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user)
):
    # If query present, do a semantic (or fallback substring) search
    logger.info(f"GET /saved for user_id={user.id} query={query!r}")
    q = db.query(PaidArticle).filter(PaidArticle.user_id == user.id)
    print("Rows before query:", q.count())
    if query:
        q = q.filter(
            PaidArticle.title.ilike(f"%{query}%") |
            PaidArticle.summary.ilike(f"%{query}%")
        )
        logger.info("Rows after query filter: %d", q.count())
    rows = q.order_by(PaidArticle.saved_at.desc()).all()
    # Ensure flag in output
    out = []
    for a in rows:
        base = ArticlePaidOut.from_orm(a).dict()
        base["is_paid"] = True          # NEW: add flag
        out.append(base)
    return out
    #return q.order_by(PaidArticle.saved_at.desc()).all()


@router.patch("/paid_articles/{id}")
def update_paid_article(
    id: int, 
    payload: UpdatePaidArticleRequest, 
    db: Session = Depends(database.get_db), 
    user=Depends(get_current_user)):
    
    logger.info(f"PATCH paid_articles/{id} called by user_id={user.id}")
    logger.info(f"Payload received: {payload}")
    article = db.query(models.PaidArticle).filter_by(id=id, user_id=user.id).first()
    logger.info(f"Article found: {article}")
    if not article:
        print("Article not found or not owned by user")
        raise HTTPException(404, "Not found")
    # Use getattr to check for None so we don't overwrite with None
    if payload.status is not None:
        print(f"Updating status to: {payload.status}")
        article.status = payload.status
    if payload.category is not None:
        print(f"Updating category to: {payload.category}")
        article.category = payload.category
    db.commit()
    db.refresh(article)
    print(f"Article after update: status={article.status}, category={article.category}")
    base = ArticlePaidOut.from_orm(article).dict()
    base["is_paid"] = True              # NEW: add flag
    return base
    #return ArticlePaidOut.from_orm(article)

def build_article_paid_out(article: dict, user_id=None, query=None) -> dict:
    return {
        "id": article.get("id"),
        "user_id": article.get("user_id", user_id),
        "title": article.get("title"),
        "summary": article.get("summary", ""),
        "content": article.get("content", ""),
        "link": article.get("link"),
        "source": article.get("source"),
        "score": article.get("score"),
        "meta_data": article.get("meta_data"),
        "saved_at": article.get("saved_at"),
        "query": article.get("query", query),
        "relevance_score": article.get("relevance_score"),
        "is_paid":True,
    }

@router.post("/fulltext")
def get_paid_article_fulltext_post(
    data: dict = Body(...),
    db: Session = Depends(database.get_db)
):
    url = data.get("url")
    summary = data.get("summary", "")
    text = fetch_or_scrape_summary(db, url, summary)
    return {"url": url, "full_text": text}