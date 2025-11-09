import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Security Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-very-secure-secret-change-this")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# API Keys - Load from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
SERP_API_KEY = os.getenv("SERP_API_KEY", "")
SLIDESGPT_API_KEY = os.getenv("SLIDESGPT_API_KEY", "")

# Application Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
BACKEND_BASE = os.getenv("BACKEND_BASE", "http://localhost:8000")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# CORS Origins - Can be comma-separated list
CORS_ORIGINS_STR = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,https://research-tool-seetha-v1.vercel.app"
)
CORS_ORIGINS_LIST = [origin.strip() for origin in CORS_ORIGINS_STR.split(",")]

# --------- Category options (backend default display names) ----------
CATEGORY_OPTIONS = [
    "AI & GenAI Trends",
    "AI in Financial Institutions",
    "Leading AI Innovators",
    "Agentic AI",
    "Broader AI Topics",
    "Tech Corner",
    "AI Beyond Finance",
    "Uncategorized",
]