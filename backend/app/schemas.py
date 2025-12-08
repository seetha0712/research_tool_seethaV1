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

class FileBase(BaseModel):
    filename: str

class FileOut(FileBase):
    id: int
    hash: str
    upload_date: datetime
    status: str

    class Config:
        from_attributes = True

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


# ==================== Sync History Schemas ====================

class SourceSyncBreakdown(BaseModel):
    """Breakdown of articles synced from a single source."""
    source_id: int
    source_name: str
    source_type: str
    count: int
    avg_score: float
    categories: Dict[str, int]  # {"AI & GenAI Trends": 3, "Tech Corner": 2}


class SyncError(BaseModel):
    """Error that occurred during sync for a specific source."""
    source_id: Optional[int] = None
    source_name: str
    error: str


class SyncHistoryOut(BaseModel):
    """Output schema for sync history records."""
    id: int
    user_id: int
    sync_timestamp: datetime
    total_articles_fetched: int
    total_sources_synced: int
    total_errors: int
    duration_seconds: Optional[float] = None
    sources_breakdown: List[Dict]
    categories_breakdown: Dict[str, int]
    scores_breakdown: Dict[str, int]  # {"high": 10, "medium": 3, "low": 2}
    errors: List[Dict]
    sync_params: Dict

    class Config:
        from_attributes = True


class SyncResultOut(BaseModel):
    """Enhanced sync response with detailed breakdown."""
    sync_id: int
    synced: List[str]  # List of article titles (for backwards compatibility)
    count: int
    total_articles_fetched: int
    duration_seconds: float
    by_source: List[Dict]
    by_category: Dict[str, int]
    by_score_tier: Dict[str, int]  # {"high (70+)": N, "medium (40-69)": N, "low (<40)": N}
    errors: List[Dict]


class SourceAnalytics(BaseModel):
    """Analytics for a single source."""
    source_id: int
    source_name: str
    source_type: str
    total_articles: int
    avg_score: float
    high_score_percentage: float  # % of articles with score >= 70
    top_categories: List[Dict]  # [{"category": "AI & GenAI Trends", "count": 10}]
    last_synced: Optional[datetime] = None
    articles_last_30_days: int


class SourceAnalyticsResponse(BaseModel):
    """Response for source analytics endpoint."""
    sources: List[SourceAnalytics]
    overall_stats: Dict  # {"total_articles": N, "avg_score": N, "total_syncs": N}