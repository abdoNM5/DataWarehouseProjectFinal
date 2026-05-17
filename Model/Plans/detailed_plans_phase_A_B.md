# 🔬 Detailed Sub-Plans — Phase A & B

> Based on your star schema with `fact_job_offer` (center), 6 dimension tables (`dim_company`, `dim_location`, `dim_job_title`, `dim_source`, `dim_date`, `dim_contract_type`), `dim_skill`, and the `bridge_offer_skill` bridge table.

---

## Phase A — Skills Extraction Module (Days 1-3)

---

### Step A.1 — Create the Skills Taxonomy File

**File:** `nlp/skills_taxonomy.py`

#### A.1.1 — Set up the `nlp/` package

1. Create directory `nlp/` at the project root (same level as `api/`, `db/`, `etl/`)
2. Create `nlp/__init__.py` (empty file — makes it a Python package)
3. Create `nlp/skills_taxonomy.py`

#### A.1.2 — Extract skills from `init.sql`

Open `db/init.sql` lines 110-157. You'll see all the seeded skills. Your taxonomy dict must **mirror exactly** what's in that SQL so `skill_name` values match the DB.

Build this structure:

```python
SKILLS_BY_CATEGORY = {
    "Programming": [
        "Python", "R", "Java", "Scala", "SQL", "JavaScript",
        "C++", "Go", "Rust", "Shell", "Bash", "SAS", "MATLAB", "Julia"
    ],
    "Databases": [
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
        "Oracle", "SQL Server", "Cassandra", "DynamoDB", "Neo4j", "SQLite"
    ],
    "Cloud": [
        "AWS", "Azure", "GCP", "Databricks", "Snowflake",
        "BigQuery", "Redshift", "S3", "Lambda"
    ],
    "Big Data": [
        "Spark", "Kafka", "Hadoop", "Airflow", "Flink", "Hive",
        "Presto", "dbt", "NiFi", "Beam", "Prefect", "Luigi"
    ],
    "ML/AI": [
        "TensorFlow", "PyTorch", "scikit-learn", "Keras", "XGBoost",
        "LightGBM", "NLP", "Computer Vision", "Deep Learning",
        "Machine Learning", "MLflow", "Hugging Face", "OpenCV",
        "spaCy", "LLM", "GenAI", "RAG"
    ],
    "BI & Visualization": [
        "Power BI", "Tableau", "Looker", "Qlik", "Metabase",
        "Grafana", "D3.js", "Matplotlib", "Plotly", "Seaborn"
    ],
    "DevOps": [
        "Docker", "Kubernetes", "Git", "CI/CD", "Terraform",
        "Ansible", "Jenkins", "GitHub Actions", "Linux"
    ],
    "Data Tools": [
        "Pandas", "NumPy", "PySpark", "Excel", "JSON", "Parquet",
        "Avro", "CSV", "API", "REST", "GraphQL", "ETL"
    ],
    "Soft Skills": [
        "Agile", "Scrum", "Communication", "Leadership",
        "Problem Solving", "Teamwork", "Project Management"
    ],
}
```

#### A.1.3 — Build the aliases dictionary

Think about how skills are written differently in job descriptions. Map every variant → canonical name (the one in `dim_skill`):

