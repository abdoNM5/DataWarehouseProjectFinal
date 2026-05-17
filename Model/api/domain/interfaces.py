"""
Domain Interfaces — abstract repository contracts.
Services depend on these interfaces, NOT on concrete implementations.
This is the core of clean architecture: dependency inversion.
"""

from abc import ABC, abstractmethod


class OfferRepository(ABC):
    """Contract for accessing job offer data."""

    @abstractmethod
    def get_total_count(self) -> int:
        """Return total number of offers in the warehouse."""

    @abstractmethod
    def get_offer_by_id(self, offer_id: int) -> dict | None:
        """Return full offer details or None if not found."""

    @abstractmethod
    def list_offers(self, city: str | None, job_family: str | None,
                    skill: str | None, limit: int, offset: int) -> list[dict]:
        """Return a filtered, paginated list of offers."""

    @abstractmethod
    def get_all_with_embeddings(self) -> tuple[list[dict], list]:
        """Return (offer_metadata_list, embeddings_list) for all embedded offers."""


class SkillRepository(ABC):
    """Contract for accessing skill data."""

    @abstractmethod
    def list_all(self) -> list[dict]:
        """Return all skills with their categories."""

    @abstractmethod
    def get_offer_skills(self) -> dict:
        """Return {offer_id: set(skill_names)} for all offers."""

    @abstractmethod
    def get_skills_for_offer(self, offer_id: int) -> list[dict]:
        """Return skills for a specific offer."""


class StatsRepository(ABC):
    """Contract for accessing aggregate statistics."""

    @abstractmethod
    def get_summary(self) -> dict:
        """Return summary stats: total offers, companies, cities, top skills."""
