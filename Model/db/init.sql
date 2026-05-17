-- ============================================================
-- PROJET JOB INTELLIGENT — Data Warehouse DDL (Star Schema)
-- Auto-executed on first boot by docker-entrypoint-initdb.d
-- ============================================================

-- ── Dimension: Company ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_company (
    company_id    SERIAL PRIMARY KEY,
    company_name  VARCHAR(300) NOT NULL,
    industry      VARCHAR(150),
    company_size  VARCHAR(50)
);

-- ── Dimension: Location ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_location (
    location_id   SERIAL PRIMARY KEY,
    raw_location  TEXT NOT NULL,
    city          VARCHAR(150),
    region        VARCHAR(150),
    country       VARCHAR(100),
    country_code  CHAR(2),
    latitude      DECIMAL(9,6),
    longitude     DECIMAL(9,6)
);

-- ── Dimension: Job Title ────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_job_title (
    title_id         SERIAL PRIMARY KEY,
    raw_title        TEXT NOT NULL,
    normalised_title VARCHAR(200) NOT NULL,
    job_family       VARCHAR(100) NOT NULL,
    seniority_level  VARCHAR(50)
);

-- ── Dimension: Source ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_source (
    source_id     SERIAL PRIMARY KEY,
    platform_name VARCHAR(100) NOT NULL UNIQUE,
    platform_url  VARCHAR(300)
);

-- Seed data for sources
INSERT INTO dim_source (platform_name, platform_url) VALUES
    ('indeed',         'https://www.indeed.com'),
    ('linkedin',       'https://www.linkedin.com'),
    ('france_travail', 'https://candidat.francetravail.fr'),
    ('remotive',       'https://remotive.com'),
    ('the_muse',       'https://www.themuse.com'),
    ('glassdoor',      'https://www.glassdoor.com')
ON CONFLICT (platform_name) DO NOTHING;

-- ── Dimension: Date ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_date (
    date_id      INTEGER PRIMARY KEY,        -- YYYYMMDD format
    full_date    DATE NOT NULL UNIQUE,
    day          SMALLINT NOT NULL,
    month        SMALLINT NOT NULL,
    month_name   VARCHAR(20) NOT NULL,
    year         SMALLINT NOT NULL,
    quarter      SMALLINT NOT NULL,
    week_number  SMALLINT NOT NULL,
    day_of_week  VARCHAR(15) NOT NULL,
    is_weekend   BOOLEAN NOT NULL
);

-- Generate dates from 2024-01-01 to 2027-12-31
INSERT INTO dim_date (date_id, full_date, day, month, month_name, year, quarter, week_number, day_of_week, is_weekend)
SELECT
    TO_CHAR(d, 'YYYYMMDD')::INTEGER                          AS date_id,
    d                                                         AS full_date,
    EXTRACT(DAY FROM d)::SMALLINT                             AS day,
    EXTRACT(MONTH FROM d)::SMALLINT                           AS month,
    TO_CHAR(d, 'Month')                                       AS month_name,
    EXTRACT(YEAR FROM d)::SMALLINT                            AS year,
    EXTRACT(QUARTER FROM d)::SMALLINT                         AS quarter,
    EXTRACT(WEEK FROM d)::SMALLINT                            AS week_number,
    TO_CHAR(d, 'Day')                                         AS day_of_week,
    EXTRACT(ISODOW FROM d) IN (6, 7)                          AS is_weekend
FROM generate_series('2024-01-01'::DATE, '2027-12-31'::DATE, '1 day'::INTERVAL) AS d
ON CONFLICT (date_id) DO NOTHING;

-- ── Dimension: Contract Type ────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_contract_type (
    contract_id       SERIAL PRIMARY KEY,
    contract_label    VARCHAR(100) NOT NULL UNIQUE,
    contract_category VARCHAR(50) NOT NULL
);

