import json
import logging
import re
import unicodedata
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


LOGGER = logging.getLogger(__name__)

COUNTRY_ALIASES = {
    "france": "France",
    "fr": "France",
    "royaume uni": "United Kingdom",
    "royaume-uni": "United Kingdom",
    "united kingdom": "United Kingdom",
    "uk": "United Kingdom",
    "angleterre": "United Kingdom",
    "england": "United Kingdom",
    "espagne": "Spain",
    "spain": "Spain",
    "allemagne": "Germany",
    "germany": "Germany",
    "italie": "Italy",
    "italy": "Italy",
    "portugal": "Portugal",
    "pays bas": "Netherlands",
    "netherlands": "Netherlands",
    "belgique": "Belgium",
    "belgium": "Belgium",
    "suisse": "Switzerland",
    "switzerland": "Switzerland",
    "canada": "Canada",
    "usa": "United States",
    "us": "United States",
    "u.s.": "United States",
    "u.s.a.": "United States",
    "united states": "United States",
    "etats unis": "United States",
    "etats-unis": "United States",
    "etatsunis": "United States",
    "australie": "Australia",
    "australia": "Australia",
    "inde": "India",
    "india": "India",
    "maroc": "Morocco",
    "morocco": "Morocco",
    "tunisie": "Tunisia",
    "tunisia": "Tunisia",
    "algerie": "Algeria",
    "algeria": "Algeria",
    "remote": "Remote",
    "worldwide": "Remote",
    "global": "Remote",
    "anywhere": "Remote",
}

US_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN",
    "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV",
    "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN",
    "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
}

SKILL_PATTERNS = {
    "Python": [r"\bpython\b"],
    "SQL": [r"\bsql\b"],
    "Airflow": [r"\bairflow\b"],
    "dbt": [r"\bdbt\b"],
    "Spark": [r"\bspark\b"],
    "Kafka": [r"\bkafka\b"],
    "AWS": [r"\baws\b", r"\bamazon web services\b"],
    "Azure": [r"\bazure\b"],
    "GCP": [r"\bgcp\b", r"\bgoogle cloud\b"],
    "Databricks": [r"\bdatabricks\b"],
    "Snowflake": [r"\bsnowflake\b"],
    "BigQuery": [r"\bbigquery\b"],
    "PostgreSQL": [r"\bpostgres(?:ql)?\b"],
    "MySQL": [r"\bmysql\b"],
    "MongoDB": [r"\bmongodb\b"],
    "Docker": [r"\bdocker\b"],
    "Kubernetes": [r"\bkubernetes\b", r"\bk8s\b"],
    "Git": [r"\bgit\b"],
    "Power BI": [r"\bpower\s*bi\b", r"\bpowerbi\b"],
    "Tableau": [r"\btableau\b"],
    "Looker": [r"\blooker\b"],
    "Excel": [r"\bexcel\b"],
    "Pandas": [r"\bpandas\b"],
    "NumPy": [r"\bnumpy\b"],
    "PySpark": [r"\bpyspark\b"],
    "TensorFlow": [r"\btensorflow\b"],
    "PyTorch": [r"\bpytorch\b"],
    "scikit-learn": [r"\bscikit\s*-?\s*learn\b", r"\bsklearn\b"],
    "Machine Learning": [r"\bmachine learning\b"],
    "Deep Learning": [r"\bdeep learning\b"],
    "NLP": [r"\bnlp\b", r"\bnatural language processing\b"],
    "LLM": [r"\bllm\b", r"\blarge language model\b"],
    "Talend": [r"\btalend\b"],
    "ETL": [r"\betl\b"],
    "API": [r"\bapi\b"],
    "REST": [r"\brest\b"],
}

ROLE_DEFAULT_SKILLS = [
    (re.compile(r"\bdata engineer\b", re.IGNORECASE), ["Python", "SQL", "ETL"]),
    (re.compile(r"\bdata analyst\b", re.IGNORECASE), ["SQL", "Excel", "Power BI"]),
    (re.compile(r"\bdata scientist\b", re.IGNORECASE), ["Python", "SQL", "Machine Learning"]),
    (re.compile(r"\bdata architect\b", re.IGNORECASE), ["SQL", "AWS", "Azure"]),
]


def normalize_whitespace(value: str) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def strip_html(value: str) -> str:
    if not value:
        return ""
    text = unescape(value)
    text = re.sub(r"<[^>]+>", " ", text)
    return normalize_whitespace(text)


