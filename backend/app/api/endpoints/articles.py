# app/api/endpoints/articles.py
from fastapi import APIRouter, Depends, HTTPException, status,Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app import models, schemas, database
from app.dependencies import get_current_user
from sqlalchemy import func 
import logging
from datetime import datetime
from sqlalchemy.orm import joinedload

from app.services.web_scrape_service import get_full_text, fetch_or_scrape_summary
from app.services.llm_service import key_insights, deep_insights_from_content

logger = logging.getLogger(__name__)

router = APIRouter()

# app/api/endpoints/articles.py (add near top, below imports)



@router.get("/", response_model=List[schemas.ArticleOut])
def list_articles(
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user),
    status: str = None,
    source_id: int = None,
    search: str = None,
    category: str = None,
    from_date: str = None,
    limit: int = 10,
    offset: int = 0,
    score: int = None,
    source_name: str = None,
    
):
    q = db.query(models.Article).filter(models.Article.user_id == user.id)
    if status:
        q = q.filter(models.Article.status == status)
    if source_id:
        q = q.filter(models.Article.source_id == source_id)
    if search:
        q = q.filter(models.Article.title.ilike(f"%{search}%"))
    if category and category != "all":
        # Case-insensitive match
        q = q.filter(func.lower(models.Article.category) == category.lower())
    if score is not None:
        # Handle range filters (e.g., "80-89" or single value "80")
        if isinstance(score, str) and "-" in score:
            min_score, max_score = map(int, score.split("-"))
            q = q.filter(
                models.Article.relevance_score >= min_score,
                models.Article.relevance_score <= max_score
            )
        else:
            # Backward compatibility: single value means >= that score
            q = q.filter(models.Article.relevance_score >= int(score))
    if source_name and source_name != "all":
        q = q.join(models.Source).filter(models.Source.name == source_name)
    logger.info(f"from_date filter is:{from_date}")
    if from_date and isinstance(from_date, str):       
        dt = datetime.fromisoformat(from_date)
        q = q.filter(models.Article.date >= dt)  
    total_count = q.count() 
    #articles = q.order_by(models.Article.date.desc()).offset(offset).limit(limit).all() 
    
    articles = (
        q.options(joinedload(models.Article.source))  # Eager load source relationship
        .order_by(models.Article.date.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    # Serialize manually to add `source_name`
    result = []
    for art in articles:
        base = schemas.ArticleOut.from_orm(art).dict()
        base["source_name"] = art.source.name if art.source else None
        base["is_paid"] = False 
        result.append(base)
    return result

@router.post("/", response_model=schemas.ArticleOut)
def create_article(
    article: schemas.ArticleCreate,
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user)
):
    db_article = models.Article(**article.dict(), user_id=user.id)
    db.add(db_article)
    db.commit()
    db.refresh(db_article)
    base = schemas.ArticleOut.from_orm(db_article).dict()
    base["source_name"] = db_article.source.name if db_article.source else None
    base["is_paid"] = False   # <-- ADD THIS
    return base    

    #return db_article

@router.get("/{article_id}", response_model=schemas.ArticleOut)
def get_article(article_id: int, db: Session = Depends(database.get_db), user=Depends(get_current_user)):
    article = db.query(models.Article).filter(models.Article.id == article_id, models.Article.user_id == user.id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    base = schemas.ArticleOut.from_orm(article).dict()
    base["source_name"] = article.source.name if article.source else None
    base["is_paid"] = False   # <-- ADD THIS
    return base
    #return article

@router.put("/{article_id}", response_model=schemas.ArticleOut)
def update_article(
    article_id: int,
    article: schemas.ArticleUpdate,
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user)
):
    db_article = db.query(models.Article).filter(models.Article.id == article_id, models.Article.user_id == user.id).first()
    if not db_article:
        raise HTTPException(status_code=404, detail="Article not found")
    for key, value in article.dict(exclude_unset=True).items():
        setattr(db_article, key, value)
    db.commit()
    db.refresh(db_article)

    base = schemas.ArticleOut.from_orm(db_article).dict()
    base["source_name"] = db_article.source.name if db_article.source else None
    base["is_paid"] = False   # <-- ADD THIS
    return base
    #return db_article

@router.delete("/{article_id}", response_model=dict)
def delete_article(article_id: int, db: Session = Depends(database.get_db), user=Depends(get_current_user)):
    article = db.query(models.Article).filter(models.Article.id == article_id, models.Article.user_id == user.id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    db.delete(article)
    db.commit()
    return {"ok": True}

@router.patch("/{article_id}/status", response_model=schemas.ArticleOut)
def update_status(article_id: int, status: str, db: Session = Depends(database.get_db), user=Depends(get_current_user)):
    article = db.query(models.Article).filter(models.Article.id == article_id, models.Article.user_id == user.id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    article.status = status
    db.commit()
    db.refresh(article)
    base = schemas.ArticleOut.from_orm(article).dict()
    base["source_name"] = article.source.name if article.source else None
    base["is_paid"] = False   # <-- ADD THIS
    return base
    #return article

@router.patch("/{article_id}/note", response_model=schemas.ArticleOut)
def update_note(article_id: int, note: str, db: Session = Depends(database.get_db), user=Depends(get_current_user)):
    article = db.query(models.Article).filter(models.Article.id == article_id, models.Article.user_id == user.id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    article.note = note
    db.commit()
    db.refresh(article)
    base = schemas.ArticleOut.from_orm(article).dict()
    base["source_name"] = article.source.name if article.source else None
    base["is_paid"] = False   # <-- ADD THIS
    return base
    #return article

# app/api/endpoints/articles.py


@router.post("/{article_id}/deep_insights", response_model=schemas.ArticleDeepInsights)
def deep_insights(
    article_id: int,
    db: Session = Depends(database.get_db),
    user=Depends(get_current_user)
):
    article = db.query(models.Article).filter(
        models.Article.id == article_id,
        models.Article.user_id == user.id
    ).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    url = (getattr(article, "meta_data", {}) or {}).get("link")
    if not url:
        raise HTTPException(status_code=400, detail="No link found in article meta_data")

    # Scrape full text (trafilatura/newspaper3k)
    full_text = get_full_text(url)
    if not full_text:
        raise HTTPException(status_code=400, detail="Unable to scrape article: site may have blocked automated access.")

    # Use unified deep insights function
    result = deep_insights_from_content(full_text[:4000])

    return schemas.ArticleDeepInsights(
        summary=result["summary"],
        key_insights=result["takeaways"],
        full_text=full_text
    )


@router.post("/fulltext")
def get_article_fulltext_post(
    data: dict = Body(...),
    db: Session = Depends(database.get_db)
):
    url = data.get("url")
    summary = data.get("summary", "")
    text = fetch_or_scrape_summary(db, url, summary)
    return {"url": url, "full_text": text}

