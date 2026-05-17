"""
Recommender — hybrid recommendation engine combining:
  1. Semantic similarity (cosine between candidate & offer embeddings)
  2. Skill overlap score (candidate skills ∩ offer skills)

Formula: final_score = alpha * semantic_score + (1 - alpha) * skill_score
"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from nlp.db_utils import get_connection, get_cursor
from nlp.embeddings import encode_text, json_to_embedding


def _load_all_offers(cur):
    """Load all offers with embeddings + metadata from the warehouse."""
    cur.execute("""
        SELECT
            f.offer_id,
            jt.normalised_title,
            jt.job_family,
            c.company_name,
            l.city,
            f.salary_min,
            f.salary_max,
            f.currency,
            f.embedding
        FROM fact_job_offer f
        JOIN dim_job_title jt ON f.dim_title_id = jt.title_id
        JOIN dim_company c   ON f.dim_company_id = c.company_id
        JOIN dim_location l  ON f.dim_location_id = l.location_id
        WHERE f.embedding IS NOT NULL
    """)
    rows = cur.fetchall()

    offers = []
    embeddings = []
    for row in rows:
        offers.append({
            "offer_id": row[0],
            "title": row[1],
            "job_family": row[2],
            "company": row[3],
            "city": row[4],
            "salary_min": float(row[5]) if row[5] else None,
            "salary_max": float(row[6]) if row[6] else None,
            "currency": row[7],
        })
        embeddings.append(json_to_embedding(row[8]))

    return offers, np.array(embeddings) if embeddings else np.empty((0, 384))


def _load_offer_skills(cur):
    """Load {offer_id: {skill1, skill2, ...}} from bridge_offer_skill."""
    cur.execute("""
        SELECT b.offer_id, s.skill_name
        FROM bridge_offer_skill b
        JOIN dim_skill s ON b.skill_id = s.skill_id
    """)
    result = {}
    for offer_id, skill_name in cur.fetchall():
        result.setdefault(offer_id, set()).add(skill_name)
    return result


def _skill_score(candidate_skills, offer_skills):
    """
    Compute skill overlap between candidate and offer.
    Returns (score, matched_list, missing_list).
    """
    if not candidate_skills:
        return 0.0, [], []

    matched = candidate_skills & offer_skills
    missing = candidate_skills - offer_skills
    score = len(matched) / len(candidate_skills)
    return score, sorted(matched), sorted(missing)


def recommend(
    candidate_text,
    candidate_skills,
    top_k=10,
    alpha=0.6,
):
    """
    Hybrid recommendation: semantic similarity + skill matching.

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
    similarities = cosine_similarity(candidate_emb, offer_embeddings)[0]

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
