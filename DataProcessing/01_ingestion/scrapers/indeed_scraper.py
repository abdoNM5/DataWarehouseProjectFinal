import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import uuid
import logging
import urllib.parse
from datetime import datetime
from pathlib import Path

# Configuration standardisée du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_ingestion_id():
    return str(uuid.uuid4())

def get_job_offers(query, location, num_pages=1):
    """
    Tente de scraper Indeed. Bascule sur un Mock en cas de blocage (403/Captcha).
    """
    # Encodage sécurisé des paramètres (transforme "C++" en "C%2B%2B", etc.)
    query_encoded = urllib.parse.quote_plus(query)
    location_encoded = urllib.parse.quote_plus(location)
    
    # Headers plus complets pour tenter (faiblement) de passer les filtres basiques
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://fr.indeed.com/"
    }

    jobs = []
    ingestion_timestamp = datetime.now().isoformat()
    
    for page in range(num_pages):
        url = f"https://fr.indeed.com/jobs?q={query_encoded}&l={location_encoded}&start={page * 10}"
        logging.info(f"🔎 Tentative Scraping Indeed: '{query}' à '{location}' (Page {page + 1})")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            job_cards = soup.find_all('div', class_='job_seen_beacon')
            
            for card in job_cards:
                # 1. Extraction de l'ID UNIQUE Indeed (Très important)
                # L'ID se trouve souvent dans la balise <a> ou un div parent avec l'attribut data-jk
                link_elem = card.find('a', id=lambda x: x and x.startswith('job_'))
                job_key = link_elem['data-jk'] if link_elem and 'data-jk' in link_elem.attrs else str(uuid.uuid4())

                title_elem = card.find('h2', class_='jobTitle')
                company_elem = card.find('span', class_='companyName')
                location_elem = card.find('div', class_='companyLocation')
                desc_elem = card.find('div', class_='job-snippet')
                
                job = {
                    "source_job_id": job_key, # Utilisation de la Job Key
                    "title": title_elem.text.strip() if title_elem else "N/A",
                    "company": company_elem.text.strip() if company_elem else "N/A",
                    "location": location_elem.text.strip() if location_elem else "N/A",
                    "description": desc_elem.text.strip() if desc_elem else "N/A",
                    "url": f"https://fr.indeed.com/viewjob?jk={job_key}" if job_key else "N/A",
                    "source": "Indeed Web Scraper",
                    "scraped_at": ingestion_timestamp
                }
                jobs.append(job)
                
            time.sleep(2) 
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logging.warning("⚠️ Erreur 403: Protection Anti-Bot Cloudflare activée.")
                logging.info("💡 Circuit Breaker: Bascule automatique sur les données Mockées pour la continuité du pipeline.")
                return generate_mock_jobs(query, location, ingestion_timestamp)
            else:
                logging.error(f"❌ Erreur HTTP inattendue : {e}")
                
        except Exception as e:
            logging.error(f"❌ Erreur lors du scraping de la page {page}: {e}")

    if not jobs:
        logging.info("Aucune donnée extraite. Bascule sur les données Mockées.")
        return generate_mock_jobs(query, location, ingestion_timestamp)
        
    return jobs

def generate_mock_jobs(query, location, timestamp):
    """Génère un dataset réaliste pour alimenter la couche Bronze."""
    mock_jobs = []
    companies = ["DataCorp", "AI Solutions", "Cloud Data", "RetailTech", "FinData Bank", "SmartStream", "Data Engineering Co"]
    
    # Générer seulement 5 offres par appel pour ne pas exploser la taille du fichier (il y a beaucoup de requêtes)
    for i in range(5):
        # Création d'une "fausse" Job Key réaliste
        fake_jk = f"mock_{uuid.uuid4().hex[:12]}"
        
        job = {
            "source_job_id": fake_jk,
            "title": f"Senior {query}",
            "company": companies[i % len(companies)],
            "location": location,
            "description": f"En tant que {query} chez {companies[i % len(companies)]} ({location}), vous concevrez et maintiendrez des pipelines de données robustes. Compétences requises : Python, SQL, Apache Spark, et une solide expérience avec un cloud provider (AWS/GCP/Azure). Familiarité avec Docker et l'orchestration via Apache Airflow.",
            "url": f"https://fr.indeed.com/viewjob?jk={fake_jk}",
            "source": "Indeed (Mocked)",
            "scraped_at": timestamp
        }
        mock_jobs.append(job)
        
    return mock_jobs

def save_to_datalake(jobs_data):
    if not jobs_data:
        logging.warning("⚠️ Aucune offre à sauvegarder.")
        return

    current_file_path = Path(__file__).resolve()
    project_root = current_file_path.parents[2] 
    output_dir = project_root / "02_data_lake" / "bronze" / "indeed"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ingestion_id = generate_ingestion_id()[:8]
    file_path = output_dir / f"indeed_{timestamp}_{ingestion_id}.json"
    
    try:
        df = pd.DataFrame(jobs_data)
        df.to_json(file_path, orient='records', lines=True, force_ascii=False)
        logging.info(f"🔥 {len(jobs_data)} offres sauvegardées dans: {file_path}")
    except Exception as e:
        logging.error(f"❌ Erreur lors de la sauvegarde : {e}")

if __name__ == "__main__":
    logging.info("🚀 Démarrage de l'ingestion Indeed...")
    
    # Pour des tests de développement, réduisez ces listes pour aller plus vite.
    roles = ["Data Engineer", "Data Architect"]
    locations = ["Paris", "Casablanca", "Remote"]
    
    all_data = []
    
    for role in roles:
        for loc in locations:
            # 1 seule page pour le test, car le Mock s'activera de toute façon
            data = get_job_offers(query=role, location=loc, num_pages=1)
            all_data.extend(data)
            time.sleep(1.5)
            
    save_to_datalake(all_data)
    logging.info(f"🏁 Processus terminé. Total offres générées: {len(all_data)}")