```python
SKILL_ALIASES = {
    # Programming aliases
    "python3": "Python",
    "py": "Python",
    "r language": "R",
    "r-lang": "R",
    "js": "JavaScript",
    "node.js": "JavaScript",
    "nodejs": "JavaScript",
    "c/c++": "C++",
    "cpp": "C++",
    "golang": "Go",
    "shell scripting": "Shell",
    "bash scripting": "Bash",

    # Database aliases
    "postgres": "PostgreSQL",
    "pg": "PostgreSQL",
    "psql": "PostgreSQL",
    "mongo": "MongoDB",
    "elastic": "Elasticsearch",
    "mssql": "SQL Server",
    "ms sql": "SQL Server",
    "dynamodb": "DynamoDB",

    # Cloud aliases
    "amazon web services": "AWS",
    "amazon aws": "AWS",
    "google cloud": "GCP",
    "google cloud platform": "GCP",
    "microsoft azure": "Azure",
    "azure cloud": "Azure",
    "aws s3": "S3",
    "aws lambda": "Lambda",

    # Big Data aliases
    "apache spark": "Spark",
    "pyspark": "Spark",
    "apache kafka": "Kafka",
    "apache airflow": "Airflow",
    "apache flink": "Flink",
    "apache hadoop": "Hadoop",
    "apache hive": "Hive",
    "apache beam": "Beam",
    "apache nifi": "NiFi",

    # ML/AI aliases
    "tf": "TensorFlow",
    "tensorflow2": "TensorFlow",
    "sklearn": "scikit-learn",
    "sk-learn": "scikit-learn",
    "sci-kit learn": "scikit-learn",
    "xgb": "XGBoost",
    "lgbm": "LightGBM",
    "light gbm": "LightGBM",
    "natural language processing": "NLP",
    "cv": "Computer Vision",
    "dl": "Deep Learning",
    "ml": "Machine Learning",
    "ml ops": "MLflow",
    "mlops": "MLflow",
    "huggingface": "Hugging Face",
    "hf": "Hugging Face",
    "large language model": "LLM",
    "large language models": "LLM",
    "generative ai": "GenAI",
    "gen ai": "GenAI",
    "retrieval augmented generation": "RAG",

    # BI aliases
    "powerbi": "Power BI",
    "power-bi": "Power BI",
    "d3": "D3.js",
    "mpl": "Matplotlib",

    # DevOps aliases
    "k8s": "Kubernetes",
    "kube": "Kubernetes",
    "github": "Git",
    "gitlab": "Git",
    "ci cd": "CI/CD",
    "cicd": "CI/CD",
    "github-actions": "GitHub Actions",

    # Data Tools aliases
    "pd": "Pandas",
    "np": "NumPy",
    "numpy": "NumPy",
    "restful": "REST",
    "rest api": "REST",
    "restful api": "REST",
}
```

#### A.1.4 — Add a helper: flat skill list

```python
# Flatten all skills into one set for fast lookup
ALL_SKILLS = set()
for category, skills in SKILLS_BY_CATEGORY.items():
    for skill in skills:
        ALL_SKILLS.add(skill.lower())  # lowercase for matching

# Also add all aliases
ALL_ALIAS_KEYS = set(SKILL_ALIASES.keys())
```

#### A.1.5 — Verify against DB

Write a quick test (run manually once):

```python
# test_taxonomy.py (scratch file)
import psycopg2

conn = psycopg2.connect("postgresql://warehouse:warehouse@localhost:5433/jobs_dw")
cur = conn.cursor()
cur.execute("SELECT skill_name FROM dim_skill")
db_skills = {row[0] for row in cur.fetchall()}

taxonomy_skills = set()
for skills in SKILLS_BY_CATEGORY.values():
    taxonomy_skills.update(skills)

# These should both be empty:
print("In DB but not in taxonomy:", db_skills - taxonomy_skills)
print("In taxonomy but not in DB:", taxonomy_skills - db_skills)
```

> [!IMPORTANT]
> If there's a mismatch, update your taxonomy OR update the DB. They must be in sync or `skill_id` lookups will fail in Step A.3.

---

### Step A.2 — Build the Skills Extractor

**File:** `nlp/skills_extractor.py`

#### A.2.1 — Import the taxonomy

```python
import re
from nlp.skills_taxonomy import SKILLS_BY_CATEGORY, SKILL_ALIASES
```

#### A.2.2 — Build a lookup dict on module load

When the module is imported, build a fast lookup structure:

