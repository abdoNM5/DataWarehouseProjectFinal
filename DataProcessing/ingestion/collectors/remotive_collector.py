"""Collector for Remotive public jobs API."""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Iterable, List
from urllib.parse import quote_plus

import requests

from .base_collector import Collector


DEFAULT_QUERIES = [
    "data engineer",
    "data scientist",
    "data analyst",
    "business analyst",
    "machine learning engineer",
    "analytics engineer",
]

DEFAULT_CATEGORIES = [
    "data",
    "software-dev",
    "product",
]


def _parse_csv_env(name: str, fallback: List[str]) -> List[str]:
    raw = os.getenv(name, "")
    if not raw.strip():
        return fallback
    return [part.strip() for part in raw.split(",") if part.strip()]


def _as_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class RemotiveCollector(Collector):
    source = "remotive"

    def __init__(self, *, query: str | None = None, since=None, client_factory=None) -> None:
        super().__init__(since=since, client_factory=client_factory)
        base_queries = [query] if query else DEFAULT_QUERIES
        remotive_queries = _parse_csv_env("REMOTIVE_QUERIES", [])
        if remotive_queries:
            self.queries = remotive_queries
        else:
            self.queries = _parse_csv_env("SCRAPE_QUERIES", base_queries)
        self.categories = _parse_csv_env("REMOTIVE_CATEGORIES", DEFAULT_CATEGORIES)
        self.include_all_jobs = _as_bool_env("REMOTIVE_INCLUDE_ALL", True)
        self.max_records = int(os.getenv("MAX_RECORDS_PER_SOURCE", "2500"))
        self.request_delay_seconds = float(os.getenv("REMOTIVE_DELAY_SECONDS", os.getenv("SCRAPE_DELAY_SECONDS", "1.8")))
        self.request_timeout_seconds = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "35"))

    def _iter_api_urls(self) -> List[str]:
        base_url = "https://remotive.com/api/remote-jobs"
        urls: List[str] = []
        if self.include_all_jobs:
            urls.append(base_url)
        for category in self.categories:
            urls.append(f"{base_url}?category={quote_plus(category)}")
        for query in self.queries:
            urls.append(f"{base_url}?search={quote_plus(query)}")

        # Keep order while removing duplicates.
        unique_urls = list(dict.fromkeys(urls))
        return unique_urls

    def _request_json(self, url: str) -> Dict[str, Any] | None:
        for attempt in range(3):
            try:
                response = requests.get(url, timeout=self.request_timeout_seconds)
            except requests.RequestException:
                time.sleep(self.request_delay_seconds * (attempt + 1))
                continue

            if response.status_code in {403, 429, 503}:
                time.sleep(self.request_delay_seconds * (attempt + 1))
                continue
            if response.status_code != 200:
                return None

            try:
                return response.json()
            except ValueError:
                return None
        return None

    def fetch(self) -> Iterable[Dict[str, Any]]:
        jobs: List[Dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for url in self._iter_api_urls():
            payload = self._request_json(url)
            if payload is None:
                time.sleep(self.request_delay_seconds)
                continue

            for item in payload.get("jobs", []):
                title = str(item.get("title") or "N/A")
                company = str(item.get("company_name") or "N/A")
                location = str(item.get("candidate_required_location") or "Remote")
                key = (title.lower(), company.lower(), location.lower())
                if key in seen:
                    continue
                seen.add(key)

                tags = item.get("tags") or []
                skills = [str(tag).strip() for tag in tags if str(tag).strip()]

                jobs.append(
                    {
                        "job_id": str(item.get("id") or uuid.uuid4()),
                        "title_raw": title,
                        "title_standard": title,
                        "company_name": company,
                        "location_raw": location,
                        "location_norm": None,
                        "employment_type": item.get("job_type"),
                        "salary_min": None,
                        "salary_max": None,
                        "currency": None,
                        "description": str(item.get("description") or "")[:1000],
                        "skills": skills,
                        "posted_at": item.get("publication_date"),
                        "ingestion_ts": datetime.utcnow().isoformat(),
                    }
                )
                if len(jobs) >= self.max_records:
                    return jobs

            time.sleep(self.request_delay_seconds)

        return jobs or self._mock_jobs()

    def _mock_jobs(self) -> List[Dict[str, Any]]:
        return [
            {
                "job_id": str(uuid.uuid4()),
                "title_raw": f"Remote {self.queries[0]} Engineer",
                "title_standard": f"Remote {self.queries[0]} Engineer",
                "company_name": "Remotive Mock Co",
                "location_raw": "Remote",
                "location_norm": None,
                "employment_type": "full_time",
                "salary_min": None,
                "salary_max": None,
                "currency": "EUR",
                "description": "Fallback mock from Remotive collector",
                "skills": ["Python"],
                "posted_at": None,
                "ingestion_ts": datetime.utcnow().isoformat(),
            }
        ]
