"""
Recommend Router — POST /api/recommend endpoint.
Thin controller: validates input, delegates to service, formats output.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.domain.entities import RecommendRequest, RecommendResponse
from api.infrastructure.database import get_db
from api.infrastructure.repositories import PostgresOfferRepository, PostgresSkillRepository
from api.services.recommendation_service import RecommendationService
from api.config import settings

router = APIRouter()


def _get_service(db: Session = Depends(get_db)) -> RecommendationService:
    """Dependency injection: wire concrete repos into the service."""
    return RecommendationService(
        offer_repo=PostgresOfferRepository(db),
        skill_repo=PostgresSkillRepository(db),
    )


@router.post("/recommend", response_model=RecommendResponse)
def get_recommendations(
    req: RecommendRequest,
    service: RecommendationService = Depends(_get_service),
):
    """
    Generate job recommendations based on a candidate profile.

    - **description**: Free-text describing your ideal role
    - **skills**: List of your skill names
    - **top_k**: Number of results to return (default 10)
    """
    result = service.recommend(
        description=req.description,
        skills=req.skills,
        top_k=req.top_k,
        alpha=settings.DEFAULT_ALPHA,
    )
    return result
