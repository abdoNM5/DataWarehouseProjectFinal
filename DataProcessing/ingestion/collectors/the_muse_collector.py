"""Collector for The Muse public jobs API."""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Any, Dict, Iterable, List
from urllib.parse import quote_plus

import requests

from .base_collector import Collector


DEFAULT_QUERIES = [
    "Data Engineer",
    "Data Scientist",
    "Data Analyst",
    "Business Analyst",
    "Machine Learning Engineer",
]

DEFAULT_LOCATIONS = [
    "New York, NY",
    "San Francisco, CA",
    "London, United Kingdom",
    "Berlin, Germany",
    "Paris, France",
    "Remote",
]


def _parse_csv_env(name: str, fallback: List[str]) -> List[str]:
    raw = os.getenv(name, "")
    if not raw.strip():
        return fallback
    return [part.strip() for part in raw.split(",") if part.strip()]


class TheMuseCollector(Collector):
    source = "the_muse"

    def __init__(self, *, query: str | None = None, location: str | None = None, pages: int = 12, since=None, client_factory=None) -> None:
        super().__init__(since=since, client_factory=client_factory)
        base_queries = [query] if query else DEFAULT_QUERIES
        base_locations = [location] if location else DEFAULT_LOCATIONS
        self.queries = _parse_csv_env("SCRAPE_QUERIES", base_queries)
        self.locations = _parse_csv_env("SCRAPE_LOCATIONS", base_locations)
        self.pages = int(os.getenv("THE_MUSE_PAGES", os.getenv("SCRAPE_PAGES", str(pages))))
        self.max_records = int(os.getenv("MAX_RECORDS_PER_SOURCE", "2500"))

    def fetch(self) -> Iterable[Dict[str, Any]]:
        jobs: List[Dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        try:
            for query in self.queries:
                for location in self.locations:
                    for page in range(1, self.pages + 1):
                        url = (
                            "https://www.themuse.com/api/public/jobs?"
                            f"page={page}&descending=true&location={quote_plus(location)}"
                        )
                        response = requests.get(url, timeout=30)
                        if response.status_code != 200:
                            continue
                        payload = response.json()
                        results = payload.get("results", [])
                        if not results:
                            break

                        for item in results:
                            locations = item.get("locations") or []
                            categories = item.get("categories") or []
                            levels = item.get("levels") or []
                            title = item.get("name", "N/A")
                            company = (item.get("company") or {}).get("name", "N/A")
                            loc = ", ".join(
                                [loc_item.get("name", "") for loc_item in locations if isinstance(loc_item, dict)]
                            ) or location
                            key = (title.lower(), company.lower(), loc.lower())
                            if key in seen:
                                continue
                            seen.add(key)

                            jobs.append(
                                {
                                    "job_id": str(item.get("id") or uuid.uuid4()),
                                    "title_raw": title,
                                    "title_standard": title,
                                    "company_name": company,
                                    "location_raw": loc,
                                    "location_norm": None,
                                    "employment_type": levels[0].get("name") if levels else None,
                                    "salary_min": None,
                                    "salary_max": None,
                                    "currency": "EUR",
                                    "description": item.get("contents", "")[:1000],
                                    "skills": [cat.get("name") for cat in categories if isinstance(cat, dict) and cat.get("name")],
                                    "posted_at": item.get("publication_date"),
                                    "ingestion_ts": datetime.utcnow().isoformat(),
                                }
                            )
                            if len(jobs) >= self.max_records:
                                return jobs
        except requests.RequestException:
            return jobs if jobs else self._mock_jobs()

        return jobs or self._mock_jobs()

    def _mock_jobs(self) -> List[Dict[str, Any]]:
        return [
            {
                "job_id": str(uuid.uuid4()),
                "title_raw": f"{self.queries[0]} Specialist",
                "title_standard": f"{self.queries[0]} Specialist",
                "company_name": "The Muse Mock Co",
                "location_raw": self.locations[0],
                "location_norm": None,
                "employment_type": None,
                "salary_min": None,
                "salary_max": None,
                "currency": "EUR",
                "description": "Fallback mock from The Muse collector",
                "skills": ["Data Analysis"],
                "posted_at": None,
                "ingestion_ts": datetime.utcnow().isoformat(),
            }
        ]
