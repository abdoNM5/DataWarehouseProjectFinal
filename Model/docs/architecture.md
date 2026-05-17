# Architecture Overview

## High-Level Flow
1. **Ingestion** – Source-specific collectors pull job postings via APIs or scraping, validate against shared schemas, and land raw payloads in the object store.
2. **Processing** – ETL/NLP jobs normalize fields, enrich with taxonomy tags + embeddings, and load curated tables plus a vector index.
3. **Serving** – Backend services expose search/recommendation APIs; a web client consumes them to deliver personalized job feeds.
4. **Analytics** – Operational dashboards monitor ingestion health, recommendation performance, and funnel KPIs.

## Component Map
- **Collectors** (Python) running on schedulers (Airflow/Prefect) with retry + alerting.
- **Data Platform** built on cloud object storage, warehouse (Snowflake/BigQuery/Postgres), and pgvector/Pinecone for semantic search.
- **Processing Layer** using dbt/Spark for transformations and spaCy/SentenceTransformers for NLP enrichment.
- **Service Layer** anchored by FastAPI (public API) and a recommender microservice (feature retrieval, ranking).
- **Experience Layer** via React/Next.js front end and optional Power BI/Looker ops dashboards.

## Cross-Cutting Concerns
- IaC (Terraform) for reproducible environments.
- Observability (structured logging, metrics, tracing) across collectors and services.
- Security: secret management, OAuth for partners, RBAC for internal tooling.
