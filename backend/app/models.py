from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, Float
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.database import Base

#Base = declarative_base()
import logging
logger = logging.getLogger(__name__)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    sources = relationship("Source", back_populates="user", cascade="all, delete")
    articles = relationship("Article", back_populates="user", cascade="all, delete")

class Source(Base):
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)   # rss, pdf, api
    url = Column(String, nullable=True) # Used for RSS/API feeds
    file_id = Column(Integer, ForeignKey("files.id"), nullable=True)
    file_path = Column(String, nullable=True) # For PDFs
    provider = Column(String, nullable=True)  
    query = Column(String, nullable=True)     
    active = Column(Boolean, default=True)
    last_synced = Column(DateTime, default=None)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="sources")
    articles = relationship("Article", back_populates="source")
    file = relationship("File", back_populates="source") 
    


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    key_insights = Column(JSON, default=[])
    content = Column(Text, nullable=True)
    date = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="new")  # new/reviewed/shortlisted/final
    tags = Column(JSON, default=[])  # List of strings
    meta_data = Column(JSON, default={})  # Extra info, not "metadata"
    note = Column(Text, nullable=True)
    relevance_score = Column(Integer, default=0)
    is_archived = Column(Boolean, default=False)
    category = Column(String, default="")
    embedding = Column(Vector(1536), nullable=True)  # OpenAI text-embedding-3-small dimension

    user = relationship("User", back_populates="articles")
    source = relationship("Source", back_populates="articles")
    
class File(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    filename = Column(String, nullable=False)
    hash = Column(String, unique=True, nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="uploaded")  # e.g., uploaded, processed, etc.
    source = relationship("Source", back_populates="file", uselist=False) 

    user = relationship("User")

class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey('articles.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

class PaidArticle(Base):
    __tablename__ = "paid_articles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    title = Column(String, index=True)
    summary = Column(Text)
    content = Column(Text)
    link = Column(String)
    source = Column(String)   # E.g., "Tavily"
    score = Column(Float)
    meta_data = Column(JSON)
    saved_at = Column(DateTime, server_default=func.now())
    query = Column(String)    # Save the user's query
    status = Column(String, default="new")          
    category = Column(String, default="uncategorized")

class ArticleFullText(Base):
    __tablename__ = "article_full_texts"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(1024), unique=True, nullable=False, index=True)
    full_text = Column(Text, nullable=True)
    summary = Column(Text, nullable=True) 
    title = Column(String(512), nullable=True)
    notes = Column(Text, nullable=True)  # For user notes or detailed notes
    infographic_url = Column(String(1024), nullable=True)  # Optional image/infographic
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())