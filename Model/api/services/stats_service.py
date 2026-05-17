"""
Stats Service — business logic for dashboard summary statistics.
"""

from api.domain.interfaces import StatsRepository


class StatsService:
    """Use case: get aggregate stats for the home page."""

    def __init__(self, stats_repo: StatsRepository):
        self._stats_repo = stats_repo

    def get_summary(self):
        """Return total offers, companies, cities, and top skills."""
        return self._stats_repo.get_summary()
