"""
Compatibility module that exposes Pydantic schemas at api.schemas.
Canonical definitions remain in api.domain.entities.
"""

from api.domain.entities import (
    OfferDetail,
    OfferResult,
    OfferSummary,
    RecommendRequest,
    RecommendResponse,
    SkillItem,
    StatsResponse,
)

__all__ = [
    "RecommendRequest",
    "OfferResult",
    "RecommendResponse",
    "OfferDetail",
    "OfferSummary",
    "SkillItem",
    "StatsResponse",
]
