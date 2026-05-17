import pandas as pd
import requests
import time
import os
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Configuration du logging (Standardisation)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_ft_access_token():
    """Récupère le token OAuth2 UNE SEULE FOIS pour toute la session."""
    client_id = os.getenv("FRANCETRAVAIL_CLIENT_ID")
    client_secret = os.getenv("FRANCETRAVAIL_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        logging.warning("Clés API France Travail introuvables. Mode MOCK activé.")
        return None

    token_url = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"
    token_params = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "api_offresdemploiv2 o2dsoffre"
    }
    
    try:
        response = requests.post(token_url, data=token_params, timeout=10)
        response.raise_for_status()
        logging.info("🔑 Token France Travail généré avec succès.")
        return response.json().get("access_token")
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Échec de l'authentification France Travail : {e}")
        return None

def get_francetravail_jobs(access_token, mots_cles, code_departement=None, limit=100):
    """
    Recherche des offres en utilisant le token fourni.
    Note: On utilise 'departement' plutôt que 'commune' pour éviter les soucis de code INSEE.
    """
    if not access_token:
        return generate_mock_jobs(mots_cles, code_departement)

    logging.info(f"Recherche France Travail: '{mots_cles}' (Dept: {code_departement or 'Tous'})...")
    
    search_url = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    
    # Paramètres corrigés
    params = {
        "motsCles": mots_cles,
        "natureContrat": "E1,E2", # E1=CDI, E2=CDD
        "sort": 1 # Tri par pertinence
    }
    # France Travail gère mieux les numéros de département (ex: 75 pour Paris, 69 pour Lyon)
    if code_departement:
        params["departement"] = code_departement
        
    try:
        response = requests.get(search_url, headers=headers, params=params, timeout=10)
        
        # Si erreur 204, cela signifie simplement "Aucun résultat", ce n'est pas une vraie erreur
        if response.status_code == 204:
            logging.info(f"Aucune offre trouvée pour '{mots_cles}'.")
            return []
            
        response.raise_for_status()
        offres_api = response.json().get("resultats", [])
        
        jobs = []
        ingestion_timestamp = datetime.now().isoformat()
        
        for offre in offres_api[:limit]:
            # Extraction propre des compétences si elles existent
            competences = [comp.get("libelle") for comp in offre.get("competences", [])]
            
            job = {
                "source_job_id": offre.get("id"), # ID NATIF OBLIGATOIRE
                "title": offre.get("intitule", "N/A"),
                "company": offre.get("entreprise", {}).get("nom", "Confidentiel"),
                "location": offre.get("lieuTravail", {}).get("libelle", "Non spécifié"),
                "rome_code": offre.get("romeCode", "N/A"), # Code métier (très utile)
                "rome_label": offre.get("appellationlibelle", "N/A"),
                "contract_type": offre.get("typeContrat", "N/A"),
                "salary": offre.get("salaire", {}).get("libelle", "N/A"),
                "skills": competences, # Ajout crucial pour le système de recommandation
                "description": offre.get("description", "N/A"),
                "source": "France Travail API",
                "scraped_at": ingestion_timestamp
            }
            jobs.append(job)
            
        logging.info(f"✅ {len(jobs)} offres récupérées.")
        return jobs
        
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Erreur API France Travail : {e}")
        return []

def generate_mock_jobs(mots_cles, location):
    # (Votre code mock reste inchangé, assurez-vous juste d'utiliser un ID unique constant ou source_job_id)
    return [] # Simplifié pour la lisibilité

def save_to_datalake(jobs_data):
    if not jobs_data:
        return

    current_file_path = Path(__file__).resolve()
    project_root = current_file_path.parents[2] 
    output_dir = project_root / "02_data_lake" / "bronze" / "francetravail"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = output_dir / f"francetravail_{timestamp}.json"
    
    try:
        df = pd.DataFrame(jobs_data)
        df.to_json(file_path, orient='records', lines=True, force_ascii=False)
        logging.info(f"🔥 {len(jobs_data)} offres sauvegardées dans: {file_path}")
    except Exception as e:
        logging.error(f"❌ Erreur de sauvegarde : {e}")

if __name__ == "__main__":
    logging.info("🚀 Démarrage du pipeline France Travail...")
    
    # 1. On récupère le token UNE SEULE FOIS
    token = get_ft_access_token()
    
    roles = ["Data Engineer", "Data Analyst", "Data Scientist"]
    
    # 2. On utilise des codes départements pour la France (75=Paris, 69=Rhône, 31=Haute-Garonne)
    # L'API France Travail n'est pas conçue pour chercher "Casablanca" en texte libre.
    departements = ["75", "69", "31", None] # None = Toute la France
    
    all_data = []
    
    for role in roles:
        for dept in departements:
            data = get_francetravail_jobs(access_token=token, mots_cles=role, code_departement=dept, limit=100)
            all_data.extend(data)
            time.sleep(1) # Respect du Rate Limiting
            
    save_to_datalake(all_data)
    logging.info(f"🏁 Processus terminé. Total : {len(all_data)} offres.")