```python
# Build: canonical_skill_lower → canonical_skill
_CANONICAL = {}
for category, skills in SKILLS_BY_CATEGORY.items():
    for skill in skills:
        _CANONICAL[skill.lower()] = skill

# Build: alias_lower → canonical_skill
_ALIASES = {alias.lower(): canonical for alias, canonical in SKILL_ALIASES.items()}
```

#### A.2.3 — Implement word-boundary matching

Simple `in` checks cause false positives (e.g., "R" matches "Required"). Use **word boundaries**:

```python
def _build_pattern(term: str) -> re.Pattern:
    """Build a regex pattern with word boundaries for a skill term."""
    escaped = re.escape(term)
    # Special case: single-char skills like "R" need strict boundaries
    if len(term) <= 2:
        return re.compile(rf'(?<![a-zA-Z]){escaped}(?![a-zA-Z])', re.IGNORECASE)
    return re.compile(rf'\b{escaped}\b', re.IGNORECASE)

# Pre-compile all patterns at module load
_SKILL_PATTERNS = {}
for lower_skill, canonical in _CANONICAL.items():
    _SKILL_PATTERNS[canonical] = _build_pattern(canonical)

_ALIAS_PATTERNS = {}
for lower_alias, canonical in _ALIASES.items():
    _ALIAS_PATTERNS[lower_alias] = (_build_pattern(lower_alias), canonical)
```

#### A.2.4 — Implement `extract_skills()`

```python
def extract_skills(description: str) -> list[tuple[str, float]]:
    """
    Extract skills from a job description using keyword + alias matching.

    Returns:
        List of (canonical_skill_name, confidence_score) tuples.
        confidence_score = 1.0 for exact keyword match.
    """
    if not description or not description.strip():
        return []

    found_skills: dict[str, float] = {}

    # 1. Check canonical skill names
    for canonical, pattern in _SKILL_PATTERNS.items():
        if pattern.search(description):
            found_skills[canonical] = 1.0

    # 2. Check aliases (only if canonical not already found)
    for alias_lower, (pattern, canonical) in _ALIAS_PATTERNS.items():
        if canonical not in found_skills and pattern.search(description):
            found_skills[canonical] = 1.0  # alias = same confidence

    # 3. Sort by skill name for consistent output
    return sorted(found_skills.items(), key=lambda x: x[0])
```

#### A.2.5 — Manual test on sample descriptions

Create `nlp/test_extractor.py`:

```python
from nlp.skills_extractor import extract_skills

# Test 1: English description
desc1 = """
We are looking for a Data Engineer with strong Python and SQL skills.
Experience with Apache Spark, Kafka, and AWS (S3, Lambda) is required.
Knowledge of Docker and Kubernetes (k8s) is a plus.
"""

# Test 2: French description
desc2 = """
Nous recherchons un ingénieur data maîtrisant Python, PostgreSQL et Spark.
Une expérience avec TensorFlow ou PyTorch est appréciée.
Environnement Agile / Scrum.
"""

for i, desc in enumerate([desc1, desc2], 1):
    skills = extract_skills(desc)
    print(f"\n--- Test {i} ---")
    for skill, score in skills:
        print(f"  {skill}: {score}")
```

**Expected output for Test 1:** Python, SQL, Spark, Kafka, AWS, S3, Lambda, Docker, Kubernetes

> [!TIP]
> If "R" is matching inside words like "Required" or "Engineer", your word-boundary regex is wrong. Debug the pattern for single-character skills specifically.

---

### Step A.3 — Populate `bridge_offer_skill` Table

**File:** `nlp/populate_skills.py`

#### A.3.1 — Database connection helper

Create `nlp/db_utils.py` (reused in Phase B and C too):

```python
import psycopg2
from contextlib import contextmanager

DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "jobs_dw",
    "user": "warehouse",
    "password": "warehouse",
}

@contextmanager
def get_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        conn.close()

@contextmanager
def get_cursor(conn, commit=True):
    cur = conn.cursor()
    try:
        yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
```

