"""
Test script — verify the embedding module works correctly.
No database needed — tests model loading, encoding, and similarity.
"""

import numpy as np
from nlp.embeddings import encode_text, encode_batch, embedding_to_json, json_to_embedding


def test_single_encode():
    """Test encoding a single text."""
    vec = encode_text("Data engineer with Python and Spark experience")
    print(f"\n--- Test 1: Single encode ---")
    print(f"  Vector shape: {vec.shape}")       # (384,)
    print(f"  Vector dtype: {vec.dtype}")        # float32
    print(f"  First 5 values: {vec[:5]}")
    assert vec.shape == (384,), f"Expected (384,), got {vec.shape}"
    print("  PASSED")


def test_semantic_similarity():
    """Similar texts should have high cosine similarity, different texts low."""
    v1 = encode_text("Data engineer with Python and Spark experience")
    v2 = encode_text("Python developer for big data pipelines")
    v3 = encode_text("Marketing manager for luxury fashion brands")

    # Since vectors are normalized, cosine similarity = dot product
    sim_12 = float(np.dot(v1, v2))
    sim_13 = float(np.dot(v1, v3))

    print(f"\n--- Test 2: Semantic similarity ---")
    print(f"  Data Eng vs Python Big Data: {sim_12:.4f}  (should be HIGH)")
    print(f"  Data Eng vs Marketing:       {sim_13:.4f}  (should be LOW)")
    assert sim_12 > sim_13, "Related texts should be more similar!"
    assert sim_12 > 0.5, f"Related texts similarity too low: {sim_12}"
    assert sim_13 < 0.5, f"Unrelated texts similarity too high: {sim_13}"
    print("  PASSED")


def test_multilingual():
    """French and English descriptions of the same job should be similar."""
    v_en = encode_text("Data engineer building data pipelines with Python and SQL")
    v_fr = encode_text("Ingenieur donnees construisant des pipelines de donnees avec Python et SQL")

    sim = float(np.dot(v_en, v_fr))
    print(f"\n--- Test 3: Multilingual (FR/EN) ---")
    print(f"  EN vs FR same job: {sim:.4f}  (should be HIGH)")
    assert sim > 0.5, f"Multilingual similarity too low: {sim}"
    print("  PASSED")


def test_batch_encode():
    """Test batch encoding multiple texts."""
    texts = [
        "Python developer",
        "Java engineer",
        "Data scientist with machine learning",
    ]
    vecs = encode_batch(texts, batch_size=2)
    print(f"\n--- Test 4: Batch encode ---")
    print(f"  Batch shape: {vecs.shape}")  # (3, 384)
    assert vecs.shape == (3, 384), f"Expected (3, 384), got {vecs.shape}"
    print("  PASSED")


def test_serialization():
    """Test JSON round-trip for DB storage."""
    original = encode_text("Test sentence for serialization")
    json_str = embedding_to_json(original)
    recovered = json_to_embedding(json_str)

    diff = float(np.max(np.abs(original - recovered)))
    print(f"\n--- Test 5: JSON serialization round-trip ---")
    print(f"  JSON length: {len(json_str)} chars")
    print(f"  Max difference after round-trip: {diff:.10f}")
    assert diff < 1e-6, f"Round-trip error too large: {diff}"
    print("  PASSED")


if __name__ == "__main__":
    print("=" * 60)
    print("  EMBEDDINGS MODULE - TEST SUITE")
    print("=" * 60)

    test_single_encode()
    test_semantic_similarity()
    test_multilingual()
    test_batch_encode()
    test_serialization()

    print("\n" + "=" * 60)
    print("  ALL TESTS PASSED")
    print("=" * 60)
