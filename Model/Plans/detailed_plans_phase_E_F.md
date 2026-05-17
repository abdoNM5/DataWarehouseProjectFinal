# 🔬 Detailed Sub-Plans — Phase E & F

---

## Phase E — Next.js Frontend (Days 14-17)

---

### Step E.1 — Scaffold the Project

#### E.1.1 — Create the Next.js app

```bash
npx -y create-next-app@latest ./frontend --ts --tailwind --app --eslint --no-src-dir
```

#### E.1.2 — Install extra dependencies

```bash
cd frontend
npm install axios lucide-react
```

- `axios` — HTTP client to call your FastAPI backend
- `lucide-react` — icon library for UI polish

#### E.1.3 — Set up API base URL

Create `frontend/lib/api.ts`:

```typescript
import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api",
  timeout: 30000,
});

export default api;
```

#### E.1.4 — Verify it runs

```bash
npm run dev
```

Open `http://localhost:3000` — you should see the default Next.js page.

---

### Step E.2 — Pages to Build

| Page | Route | File | Priority |
|---|---|---|---|
| **Home** | `/` | `app/page.tsx` | High |
| **Recommend** | `/recommend` | `app/recommend/page.tsx` | **Critical** |
| **Browse** | `/offers` | `app/offers/page.tsx` | Medium |
| **Offer Detail** | `/offers/[id]` | `app/offers/[id]/page.tsx` | Medium |

#### E.2.1 — Create the file structure

```
frontend/app/
├── layout.tsx          ← root layout (navbar, global styles)
├── page.tsx            ← Home page
├── recommend/
│   └── page.tsx        ← Recommendation page
├── offers/
│   ├── page.tsx        ← Browse all offers
│   └── [id]/
│       └── page.tsx    ← Single offer detail
```

#### E.2.2 — Layout with navigation

In `app/layout.tsx`, add a navbar with links to all 3 pages:

```typescript
// Key elements for the navbar:
// - Logo/title: "Job Intelligent"
// - Links: Home, Recommend, Browse Offers
// - Dark theme styling (matches your schema screenshot aesthetic)
```

#### E.2.3 — Home page (`app/page.tsx`)

1. Call `GET /api/stats` on page load
2. Display:
   - Hero section: project title + one-liner
   - Stats cards: Total offers, Total companies, Total cities
   - Top 10 skills bar chart or tag cloud
   - CTA button → "Find Your Match" linking to `/recommend`

#### E.2.4 — Browse page (`app/offers/page.tsx`)

1. Call `GET /api/offers?limit=20&offset=0`
2. Display offers as cards or table rows
3. Add filters: city dropdown, job family dropdown
4. Pagination: "Load more" button that increases offset

#### E.2.5 — Offer detail page (`app/offers/[id]/page.tsx`)

1. Call `GET /api/offers/{id}` using the route param
2. Display:
   - Title, company, city, salary range
   - Full description (rendered as formatted text)
   - Skills as colored badges grouped by category
   - Link to original job posting (`url` field)

---

### Step E.3 — Recommendation Page (The Star Feature)

**File:** `app/recommend/page.tsx`

This is the most important page — it showcases your NLP work.

#### E.3.1 — Component: Skill Tag Selector

```
How it works:
1. On mount: fetch GET /api/skills → get all skill names
2. Show a text input with autocomplete dropdown
3. When user types, filter the skill list
4. Click a suggestion → add it as a colored tag below the input
5. Click the "x" on a tag → remove it
6. Store selected skills in React state: string[]
```

State to manage:
```typescript
const [allSkills, setAllSkills] = useState<string[]>([]);
const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
const [searchTerm, setSearchTerm] = useState("");
```

#### E.3.2 — Component: Description Textarea

```
A simple <textarea> with:
- Placeholder: "Describe your ideal job role, experience, and interests..."
- Min height: ~120px
- Character count indicator
- Store in state: description: string
```

#### E.3.3 — Submit and call API

```typescript
const handleSubmit = async () => {
  setLoading(true);
  const response = await api.post("/recommend", {
    description: description,
    skills: selectedSkills,
    top_k: 10,
  });
  setResults(response.data.recommendations);
  setLoading(false);
};
```

#### E.3.4 — Component: Results Cards

For each result, display a card with:

```
┌─────────────────────────────────────────────────┐
│ #1  Data Engineer                    Score: 87%  │
│     Capgemini — Paris                            │
│                                                  │
│  ██████████████████░░░░  87% match               │
│                                                  │
│  ✅ Python  ✅ SQL  ✅ Spark                      │
│  ❌ AWS  ❌ Kafka                                 │
│                                                  │
│  [View Details →]                                │
└─────────────────────────────────────────────────┘
```

Key UI elements:
- **Progress bar** colored by score: green (>80%), yellow (>60%), red (<60%)
- **Matched skills**: green badges
- **Missing skills**: grey/red badges
- **Link**: to `/offers/[id]` for full details

#### E.3.5 — Add processing time display

After results load, show:
```
Found 10 matches out of 1,200 offers in 340ms
```

This comes from the API response fields `total_offers_searched` and `processing_time_ms`.