#### A.3.2 — Build the skill_name → skill_id mapping

```python
def load_skill_id_map(cur) -> dict[str, int]:
    """Load {skill_name: skill_id} from dim_skill."""
    cur.execute("SELECT skill_id, skill_name FROM dim_skill")
    return {name: sid for sid, name in cur.fetchall()}
```

#### A.3.3 — Fetch offers that need processing

```python
def get_unprocessed_offers(cur) -> list[tuple[int, str]]:
    """Get offers that don't yet have skills in bridge_offer_skill."""
    cur.execute("""
        SELECT f.offer_id, f.description_clean
        FROM fact_job_offer f
        LEFT JOIN bridge_offer_skill b ON f.offer_id = b.offer_id
        WHERE b.offer_id IS NULL
          AND f.description_clean IS NOT NULL
          AND f.description_clean != ''
    """)
    return cur.fetchall()
```

#### A.3.4 — Insert skills into bridge table

```python
def insert_offer_skills(cur, offer_id: int, skills: list[tuple[str, float]], skill_map: dict):
    """Insert extracted skills into bridge_offer_skill."""
    for skill_name, confidence in skills:
        skill_id = skill_map.get(skill_name)
        if skill_id is None:
            continue  # skill not in dim_skill, skip
        cur.execute("""
            INSERT INTO bridge_offer_skill (offer_id, skill_id, confidence_score)
            VALUES (%s, %s, %s)
            ON CONFLICT (offer_id, skill_id) DO NOTHING
        """, (offer_id, skill_id, confidence))
```

#### A.3.5 — Main script with progress tracking

```python
from nlp.skills_extractor import extract_skills
from nlp.db_utils import get_connection, get_cursor

def main():
    with get_connection() as conn:
        with get_cursor(conn, commit=False) as cur:
            # 1. Load skill map
            skill_map = load_skill_id_map(cur)
            print(f"Loaded {len(skill_map)} skills from dim_skill")

            # 2. Get unprocessed offers
            offers = get_unprocessed_offers(cur)
            print(f"Found {len(offers)} offers to process")

            # 3. Process each offer
            total_skills_inserted = 0
            for i, (offer_id, description) in enumerate(offers):
                skills = extract_skills(description)
                insert_offer_skills(cur, offer_id, skills, skill_map)
                total_skills_inserted += len(skills)

                if (i + 1) % 100 == 0:
                    conn.commit()  # commit every 100 offers
                    print(f"  Processed {i+1}/{len(offers)} offers...")

            conn.commit()  # final commit

    print(f"\nDone! Inserted {total_skills_inserted} skill links for {len(offers)} offers.")

if __name__ == "__main__":
    main()
```

#### A.3.6 — Verify results in SQL

After running, check:

```sql
-- How many links were created?
SELECT COUNT(*) FROM bridge_offer_skill;

-- Top 10 most common skills
SELECT s.skill_name, s.skill_category, COUNT(*) as offer_count
FROM bridge_offer_skill b
JOIN dim_skill s ON b.skill_id = s.skill_id
GROUP BY s.skill_name, s.skill_category
ORDER BY offer_count DESC
LIMIT 10;

-- Sample: skills for a specific offer
SELECT f.offer_id, s.skill_name, b.confidence_score
FROM bridge_offer_skill b
JOIN fact_job_offer f ON b.offer_id = f.offer_id
JOIN dim_skill s ON b.skill_id = s.skill_id
WHERE f.offer_id = 1;
```

---

## Phase B — Sentence Embeddings (Days 4-6)

---

### Step B.1 — Install Dependencies

#### B.1.1 — Create `nlp/requirements.txt`

```
sentence-transformers==3.0.1
torch>=2.0.0
scikit-learn>=1.3.0
psycopg2-binary>=2.9.9
numpy>=1.24.0
```

