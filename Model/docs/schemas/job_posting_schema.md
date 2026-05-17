# Job Posting Schema (Draft)

| Field            | Type        | Required | Description |
|-----------------|-------------|----------|-------------|
| job_id          | string (UUID) | Yes | Unique identifier assigned after deduplication |
| source          | enum         | Yes | Job board slug (`indeed`, `linkedin`, `france_travail`, etc.) |
| title_raw       | string       | Yes | Original title from source |
| title_standard  | string       | Yes | Normalized title aligned to taxonomy |
| company_name    | string       | Yes | Employer name |
| location_raw    | string       | Yes | Original location string |
| location_norm   | struct       | No  | `{country, region, city}` normalized |
| employment_type | enum         | No  | `full_time`, `contract`, `internship`, `freelance`, `other` |
| salary_min      | decimal      | No  | Minimum annual compensation in EUR |
| salary_max      | decimal      | No  | Maximum annual compensation in EUR |
| currency        | string (ISO 4217) | No | Currency code, default `EUR` |
| description     | text         | Yes | Cleaned job description |
| skills          | array<string> | No | NLP-extracted skill tags |
| posted_at       | timestamp    | Yes | Publish date from source |
| ingestion_ts    | timestamp    | Yes | When the platform ingested the record |

## JSON Snippet
```json
{
  "job_id": "c62dc228-8470-4d9c-a03c-0d43a0db0b67",
  "source": "indeed",
  "title_raw": "Senior Data Scientist",
  "title_standard": "Senior Data Scientist",
  "company_name": "DataCorp",
  "location_raw": "Paris, Île-de-France",
  "location_norm": {"country": "FR", "region": "IDF", "city": "Paris"},
  "employment_type": "full_time",
  "salary_min": 60000,
  "salary_max": 80000,
  "currency": "EUR",
  "description": "You will build ML models...",
  "skills": ["Python", "Spark", "NLP"],
  "posted_at": "2026-02-15T09:15:00Z",
  "ingestion_ts": "2026-02-15T09:45:03Z"
}
```