def _normalize_token(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.lower()
    normalized = normalized.replace("_", " ").replace("-", " ")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def parse_location(location_raw: str) -> Tuple[str, str]:
    clean = normalize_whitespace(location_raw)
    if not clean:
        return "Unknown", "Unknown"

    if _normalize_token(clean) in {"remote", "anywhere", "worldwide", "global"}:
        return "Remote", "Remote"

    parts = [normalize_whitespace(p) for p in clean.split(",") if normalize_whitespace(p)]
    city = parts[0] if parts else clean
    country = "Unknown"

    for candidate in reversed(parts if parts else [clean]):
        token = _normalize_token(candidate)
        if token in COUNTRY_ALIASES:
            country = COUNTRY_ALIASES[token]
            break

    if country == "Unknown" and parts:
        last = parts[-1].upper()
        if last in US_STATE_CODES:
            country = "United States"

    return city, country


def normalize_contract_type(raw_contract: str, title: str = "", description: str = "") -> str:
    text = " ".join([raw_contract or "", title or "", description or ""]).lower()

    if any(k in text for k in ["intern", "internship", "stage", "alternance", "apprentice"]):
        return "Internship"
    if any(k in text for k in ["part-time", "part time", "temps partiel"]):
        return "Part-time"
    if any(k in text for k in ["freelance", "contractor", "independent"]):
        return "Freelance"
    if any(k in text for k in ["cdd", "fixed-term", "fixed term", "temporary", "temporaire", "contract"]):
        return "Contract"
    if any(k in text for k in ["cdi", "full-time", "full time", "permanent", "temps plein"]):
        return "Full-time"

    return "Unknown"


def _extract_from_patterns(text: str) -> List[str]:
    found = set()
    for skill_name, patterns in SKILL_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                found.add(skill_name)
                break
    return sorted(found)


def extract_skills(title: str, description: str, extra_terms: Optional[Sequence[str]] = None) -> List[str]:
    title_text = normalize_whitespace(title)
    desc_text = normalize_whitespace(description)
    extra_text = " ".join(normalize_whitespace(term) for term in (extra_terms or []) if term)

    combined = " ".join([title_text, desc_text, extra_text]).strip()
    if not combined:
        return []

    skills = set(_extract_from_patterns(combined.lower()))

    if not skills:
        for pattern, defaults in ROLE_DEFAULT_SKILLS:
            if pattern.search(title_text):
                skills.update(defaults)

    return sorted(skills)


def safe_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", ".").strip())
    except (TypeError, ValueError):
        return None


def build_job_record(
    *,
    job_id: str,
    title: str,
    company: str,
    location_raw: str,
    description_html_or_text: str,
    source_name: str,
    url: str = "",
    posted_at: Optional[str] = None,
    contract_type: str = "",
    skills: Optional[Sequence[str]] = None,
    salary_min: Any = None,
    salary_max: Any = None,
    currency: Optional[str] = None,
    scraped_at: Optional[str] = None,
) -> Dict[str, Any]:
    description_clean = strip_html(description_html_or_text)
    city, country = parse_location(location_raw)

    normalized_skills = extract_skills(
        title=title,
        description=description_clean,
        extra_terms=skills or [],
    )

    return {
        "id_offer": str(job_id).strip(),
        "title": normalize_whitespace(title) or "Unknown",
        "company": normalize_whitespace(company) or "Unknown",
        "location": normalize_whitespace(location_raw) or "Unknown",
        "city": city,
        "country": country,
        "description": description_clean,
        "employment_type": normalize_contract_type(contract_type, title, description_clean),
        "salary_min": safe_float(salary_min),
        "salary_max": safe_float(salary_max),
        "currency": (currency or "EUR").strip().upper() if currency else "EUR",
        "skills": normalized_skills,
        "url": normalize_whitespace(url),
        "posted_at": posted_at,
        "source": source_name,
        "scraped_at": scraped_at or datetime.now().isoformat(),
    }


def resolve_project_root(current_file: Path) -> Path:
    resolved = current_file.resolve()
    for parent in resolved.parents:
        if (parent / "01_ingestion").exists():
            return parent
    return resolved.parents[2]


def save_json_lines(
    records: Sequence[Dict[str, Any]],
    *,
    source_folder: str,
    current_file: Path,
    output_root_name: str = "bronze2",
) -> Optional[Path]:
    if not records:
        LOGGER.warning("No records to save for %s", source_folder)
        return None

    project_root = resolve_project_root(current_file)
    out_dir = project_root / output_root_name / source_folder
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"{source_folder}_jobs_{timestamp}.json"

    with out_file.open("w", encoding="utf-8") as handle:
        for row in records:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    LOGGER.info("Saved %s rows to %s", len(records), out_file)
    return out_file
