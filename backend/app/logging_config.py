# app/logging_config.py
import logging
import sys
import os
from app.core.config import LOG_LEVEL

def setup_logging():
    log_level = LOG_LEVEL
    handlers = [logging.StreamHandler(sys.stdout)]
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )
    # Optional: suppress noisy logs from 3rd-party libs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
