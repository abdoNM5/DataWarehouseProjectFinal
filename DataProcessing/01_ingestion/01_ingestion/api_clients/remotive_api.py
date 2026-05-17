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

REMOTIVE_URL = "https://remotive.com/api/remote-jobs"


def get_remotive_jobs(category: str = "data") -> List[dict]:
    LOGGER.info("Remotive request category=%s", category)
    scraped_at = datetime.now().isoformat()

    try:
        response = requests.get(REMOTIVE_URL, params={"category": category}, timeout=20)
        response.raise_for_status()
    except requests.RequestException as exc:
        LOGGER.error("Remotive API request failed: %s", exc)
        return []

    jobs = response.json().get("jobs", [])
    rows: List[dict] = []

    for job in jobs:
        tags = job.get("tags") or []
        rows.append(
            build_job_record(
                job_id=str(job.get("id", "")),
                title=job.get("title", "Unknown"),
                company=job.get("company_name", "Unknown"),
                location_raw=job.get("candidate_required_location", "Remote"),
                description_html_or_text=job.get("description", ""),
                source_name="remotive",
                url=job.get("url", ""),
                posted_at=job.get("publication_date"),
                contract_type=job.get("job_type", ""),
                skills=tags,
                salary_min=job.get("salary", None),
                salary_max=None,
                currency="USD",
                scraped_at=scraped_at,
            )
        )

    return rows


def save_to_bronze(records: Sequence[dict]):
    save_json_lines(records, source_folder="remotive", current_file=Path(__file__))


if __name__ == "__main__":
    LOGGER.info("Starting Remotive ingestion")

    all_rows: List[dict] = []
    for category in ["data", "software-dev"]:
        all_rows.extend(get_remotive_jobs(category=category))
        time.sleep(1.0)

    save_to_bronze(all_rows)
    LOGGER.info("Remotive ingestion complete. rows=%s", len(all_rows))
