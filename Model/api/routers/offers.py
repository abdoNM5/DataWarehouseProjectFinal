"""
Offers Router — GET /api/offers and GET /api/offers/{id}.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from api.domain.entities import OfferDetail, OfferSummary
from api.infrastructure.database import get_db
from api.infrastructure.repositories import PostgresOfferRepository, PostgresSkillRepository
from api.services.offer_service import OfferService

router = APIRouter()


def _get_service(db: Session = Depends(get_db)) -> OfferService:
    return OfferService(
        offer_repo=PostgresOfferRepository(db),
        skill_repo=PostgresSkillRepository(db),
    )


@router.get("/offers", response_model=list[OfferSummary])
def list_offers(
    city: str = Query(None, description="Filter by city name"),
    job_family: str = Query(None, description="Filter by job family"),
    skill: str = Query(None, description="Filter by required skill name"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: OfferService = Depends(_get_service),
):
    """Browse and filter job offers with pagination."""
    return service.list_offers(city, job_family, skill, limit, offset)


@router.get("/offers/{offer_id}", response_model=OfferDetail)
def get_offer(
    offer_id: int,
    service: OfferService = Depends(_get_service),
):
    """Get full details for a specific offer, including extracted skills."""
    result = service.get_offer_detail(offer_id)
    if not result:
        raise HTTPException(status_code=404, detail="Offer not found")
    return result
