"""
Test Recommender — verify recommendations with synthetic candidate profiles.
Requires: Docker running, mock data loaded, skills populated, embeddings generated.
"""

from nlp.recommender import recommend


PROFILES = [
    {
        "name": "Junior Data Engineer",
        "text": "Computer science student looking for a data engineering internship. "
                "I know Python, SQL, and have basic knowledge of Spark and Airflow. "
                "I want to build ETL pipelines and work with cloud infrastructure.",
        "skills": ["Python", "SQL", "Spark", "Git", "Docker"],
        "expected_families": ["Data Engineer"],
    },
    {
        "name": "ML Engineer",
        "text": "Machine learning engineer with experience in PyTorch, NLP, and model "
                "deployment on AWS. Looking for a role building production ML systems.",
        "skills": ["Python", "PyTorch", "scikit-learn", "Docker", "AWS"],
        "expected_families": ["ML Engineer", "Data Scientist"],
    },
    {
        "name": "Data Analyst",
        "text": "Analyst with strong SQL and visualization skills. Experience with "
                "Power BI dashboards and Excel reporting for business insights.",
        "skills": ["SQL", "Power BI", "Excel", "Python", "Tableau"],
        "expected_families": ["Data Analyst", "Business Analyst", "BI Developer / Analytics Engineer"],
    },
    {
        "name": "Senior Cloud Data Engineer",
        "text": "Experienced data engineer specializing in cloud platforms, real-time "
                "streaming with Kafka, and large-scale data processing with Spark on GCP.",
        "skills": ["Python", "Spark", "Kafka", "GCP", "BigQuery", "Docker", "Terraform", "Airflow"],
        "expected_families": ["Data Engineer"],
    },
    {
        "name": "NLP Data Scientist",
        "text": "Data scientist specializing in natural language processing and deep learning. "
                "Experience building recommendation systems with transformer models.",
        "skills": ["Python", "PyTorch", "TensorFlow", "NLP", "Deep Learning", "Hugging Face", "spaCy"],
        "expected_families": ["Data Scientist", "ML Engineer"],
    },
]


def run_tests():
    for profile in PROFILES:
        print(f"\n{'='*70}")
        print(f"  Profile: {profile['name']}")
        print(f"  Skills:  {', '.join(profile['skills'])}")
        print(f"{'='*70}")

        results = recommend(
            candidate_text=profile["text"],
            candidate_skills=profile["skills"],
            top_k=5,
        )

        for j, r in enumerate(results, 1):
            score_bar = "#" * int(r["match_score"] * 20)
            print(f"\n  #{j}  {r['title']} @ {r['company']} ({r['city']})")
            print(f"      Score: {r['match_score']:.2f}  [{score_bar:<20}]")
            print(f"      Semantic: {r['semantic_score']:.2f}  |  Skill: {r['skill_score']:.2f}")
            print(f"      Matched: {', '.join(r['matched_skills']) or 'none'}")
            print(f"      Missing: {', '.join(r['missing_skills']) or 'none'}")
            print(f"      Family:  {r['job_family']}")

        # Check if top result matches expected families
        if results:
            top_family = results[0]["job_family"]
            expected = profile["expected_families"]
            match = top_family in expected
            status = "PASS" if match else "WARN"
            print(f"\n  [{status}] Top result family '{top_family}' "
                  f"{'matches' if match else 'does NOT match'} expected {expected}")


if __name__ == "__main__":
    print("=" * 70)
    print("  RECOMMENDATION ENGINE - TEST SUITE")
    print("=" * 70)
    run_tests()
    print("\n" + "=" * 70)
    print("  TESTS COMPLETE")
    print("=" * 70)
