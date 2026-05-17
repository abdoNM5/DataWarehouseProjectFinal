"""
Skills Router — GET /api/skills (for frontend autocomplete).
Stats Router — GET /api/stats (for home page dashboard).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.domain.entities import SkillItem, StatsResponse
from api.infrastructure.database import get_db
from api.infrastructure.repositories import PostgresSkillRepository, PostgresStatsRepository
from api.services.stats_service import StatsService

router = APIRouter()


@router.get("/skills", response_model=list[SkillItem])
def list_skills(db: Session = Depends(get_db)):
    """List all skills with categories (for frontend autocomplete)."""
    repo = PostgresSkillRepository(db)
    return repo.list_all()


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    """Summary statistics for the home page dashboard."""
    service = StatsService(stats_repo=PostgresStatsRepository(db))
    return service.get_summary()
