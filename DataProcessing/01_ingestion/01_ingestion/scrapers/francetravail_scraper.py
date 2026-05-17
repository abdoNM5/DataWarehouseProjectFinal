import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import requests
from dotenv import load_dotenv

INGESTION_ROOT = Path(__file__).resolve().parents[1]
if str(INGESTION_ROOT) not in sys.path:
    sys.path.insert(0, str(INGESTION_ROOT))

from common_enrichment import build_job_record, save_json_lines


load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
LOGGER = logging.getLogger(__name__)

TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"
SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"


def get_access_token() -> Optional[str]:
    client_id = os.getenv("FRANCETRAVAIL_CLIENT_ID")
    client_secret = os.getenv("FRANCETRAVAIL_CLIENT_SECRET")

    if not client_id or not client_secret:
        LOGGER.warning("France Travail credentials are missing. Running in mock mode.")
        return None

    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "api_offresdemploiv2 o2dsoffre",
    }

    try:
        response = requests.post(TOKEN_URL, data=payload, timeout=15)
        response.raise_for_status()
        return response.json().get("access_token")
    except requests.RequestException as exc:
        LOGGER.error("France Travail token request failed: %s", exc)
        return None


def _parse_salary_label(salary_label: str) -> Tuple[Optional[float], Optional[float], str]:
    if not salary_label:
        return None, None, "EUR"

    numbers = [float(match.replace(",", ".")) for match in re.findall(r"\d+[\d\s]*(?:[.,]\d+)?", salary_label)]
    cleaned = []
    for number in numbers:
        if number < 1000:
            cleaned.append(number * 1000)
        else:
            cleaned.append(number)

    if not cleaned:
        return None, None, "EUR"

    cleaned = sorted(set(cleaned))
    if len(cleaned) == 1:
        return cleaned[0], cleaned[0], "EUR"

    return cleaned[0], cleaned[-1], "EUR"


def get_francetravail_jobs(
    access_token: Optional[str],
    keywords: str,
    department_code: Optional[str] = None,
    limit: int = 150,
) -> List[dict]:
    scraped_at = datetime.now().isoformat()

    if not access_token:
        return generate_mock_jobs(keywords, department_code or "France", scraped_at)

    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    params = {
        "motsCles": keywords,
        "sort": 1,
        "range": f"0-{max(1, limit - 1)}",
    }
    if department_code:
        params["departement"] = department_code

    LOGGER.info("France Travail query='%s' department=%s", keywords, department_code or "all")

    try:
        response = requests.get(SEARCH_URL, headers=headers, params=params, timeout=20)
        if response.status_code == 204:
            return []

        response.raise_for_status()
    except requests.RequestException as exc:
        LOGGER.warning("France Travail search failed: %s", exc)
        return generate_mock_jobs(keywords, department_code or "France", scraped_at)

    data = response.json().get("resultats", [])
    rows: List[dict] = []

    for job in data[:limit]:
        skills = [item.get("libelle", "") for item in job.get("competences", []) if item.get("libelle")]

        location_struct = job.get("lieuTravail", {})
        location_label = location_struct.get("libelle") or location_struct.get("commune") or "France"

        salary_label = (job.get("salaire") or {}).get("libelle", "")
        salary_min, salary_max, currency = _parse_salary_label(salary_label)

        rows.append(
            build_job_record(
                job_id=job.get("id") or "",
                title=job.get("intitule", "Unknown"),
                company=(job.get("entreprise") or {}).get("nom", "Confidentiel"),
                location_raw=location_label,
                description_html_or_text=job.get("description", ""),
                source_name="france_travail",
                url=job.get("origineOffre", {}).get("urlOrigine", ""),
                posted_at=job.get("dateCreation"),
                contract_type=job.get("typeContratLibelle") or job.get("typeContrat", ""),
                skills=skills,
                salary_min=salary_min,
                salary_max=salary_max,
                currency=currency,
                scraped_at=scraped_at,
            )
        )

    return rows


def generate_mock_jobs(keywords: str, location: str, scraped_at: str) -> List[dict]:
    rows = []
    for idx in range(8):
        rows.append(
            build_job_record(
                job_id=f"mock_ft_{idx}_{datetime.now().strftime('%H%M%S')}",
                title=f"{keywords}",
                company="France Data SA",
                location_raw=location,
                description_html_or_text=(
                    f"{keywords} role for data platform delivery. "
                    "Required skills: SQL, Python, Talend, Power BI, cloud integration."
                ),
                source_name="france_travail",
                contract_type="CDI",
                skills=["SQL", "Python", "Talend", "Power BI"],
                salary_min=42000,
                salary_max=60000,
                currency="EUR",
                scraped_at=scraped_at,
            )
        )
    return rows


def save_to_bronze(records: Sequence[dict]):
    save_json_lines(records, source_folder="francetravail", current_file=Path(__file__))


if __name__ == "__main__":
    LOGGER.info("Starting France Travail ingestion")

    token = get_access_token()
    all_rows: List[dict] = []

    roles = ["Data Engineer", "Data Analyst", "Data Scientist"]
    departments = ["75", "69", "31", None]

    for role in roles:
        for department in departments:
            all_rows.extend(get_francetravail_jobs(token, role, department_code=department, limit=120))
            time.sleep(0.8)

    save_to_bronze(all_rows)
    LOGGER.info("France Travail ingestion complete. rows=%s", len(all_rows))
