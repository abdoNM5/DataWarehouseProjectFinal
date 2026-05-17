# 🔬 Detailed Sub-Plans — Phase C & D

---

## Phase C — Recommendation Engine (Days 7-9)

---

### Step C.1 — Build the Recommender

**File:** `nlp/recommender.py`

#### C.1.1 — Load all offer embeddings from DB

```python
import numpy as np
from nlp.db_utils import get_connection, get_cursor
from nlp.embeddings import encode_text, json_to_embedding

def _load_all_offers(cur) -> tuple[list[dict], np.ndarray]:
    """
    Load all offers with their embeddings from the warehouse.
    Returns (offer_metadata_list, embedding_matrix).
    """
    cur.execute("""
        SELECT
            f.offer_id,
            jt.normalised_title,
            c.company_name,
            l.city,
            f.salary_min,
            f.salary_max,
            f.currency,
            f.embedding
        FROM fact_job_offer f
        JOIN dim_job_title jt ON f.dim_title_id = jt.title_id
        JOIN dim_company c ON f.dim_company_id = c.company_id
        JOIN dim_location l ON f.dim_location_id = l.location_id
        WHERE f.embedding IS NOT NULL
    """)
    rows = cur.fetchall()

    offers = []
    embeddings = []
    for row in rows:
        offers.append({
            "offer_id": row[0],
            "title": row[1],
            "company": row[2],
            "city": row[3],
            "salary_min": float(row[4]) if row[4] else None,
            "salary_max": float(row[5]) if row[5] else None,
            "currency": row[6],
        })
        embeddings.append(json_to_embedding(row[7]))

    return offers, np.array(embeddings)  # shape: (N, 384)
```

#### C.1.2 — Load skills per offer from bridge table

```python
def _load_offer_skills(cur) -> dict[int, set[str]]:
    """
    Load {offer_id: {skill1, skill2, ...}} from bridge_offer_skill.
    """
    cur.execute("""
        SELECT b.offer_id, s.skill_name
        FROM bridge_offer_skill b
        JOIN dim_skill s ON b.skill_id = s.skill_id
    """)
    result: dict[int, set[str]] = {}
    for offer_id, skill_name in cur.fetchall():
        result.setdefault(offer_id, set()).add(skill_name)
    return result
```

#### C.1.3 — Compute skill overlap score

```python
def _skill_score(candidate_skills: set[str], offer_skills: set[str]) -> tuple[float, list, list]:
    """
    Compute skill overlap between candidate and offer.
    Returns (score, matched_list, missing_list).
    """
    if not candidate_skills:
        return 0.0, [], []

    matched = candidate_skills & offer_skills
    missing = candidate_skills - offer_skills
    score = len(matched) / len(candidate_skills) if candidate_skills else 0.0
    return score, sorted(matched), sorted(missing)
```

#### C.1.4 — Main `recommend()` function

```python
from sklearn.metrics.pairwise import cosine_similarity

def recommend(
    candidate_text: str,
    candidate_skills: list[str],
    top_k: int = 10,
    alpha: float = 0.6,
) -> list[dict]:
    """
    Hybrid recommendation: semantic similarity + skill matching.

    Formula: final_score = alpha * semantic_score + (1 - alpha) * skill_score

    Args:
        candidate_text: free-text description of ideal job
        candidate_skills: list of skill names the candidate has
        top_k: number of results to return
        alpha: weight for semantic vs skill (0.6 = 60% semantic)

    Returns:
        List of top-K offer dicts sorted by final_score descending.
    """
    # 1. Encode the candidate text
    candidate_emb = encode_text(candidate_text).reshape(1, -1)  # (1, 384)
    candidate_skill_set = set(candidate_skills)

    # 2. Load all offers from DB
    with get_connection() as conn:
        with get_cursor(conn, commit=False) as cur:
            offers, offer_embeddings = _load_all_offers(cur)
            offer_skills_map = _load_offer_skills(cur)

    if not offers:
        return []

    # 3. Compute semantic similarity (candidate vs ALL offers at once)
    similarities = cosine_similarity(candidate_emb, offer_embeddings)[0]  # shape: (N,)

    # 4. Combine scores
    results = []
    for i, offer in enumerate(offers):
        oid = offer["offer_id"]
        semantic = float(similarities[i])

        offer_sk = offer_skills_map.get(oid, set())
        skill_sc, matched, missing = _skill_score(candidate_skill_set, offer_sk)

        final = alpha * semantic + (1 - alpha) * skill_sc

        results.append({
            **offer,
            "match_score": round(final, 4),
            "semantic_score": round(semantic, 4),
            "skill_score": round(skill_sc, 4),
            "matched_skills": matched,
            "missing_skills": missing,
        })

    # 5. Sort by final score and return top-K
    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results[:top_k]
```

