"""Backend-specific configuration. Reuses project settings."""
import os

from backend.core.settings import OUTPUT_DIR

# Server
HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
PORT = int(os.getenv("BACKEND_PORT", "8000"))

# CORS allowed origins (comma-separated)
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if o.strip()
]

# Page count bounds
MIN_PAGE_COUNT = 1
MAX_PAGE_COUNT = 10

__all__ = [
    "HOST", "PORT", "CORS_ORIGINS",
    "MIN_PAGE_COUNT", "MAX_PAGE_COUNT", "OUTPUT_DIR",
]
