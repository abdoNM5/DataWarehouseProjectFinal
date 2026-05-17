# Data Talent Intelligence Platform

## Problem Statement
Data professionals must scan dozens of fragmented job boards with inconsistent titles, skills, and formats. This creates noisy searches, missed opportunities, and lengthy application cycles. Recruiters also struggle to surface qualified candidates quickly.

## Solution Scope
- Aggregate data-centric job postings from major sources (Indeed, LinkedIn, France-Travail, etc.) into a unified catalog.
- Normalize metadata (titles, skills, salary, location) and enrich it with NLP-driven tagging.
- Provide APIs and a web experience that deliver personalized recommendations, saved searches, and alerts for candidates.
- Supply internal analytics so the team can monitor ingestion health and marketplace KPIs.

## Success Metrics
- **Coverage**: ≥80% of relevant data job postings from target sources refreshed every 24 hours.
- **Relevance**: ≥25% lift in click-through rate on recommended jobs versus generic listings.
- **Latency**: API p95 response time under 400 ms for search/recommendation endpoints.
- **Reliability**: <1% failed ingestion runs per week with automated retries.

## Getting Started (Early Draft)
1. Copy `.env.example` to `.env` and configure source credentials plus service secrets.
2. Review `docs/architecture.md` for the high-level system map.
3. Align on schemas (`docs/schemas/`) and API contracts (`docs/api-contracts/`) before building collectors or services.
4. To run the ingestion DAGs locally, start Airflow: `docker compose up airflow-webserver airflow-scheduler` and visit http://localhost:8080 (user/pass `admin`).

## Recommendation Engine (NLP)

### Quick Start
1. Ensure the PostgreSQL Warehouse DB is running: `docker compose up -d warehouse-db`
2. Populate the NLP data:
   ```bash
   python -m nlp.populate_skills
   python -m nlp.generate_embeddings
   ```
3. Start the Backend and Frontend via Docker Compose (or run locally):
   ```bash
   docker compose up -d api frontend
   ```
4. Open the intelligent dashboard at [http://localhost:3000](http://localhost:3000)

### Architecture & APIs
- Full architectural details: [docs/nlp_architecture.md](docs/nlp_architecture.md)
- REST API Reference: [docs/api_reference.md](docs/api_reference.md)
