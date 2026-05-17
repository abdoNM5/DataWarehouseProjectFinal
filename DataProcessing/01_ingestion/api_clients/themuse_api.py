import pandas as pd
import requests
import uuid
import time
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_ingestion_id():
    return str(uuid.uuid4())

def get_themuse_jobs(category="Data and Analytics", max_pages=5):
    """
    Appelle l'API The Muse avec une pagination dynamique basée sur 'page_count'
    et une limite de sécurité (max_pages).
    """
    logging.info(f"Début de l'extraction The Muse pour : '{category}'...")
    
    jobs = []
    base_url = "https://www.themuse.com/api/public/jobs"
    ingestion_timestamp = datetime.now().isoformat()
    
    current_page = 1
    total_pages = 1 # Sera mis à jour après le premier appel
    
    # Boucle dynamique contrôlée par les métadonnées de l'API ET notre limite
    while current_page <= total_pages and current_page <= max_pages:
        params = {"page": current_page, "category": category}
            
        try:
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Mise à jour du nombre total de pages réelles disponibles selon l'API
            total_pages = data.get("page_count", 0)
            results = data.get("results", [])
            
            if not results:
                break

            for offre in results:
                # Extraction propre sans risque de crash (IndexError)
                locations = [loc.get("name") for loc in offre.get("locations", [])]
                levels = [lvl.get("name") for lvl in offre.get("levels", [])]
                
                job = {
                    "source_job_id": str(offre.get("id")),
                    "title": offre.get("name", "N/A"),
                    "company": offre.get("company", {}).get("name", "N/A"),
                    # On joint les localisations s'il y en a plusieurs, sinon on met "Unspecified"
                    "location": ", ".join(locations) if locations else "Unspecified",
                    "levels": levels, 
                    "publication_date": offre.get("publication_date", "N/A"),
                    "url": offre.get("refs", {}).get("landing_page", ""),
                    "description": offre.get("contents", "N/A"),
                    "source": "TheMuse API",
                    "scraped_at": ingestion_timestamp
                }
                jobs.append(job)
                
            logging.info(f"✅ The Muse [{category}] - Page {current_page}/{min(total_pages, max_pages)} : {len(results)} offres.")
            
            current_page += 1
            time.sleep(1) # Rate limiting
            
        except requests.exceptions.RequestException as e:
            logging.error(f"❌ Erreur réseau The Muse (page {current_page}) : {e}")
            break
            
    return jobs

def save_to_datalake(jobs_data):
    if not jobs_data:
        logging.warning("⚠️ Aucune offre à sauvegarder.")
        return

    current_file_path = Path(__file__).resolve()
    project_root = current_file_path.parents[2] 
    output_dir = project_root / "02_data_lake" / "bronze" / "themuse"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ingestion_id = generate_ingestion_id()[:8]
    file_path = output_dir / f"themuse_{timestamp}_{ingestion_id}.json"
    
    try:
        df = pd.DataFrame(jobs_data)
        df.to_json(file_path, orient='records', lines=True, force_ascii=False)
        logging.info(f"🔥 {len(jobs_data)} offres sauvegardées dans: {file_path}")
    except Exception as e:
        logging.error(f"❌ Erreur de sauvegarde : {e}")

if __name__ == "__main__":
    logging.info("🚀 Démarrage du pipeline The Muse...")
    
    # Réduction à des catégories très ciblées Data pour l'exemple
    categories = ["Data and Analytics", "Software Engineering"]
    all_data = []
    
    for cat in categories:
        # max_pages=3 pour les tests de dev, à augmenter (ex: 20) en production
        real_data = get_themuse_jobs(category=cat, max_pages=3) 
        all_data.extend(real_data)
        time.sleep(2)
        
    save_to_datalake(all_data)
    logging.info(f"🏁 Pipeline terminé. Total offres : {len(all_data)}")