-- Seed data for contract types
INSERT INTO dim_contract_type (contract_label, contract_category) VALUES
    ('Full-time',   'Permanent'),
    ('CDI',         'Permanent'),
    ('CDD',         'Temporary'),
    ('Contract',    'Temporary'),
    ('Freelance',   'Freelance'),
    ('Part-time',   'Part-time'),
    ('Internship',  'Internship'),
    ('Alternance',  'Internship'),
    ('Unknown',     'Unknown')
ON CONFLICT (contract_label) DO NOTHING;

-- ── Dimension: Skill ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_skill (
    skill_id       SERIAL PRIMARY KEY,
    skill_name     VARCHAR(100) NOT NULL UNIQUE,
    skill_category VARCHAR(50) NOT NULL
);

-- Seed data for skills taxonomy
INSERT INTO dim_skill (skill_name, skill_category) VALUES
    -- Programming
    ('Python', 'Programming'), ('R', 'Programming'), ('Java', 'Programming'),
    ('Scala', 'Programming'), ('SQL', 'Programming'), ('JavaScript', 'Programming'),
    ('C++', 'Programming'), ('Go', 'Programming'), ('Rust', 'Programming'),
    ('Shell', 'Programming'), ('Bash', 'Programming'), ('SAS', 'Programming'),
    ('MATLAB', 'Programming'), ('Julia', 'Programming'),
    -- Databases
    ('PostgreSQL', 'Databases'), ('MySQL', 'Databases'), ('MongoDB', 'Databases'),
    ('Redis', 'Databases'), ('Elasticsearch', 'Databases'), ('Oracle', 'Databases'),
    ('SQL Server', 'Databases'), ('Cassandra', 'Databases'), ('DynamoDB', 'Databases'),
    ('Neo4j', 'Databases'), ('SQLite', 'Databases'),
    -- Cloud
    ('AWS', 'Cloud'), ('Azure', 'Cloud'), ('GCP', 'Cloud'),
    ('Databricks', 'Cloud'), ('Snowflake', 'Cloud'), ('BigQuery', 'Cloud'),
    ('Redshift', 'Cloud'), ('S3', 'Cloud'), ('Lambda', 'Cloud'),
    -- Big Data
    ('Spark', 'Big Data'), ('Kafka', 'Big Data'), ('Hadoop', 'Big Data'),
    ('Airflow', 'Big Data'), ('Flink', 'Big Data'), ('Hive', 'Big Data'),
    ('Presto', 'Big Data'), ('dbt', 'Big Data'), ('NiFi', 'Big Data'),
    ('Beam', 'Big Data'), ('Prefect', 'Big Data'), ('Luigi', 'Big Data'),
    -- ML / AI
    ('TensorFlow', 'ML/AI'), ('PyTorch', 'ML/AI'), ('scikit-learn', 'ML/AI'),
    ('Keras', 'ML/AI'), ('XGBoost', 'ML/AI'), ('LightGBM', 'ML/AI'),
    ('NLP', 'ML/AI'), ('Computer Vision', 'ML/AI'), ('Deep Learning', 'ML/AI'),
    ('Machine Learning', 'ML/AI'), ('MLflow', 'ML/AI'), ('Hugging Face', 'ML/AI'),
    ('OpenCV', 'ML/AI'), ('spaCy', 'ML/AI'), ('LLM', 'ML/AI'),
    ('GenAI', 'ML/AI'), ('RAG', 'ML/AI'),
    -- BI & Visualization
    ('Power BI', 'BI & Visualization'), ('Tableau', 'BI & Visualization'),
    ('Looker', 'BI & Visualization'), ('Qlik', 'BI & Visualization'),
    ('Metabase', 'BI & Visualization'), ('Grafana', 'BI & Visualization'),
    ('D3.js', 'BI & Visualization'), ('Matplotlib', 'BI & Visualization'),
    ('Plotly', 'BI & Visualization'), ('Seaborn', 'BI & Visualization'),
    -- DevOps
    ('Docker', 'DevOps'), ('Kubernetes', 'DevOps'), ('Git', 'DevOps'),
    ('CI/CD', 'DevOps'), ('Terraform', 'DevOps'), ('Ansible', 'DevOps'),
    ('Jenkins', 'DevOps'), ('GitHub Actions', 'DevOps'), ('Linux', 'DevOps'),
    -- Data Formats & Tools
    ('Pandas', 'Data Tools'), ('NumPy', 'Data Tools'), ('PySpark', 'Data Tools'),
    ('Excel', 'Data Tools'), ('JSON', 'Data Tools'), ('Parquet', 'Data Tools'),
    ('Avro', 'Data Tools'), ('CSV', 'Data Tools'), ('API', 'Data Tools'),
    ('REST', 'Data Tools'), ('GraphQL', 'Data Tools'), ('ETL', 'Data Tools'),
    -- Soft Skills
    ('Agile', 'Soft Skills'), ('Scrum', 'Soft Skills'), ('Communication', 'Soft Skills'),
    ('Leadership', 'Soft Skills'), ('Problem Solving', 'Soft Skills'),
    ('Teamwork', 'Soft Skills'), ('Project Management', 'Soft Skills')
