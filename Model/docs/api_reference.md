# API Reference

The Job Intelligent API is built with FastAPI and follows Clean Architecture principles. It serves as the bridge between the React frontend and the PostgreSQL Data Warehouse.

## Endpoints

### 1. `POST /api/recommend`
Generates job recommendations based on a candidate profile.
- **Body**: 
  ```json
  {
    "description": "Python data engineer looking for remote work",
    "skills": ["Python", "SQL", "Spark"],
    "top_k": 10
  }
  ```
- **Response**: Returns a `RecommendResponse` containing a ranked list of job offers, each with `match_score`, `semantic_score`, `skill_score`, and lists of `matched_skills` and `missing_skills`. Includes processing time metadata.

### 2. `GET /api/offers`
Browse and filter job offers with pagination.
- **Query Params**:
  - `city` (optional): Filter by city name (e.g., "Paris").
  - `job_family` (optional): Filter by job category.
  - `limit` (default 50): Number of results per page.
  - `offset` (default 0): Pagination offset.
- **Response**: Array of lightweight `OfferSummary` objects.

### 3. `GET /api/offers/{id}`
Retrieve full details for a specific job offer.
- **Path Param**: `id` (integer)
- **Response**: An `OfferDetail` object including the full description, URL, and a categorized array of extracted skills.

### 4. `GET /api/skills`
List all skills available in the taxonomy (used for frontend autocomplete).
- **Response**: Array of `SkillItem` objects with `name` and `category`.

### 5. `GET /api/stats`
Summary statistics for the dashboard.
- **Response**: Returns `StatsResponse` with total offers, companies, cities, and an aggregated list of the top 10 most demanded skills across all offers.
