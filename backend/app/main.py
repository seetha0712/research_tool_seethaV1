from fastapi import FastAPI
from app.api.endpoints import (auth, users, sources, articles, files, sync,paid_search,
    dashboard, slidesgpt_proxy,deck_builder)

from app.database import init_db
from fastapi.middleware.cors import CORSMiddleware
from app.logging_config import setup_logging
from fastapi.staticfiles import StaticFiles
from app.core.config import CORS_ORIGINS_LIST, ENVIRONMENT
import os

setup_logging()

import logging
logger = logging.getLogger(__name__)

app = FastAPI(
    title="GenAI Research Tool API",
    description="API backend for GenAI Research Tool",
    version="1.0.0"
)

# Load CORS origins from config (environment-aware)
origins = CORS_ORIGINS_LIST

logger.info(f"Starting application in {ENVIRONMENT} mode")
logger.info(f"CORS origins: {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ... after app creation, before include_router:
os.makedirs("static/decks", exist_ok=True)   # NEW
app.mount("/static", StaticFiles(directory="static"), name="static")  # NEW

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(sources.router, prefix="/sources", tags=["Sources"])
app.include_router(articles.router, prefix="/articles", tags=["Articles"])
app.include_router(files.router, prefix="/files", tags=["Files"])
app.include_router(sync.router, prefix="/sync", tags=["Sync"])
app.include_router(paid_search.router, prefix="/paid_search", tags=["paid_search"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(deck_builder.router, tags=["Deck Builder"]) 

#app.include_router(articles.router, prefix="/api/article", tags=["Articles_Full"])
#app.include_router(paid_search.router, prefix="/api/paid_article", tags=["PaidArticles_Full"])

app.include_router(slidesgpt_proxy.router, tags=["SlidesGPT"])

# Health check endpoint
@app.get("/")
def health_check():
    return {"status": "ok", "service": "GenAI Research Tool API"}

# Initialize DB on start
@app.on_event("startup")
def on_startup():
    init_db()