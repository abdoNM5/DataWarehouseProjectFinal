"""
Configuration — centralised settings loaded from environment variables.
"""

import os


class Settings:
    """Application settings. Override via environment variables."""

    APP_TITLE: str = "Job Intelligent API"
    APP_DESCRIPTION: str = "Semantic job recommendation engine powered by NLP"
    APP_VERSION: str = "1.0.0"

    # Database (warehouse-db on Docker)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://warehouse:warehouse@localhost:5433/jobs_dw"
    )

    # CORS (allow both 3000 and 3001 in case one is busy)
    FRONTEND_URLS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
    ]

    # Recommendation defaults
    DEFAULT_TOP_K: int = 10
    DEFAULT_ALPHA: float = 0.6  # semantic weight in hybrid scoring
    MAX_TOP_K: int = 50


settings = Settings()
