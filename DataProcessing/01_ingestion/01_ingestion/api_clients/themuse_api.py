import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Sequence

import requests

INGESTION_ROOT = Path(__file__).resolve().parents[1]
if str(INGESTION_ROOT) not in sys.path:
    sys.path.insert(0, str(INGESTION_ROOT))

from common_enrichment import build_job_record, save_json_lines


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
LOGGER = logging.getLogger(__name__)

THEMUSE_URL = "https://www.themuse.com/api/public/jobs"


def get_themuse_jobs(category: str = "Data and Analytics", max_pages: int = 5) -> List[dict]:
    scraped_at = datetime.now().isoformat()
    rows: List[dict] = []

    page = 1
    total_pages = 1

    while page <= total_pages and page <= max_pages:
        LOGGER.info("TheMuse request category='%s' page=%s", category, page)

        params = {"page": page, "category": category}
        try:
            response = requests.get(THEMUSE_URL, params=params, timeout=20)
            response.raise_for_status()
        except requests.RequestException as exc:
            LOGGER.error("TheMuse API request failed on page %s: %s", page, exc)
            break

        payload = response.json()
        total_pages = payload.get("page_count", 0) or 0
        results = payload.get("results", [])

        if not results:
            break

        for job in results:
            locations = [loc.get("name", "") for loc in job.get("locations", []) if loc.get("name")]
            levels = [lvl.get("name", "") for lvl in job.get("levels", []) if lvl.get("name")]
            categories = [cat.get("name", "") for cat in job.get("categories", []) if cat.get("name")]

            location_raw = locations[0] if locations else "Remote"
            contract_hint = job.get("type") or " ".join(levels)

            rows.append(
                build_job_record(
                    job_id=str(job.get("id", "")),
                    title=job.get("name", "Unknown"),
                    company=(job.get("company") or {}).get("name", "Unknown"),
                    location_raw=location_raw,
                    description_html_or_text=job.get("contents", ""),
                    source_name="the_muse",
                    url=(job.get("refs") or {}).get("landing_page", ""),
                    posted_at=job.get("publication_date"),
                    contract_type=contract_hint,
                    skills=categories + levels,
                    scraped_at=scraped_at,
                )
            )

        page += 1
        time.sleep(1.0)

    return rows


def save_to_bronze(records: Sequence[dict]):
    save_json_lines(records, source_folder="themuse", current_file=Path(__file__))


if __name__ == "__main__":
    LOGGER.info("Starting TheMuse ingestion")

    all_rows: List[dict] = []
    for category in ["Data and Analytics", "Software Engineering"]:
        all_rows.extend(get_themuse_jobs(category=category, max_pages=4))
        time.sleep(1.0)

    save_to_bronze(all_rows)
    LOGGER.info("TheMuse ingestion complete. rows=%s", len(all_rows))
