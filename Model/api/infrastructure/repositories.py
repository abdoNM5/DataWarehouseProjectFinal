"""
Concrete Repositories — PostgreSQL implementations of domain interfaces.
These are the ONLY classes that contain raw SQL. Everything else goes
through the abstract interfaces defined in domain/interfaces.py.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

from api.domain.interfaces import OfferRepository, SkillRepository, StatsRepository
from nlp.embeddings import json_to_embedding


# ── Offer Repository ────────────────────────────────────────

class PostgresOfferRepository(OfferRepository):
    """PostgreSQL implementation of OfferRepository."""

    def __init__(self, db: Session):
        self._db = db

    def get_total_count(self) -> int:
        result = self._db.execute(text("SELECT COUNT(*) FROM fact_job_offer"))
        return result.scalar()

    def get_offer_by_id(self, offer_id: int) -> dict | None:
        row = self._db.execute(text("""
            SELECT f.offer_id, jt.normalised_title, jt.job_family,
                   c.company_name, l.city,
                   f.salary_min, f.salary_max, f.currency,
                   f.description_clean, f.url
            FROM fact_job_offer f
            JOIN dim_job_title jt ON f.dim_title_id = jt.title_id
            JOIN dim_company c   ON f.dim_company_id = c.company_id
            JOIN dim_location l  ON f.dim_location_id = l.location_id
            WHERE f.offer_id = :oid
        """), {"oid": offer_id}).fetchone()

        if not row:
            return None

        return {
            "offer_id": row[0], "title": row[1], "job_family": row[2],
            "company": row[3], "city": row[4],
            "salary_min": float(row[5]) if row[5] else None,
            "salary_max": float(row[6]) if row[6] else None,
            "currency": row[7], "description": row[8], "url": row[9],
        }

    def list_offers(self, city=None, job_family=None, skill=None, limit=50, offset=0):
        query = """
            SELECT f.offer_id, jt.normalised_title, jt.job_family,
                   c.company_name, l.city, f.salary_min, f.salary_max
            FROM fact_job_offer f
            JOIN dim_job_title jt ON f.dim_title_id = jt.title_id
            JOIN dim_company c   ON f.dim_company_id = c.company_id
            JOIN dim_location l  ON f.dim_location_id = l.location_id
            WHERE 1=1
        """
        params = {"limit": limit, "offset": offset}

        if city:
            query += " AND LOWER(l.city) = LOWER(:city)"
            params["city"] = city
        if job_family:
            query += " AND LOWER(jt.job_family) = LOWER(:jf)"
            params["jf"] = job_family
        if skill:
            query += """
                AND EXISTS (
                    SELECT 1
                    FROM bridge_offer_skill b
                    JOIN dim_skill s ON b.skill_id = s.skill_id
                    WHERE b.offer_id = f.offer_id
                      AND LOWER(s.skill_name) = LOWER(:skill)
                )
            """
            params["skill"] = skill

        query += " ORDER BY f.offer_id DESC LIMIT :limit OFFSET :offset"

        rows = self._db.execute(text(query), params).fetchall()
        return [
            {
                "offer_id": r[0], "title": r[1], "job_family": r[2],
                "company": r[3], "city": r[4],
                "salary_min": float(r[5]) if r[5] else None,
                "salary_max": float(r[6]) if r[6] else None,
            }
            for r in rows
        ]

    def get_all_with_embeddings(self):
        rows = self._db.execute(text("""
            SELECT f.offer_id, jt.normalised_title, jt.job_family,
                   c.company_name, l.city,
                   f.salary_min, f.salary_max, f.currency, f.embedding
            FROM fact_job_offer f
            JOIN dim_job_title jt ON f.dim_title_id = jt.title_id
            JOIN dim_company c   ON f.dim_company_id = c.company_id
            JOIN dim_location l  ON f.dim_location_id = l.location_id
            WHERE f.embedding IS NOT NULL
        """)).fetchall()

        offers = []
        embeddings = []
        for r in rows:
            offers.append({
                "offer_id": r[0], "title": r[1], "job_family": r[2],
                "company": r[3], "city": r[4],
                "salary_min": float(r[5]) if r[5] else None,
                "salary_max": float(r[6]) if r[6] else None,
                "currency": r[7],
            })
            embeddings.append(json_to_embedding(r[8]))
        return offers, embeddings


# ── Skill Repository ────────────────────────────────────────

class PostgresSkillRepository(SkillRepository):
    """PostgreSQL implementation of SkillRepository."""

    def __init__(self, db: Session):
        self._db = db

    def list_all(self):
        rows = self._db.execute(text(
            "SELECT skill_name, skill_category FROM dim_skill ORDER BY skill_name"
        )).fetchall()
        return [{"name": r[0], "category": r[1]} for r in rows]

    def get_offer_skills(self):
        rows = self._db.execute(text("""
            SELECT b.offer_id, s.skill_name
            FROM bridge_offer_skill b
            JOIN dim_skill s ON b.skill_id = s.skill_id
        """)).fetchall()
        result = {}
        for offer_id, skill_name in rows:
            result.setdefault(offer_id, set()).add(skill_name)
        return result

    def get_skills_for_offer(self, offer_id: int):
        rows = self._db.execute(text("""
            SELECT s.skill_name, s.skill_category, b.confidence_score
            FROM bridge_offer_skill b
            JOIN dim_skill s ON b.skill_id = s.skill_id
            WHERE b.offer_id = :oid
        """), {"oid": offer_id}).fetchall()
        return [
            {"name": r[0], "category": r[1], "confidence": float(r[2])}
            for r in rows
        ]


# ── Stats Repository ────────────────────────────────────────

class PostgresStatsRepository(StatsRepository):
    """PostgreSQL implementation of StatsRepository."""

    def __init__(self, db: Session):
        self._db = db

    def get_summary(self):
        total = self._db.execute(text(
            "SELECT COUNT(*) FROM fact_job_offer"
        )).scalar()

        companies = self._db.execute(text(
            "SELECT COUNT(DISTINCT dim_company_id) FROM fact_job_offer"
        )).scalar()

        cities = self._db.execute(text(
            "SELECT COUNT(DISTINCT dim_location_id) FROM fact_job_offer"
        )).scalar()

        top_skills = self._db.execute(text("""
            SELECT s.skill_name, COUNT(*) as cnt
            FROM bridge_offer_skill b
            JOIN dim_skill s ON b.skill_id = s.skill_id
            GROUP BY s.skill_name
            ORDER BY cnt DESC
            LIMIT 10
        """)).fetchall()

        return {
            "total_offers": total,
            "total_companies": companies,
            "total_cities": cities,
            "top_skills": [{"name": r[0], "count": r[1]} for r in top_skills],
        }
