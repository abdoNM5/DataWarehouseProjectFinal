"""
Offer Service — business logic for browsing and viewing offers.
"""

from api.domain.interfaces import OfferRepository, SkillRepository


class OfferService:
    """Use case: browse, filter, and view job offer details."""

    def __init__(self, offer_repo: OfferRepository, skill_repo: SkillRepository):
        self._offer_repo = offer_repo
        self._skill_repo = skill_repo

    def list_offers(self, city=None, job_family=None, skill=None, limit=50, offset=0):
        """Return a paginated, filtered list of offers."""
        return self._offer_repo.list_offers(city, job_family, skill, limit, offset)

    def get_offer_detail(self, offer_id: int):
        """Return full offer details with extracted skills."""
        offer = self._offer_repo.get_offer_by_id(offer_id)
        if not offer:
            return None
        offer["skills"] = self._skill_repo.get_skills_for_offer(offer_id)
        return offer