---

### Step C.2 — Test with Synthetic Profiles

**File:** `nlp/test_recommender.py`

#### C.2.1 — Define test profiles

```python
PROFILES = [
    {
        "name": "Junior Data Engineer",
        "text": "Computer science student looking for a data engineering internship. I know Python, SQL, and have basic knowledge of Spark and Airflow.",
        "skills": ["Python", "SQL", "Spark", "Git", "Docker"],
        "expected_families": ["Data Engineer"],
    },
    {
        "name": "ML Engineer",
        "text": "Machine learning engineer with experience in PyTorch, NLP, and model deployment on AWS.",
        "skills": ["Python", "PyTorch", "scikit-learn", "Docker", "AWS"],
        "expected_families": ["ML Engineer", "Data Scientist"],
    },
    {
        "name": "Data Analyst",
        "text": "Analyst with strong SQL and visualization skills. Experience with Power BI dashboards and Excel reporting.",
        "skills": ["SQL", "Power BI", "Excel", "Python", "Tableau"],
        "expected_families": ["Data Analyst", "Business Analyst"],
    },
]
```

#### C.2.2 — Run and print results

```python
from nlp.recommender import recommend

for profile in PROFILES:
    print(f"\n{'='*60}")
    print(f"Profile: {profile['name']}")
    print(f"Skills: {', '.join(profile['skills'])}")
    print(f"{'='*60}")

    results = recommend(
        candidate_text=profile["text"],
        candidate_skills=profile["skills"],
        top_k=5,
    )

    for j, r in enumerate(results, 1):
        print(f"\n  #{j} — {r['title']} @ {r['company']} ({r['city']})")
        print(f"       Score: {r['match_score']:.2f}  (semantic={r['semantic_score']:.2f}, skill={r['skill_score']:.2f})")
        print(f"       ✅ Matched: {', '.join(r['matched_skills']) or 'none'}")
        print(f"       ❌ Missing: {', '.join(r['missing_skills']) or 'none'}")
```

#### C.2.3 — What to check

- Does "Junior Data Engineer" get data engineering jobs ranked first?
- Does "ML Engineer" get ML/DS jobs, NOT marketing or finance jobs?
- Are `matched_skills` and `missing_skills` correct?
- Is the score spread reasonable? (top result ~0.7-0.9, bottom ~0.3-0.5)

---

### Step C.3 — Evaluation Metrics

**File:** `nlp/evaluate.py`

#### C.3.1 — Precision@K

```python
def precision_at_k(results: list[dict], relevant_families: list[str], k: int = 10) -> float:
    """
    Of the top-K recommended offers, how many belong to the expected job families?
    Requires dim_job_title.job_family to be loaded in the results.
    """
    # You need to join job_family — add it to the recommender output or query here
    hits = 0
    for r in results[:k]:
        if r.get("job_family") in relevant_families:
            hits += 1
    return hits / k if k > 0 else 0.0
```

#### C.3.2 — Mean Reciprocal Rank (MRR)

```python
def mrr(results: list[dict], relevant_families: list[str]) -> float:
    """At what rank does the first relevant result appear?"""
    for i, r in enumerate(results, 1):
        if r.get("job_family") in relevant_families:
            return 1.0 / i
    return 0.0
```

#### C.3.3 — Run evaluation across all profiles and print summary