---

### Step E.4 — Dockerise

#### E.4.1 — Create `api/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Also copy the nlp module (it's used by the API)
COPY ../nlp /app/nlp

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### E.4.2 — Create `frontend/Dockerfile`

```dockerfile
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
```

#### E.4.3 — Add to `docker-compose.yml`

Append these two services to your existing docker-compose:

```yaml
  api:
    build:
      context: .
      dockerfile: api/Dockerfile
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: "postgresql://warehouse:warehouse@warehouse-db:5432/jobs_dw"
    depends_on:
      - warehouse-db

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: "http://localhost:8000/api"
    depends_on:
      - api
```

> [!IMPORTANT]
> Note `warehouse-db:5432` (not `localhost:5433`) — inside Docker, services communicate via service names on internal port 5432.

#### E.4.4 — Test with Docker

```bash
docker compose up --build
```

Then open:
- `http://localhost:3000` → Frontend
- `http://localhost:8000/docs` → API Swagger

---

## Phase F — Integration & Polish (Days 18-19)

---

### Step F.1 — End-to-End Test

#### F.1.1 — Start all services

```bash
docker compose up -d
```

Verify all containers are running:
```bash
docker compose ps
```

You should see: `postgres`, `warehouse-db`, `jupyter-spark`, `airflow-*`, `api`, `frontend`

#### F.1.2 — Check data is loaded

```bash
docker compose exec warehouse-db psql -U warehouse -d jobs_dw -c "SELECT COUNT(*) FROM fact_job_offer;"
```

If 0 → your partner's ETL hasn't run yet. Use mock data or insert manually.

#### F.1.3 — Run NLP pipeline

```bash
# From project root (outside Docker, connecting to localhost:5433)
python -m nlp.populate_skills
python -m nlp.generate_embeddings
```

#### F.1.4 — Verify skills extracted

```sql
SELECT COUNT(*) FROM bridge_offer_skill;
-- Should be > 0

SELECT s.skill_name, COUNT(*) as cnt
FROM bridge_offer_skill b
JOIN dim_skill s ON b.skill_id = s.skill_id
GROUP BY s.skill_name
ORDER BY cnt DESC LIMIT 5;
```

#### F.1.5 — Verify embeddings stored

```sql
SELECT COUNT(*) FROM fact_job_offer WHERE embedding IS NOT NULL;
-- Should match total offers
```

#### F.1.6 — Test recommendation end-to-end

```bash
curl -X POST http://localhost:8000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{"description": "Python data engineer", "skills": ["Python", "SQL"], "top_k": 3}'
```

Verify you get 3 results with scores.

#### F.1.7 — Test frontend flow

1. Open `http://localhost:3000`
2. Click "Find Your Match" → `/recommend`
3. Select skills: Python, SQL, Spark
4. Type: "Looking for a data engineering role"
5. Click Submit
6. Verify results appear with scores and skill badges
7. Click "View Details" on a result → verify detail page loads

---

### Step F.2 — Documentation

#### F.2.1 — `docs/nlp_architecture.md`

Write a document covering:

```markdown
# NLP & Recommendation Architecture

## Overview
The recommendation engine combines two scoring methods:
1. **Semantic similarity** — using Sentence-Transformers embeddings
2. **Skill matching** — using keyword extraction from job descriptions

## Model: paraphrase-multilingual-MiniLM-L12-v2
- Architecture: 12-layer MiniLM transformer
- Parameters: 118M
- Output: 384-dimensional normalized vectors
- Languages: French + English (+ 50 others)
- Why this model: [explain your reasoning]

## Scoring Formula
```
Final Score = 0.6 × cosine_similarity(candidate, offer) + 0.4 × skill_overlap
```

## Data Flow
1. ETL loads offers into `fact_job_offer` with `description_clean`
2. `populate_skills.py` extracts skills → `bridge_offer_skill`
3. `generate_embeddings.py` encodes descriptions → `embedding` column
4. API receives candidate profile → encodes → ranks all offers → returns top-K

## Evaluation Results
- Precision@5: X.XX
- MRR: X.XX
```

#### F.2.2 — `docs/api_reference.md`

FastAPI auto-generates OpenAPI docs. Export them:

```python
# export_openapi.py
import json
from api.main import app

schema = app.openapi()
with open("docs/api_reference.json", "w") as f:
    json.dump(schema, f, indent=2)
```

Or just document the 5 endpoints manually with request/response examples.

#### F.2.3 — Update `README.md`

Add a section about your NLP work:

```markdown
## Recommendation Engine (by Bouzi)

### Quick Start
1. `docker compose up -d`
2. `python -m nlp.populate_skills`
3. `python -m nlp.generate_embeddings`
4. Open `http://localhost:3000/recommend`

### Architecture
See [docs/nlp_architecture.md](docs/nlp_architecture.md)

### API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/recommend` | Get job recommendations |
| GET | `/api/offers` | Browse offers |
| GET | `/api/offers/{id}` | Offer details |
| GET | `/api/skills` | List all skills |
| GET | `/api/stats` | Dashboard stats |
```
