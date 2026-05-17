import logging
import time

from api_clients.remotive_api import get_remotive_jobs, save_to_bronze as save_remotive
from api_clients.themuse_api import get_themuse_jobs, save_to_bronze as save_themuse
from scrapers.francetravail_scraper import (
    get_access_token,
    get_francetravail_jobs,
    save_to_bronze as save_francetravail,
)
from scrapers.indeed_scraper import get_indeed_jobs, save_to_bronze as save_indeed
from scrapers.linkedin_scraper import get_linkedin_jobs, save_to_bronze as save_linkedin


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
LOGGER = logging.getLogger(__name__)


def run_linkedin() -> int:
    rows = []
    for role in ["Data Engineer", "Data Analyst", "Data Scientist"]:
        for location in ["Paris", "London", "Remote"]:
            rows.extend(get_linkedin_jobs(query=role, location=location, num_pages=1))
            time.sleep(0.8)

    save_linkedin(rows)
    return len(rows)


def run_indeed() -> int:
    rows = []
    for role in ["Data Engineer", "Data Analyst", "Data Scientist"]:
        for location in ["Paris", "Lyon", "Remote"]:
            rows.extend(get_indeed_jobs(query=role, location=location, num_pages=1))
            time.sleep(0.8)

    save_indeed(rows)
    return len(rows)


def run_francetravail() -> int:
    rows = []
    token = get_access_token()

    for role in ["Data Engineer", "Data Analyst", "Data Scientist"]:
        for department in ["75", "69", "31", None]:
            rows.extend(get_francetravail_jobs(token, role, department_code=department, limit=120))
            time.sleep(0.6)

    save_francetravail(rows)
    return len(rows)


def run_remotive() -> int:
    rows = []
    for category in ["data", "software-dev"]:
        rows.extend(get_remotive_jobs(category=category))
        time.sleep(0.6)

    save_remotive(rows)
    return len(rows)


def run_themuse() -> int:
    rows = []
    for category in ["Data and Analytics", "Software Engineering"]:
        rows.extend(get_themuse_jobs(category=category, max_pages=4))
        time.sleep(0.6)

    save_themuse(rows)
    return len(rows)


def main():
    LOGGER.info("Starting full ingestion run to bronze2")

    linkedin_count = run_linkedin()
    indeed_count = run_indeed()
    francetravail_count = run_francetravail()
    remotive_count = run_remotive()
    themuse_count = run_themuse()

    total = linkedin_count + indeed_count + francetravail_count + remotive_count + themuse_count

    LOGGER.info("Ingestion summary")
    LOGGER.info("linkedin rows: %s", linkedin_count)
    LOGGER.info("indeed rows: %s", indeed_count)
    LOGGER.info("francetravail rows: %s", francetravail_count)
    LOGGER.info("remotive rows: %s", remotive_count)
    LOGGER.info("themuse rows: %s", themuse_count)
    LOGGER.info("total rows: %s", total)


if __name__ == "__main__":
    main()
