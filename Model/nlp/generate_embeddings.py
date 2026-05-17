"""
Generate Embeddings — encodes all job descriptions into 384-d vectors
and stores them in the fact_job_offer.embedding JSONB column.
"""

import time
from nlp.db_utils import get_connection, get_cursor
from nlp.embeddings import encode_batch, embedding_to_json


def get_offers_without_embeddings(cur) -> list:
    """Get offers where embedding IS NULL and description_clean exists."""
    cur.execute("""
        SELECT offer_id, description_clean
        FROM fact_job_offer
        WHERE embedding IS NULL
          AND description_clean IS NOT NULL
          AND description_clean != ''
        ORDER BY offer_id
    """)
    return cur.fetchall()


def generate_and_store_embeddings(batch_size: int = 64):
    """Main function: encode all descriptions and store in DB."""
    start = time.time()

    with get_connection() as conn:
        with get_cursor(conn, commit=False) as cur:
            # 1. Fetch offers
            offers = get_offers_without_embeddings(cur)
            print(f"Found {len(offers)} offers without embeddings")

            if not offers:
                print("Nothing to do!")
                return

            # 2. Separate IDs and texts
            offer_ids = [o[0] for o in offers]
            descriptions = [o[1] for o in offers]

            # 3. Encode all at once
            print(f"Encoding {len(descriptions)} descriptions...")
            embeddings = encode_batch(descriptions, batch_size=batch_size)
            print(f"Encoding done in {time.time() - start:.1f}s")

            # 4. Store each embedding back in the DB
            print("Storing embeddings in database...")
            for i, (oid, emb) in enumerate(zip(offer_ids, embeddings)):
                json_emb = embedding_to_json(emb)
                cur.execute(
                    "UPDATE fact_job_offer SET embedding = %s WHERE offer_id = %s",
                    (json_emb, oid)
                )
                if (i + 1) % 200 == 0:
                    conn.commit()
                    print(f"  Stored {i+1}/{len(offer_ids)}...")

            conn.commit()

    elapsed = time.time() - start
    print(f"\nDone! Encoded {len(offer_ids)} offers in {elapsed:.1f}s")


if __name__ == "__main__":
    generate_and_store_embeddings()
