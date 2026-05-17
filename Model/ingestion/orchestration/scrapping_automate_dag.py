"""
Airflow DAG: Scraping Automation → MinIO Bronze Layer
=====================================================
Orchestrates all job data scrapers and API clients:
  1. Migrate existing local bronze files to MinIO (one-time, idempotent)
  2. Scrape / call APIs in parallel (Indeed, LinkedIn, FranceTravail, Remotive, TheMuse)
  3. Upload scraped data as JSONL to MinIO bronze bucket

Schedule: Daily at 06:00 UTC
"""

from __future__ import annotations

import importlib.util
import io
import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from airflow import DAG
from airflow.operators.python import PythonOperator

logger = logging.getLogger(__name__)

# ── Paths inside the Airflow container ──────────────────
# DataProcessing is mounted at /opt/airflow/project/DataProcessing
SCRAPERS_DIR = Path("/opt/airflow/project/DataProcessing/01_ingestion/scrapers")
API_CLIENTS_DIR = Path("/opt/airflow/project/DataProcessing/01_ingestion/api_clients")
LOCAL_BRONZE_DIR = Path("/opt/airflow/project/DataProcessing/01_ingestion/bronze")

# ── MinIO configuration (from env vars set in docker-compose) ──
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minio")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minio123")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET_BRONZE", "bronze")


# ── Helpers ────────────────────────────────────────────

def _load_module(module_name: str, file_path: Path):
    """
    Dynamically import a Python module from an arbitrary path.
    Needed because '01_ingestion' starts with a digit (invalid Python package name).
    """
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {file_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _get_minio_client():
    """Create and return a MinIO client instance."""
    from minio import Minio
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
    )


def _ensure_bucket(client, bucket_name: str):
    """Create bucket if it does not exist."""
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)
        logger.info(f"Created bucket: {bucket_name}")


def _upload_records_to_minio(source: str, records: List[Dict[str, Any]]) -> int:
    """
    Serialize records as JSONL and upload to MinIO bronze bucket.
    Object path: {source}/{YYYY-MM-DD}/{source}_{timestamp}.jsonl
    Returns the number of records uploaded.
    """
    if not records:
        logger.warning(f"⚠️ No records to upload for source '{source}'")
        return 0

    client = _get_minio_client()
    _ensure_bucket(client, MINIO_BUCKET)

    now = datetime.utcnow()
    date_partition = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    object_name = f"{source}/{date_partition}/{source}_{timestamp}.jsonl"

    # Convert to JSONL (newline-delimited JSON)
    jsonl_content = "\n".join(
        json.dumps(record, ensure_ascii=False, default=str)
        for record in records
    )
    data = jsonl_content.encode("utf-8")

    client.put_object(
        MINIO_BUCKET,
        object_name,
        io.BytesIO(data),
        length=len(data),
        content_type="application/x-ndjson",
    )
    logger.info(f"✅ Uploaded {len(records)} records → minio://{MINIO_BUCKET}/{object_name}")
    return len(records)


def _upload_file_to_minio(client, local_path: Path, object_name: str):
    """Upload a local file directly to MinIO."""
    _ensure_bucket(client, MINIO_BUCKET)
    client.fput_object(MINIO_BUCKET, object_name, str(local_path))
    logger.info(f"📦 Migrated: {local_path.name} → minio://{MINIO_BUCKET}/{object_name}")


# ── Task Callables ────────────────────────────────────

def migrate_bronze_to_minio(**context):
    """
    One-time migration: upload all existing local bronze JSON files to MinIO.
    Idempotent — re-uploading the same file overwrites the object.
    """
    logger.info("🔄 Starting migration of local bronze data to MinIO...")

    if not LOCAL_BRONZE_DIR.exists():
        logger.info("No local bronze directory found. Skipping migration.")
        return {"migrated_files": 0}

    client = _get_minio_client()
    _ensure_bucket(client, MINIO_BUCKET)
    migrated = 0

    for source_dir in sorted(LOCAL_BRONZE_DIR.iterdir()):
        if not source_dir.is_dir():
            continue
        source_name = source_dir.name  # e.g. "indeed", "linkedin"

        for file_path in sorted(source_dir.rglob("*.json*")):
            # Put migrated files under a 'migrated/' prefix for traceability
            object_name = f"{source_name}/migrated/{file_path.name}"

            # Skip if already exists in MinIO (idempotent check)
            try:
                client.stat_object(MINIO_BUCKET, object_name)
                logger.info(f"⏭️  Already exists, skipping: {object_name}")
                continue
            except Exception:
                pass  # Object doesn't exist, proceed with upload

            _upload_file_to_minio(client, file_path, object_name)
            migrated += 1

    logger.info(f"🏁 Migration complete: {migrated} files uploaded to MinIO")
    context["task_instance"].xcom_push(key="migrated_files", value=migrated)
    return {"migrated_files": migrated}


