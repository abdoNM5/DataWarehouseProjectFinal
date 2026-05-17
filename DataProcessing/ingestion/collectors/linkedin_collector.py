"""LinkedIn web scraper collector (no API key required)."""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Iterable, List
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from .base_collector import Collector


DEFAULT_QUERIES = [
    "Data Engineer",
    "Data Scientist",
    "Data Analyst",
    "Business Analyst",
    "BI Analyst",
    "Machine Learning Engineer",
]

DEFAULT_LOCATIONS = [
    "New York",
    "San Francisco",
    "London",
    "Berlin",
    "Paris",
    "Toronto",
    "Sydney",
    "Tokyo",
    "Remote",
]


def _parse_csv_env(name: str, fallback: List[str]) -> List[str]:
    raw = os.getenv(name, "")
    if not raw.strip():
        return fallback
    return [part.strip() for part in raw.split(",") if part.strip()]


class LinkedInCollector(Collector):
    source = "linkedin"

    def __init__(self, *, query: str | None = None, location: str | None = None, pages: int = 10, since=None, client_factory=None) -> None:
        super().__init__(since=since, client_factory=client_factory)
        base_queries = [query] if query else DEFAULT_QUERIES
        base_locations = [location] if location else DEFAULT_LOCATIONS
        self.queries = _parse_csv_env("SCRAPE_QUERIES", base_queries)
        self.locations = _parse_csv_env("SCRAPE_LOCATIONS", base_locations)
        self.pages = int(os.getenv("LINKEDIN_PAGES", os.getenv("SCRAPE_PAGES", str(pages))))
        self.max_records = int(os.getenv("MAX_RECORDS_PER_SOURCE", "2500"))

    def fetch(self) -> Iterable[Dict[str, Any]]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        jobs: List[Dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        try:
            for query in self.queries:
                for location in self.locations:
                    for page in range(self.pages):
                        url = (
                            "https://www.linkedin.com/jobs/search/?"
                            f"keywords={quote_plus(query)}&location={quote_plus(location)}&start={page * 25}"
                        )
                        response = requests.get(url, headers=headers, timeout=30)
                        if response.status_code != 200:
                            time.sleep(2)
                            continue
                        soup = BeautifulSoup(response.text, "html.parser")
                        cards = soup.find_all("div", class_="base-card")

                        for card in cards:
                            title_elem = card.find("h3", class_="base-search-card__title")
                            company_elem = card.find("h4", class_="base-search-card__subtitle")
                            location_elem = card.find("span", class_="job-search-card__location")
                            title = title_elem.get_text(strip=True) if title_elem else "N/A"
                            company = company_elem.get_text(strip=True) if company_elem else "N/A"
                            loc = location_elem.get_text(strip=True) if location_elem else location
                            key = (title.lower(), company.lower(), loc.lower())
                            if key in seen:
                                continue
                            seen.add(key)

                            jobs.append(
                                {
                                    "job_id": str(uuid.uuid4()),
                                    "title_raw": title,
                                    "title_standard": title,
                                    "company_name": company,
                                    "location_raw": loc,
                                    "location_norm": None,
                                    "employment_type": None,
                                    "salary_min": None,
                                    "salary_max": None,
                                    "currency": "EUR",
                                    "description": "Description not available on listing page",
                                    "skills": [],
                                    "posted_at": None,
                                    "ingestion_ts": datetime.utcnow().isoformat(),
                                }
                            )
                            if len(jobs) >= self.max_records:
                                return jobs
                        time.sleep(1.2)
        except requests.RequestException:
            return jobs if jobs else self._mock_jobs()

        if not jobs:
            return self._mock_jobs()
        return jobs

    def _mock_jobs(self) -> List[Dict[str, Any]]:
        companies = ["AnalyticsGroup", "BizData", "NeoTech", "ScaleUp Inc", "BankCorp"]
        items: List[Dict[str, Any]] = []
        for idx, company in enumerate(companies):
            items.append(
                {
                    "job_id": str(uuid.uuid4()),
                    "title_raw": self.queries[0],
                    "title_standard": self.queries[0],
                    "company_name": company,
                    "location_raw": self.locations[0],
                    "location_norm": None,
                    "employment_type": None,
                    "salary_min": None,
                    "salary_max": None,
                    "currency": "EUR",
                    "description": f"Mock LinkedIn job {idx + 1} for {self.queries[0]} in {self.locations[0]}",
                    "skills": ["Spark", "Kafka"],
                    "posted_at": None,
                    "ingestion_ts": datetime.utcnow().isoformat(),
                }
            )
        return items
