"""
Evaluation metrics for the recommendation engine.
Computes Precision@K and Mean Reciprocal Rank (MRR).
"""


def precision_at_k(results, relevant_families, k=10):
    """
    Of the top-K recommended offers, how many belong to the expected job families?

    Args:
        results: list of offer dicts (must contain 'job_family' key)
        relevant_families: list of expected job family strings
        k: number of top results to evaluate

    Returns:
        float between 0.0 and 1.0
    """
    if k <= 0:
        return 0.0
    hits = sum(1 for r in results[:k] if r.get("job_family") in relevant_families)
    return hits / k


def mrr(results, relevant_families):
    """
    Mean Reciprocal Rank — at what rank does the first relevant result appear?

    Returns:
        1/rank of first relevant result, or 0.0 if none found.
    """
    for i, r in enumerate(results, 1):
        if r.get("job_family") in relevant_families:
            return 1.0 / i
    return 0.0


def evaluate_all(profiles, recommend_fn, top_k=10):
    """
    Run evaluation across all profiles and print summary.

    Args:
        profiles: list of dicts with 'name', 'text', 'skills', 'expected_families'
        recommend_fn: the recommend() function to call
        top_k: K for precision calculation
    """
    p_at_5_scores = []
    mrr_scores = []

    for p in profiles:
        results = recommend_fn(p["text"], p["skills"], top_k=top_k)
        p5 = precision_at_k(results, p["expected_families"], k=5)
        m = mrr(results, p["expected_families"])
        p_at_5_scores.append(p5)
        mrr_scores.append(m)
        print(f"  {p['name']:30s}  P@5={p5:.2f}  MRR={m:.2f}")

    avg_p5 = sum(p_at_5_scores) / len(p_at_5_scores) if p_at_5_scores else 0
    avg_mrr = sum(mrr_scores) / len(mrr_scores) if mrr_scores else 0

    print(f"\n  {'AVERAGE':30s}  P@5={avg_p5:.2f}  MRR={avg_mrr:.2f}")
    return avg_p5, avg_mrr
