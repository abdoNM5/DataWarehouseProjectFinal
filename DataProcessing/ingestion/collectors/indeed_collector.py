"""Indeed web scraper collector (no API key required)."""

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
    "BI Developer",
    "Machine Learning Engineer",
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
    "www.indeed.com",
    "uk.indeed.com",
    "ca.indeed.com",
    "au.indeed.com",
    "in.indeed.com",
    "sg.indeed.com",
    "de.indeed.com",
    "fr.indeed.com",
    "nl.indeed.com",
    "br.indeed.com",
    "mx.indeed.com",
    "ae.indeed.com",
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
    direct_id = card.get("data-jk")
    if isinstance(direct_id, str) and direct_id.strip():
        return direct_id

    if job_url and "jk=" in job_url:
        return job_url.split("jk=")[-1].split("&", 1)[0]
    return str(uuid.uuid4())


class IndeedCollector(Collector):
    source = "indeed"

    def __init__(self, *, query: str | None = None, location: str | None = None, pages: int = 8, since=None, client_factory=None) -> None:
        super().__init__(since=since, client_factory=client_factory)
        base_queries = [query] if query else DEFAULT_QUERIES
        base_locations = [location] if location else DEFAULT_LOCATIONS
        self.queries = _parse_csv_env("SCRAPE_QUERIES", base_queries)
        self.locations = _parse_csv_env("SCRAPE_LOCATIONS", base_locations)
        self.sites = _parse_csv_env("INDEED_SITES", DEFAULT_SITES)
        self.pages = int(os.getenv("INDEED_PAGES", os.getenv("SCRAPE_PAGES", str(pages))))
        self.max_records = int(os.getenv("MAX_RECORDS_PER_SOURCE", "2500"))
        self.request_delay_seconds = float(os.getenv("INDEED_DELAY_SECONDS", os.getenv("SCRAPE_DELAY_SECONDS", "1.8")))
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
                    for page in range(self.pages):
                        url = (
                            f"https://{site}/jobs?"
                            f"q={quote_plus(query)}&l={quote_plus(location)}&start={page * 10}"
                        )
                        response = self._request(url, headers)
                        if response is None:
                            time.sleep(self.request_delay_seconds)
                            continue

                        soup = BeautifulSoup(response.text, "html.parser")
                        cards = soup.select("div.job_seen_beacon, div.slider_item")
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
                                ["h2.jobTitle", "h2 a span", "a.jcs-JobTitle span"],
                                "N/A",
                            )
                            company = _first_text(
                                card,
                                ["span.companyName", "span[data-testid='company-name']"],
                                "N/A",
                            )
                            loc = _first_text(
                                card,
                                ["div.companyLocation", "div[data-testid='text-location']"],
                                location,
                            )
                            if title == "N/A" and company == "N/A":
                                continue

                            dedupe_key = (title.lower(), company.lower(), loc.lower())
                            if dedupe_key in seen:
                                continue
                            seen.add(dedupe_key)

                            link_element = card.select_one("a.jcs-JobTitle, a.tapItem, a[href*='/viewjob']")
                            job_url = None
                            if link_element and link_element.get("href"):
                                href = str(link_element.get("href"))
                                job_url = href if href.startswith("http") else f"https://{site}{href}"

                            description = _first_text(
                                card,
                                ["div.job-snippet", "div[data-testid='jobsnippet_footer']"],
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

        if not jobs:
            return self._mock_jobs()
        return jobs

    def _mock_jobs(self) -> List[Dict[str, Any]]:
        companies = ["TechCorp", "DataSolution", "AI Innovate", "CloudFinance", "WebRetail"]
        items: List[Dict[str, Any]] = []
        for idx, company in enumerate(companies):
            items.append(
                {
                    "job_id": str(uuid.uuid4()),
                    "title_raw": f"Senior {self.queries[0]}",
                    "title_standard": f"Senior {self.queries[0]}",
                    "company_name": company,
                    "location_raw": self.locations[0],
                    "location_norm": None,
                    "employment_type": None,
                    "salary_min": None,
                    "salary_max": None,
                    "currency": "EUR",
                    "description": f"Mock job {idx + 1} for {self.queries[0]} in {self.locations[0]}.",
                    "skills": ["Python", "SQL"],
                    "posted_at": None,
                    "ingestion_ts": datetime.utcnow().isoformat(),
                }
            )
        return items
