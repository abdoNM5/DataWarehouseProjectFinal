"""
Recommendation Service — orchestrates the hybrid recommendation logic.
Depends on domain interfaces (OfferRepository, SkillRepository), NOT on
concrete PostgreSQL implementations. This is the key clean architecture rule.
"""

import time
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from api.domain.interfaces import OfferRepository, SkillRepository
from nlp.embeddings import encode_text


class RecommendationService:
    """
    Use case: given a candidate profile, return ranked job recommendations.

    Formula: final_score = alpha * semantic_score + (1 - alpha) * skill_score
    """

    def __init__(self, offer_repo: OfferRepository, skill_repo: SkillRepository):
        self._offer_repo = offer_repo
        self._skill_repo = skill_repo

    def recommend(self, description: str, skills: list[str],
                  top_k: int = 10, alpha: float = 0.6) -> dict:
        """
        Generate hybrid recommendations.

        Returns dict with 'recommendations', 'total_offers_searched', 'processing_time_ms'.
        """
        start = time.time()

        # 1. Encode candidate text
        candidate_emb = encode_text(description).reshape(1, -1)
        candidate_skill_set = set(skills)

        # 2. Load all offers with embeddings
        offers, raw_embeddings = self._offer_repo.get_all_with_embeddings()
        if not offers:
            return {
                "recommendations": [],
                "total_offers_searched": 0,
                "processing_time_ms": 0,
            }

        offer_embeddings = np.array(raw_embeddings)

        # 3. Load skill mappings
        offer_skills_map = self._skill_repo.get_offer_skills()

        # 4. Compute semantic similarity (candidate vs ALL offers at once)
        similarities = cosine_similarity(candidate_emb, offer_embeddings)[0]

        # 5. Combine scores
        results = []
        for i, offer in enumerate(offers):
            oid = offer["offer_id"]
            semantic = float(similarities[i])

            offer_sk = offer_skills_map.get(oid, set())
            skill_sc, matched, missing = self._compute_skill_score(
                candidate_skill_set, offer_sk
            )

            final = alpha * semantic + (1 - alpha) * skill_sc

            results.append({
                **offer,
                "match_score": round(final, 4),
                "semantic_score": round(semantic, 4),
                "skill_score": round(skill_sc, 4),
                "matched_skills": matched,
                "missing_skills": missing,
            })

        # 6. Sort and return top-K
        results.sort(key=lambda x: x["match_score"], reverse=True)
        elapsed_ms = int((time.time() - start) * 1000)

        return {
            "recommendations": results[:top_k],
            "total_offers_searched": len(offers),
            "processing_time_ms": elapsed_ms,
        }

    @staticmethod
    def _compute_skill_score(candidate_skills: set, offer_skills: set):
        """Compute overlap between candidate and offer skill sets."""
        if not candidate_skills:
            return 0.0, [], []
        matched = candidate_skills & offer_skills
        missing = candidate_skills - offer_skills
        score = len(matched) / len(candidate_skills)
        return score, sorted(matched), sorted(missing)