#### B.1.2 — Install in your environment

```bash
pip install -r nlp/requirements.txt
```

> [!NOTE]
> This downloads ~2GB (PyTorch for CPU). Make sure you have disk space. If on a slow connection, it may take 10-15 min.

#### B.1.3 — Verify installation

```python
# quick_test.py
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
vec = model.encode("test sentence")
print(f"Vector shape: {vec.shape}")  # Should print: (384,)
print(f"First 5 values: {vec[:5]}")
print("✅ Installation OK!")
```

---

### Step B.2 — Build the Embedding Module

**File:** `nlp/embeddings.py`

#### B.2.1 — Singleton model loading

The model is ~500MB in memory. Load it ONCE, not on every call:

```python
import numpy as np
from sentence_transformers import SentenceTransformer

_MODEL = None

def _get_model() -> SentenceTransformer:
    """Lazy-load the model (singleton pattern)."""
    global _MODEL
    if _MODEL is None:
        print("Loading SentenceTransformer model (first time, ~5 seconds)...")
        _MODEL = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        print("Model loaded ✅")
    return _MODEL
```

#### B.2.2 — Single text encoding

```python
def encode_text(text: str) -> np.ndarray:
    """
    Encode a single text into a 384-dimensional vector.
    The vector is L2-normalized (unit length), so cosine similarity = dot product.

    Args:
        text: any string (job description, candidate profile, etc.)

    Returns:
        np.ndarray of shape (384,) with float32 values
    """
    model = _get_model()
    return model.encode(text, normalize_embeddings=True)
```

#### B.2.3 — Batch encoding (for processing all offers)

```python
def encode_batch(texts: list[str], batch_size: int = 32) -> np.ndarray:
    """
    Encode multiple texts at once (much faster than one-by-one).

    Args:
        texts: list of N strings
        batch_size: how many texts to process at once (32 is good for CPU)

    Returns:
        np.ndarray of shape (N, 384)
    """
    model = _get_model()
    return model.encode(
        texts,
        normalize_embeddings=True,
        batch_size=batch_size,
        show_progress_bar=True,
    )
```

#### B.2.4 — Serialization helpers (for DB storage)

```python
import json

def embedding_to_json(embedding: np.ndarray) -> str:
    """Convert a 384-d numpy array to a JSON string for JSONB storage."""
    return json.dumps(embedding.tolist())

def json_to_embedding(json_str: str) -> np.ndarray:
    """Convert a JSON string back to a numpy array."""
    return np.array(json.loads(json_str), dtype=np.float32)
```

#### B.2.5 — Test the module

```python
# test_embeddings.py
from nlp.embeddings import encode_text, encode_batch
import numpy as np

# Test single encode
v1 = encode_text("Data engineer with Python and Spark experience")
v2 = encode_text("Python developer for big data pipelines")
v3 = encode_text("Marketing manager for luxury brands")

# Cosine similarity (since normalized, just dot product)
sim_12 = np.dot(v1, v2)  # Should be HIGH (~0.6-0.8)
sim_13 = np.dot(v1, v3)  # Should be LOW (~0.1-0.3)

print(f"Data Eng vs Python Big Data: {sim_12:.4f}")  # expect ~0.7
print(f"Data Eng vs Marketing:       {sim_13:.4f}")  # expect ~0.2

# Test batch
texts = ["Hello world", "Bonjour le monde", "Hola mundo"]
vecs = encode_batch(texts)
print(f"Batch shape: {vecs.shape}")  # (3, 384)
```

---

### Step B.3 — Add Embedding Column to Database

**File:** `db/migrations/add_embeddings.sql`

#### B.3.1 — Create migrations directory

```
db/
├── init.sql          ← existing
└── migrations/
    └── add_embeddings.sql   ← NEW
```

#### B.3.2 — Write the migration (JSONB approach)