```python
def evaluate_all(profiles: list[dict]):
    from nlp.recommender import recommend

    p_at_5_scores = []
    mrr_scores = []

    for p in profiles:
        results = recommend(p["text"], p["skills"], top_k=10)
        p5 = precision_at_k(results, p["expected_families"], k=5)
        m = mrr(results, p["expected_families"])
        p_at_5_scores.append(p5)
        mrr_scores.append(m)
        print(f"{p['name']}: P@5={p5:.2f}, MRR={m:.2f}")

    print(f"\nAverage P@5: {sum(p_at_5_scores)/len(p_at_5_scores):.2f}")
    print(f"Average MRR: {sum(mrr_scores)/len(mrr_scores):.2f}")
```

---

## Phase D — FastAPI Backend (Days 10-13)

---

### Step D.1 — Project Setup

#### D.1.1 — Create the `api/` directory structure

```
api/
├── __init__.py
├── main.py
├── database.py
├── schemas.py
├── routers/
│   ├── __init__.py
│   ├── recommend.py
│   └── offers.py
├── requirements.txt
└── Dockerfile
```

#### D.1.2 — `api/requirements.txt`

```
fastapi==0.111.0
uvicorn[standard]==0.30.1
psycopg2-binary==2.9.9
sqlalchemy==2.0.30
sentence-transformers==3.0.1
scikit-learn>=1.3.0
numpy>=1.24.0
```

#### D.1.3 — `api/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import recommend, offers

app = FastAPI(
    title="Job Intelligent API",
    description="Semantic job recommendation engine powered by NLP",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recommend.router, prefix="/api", tags=["Recommendations"])
app.include_router(offers.router, prefix="/api", tags=["Offers"])

@app.get("/api/health")
def health_check():
    return {"status": "ok"}
```

---

### Step D.2 — Database Connection

**File:** `api/database.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://warehouse:warehouse@localhost:5433/jobs_dw"

engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def get_db():
    """FastAPI dependency: yields a DB session, auto-closes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

### Step D.3 — API Endpoints

#### D.3.1 — `api/routers/recommend.py`

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from api.database import get_db
from api.schemas import RecommendRequest, RecommendResponse
from nlp.recommender import recommend
import time

router = APIRouter()

@router.post("/recommend", response_model=RecommendResponse)
def get_recommendations(req: RecommendRequest, db: Session = Depends(get_db)):
    start = time.time()

    results = recommend(
        candidate_text=req.description,
        candidate_skills=req.skills,
        top_k=req.top_k,
        alpha=0.6,
    )

    # Get total offers count
    total = db.execute("SELECT COUNT(*) FROM fact_job_offer").scalar()

    elapsed_ms = int((time.time() - start) * 1000)

    return RecommendResponse(
        recommendations=results,
        total_offers_searched=total,
        processing_time_ms=elapsed_ms,
    )
```

#### D.3.2 — `api/routers/offers.py`

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from api.database import get_db

router = APIRouter()

@router.get("/offers")
def list_offers(
    city: str = Query(None),
    job_family: str = Query(None),
    skill: str = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    """List offers with optional filters."""
    query = """
        SELECT f.offer_id, jt.normalised_title, c.company_name,
               l.city, f.salary_min, f.salary_max
        FROM fact_job_offer f
        JOIN dim_job_title jt ON f.dim_title_id = jt.title_id
        JOIN dim_company c ON f.dim_company_id = c.company_id
        JOIN dim_location l ON f.dim_location_id = l.location_id
        WHERE 1=1
    """
    params = {}

    if city:
        query += " AND LOWER(l.city) = LOWER(:city)"
        params["city"] = city
    if job_family:
        query += " AND LOWER(jt.job_family) = LOWER(:job_family)"
        params["job_family"] = job_family

    query += " ORDER BY f.offer_id DESC LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = offset

    rows = db.execute(query, params).fetchall()
    return [
        {
            "offer_id": r[0], "title": r[1], "company": r[2],
            "city": r[3], "salary_min": float(r[4]) if r[4] else None,
            "salary_max": float(r[5]) if r[5] else None,
        }
        for r in rows
    ]

@router.get("/offers/{offer_id}")
def get_offer(offer_id: int, db: Session = Depends(get_db)):
    """Get full offer details including extracted skills."""
    row = db.execute("""
        SELECT f.offer_id, jt.normalised_title, c.company_name, l.city,
               f.salary_min, f.salary_max, f.currency, f.description_clean, f.url
        FROM fact_job_offer f
        JOIN dim_job_title jt ON f.dim_title_id = jt.title_id
        JOIN dim_company c ON f.dim_company_id = c.company_id
        JOIN dim_location l ON f.dim_location_id = l.location_id
        WHERE f.offer_id = :oid
    """, {"oid": offer_id}).fetchone()

    if not row:
        return {"error": "Offer not found"}

    skills = db.execute("""
        SELECT s.skill_name, s.skill_category, b.confidence_score
        FROM bridge_offer_skill b
        JOIN dim_skill s ON b.skill_id = s.skill_id
        WHERE b.offer_id = :oid
    """, {"oid": offer_id}).fetchall()

    return {
        "offer_id": row[0], "title": row[1], "company": row[2], "city": row[3],
        "salary_min": float(row[4]) if row[4] else None,
        "salary_max": float(row[5]) if row[5] else None,
        "currency": row[6], "description": row[7], "url": row[8],
        "skills": [{"name": s[0], "category": s[1], "confidence": float(s[2])} for s in skills],
    }

@router.get("/skills")
def list_skills(db: Session = Depends(get_db)):
    """List all skills (for frontend autocomplete)."""
    rows = db.execute("SELECT skill_name, skill_category FROM dim_skill ORDER BY skill_name").fetchall()
    return [{"name": r[0], "category": r[1]} for r in rows]

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Summary statistics for the home page."""
    total = db.execute("SELECT COUNT(*) FROM fact_job_offer").scalar()
    companies = db.execute("SELECT COUNT(DISTINCT dim_company_id) FROM fact_job_offer").scalar()
    cities = db.execute("SELECT COUNT(DISTINCT dim_location_id) FROM fact_job_offer").scalar()

    top_skills = db.execute("""
        SELECT s.skill_name, COUNT(*) as cnt
        FROM bridge_offer_skill b JOIN dim_skill s ON b.skill_id = s.skill_id
        GROUP BY s.skill_name ORDER BY cnt DESC LIMIT 10
    """).fetchall()

    return {
        "total_offers": total,
        "total_companies": companies,
        "total_cities": cities,
        "top_skills": [{"name": r[0], "count": r[1]} for r in top_skills],
    }
```

---

### Step D.4 — Pydantic Schemas

**File:** `api/schemas.py`

```python
from pydantic import BaseModel, Field

class RecommendRequest(BaseModel):
    description: str = Field(..., min_length=10, description="Describe your ideal job")
    skills: list[str] = Field(default=[], description="Your skills")
    top_k: int = Field(default=10, ge=1, le=50)

class OfferResult(BaseModel):
    offer_id: int
    title: str
    company: str
    city: str | None
    salary_min: float | None
    salary_max: float | None
    match_score: float
    semantic_score: float
    skill_score: float
    matched_skills: list[str]
    missing_skills: list[str]

class RecommendResponse(BaseModel):
    recommendations: list[OfferResult]
    total_offers_searched: int
    processing_time_ms: int
```

---

### Step D.5 — Run & Test via Swagger

#### D.5.1 — Start the server

```bash
cd <project_root>
uvicorn api.main:app --reload --port 8000
```

#### D.5.2 — Open Swagger UI

Go to `http://localhost:8000/docs`

#### D.5.3 — Test each endpoint

1. **GET /api/health** → `{"status": "ok"}`
2. **GET /api/stats** → verify total_offers > 0
3. **GET /api/skills** → verify list of ~90+ skills
4. **GET /api/offers?limit=5** → verify 5 offers returned
5. **GET /api/offers/1** → verify full offer with skills array
6. **POST /api/recommend** with body:
   ```json
   {
     "description": "Data engineer with Python, Spark, and cloud experience",
     "skills": ["Python", "SQL", "Spark", "AWS"],
     "top_k": 5
   }
   ```
   → Verify 5 results with scores and matched/missing skills
