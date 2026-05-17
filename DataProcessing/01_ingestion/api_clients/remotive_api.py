import pandas as pd
import requests
import uuid
import time
import logging
from datetime import datetime
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_ingestion_id():
    """
    Génère un ID unique pour le lot d'ingestion (traçabilité).
    """
    return str(uuid.uuid4())

def get_remotive_jobs(category=None):
    """
    Appelle l'API publique de Remotive pour récupérer des offres d'emploi 100% remote.
    """
    logging.info(f"Appel de l'API Remotive pour la catégorie : {category or 'Toutes'}...")
    
    jobs = []
    url = "https://remotive.com/api/remote-jobs"
    params = {"category": category} if category else {}
        
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json() 
        
        results = data.get("jobs", [])
        ingestion_timestamp = datetime.now().isoformat()
        
        for offre in results:
            job = {
                # On utilise l'ID de Remotive pour éviter les doublons dans le Data Lake
                "source_job_id": str(offre.get("id")), 
                "title": offre.get("title", "N/A"),
                "company": offre.get("company_name", "N/A"),
                "location": offre.get("candidate_required_location", "Remote Global"),
                "job_type": offre.get("job_type", "N/A"),
                "tags": offre.get("tags", []),
                "publication_date": offre.get("publication_date", "N/A"),
                "url": offre.get("url", ""),
                "description": offre.get("description", "N/A"),
                "source": "Remotive API",
                "scraped_at": ingestion_timestamp
            }
            jobs.append(job)
            
        logging.info(f"✅ Catégorie '{category}': {len(jobs)} offres récupérées avec succès !")
        
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Erreur réseau lors de l'appel API Remotive : {e}")
    except Exception as e:
        logging.error(f"❌ Erreur inattendue : {e}")
            
    return jobs

def save_to_datalake(jobs_data):
    if not jobs_data:
        logging.warning("⚠️ Aucune offre à sauvegarder.")
        return

    current_file_path = Path(__file__).resolve()
    project_root = current_file_path.parents[2] 
    output_dir = project_root / "02_data_lake" / "bronze" / "remotive"
    
    # Création des dossiers si nécessaires
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Nom du fichier avec UUID d'ingestion pour garantir l'unicité
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ingestion_id = generate_ingestion_id()[:8]
    file_path = output_dir / f"remotive_{timestamp}_{ingestion_id}.json"
    
    try:
        df = pd.DataFrame(jobs_data)
        # L'enregistrement en JSON Lines (ndjson) est parfait pour la couche Bronze
        df.to_json(file_path, orient='records', lines=True, force_ascii=False)
        logging.info(f"🔥 {len(jobs_data)} offres sauvegardées dans: {file_path}")
    except Exception as e:
        logging.error(f"❌ Erreur lors de la sauvegarde dans le Data Lake : {e}")

if __name__ == "__main__":
    logging.info("🚀 Démarrage du pipeline d'ingestion Remotive...")
    
    # Categories pertinentes pour le projet Data
    categories = ["data", "software-dev"]
    all_data = []
    
    for cat in categories:
        real_data = get_remotive_jobs(category=cat)
        all_data.extend(real_data)
        # Petite pause pour ne pas spammer l'API
        time.sleep(1.5)
        
    save_to_datalake(all_data)
    logging.info(f"🏁 Processus terminé. Total des offres brutes récupérées : {len(all_data)}")