```sql
-- Migration: Add embedding column to fact_job_offer
-- Run this ONCE after the initial schema is created

-- Option 1: JSONB (simple, recommended to start)
ALTER TABLE fact_job_offer
ADD COLUMN IF NOT EXISTS embedding JSONB;

-- Index for checking which offers need embeddings
CREATE INDEX IF NOT EXISTS idx_fact_embedding_null
ON fact_job_offer (offer_id)
WHERE embedding IS NULL;

-- Verify
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'fact_job_offer' AND column_name = 'embedding';
```

#### B.3.3 — Run the migration

```bash
psql -h localhost -p 5433 -U warehouse -d jobs_dw -f db/migrations/add_embeddings.sql
```

Or from Python:

```python
from nlp.db_utils import get_connection, get_cursor

with get_connection() as conn:
    with get_cursor(conn) as cur:
        cur.execute("""
            ALTER TABLE fact_job_offer
            ADD COLUMN IF NOT EXISTS embedding JSONB
        """)
        print("Column added ✅")
```

---

### Step B.4 — Generate Embeddings for All Offers

**File:** `nlp/generate_embeddings.py`

#### B.4.1 — Fetch offers without embeddings

```python
from nlp.db_utils import get_connection, get_cursor
from nlp.embeddings import encode_batch, embedding_to_json
import time

def get_offers_without_embeddings(cur) -> list[tuple[int, str]]:
    """Get offers where embedding IS NULL and description_clean exists."""
    cur.execute("""
        SELECT offer_id, description_clean
        FROM fact_job_offer
        WHERE embedding IS NULL
          AND description_clean IS NOT NULL
          AND description_clean != ''
        ORDER BY offer_id
    """)
    return cur.fetchall()
```

#### B.4.2 — Process in batches and store

```python
def generate_and_store_embeddings(batch_size: int = 64):
    """Main function: encode all descriptions and store in DB."""
    start = time.time()

    with get_connection() as conn:
        with get_cursor(conn, commit=False) as cur:
            # 1. Fetch offers
            offers = get_offers_without_embeddings(cur)
            print(f"Found {len(offers)} offers without embeddings")

            if not offers:
                print("Nothing to do!")
                return

            # 2. Separate IDs and texts
            offer_ids = [o[0] for o in offers]
            descriptions = [o[1] for o in offers]

            # 3. Encode all at once (the model handles batching internally)
            print(f"Encoding {len(descriptions)} descriptions...")
            embeddings = encode_batch(descriptions, batch_size=batch_size)
            print(f"Encoding done in {time.time() - start:.1f}s")

            # 4. Store each embedding back in the DB
            print("Storing embeddings in database...")
            for i, (oid, emb) in enumerate(zip(offer_ids, embeddings)):
                json_emb = embedding_to_json(emb)
                cur.execute(
                    "UPDATE fact_job_offer SET embedding = %s WHERE offer_id = %s",
                    (json_emb, oid)
                )
                if (i + 1) % 200 == 0:
                    conn.commit()
                    print(f"  Stored {i+1}/{len(offer_ids)}...")

            conn.commit()

    elapsed = time.time() - start
    print(f"\n✅ Done! Encoded {len(offer_ids)} offers in {elapsed:.1f}s")
```

#### B.4.3 — Main entry point

```python
if __name__ == "__main__":
    generate_and_store_embeddings()
```

#### B.4.4 — Verify stored embeddings

```sql
-- Check count
SELECT COUNT(*) FROM fact_job_offer WHERE embedding IS NOT NULL;

-- Check vector length (should be 384)
SELECT offer_id, jsonb_array_length(embedding) as vec_length
FROM fact_job_offer
WHERE embedding IS NOT NULL
LIMIT 5;

-- Check a sample value
SELECT offer_id, embedding->0 as first_dim
FROM fact_job_offer
WHERE embedding IS NOT NULL
LIMIT 3;
```
