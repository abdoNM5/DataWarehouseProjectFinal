# Ingestion Layer

The ingestion package is responsible for pulling job postings from each external
source, normalizing them into the shared schema (see `docs/schemas/`), and
sending the payloads downstream to the data lake or queue.

This setup is scraping-first for Indeed, LinkedIn, and France Travail websites,
plus public APIs that do not require secrets (The Muse, Remotive).

## Components
- `collectors/` – Source-specific adapters built on a common base class.
- `orchestration/` – Airflow (or Prefect) DAGs that schedule collectors and
  ensure retries/backfills.
- `tests/` – Unit and contract tests that validate request/response handling.

## Data Storage (Cahier de charge alignment)
- Raw ingestion lands in local bronze layer under:
	`data_lake/bronze/<source>/ingestion_date=YYYY-MM-DD/*.jsonl`
- Next phase: transform bronze files to curated tables for recommendation and
	Power BI dashboards.

## Local Workflow
1. Copy `.env.example` into `.env` and configure `SCRAPE_QUERY`,
   `SCRAPE_LOCATION`, `SCRAPE_PAGES`.
2. Run a collector directly:
	```bash
	python -c "from ingestion.collectors.indeed_collector import IndeedCollector; print(len(list(IndeedCollector().run())))"
	```
3. Run Airflow DAG to persist JSONL into `data_lake/bronze`.

Actual production runs are triggered by the Airflow DAG in
`orchestration/job_ingestion_dag.py`.
