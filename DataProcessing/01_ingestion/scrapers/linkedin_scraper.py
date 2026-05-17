import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import os
import uuid
import logging
import urllib.parse
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_ingestion_id():
    return str(uuid.uuid4())

def get_linkedin_jobs(query, location, num_pages=1):
    """
    Tente de scraper l'URL publique de LinkedIn. Bascule sur Mock si bloqué.
    """
    query_encoded = urllib.parse.quote_plus(query)
    location_encoded = urllib.parse.quote_plus(location)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    jobs = []
    ingestion_timestamp = datetime.now().isoformat()
    
    for page in range(num_pages):
        url = f"https://www.linkedin.com/jobs/search/?keywords={query_encoded}&location={location_encoded}&start={page * 25}"
        logging.info(f"🔎 Scraping LinkedIn: '{query}' à '{location}' (Page {page + 1})")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            job_cards = soup.find_all('div', class_='base-card')
            
            for card in job_cards:
                # 1. Extraction de l'ID natif LinkedIn (ex: urn:li:jobPosting:3847593)
                job_id = card.get('data-entity-urn', '').split(':')[-1]
                if not job_id:
                    # Alternative si la structure HTML a changé
                    link_elem = card.find('a', class_='base-card__full-link')
                    if link_elem and 'href' in link_elem.attrs:
                        job_id = link_elem['href'].split('?')[0].split('-')[-1]
                    else:
                        job_id = str(uuid.uuid4())

                title_elem = card.find('h3', class_='base-search-card__title')
                company_elem = card.find('h4', class_='base-search-card__subtitle')
                location_elem = card.find('span', class_='job-search-card__location')
                
                job = {
                    "source_job_id": job_id,
                    "title": title_elem.text.strip() if title_elem else "N/A",
                    "company": company_elem.text.strip() if company_elem else "N/A",
                    "location": location_elem.text.strip() if location_elem else "N/A",
                    "url": f"https://www.linkedin.com/jobs/view/{job_id}" if job_id else "N/A",
                    "description": "N/A", # Impossible d'avoir la description complète ici
                    "source": "LinkedIn Web Scraper",
                    "scraped_at": ingestion_timestamp
                }
                jobs.append(job)
                
            time.sleep(2) 
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in [429, 400, 999]:
                logging.warning(f"⚠️ Erreur {e.response.status_code}: LinkedIn a bloqué la requête (Anti-Bot).")
                logging.info("💡 Circuit Breaker activé: Génération de données Mockées avec descriptions factices.")
                return generate_mock_jobs(query, location, ingestion_timestamp)
            else:
                logging.error(f"❌ Erreur HTTP inattendue : {e}")
                
        except Exception as e:
            logging.error(f"❌ Erreur inattendue: {e}")

    if not jobs:
        return generate_mock_jobs(query, location, ingestion_timestamp)
        
    return jobs

def generate_mock_jobs(query, location, timestamp):
    mock_jobs = []
    companies = ["AnalyticsGroup", "NeoTech", "ScaleUp Inc", "BankCorp", "DataOps LLC"]
    
    for i in range(5):
        fake_id = f"mock_li_{uuid.uuid4().hex[:10]}"
        job = {
            "source_job_id": fake_id,
            "title": f"{query}",
            "company": companies[i % len(companies)],
            "location": location,
            "url": f"https://www.linkedin.com/jobs/view/{fake_id}",
            "description": f"Nous recherchons un(e) {query} dynamique pour rejoindre notre équipe à {location}. Vous maîtrisez Python, SQL et l'écosystème Big Data. Vous avez une forte capacité d'analyse et savez créer des pipelines ETL performants. Une expérience avec Snowflake ou BigQuery est un vrai plus.",
            "source": "LinkedIn (Mocked)",
            "scraped_at": timestamp
        }
        mock_jobs.append(job)
    return mock_jobs

def save_to_datalake(jobs_data):
    if not jobs_data:
        return

    current_file_path = Path(__file__).resolve()
    project_root = current_file_path.parents[2] 
    output_dir = project_root / "02_data_lake" / "bronze" / "linkedin"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ingestion_id = generate_ingestion_id()[:8]
    file_path = output_dir / f"linkedin_{timestamp}_{ingestion_id}.json"
    
    try:
        df = pd.DataFrame(jobs_data)
        df.to_json(file_path, orient='records', lines=True, force_ascii=False)
        logging.info(f"🔥 {len(jobs_data)} offres sauvegardées dans: {file_path}")
    except Exception as e:
        logging.error(f"❌ Erreur de sauvegarde: {e}")

if __name__ == "__main__":
    logging.info("🚀 Démarrage du pipeline LinkedIn (Dev)...")
    
    roles = ["Data Engineer"]
    locations = ["Paris"]
    
    all_data = []
    
    for role in roles:
        for loc in locations:
            data = get_linkedin_jobs(query=role, location=loc, num_pages=1)
            all_data.extend(data)
            
    save_to_datalake(all_data)