"""
Domain Entities — Pydantic models for request/response validation.
These are pure data objects with no infrastructure dependencies.
"""

from pydantic import BaseModel, Field


# ── Request Models ───────────────────────────────────────────

class RecommendRequest(BaseModel):
    """Candidate profile for generating recommendations."""
    description: str = Field(
        ...,
        min_length=10,
        description="Describe your ideal job, experience, and interests",
        examples=["Data engineer with Python, Spark, and cloud experience"],
    )
    skills: list[str] = Field(
        default=[],
        description="List of your skill names (must match dim_skill)",
        examples=[["Python", "SQL", "Spark", "AWS"]],
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of recommendations to return",
    )


# ── Response Models ──────────────────────────────────────────

class OfferResult(BaseModel):
    """A single recommended offer with scoring breakdown."""
    offer_id: int
    title: str
    job_family: str
    company: str
    city: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    currency: str | None = None
    match_score: float
    semantic_score: float
    skill_score: float
    matched_skills: list[str]
    missing_skills: list[str]


class RecommendResponse(BaseModel):
    """Full recommendation response with metadata."""
    recommendations: list[OfferResult]
    total_offers_searched: int
    processing_time_ms: int


class OfferDetail(BaseModel):
    """Full offer details for the detail page."""
    offer_id: int
    title: str
    job_family: str
    company: str
    city: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    currency: str | None = None
    description: str | None = None
    url: str | None = None
    skills: list[dict]


class OfferSummary(BaseModel):
    """Lightweight offer for list views."""
    offer_id: int
    title: str
    job_family: str
    company: str
    city: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None


class SkillItem(BaseModel):
    """A skill with its category."""
    name: str
    category: str


class StatsResponse(BaseModel):
    """Dashboard summary statistics."""
    total_offers: int
    total_companies: int
    total_cities: int
    top_skills: list[dict]