def ingest_indeed(**context):
    """Scrape Indeed job offers and upload to MinIO."""
    logger.info("🔎 Starting Indeed ingestion...")

    mod = _load_module("indeed_scraper", SCRAPERS_DIR / "indeed_scraper.py")

    roles = ["Data Engineer", "Data Analyst", "Data Scientist", "Data Architect"]
    locations = ["Paris", "Casablanca", "Remote"]

    all_data = []
    for role in roles:
        for loc in locations:
            try:
                data = mod.get_job_offers(query=role, location=loc, num_pages=1)
                all_data.extend(data)
                time.sleep(1.5)
            except Exception as e:
                logger.error(f"❌ Indeed error for '{role}' @ '{loc}': {e}")

    count = _upload_records_to_minio("indeed", all_data)
    context["task_instance"].xcom_push(key="indeed_count", value=count)
    logger.info(f"🏁 Indeed ingestion complete: {count} records")
    return count


def ingest_linkedin(**context):
    """Scrape LinkedIn job offers and upload to MinIO."""
    logger.info("🔎 Starting LinkedIn ingestion...")

    mod = _load_module("linkedin_scraper", SCRAPERS_DIR / "linkedin_scraper.py")

    roles = ["Data Engineer", "Data Analyst", "Data Scientist"]
    locations = ["Paris", "Casablanca", "Remote"]

    all_data = []
    for role in roles:
        for loc in locations:
            try:
                data = mod.get_linkedin_jobs(query=role, location=loc, num_pages=1)
                all_data.extend(data)
                time.sleep(2)
            except Exception as e:
                logger.error(f"❌ LinkedIn error for '{role}' @ '{loc}': {e}")

    count = _upload_records_to_minio("linkedin", all_data)
    context["task_instance"].xcom_push(key="linkedin_count", value=count)
    logger.info(f"🏁 LinkedIn ingestion complete: {count} records")
    return count


def ingest_francetravail(**context):
    """Fetch France Travail job offers via API and upload to MinIO."""
    logger.info("🔎 Starting France Travail ingestion...")

    mod = _load_module("francetravail_scraper", SCRAPERS_DIR / "francetravail_scraper.py")

    # Get OAuth2 token once for the entire run
    token = mod.get_ft_access_token()

    roles = ["Data Engineer", "Data Analyst", "Data Scientist"]
    # French department codes: 75=Paris, 69=Rhône, 31=Haute-Garonne, None=All France
    departements = ["75", "69", "31", None]

    all_data = []
    for role in roles:
        for dept in departements:
            try:
                data = mod.get_francetravail_jobs(
                    access_token=token,
                    mots_cles=role,
                    code_departement=dept,
                    limit=100,
                )
                all_data.extend(data)
                time.sleep(1)
            except Exception as e:
                logger.error(f"❌ FranceTravail error for '{role}' (dept={dept}): {e}")

    count = _upload_records_to_minio("francetravail", all_data)
    context["task_instance"].xcom_push(key="francetravail_count", value=count)
    logger.info(f"🏁 France Travail ingestion complete: {count} records")
    return count


def ingest_remotive(**context):
    """Fetch Remotive remote job offers via API and upload to MinIO."""
    logger.info("🔎 Starting Remotive ingestion...")

    mod = _load_module("remotive_api", API_CLIENTS_DIR / "remotive_api.py")

    categories = ["data", "software-dev"]
    all_data = []

    for cat in categories:
        try:
            data = mod.get_remotive_jobs(category=cat)
            all_data.extend(data)
            time.sleep(1.5)
        except Exception as e:
            logger.error(f"❌ Remotive error for category '{cat}': {e}")

    count = _upload_records_to_minio("remotive", all_data)
    context["task_instance"].xcom_push(key="remotive_count", value=count)
    logger.info(f"🏁 Remotive ingestion complete: {count} records")
    return count


def ingest_themuse(**context):
    """Fetch TheMuse job offers via API and upload to MinIO."""
    logger.info("🔎 Starting TheMuse ingestion...")

    mod = _load_module("themuse_api", API_CLIENTS_DIR / "themuse_api.py")

    categories = ["Data and Analytics", "Software Engineering"]
    all_data = []

    for cat in categories:
        try:
            data = mod.get_themuse_jobs(category=cat, max_pages=3)
            all_data.extend(data)
            time.sleep(2)
        except Exception as e:
            logger.error(f"❌ TheMuse error for category '{cat}': {e}")

    count = _upload_records_to_minio("themuse", all_data)
    context["task_instance"].xcom_push(key="themuse_count", value=count)
    logger.info(f"🏁 TheMuse ingestion complete: {count} records")
    return count