ON CONFLICT (skill_name) DO NOTHING;

-- ── Fact: Job Offer ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fact_job_offer (
    offer_id          SERIAL PRIMARY KEY,

    -- Foreign Keys
    dim_company_id    INTEGER NOT NULL REFERENCES dim_company(company_id),
    dim_location_id   INTEGER NOT NULL REFERENCES dim_location(location_id),
    dim_title_id      INTEGER NOT NULL REFERENCES dim_job_title(title_id),
    dim_source_id     INTEGER NOT NULL REFERENCES dim_source(source_id),
    dim_date_id       INTEGER NOT NULL REFERENCES dim_date(date_id),
    dim_contract_id   INTEGER NOT NULL REFERENCES dim_contract_type(contract_id),

    -- Measures
    salary_min        DECIMAL(12,2),
    salary_max        DECIMAL(12,2),
    currency          CHAR(3) DEFAULT 'EUR',

    -- Degenerate Dimensions
    description_raw   TEXT,
    description_clean TEXT,
    url               TEXT,
    source_job_id     VARCHAR(200),

    -- Metadata
    ingestion_ts      TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Uniqueness constraint
    UNIQUE (source_job_id, dim_source_id)
);

-- ── Bridge: Offer ↔ Skill ───────────────────────────────────
CREATE TABLE IF NOT EXISTS bridge_offer_skill (
    offer_id         INTEGER NOT NULL REFERENCES fact_job_offer(offer_id) ON DELETE CASCADE,
    skill_id         INTEGER NOT NULL REFERENCES dim_skill(skill_id),
    confidence_score DECIMAL(3,2) DEFAULT 1.00,

    PRIMARY KEY (offer_id, skill_id)
);

-- ── Performance Indexes ─────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_fact_company    ON fact_job_offer(dim_company_id);
CREATE INDEX IF NOT EXISTS idx_fact_location   ON fact_job_offer(dim_location_id);
CREATE INDEX IF NOT EXISTS idx_fact_title      ON fact_job_offer(dim_title_id);
CREATE INDEX IF NOT EXISTS idx_fact_source     ON fact_job_offer(dim_source_id);
CREATE INDEX IF NOT EXISTS idx_fact_date       ON fact_job_offer(dim_date_id);
CREATE INDEX IF NOT EXISTS idx_fact_contract   ON fact_job_offer(dim_contract_id);
CREATE INDEX IF NOT EXISTS idx_bridge_skill    ON bridge_offer_skill(skill_id);
CREATE INDEX IF NOT EXISTS idx_fact_source_job ON fact_job_offer(source_job_id, dim_source_id);
CREATE INDEX IF NOT EXISTS idx_location_city   ON dim_location(city);
CREATE INDEX IF NOT EXISTS idx_location_country ON dim_location(country_code);
CREATE INDEX IF NOT EXISTS idx_skill_name      ON dim_skill(skill_name);
CREATE INDEX IF NOT EXISTS idx_title_family    ON dim_job_title(job_family);
