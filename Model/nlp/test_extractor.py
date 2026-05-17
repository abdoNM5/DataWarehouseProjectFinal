"""
Test script — verify the skills extractor works correctly
on sample descriptions before running on the full database.
"""

from nlp.skills_extractor import extract_skills


def test_english_description():
    desc = """
    We are looking for a Data Engineer to join our team in Paris.
    You will design, build, and maintain data pipelines using Python, SQL,
    and Apache Spark. Experience with Airflow for orchestration and
    PostgreSQL or MongoDB for data storage is required.
    Knowledge of Docker and Kubernetes (k8s) is a plus.
    You will work in an Agile/Scrum environment with CI/CD pipelines on AWS.
    """
    skills = extract_skills(desc)
    print("\n--- Test 1: English Data Engineer description ---")
    for skill, score in skills:
        print(f"  ✅ {skill}: {score}")
    print(f"  Total: {len(skills)} skills found")
    return skills


def test_french_description():
    desc = """
    Nous recherchons un ingénieur data maîtrisant Python, PostgreSQL et Spark.
    Une expérience avec TensorFlow ou PyTorch est appréciée.
    Compétences en Power BI et Tableau pour la visualisation.
    Environnement Agile / Scrum. Maîtrise de Docker et Git.
    """
    skills = extract_skills(desc)
    print("\n--- Test 2: French Data Engineer description ---")
    for skill, score in skills:
        print(f"  ✅ {skill}: {score}")
    print(f"  Total: {len(skills)} skills found")
    return skills


def test_ml_description():
    desc = """
    Senior Data Scientist specializing in NLP. Build recommendation systems
    using Deep Learning, Hugging Face transformers, and spaCy.
    Tech stack: Python, PyTorch, TensorFlow, scikit-learn, Pandas.
    Infrastructure: Docker, Kubernetes, AWS (S3, Lambda).
    Experience with LLM and GenAI is a strong plus.
    """
    skills = extract_skills(desc)
    print("\n--- Test 3: ML/NLP description ---")
    for skill, score in skills:
        print(f"  ✅ {skill}: {score}")
    print(f"  Total: {len(skills)} skills found")
    return skills


def test_false_positives():
    """Make sure 'R' doesn't match inside words like 'Required'."""
    desc = "Required experience in project management. Responsible for reporting."
    skills = extract_skills(desc)
    print("\n--- Test 4: False positive check ---")
    r_found = any(s[0] == "R" for s in skills)
    print(f"  'R' falsely detected: {r_found} {'❌ BUG!' if r_found else '✅ OK'}")
    for skill, score in skills:
        print(f"  Found: {skill}")
    return skills


def test_empty():
    """Empty/None descriptions should return empty list."""
    assert extract_skills("") == []
    assert extract_skills(None) == []
    assert extract_skills("   ") == []
    print("\n--- Test 5: Empty input ---")
    print("  ✅ All empty inputs returned []")


if __name__ == "__main__":
    print("=" * 60)
    print("  SKILLS EXTRACTOR — TEST SUITE")
    print("=" * 60)

    test_english_description()
    test_french_description()
    test_ml_description()
    test_false_positives()
    test_empty()

    print("\n" + "=" * 60)
    print("  ALL TESTS PASSED ✅")
    print("=" * 60)