def log_summary(**context):
    """Log a summary of all ingestion tasks."""
    ti = context["task_instance"]

    migrated = ti.xcom_pull(task_ids="migrate_bronze_to_minio", key="migrated_files") or 0
    indeed = ti.xcom_pull(task_ids="ingest_indeed", key="indeed_count") or 0
    linkedin = ti.xcom_pull(task_ids="ingest_linkedin", key="linkedin_count") or 0
    francetravail = ti.xcom_pull(task_ids="ingest_francetravail", key="francetravail_count") or 0
    remotive = ti.xcom_pull(task_ids="ingest_remotive", key="remotive_count") or 0
    themuse = ti.xcom_pull(task_ids="ingest_themuse", key="themuse_count") or 0

    total_scraped = indeed + linkedin + francetravail + remotive + themuse

    logger.info("=" * 65)
    logger.info("📊 SCRAPING AUTOMATION — EXECUTION SUMMARY")
    logger.info("=" * 65)
    logger.info(f"  📦 Bronze files migrated to MinIO : {migrated}")
    logger.info(f"  🔹 Indeed       : {indeed} records")
    logger.info(f"  🔹 LinkedIn     : {linkedin} records")
    logger.info(f"  🔹 FranceTravail: {francetravail} records")
    logger.info(f"  🔹 Remotive     : {remotive} records")
    logger.info(f"  🔹 TheMuse      : {themuse} records")
    logger.info(f"  ────────────────────────────────────")
    logger.info(f"  🏆 TOTAL SCRAPED: {total_scraped} records")
    logger.info("=" * 65)

    return {
        "migrated_files": migrated,
        "total_scraped": total_scraped,
        "by_source": {
            "indeed": indeed,
            "linkedin": linkedin,
            "francetravail": francetravail,
            "remotive": remotive,
            "themuse": themuse,
        },
    }


# ── DAG Definition ────────────────────────────────────

default_args = {
    "owner": "data-ami",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "start_date": datetime(2026, 5, 17),
    "email_on_failure": False,
    "email_on_retry": False,
}

with DAG(
    dag_id="scrapping_automate_dag",
    default_args=default_args,
    description="Automated scraping pipeline: scrape all job sources → upload JSONL to MinIO bronze bucket",
    schedule_interval="0 6 * * *",  # Daily at 06:00 UTC
    catchup=False,
    tags=["ingestion", "scraping", "minio", "bronze"],
    max_active_runs=1,
) as dag:

    # ── Task 0: Migrate existing local bronze files to MinIO ──
    t_migrate = PythonOperator(
        task_id="migrate_bronze_to_minio",
        python_callable=migrate_bronze_to_minio,
        doc="One-time migration of existing local bronze JSON files to MinIO (idempotent)",
    )

    # ── Tasks 1-5: Scrape / call APIs in parallel ──
    t_indeed = PythonOperator(
        task_id="ingest_indeed",
        python_callable=ingest_indeed,
        doc="Scrape Indeed job offers and upload JSONL to MinIO",
    )

    t_linkedin = PythonOperator(
        task_id="ingest_linkedin",
        python_callable=ingest_linkedin,
        doc="Scrape LinkedIn job offers and upload JSONL to MinIO",
    )

    t_francetravail = PythonOperator(
        task_id="ingest_francetravail",
        python_callable=ingest_francetravail,
        doc="Fetch France Travail jobs via API and upload JSONL to MinIO",
    )

    t_remotive = PythonOperator(
        task_id="ingest_remotive",
        python_callable=ingest_remotive,
        doc="Fetch Remotive remote jobs via API and upload JSONL to MinIO",
    )

    t_themuse = PythonOperator(
        task_id="ingest_themuse",
        python_callable=ingest_themuse,
        doc="Fetch TheMuse jobs via API and upload JSONL to MinIO",
    )

    # ── Task 6: Summary ──
    t_summary = PythonOperator(
        task_id="log_summary",
        python_callable=log_summary,
        trigger_rule="all_done",  # Run even if some scrapers fail
        doc="Log execution summary with record counts per source",
    )

    # ── DAG Flow ────────────────────────────────────────
    # 1. Migrate first, then scrape all sources in parallel, then summarize
    #
    #                 ┌─ ingest_indeed ───────┐
    #                 ├─ ingest_linkedin ─────┤
    # migrate_bronze ─┼─ ingest_francetravail ┼──► log_summary
    #                 ├─ ingest_remotive ─────┤
    #                 └─ ingest_themuse ──────┘

    scrapers = [t_indeed, t_linkedin, t_francetravail, t_remotive, t_themuse]
    t_migrate >> scrapers >> t_summary
