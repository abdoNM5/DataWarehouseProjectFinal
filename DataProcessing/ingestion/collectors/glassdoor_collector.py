"""Glassdoor web scraper collector (no API key required)."""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Iterable, List
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup, Tag

from .base_collector import Collector


DEFAULT_QUERIES = [
    "Data Engineer",
    "Data Scientist",
    "Data Analyst",
    "Business Analyst",
    "Machine Learning Engineer",
    "Analytics Engineer",
]

DEFAULT_LOCATIONS = [
    "New York, NY, United States",
    "San Francisco, CA, United States",
    "Toronto, ON, Canada",
    "London, United Kingdom",
    "Berlin, Germany",
    "Paris, France",
    "Sao Paulo, Brazil",
    "Mexico City, Mexico",
    "Dubai, United Arab Emirates",
    "Singapore",
    "Bangalore, India",
    "Tokyo, Japan",
    "Sydney, Australia",
    "Cape Town, South Africa",
    "Remote",
]

DEFAULT_SITES = [
    "www.glassdoor.com",
    "www.glassdoor.co.uk",
    "www.glassdoor.de",
    "www.glassdoor.fr",
    "www.glassdoor.ca",
    "www.glassdoor.com.au",
]


def _parse_csv_env(name: str, fallback: List[str]) -> List[str]:
    raw = os.getenv(name, "")
    if not raw.strip():
        return fallback
    return [part.strip() for part in raw.split(",") if part.strip()]


def _first_text(card: Tag, selectors: List[str], fallback: str) -> str:
    for selector in selectors:
        element = card.select_one(selector)
        if element:
            return element.get_text(" ", strip=True)
    return fallback


def _extract_job_id(card: Tag, job_url: str | None) -> str:
    card_id = card.get("data-id")
    if isinstance(card_id, str) and card_id.strip():
        return card_id

    if job_url and "/job-listing/" in job_url:
        return job_url.split("/job-listing/")[-1].split("?", 1)[0]
    return str(uuid.uuid4())


