from pydantic import BaseModel, Field, HttpUrl
from typing import Optional,List, Dict
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class SourceBase(BaseModel):
    name: str
    type: str
    url: Optional[str] = None
    active: Optional[bool] = True
    provider: Optional[str] = None    
    query: Optional[str] = None       

class SourceCreate(SourceBase):
    pass

class SourceUpdate(BaseModel):
    name: Optional[str]
    url: Optional[str]
    active: Optional[bool]
    provider: Optional[str] = None
    query: Optional[str] = None

class SourceOut(SourceBase):
    id: int
    file_path: Optional[str]
    file_id: Optional[int]
    active: bool
    last_synced: Optional[datetime] 
    created_at: Optional[datetime] 

    class Config:
        from_attributes = True
        orm_mode = True

class ArticleBase(BaseModel):
    title: str
    summary: Optional[str] = None
    key_insights: Optional[List[str]] = []
    content: Optional[str] = None
    date: Optional[datetime] = None
    status: Optional[str] = "new"
    tags: Optional[List[str]] = Field(default_factory=list)
    meta_data: Optional[Dict] = Field(default_factory=dict)
    note: Optional[str] = None
    relevance_score: Optional[int] = 0
    is_archived: Optional[bool] = False
    

class ArticleCreate(ArticleBase):
    source_id: Optional[int] = None

class ArticleUpdate(BaseModel):
    title: Optional[str]
    summary: Optional[str]
    content: Optional[str]
    status: Optional[str]
    tags: Optional[List[str]]
    meta_data: Optional[Dict]
    note: Optional[str]
    relevance_score: Optional[int]
    is_archived: Optional[bool]

class ArticleOut(ArticleBase):
    id: int
    user_id: int
    source_id: Optional[int]
    source_name: Optional[str] = None  
    relevance_score: int = 0
    category: str = ""
    source_name: Optional[str]  
    is_paid: bool = False 
    class Config:
        from_attributes = True
        orm_mode = True

class FileBase(BaseModel):
    filename: str

class FileOut(FileBase):
    id: int
    hash: str
    upload_date: datetime
    status: str

    class Config:
        from_attributes = True
        orm_mode = True

# Deep insights endpoint schema
class ArticleDeepInsights(BaseModel):
    summary: str
    key_insights: List[str]
    full_text: str



class ArticlePaidOut(BaseModel):
    id: Optional[int]
    user_id: Optional[int]
    title: str
    summary: Optional[str] = ""
    content: Optional[str] = ""
    link: Optional[str]
    source: Optional[str]
    score: Optional[float]
    meta_data: Optional[Dict] = None
    saved_at: Optional[datetime] = None
    query: Optional[str] = None
    relevance_score: Optional[float] = None
    status: Optional[str] = "new"
    category: Optional[str] = "uncategorized"
    is_paid: bool = True
    
    class Config:
        orm_mode = True 
        from_attributes = True 


class UpdatePaidArticleRequest(BaseModel):
    status: Optional[str] = None
    category: Optional[str] = None


class ArticleFullTextBase(BaseModel):
    url: HttpUrl
    title: Optional[str] = None
    notes: Optional[str] = None
    infographic_url: Optional[HttpUrl] = None
    summary: Optional[str] = None  

class ArticleFullTextCreate(ArticleFullTextBase):
    full_text: Optional[str] = None

class ArticleFullTextOut(ArticleFullTextBase):
    id: int
    full_text: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True