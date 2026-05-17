"""
Populate bridge_offer_skill — extracts skills from all job descriptions
and inserts (offer_id, skill_id, confidence_score) into the bridge table.
"""

from nlp.skills_extractor import extract_skills
from nlp.db_utils import get_connection, get_cursor


def load_skill_id_map(cur) -> dict:
    """Load {skill_name: skill_id} from dim_skill."""
    cur.execute("SELECT skill_id, skill_name FROM dim_skill")
    return {name: sid for sid, name in cur.fetchall()}


def get_unprocessed_offers(cur) -> list:
    """Get offers that don't yet have skills in bridge_offer_skill."""
    cur.execute("""
        SELECT f.offer_id, f.description_clean
        FROM fact_job_offer f
        LEFT JOIN bridge_offer_skill b ON f.offer_id = b.offer_id
        WHERE b.offer_id IS NULL
          AND f.description_clean IS NOT NULL
          AND f.description_clean != ''
    """)
    return cur.fetchall()


def insert_offer_skills(cur, offer_id: int, skills: list, skill_map: dict):
    """Insert extracted skills into bridge_offer_skill."""
    for skill_name, confidence in skills:
        skill_id = skill_map.get(skill_name)
        if skill_id is None:
            continue  # skill not in dim_skill, skip
        cur.execute("""
            INSERT INTO bridge_offer_skill (offer_id, skill_id, confidence_score)
            VALUES (%s, %s, %s)
            ON CONFLICT (offer_id, skill_id) DO NOTHING
        """, (offer_id, skill_id, confidence))


def main():
    """Main entry point — extract skills for all unprocessed offers."""
    with get_connection() as conn:
        with get_cursor(conn, commit=False) as cur:
            # 1. Load skill map
            skill_map = load_skill_id_map(cur)
            print(f"Loaded {len(skill_map)} skills from dim_skill")

            # 2. Get unprocessed offers
            offers = get_unprocessed_offers(cur)
            print(f"Found {len(offers)} offers to process")

            if not offers:
                print("Nothing to do!")
                return

            # 3. Process each offer
            total_skills_inserted = 0
            for i, (offer_id, description) in enumerate(offers):
                skills = extract_skills(description)
                insert_offer_skills(cur, offer_id, skills, skill_map)
                total_skills_inserted += len(skills)

                if (i + 1) % 100 == 0:
                    conn.commit()
                    print(f"  Processed {i+1}/{len(offers)} offers...")

            conn.commit()

    print(f"\nDone! Inserted {total_skills_inserted} skill links for {len(offers)} offers.")


if __name__ == "__main__":
    main()