class GlassdoorCollector(Collector):
    source = "glassdoor"

    def __init__(
        self,
        *,
        query: str | None = None,
        location: str | None = None,
        pages: int = 8,
        since=None,
        client_factory=None,
    ) -> None:
        super().__init__(since=since, client_factory=client_factory)
        base_queries = [query] if query else DEFAULT_QUERIES
        base_locations = [location] if location else DEFAULT_LOCATIONS

        glassdoor_queries = _parse_csv_env("GLASSDOOR_QUERIES", [])
        glassdoor_locations = _parse_csv_env("GLASSDOOR_LOCATIONS", [])
        self.queries = glassdoor_queries or _parse_csv_env("SCRAPE_QUERIES", base_queries)
        self.locations = glassdoor_locations or _parse_csv_env("SCRAPE_LOCATIONS", base_locations)
        self.sites = _parse_csv_env("GLASSDOOR_SITES", DEFAULT_SITES)

        self.pages = int(os.getenv("GLASSDOOR_PAGES", os.getenv("SCRAPE_PAGES", str(pages))))
        self.max_records = int(os.getenv("MAX_RECORDS_PER_SOURCE", "2500"))
        self.request_delay_seconds = float(os.getenv("GLASSDOOR_DELAY_SECONDS", os.getenv("SCRAPE_DELAY_SECONDS", "2.2")))
        self.request_timeout_seconds = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "35"))

    def _request(self, url: str, headers: Dict[str, str]) -> requests.Response | None:
        for attempt in range(3):
            try:
                response = requests.get(url, headers=headers, timeout=self.request_timeout_seconds)
            except requests.RequestException:
                time.sleep(self.request_delay_seconds * (attempt + 1))
                continue

            if response.status_code in {403, 429, 503}:
                time.sleep(self.request_delay_seconds * (attempt + 1))
                continue
            if response.status_code != 200:
                return None
            return response
        return None

    def fetch(self) -> Iterable[Dict[str, Any]]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        jobs: List[Dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()

        for site in self.sites:
            for query in self.queries:
                for location in self.locations:
                    empty_pages = 0
                    for page in range(1, self.pages + 1):
                        url = (
                            f"https://{site}/Job/jobs.htm?"
                            f"sc.keyword={quote_plus(query)}&locT=C&locKeyword={quote_plus(location)}&p={page}"
                        )
                        response = self._request(url, headers)
                        if response is None:
                            time.sleep(self.request_delay_seconds)
                            continue

                        soup = BeautifulSoup(response.text, "html.parser")
                        cards = soup.select(
                            "li.react-job-listing, "
                            "li[data-test='jobListing'], "
                            "li[class*='JobsList_jobListItem'], "
                            "article[data-test='jobListing']"
                        )
                        if not cards:
                            empty_pages += 1
                            if empty_pages >= 2:
                                break
                            time.sleep(self.request_delay_seconds)
                            continue
                        empty_pages = 0

                        for card in cards:
                            title = _first_text(
                                card,
                                [
                                    "a[data-test='job-link']",
                                    "a.jobLink",
                                    "a[class*='JobCard_jobTitle']",
                                    "div[class*='JobCard_jobTitle']",
                                ],
                                "N/A",
                            )
                            company = _first_text(
                                card,
                                [
                                    "span[data-test='employer-name']",
                                    "div[data-test='employerName']",
                                    "span[class*='EmployerProfile_compactEmployerName']",
                                ],
                                "N/A",
                            )
                            loc = _first_text(
                                card,
                                [
                                    "div[data-test='emp-location']",
                                    "span[data-test='location']",
                                    "div[class*='JobCard_location']",
                                ],
                                location,
                            )
                            if title == "N/A" and company == "N/A":
                                continue

                            dedupe_key = (title.lower(), company.lower(), loc.lower())
                            if dedupe_key in seen:
                                continue
                            seen.add(dedupe_key)

                            link_element = card.select_one("a[data-test='job-link'], a.jobLink, a[href*='/job-listing/']")
                            job_url = None
                            if link_element and link_element.get("href"):
                                href = str(link_element.get("href"))
                                job_url = href if href.startswith("http") else f"https://{site}{href}"

                            description = _first_text(
                                card,
                                [
                                    "div[data-test='job-description']",
                                    "div[class*='JobCard_jobDescriptionSnippet']",
                                ],
                                "Description not available from listing page",
                            )

                            jobs.append(
                                {
                                    "job_id": _extract_job_id(card, job_url),
                                    "title_raw": title,
                                    "title_standard": title,
                                    "company_name": company,
                                    "location_raw": loc,
                                    "location_norm": None,
                                    "employment_type": None,
                                    "salary_min": None,
                                    "salary_max": None,
                                    "currency": None,
                                    "description": description,
                                    "skills": [],
                                    "posted_at": None,
                                    "ingestion_ts": datetime.utcnow().isoformat(),
                                }
                            )
                            if len(jobs) >= self.max_records:
                                return jobs

                        time.sleep(self.request_delay_seconds)

        return jobs or self._mock_jobs()

    def _mock_jobs(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for idx in range(5):
            items.append(
                {
                    "job_id": str(uuid.uuid4()),
                    "title_raw": f"{self.queries[0]} - Glassdoor Mock",
                    "title_standard": f"{self.queries[0]} - Glassdoor Mock",
                    "company_name": "Glassdoor Mock Co",
                    "location_raw": self.locations[0],
                    "location_norm": None,
                    "employment_type": None,
                    "salary_min": None,
                    "salary_max": None,
                    "currency": None,
                    "description": f"Mock Glassdoor job {idx + 1} for {self.queries[0]}.",
                    "skills": ["Data"],
                    "posted_at": None,
                    "ingestion_ts": datetime.utcnow().isoformat(),
                }
            )
        return items