# 🧠 Projet Job Intelligent — Plan de Continuation (Duo)

## 📋 Résumé de ce qui est DÉJÀ FAIT

Avant de planifier la suite, voici l'inventaire complet de ce qui existe dans le projet :

| Composant | Statut | Fichiers |
|-----------|--------|----------|
| **Repo & Structure** | ✅ Terminé | `.gitignore`, `README.md`, `.env` |
| **Docker Compose** | ✅ Terminé | `docker-compose.yml` — PostgreSQL (Airflow), PostgreSQL (warehouse), Jupyter+PySpark, Airflow |
| **6 Collectors (Ingestion)** | ✅ Terminé | `ingestion/collectors/` — Indeed, LinkedIn, France Travail, Remotive, The Muse, Glassdoor |
| **Airflow DAG d'ingestion** | ✅ Terminé | `ingestion/orchestration/job_ingestion_dag.py` |
| **Bronze Data Lake** | ✅ Terminé | ~4 000 records scrapés (996 France Travail, 2500 LinkedIn, 476 The Muse, 20 Remotive, 5 Indeed) |
| **Modélisation Star Schema** | ✅ Terminé | `docs/modelisation.md` — 572 lignes de documentation détaillée |
| **DDL SQL (init.sql)** | ✅ Terminé | `db/init.sql` — Toutes les tables, seed data, indexes |
| **Data Exploration Notebook** | ✅ Terminé | `notebooks/01_data_exploration.ipynb` |
| **API Contract (OpenAPI)** | ✅ Terminé | `docs/api-contracts/job-api.yaml` |
| **Schema Documentation** | ✅ Terminé | `docs/schemas/job_posting_schema.md` |
| **ETL Pipeline** | ❌ Vide | `etl/__init__.py` seulement |
| **NLP Module** | ❌ Inexistant | Pas de dossier `nlp/` |
| **FastAPI Backend** | ❌ Inexistant | Pas de dossier `api/` |
| **Frontend Web** | ❌ Inexistant | Pas de dossier `frontend/` |
| **Power BI Dashboard** | ❌ Inexistant | Pas de dossier `dashboard/` |

---

## 🤝 Répartition du Travail

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PROJET JOB INTELLIGENT                           │
│                                                                     │
│  ┌──────────────────────────┐    ┌──────────────────────────────┐  │
│  │     🧑 TOI (Part A)      │    │    👤 TON AMI (Part B)       │  │
│  │                          │    │                              │  │
│  │  1. NLP Model            │    │  1. ETL Pipeline             │  │
│  │     - Skills Extraction  │    │     - Extract (bronze→)      │  │
│  │     - Title Normaliser   │    │     - Transform (clean)      │  │
│  │     - Embeddings         │    │     - Load (→ star schema)   │  │
│  │     - Recommender        │    │                              │  │
│  │                          │    │  2. Airflow DAG ETL          │  │
│  │  2. FastAPI Backend      │    │     - Orchestration T+L      │  │
│  │     - /jobs endpoint     │    │                              │  │
│  │     - /recommend endpoint│    │  3. Power BI Dashboard       │  │
│  │     - /skills endpoint   │    │     - 6 pages                │  │
│  │                          │    │     - Connexion PostgreSQL    │  │
│  │  3. Frontend Website     │    │     - Thème & Polish         │  │
│  │     - Search & Filters   │    │                              │  │
│  │     - Recommendations    │    │                              │  │
│  │     - Job Details        │    │                              │  │
│  └──────────┬───────────────┘    └──────────────┬───────────────┘  │
│             │                                    │                  │
│             └──────────┐    ┌────────────────────┘                  │
│                        ▼    ▼                                       │
│              ┌─────────────────────┐                                │
│              │  PostgreSQL Star    │                                │
│              │  Schema (partagé)   │                                │
│              │  + bridge_offer_    │                                │
│              │    skill            │                                │
│              └─────────────────────┘                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔗 Interface Partagée (Contrat entre les deux parties)

> [!IMPORTANT]
> **Ce contrat est la clé pour travailler en parallèle sans se bloquer.** Les deux parties doivent respecter ces interfaces pour que le projet s'assemble correctement.

### 1. La base de données Star Schema (`warehouse-db`)
- **Connexion** : `postgresql://warehouse:warehouse@localhost:5433/jobs_dw`
- **Tables** : Exactement celles définies dans `db/init.sql` (déjà créées)
- **Propriétaire** : L'ami gère le contenu (ETL load), toi tu lis les données (API)

### 2. Le bridge `bridge_offer_skill` — zone de collaboration
- **L'ami** charge les skills qui viennent directement des sources (champ `skills[]` des données brutes) avec `confidence_score = 1.00`
- **Toi** tu ajoutes les skills extraites par NLP depuis les descriptions avec `confidence_score` variable (0.50 à 0.95)
- Les deux écrivent dans la même table, mais avec des sources différentes

### 3. La table `dim_skill` — référentiel partagé
- Le seed data dans `init.sql` contient déjà ~100 skills. Les deux parties peuvent ajouter de nouvelles skills via `INSERT ... ON CONFLICT DO NOTHING`

### 4. Fichiers de données Bronze
- Chemin : `data_lake/bronze/{source}/` (fichiers JSONL)
- L'ami lit ces fichiers pour l'ETL
- Toi, tu lis `description_clean` depuis `fact_job_offer` (après que l'ami l'a chargé) pour le NLP

---

# 🧑 PART A — TOI : NLP Model + Website

---

## A1. Module NLP — Skills Extraction (`nlp/skills_extractor.py`)

### Objectif
Extraire automatiquement les compétences techniques depuis les descriptions d'offres d'emploi, même quand la source ne les fournit pas (France Travail = 0%, LinkedIn = 0%).

### Sous-tâches détaillées

#### A1.1 — Créer le dossier `nlp/` et la structure

```
nlp/
├── __init__.py
├── skills_extractor.py      # Extraction de skills par regex + spaCy
├── title_normaliser.py      # Normalisation des titres → job_family
├── embeddings.py            # Génération d'embeddings vectoriels
├── recommender.py           # Moteur de recommandation
└── config.py                # Dictionnaires, seuils, paramètres
```

#### A1.2 — Skills Extractor (Regex + spaCy Matcher)

**Approche hybride recommandée :**

1. **Phase 1 — Regex (rapide, fiable)** :
   - Charger la liste des ~100 skills depuis `dim_skill` en base
   - Pour chaque description, chercher les skills par exact match (case-insensitive)
   - Gérer les variantes : `"scikit-learn"` / `"sklearn"` / `"scikit learn"`
   - `confidence_score = 1.00` pour les matchs exacts

2. **Phase 2 — spaCy Matcher (plus intelligent)** :
   - Utiliser `spaCy` avec le modèle `fr_core_news_md` (français) ou `en_core_web_md` (anglais)
   - Créer un `PhraseMatcher` avec les patterns de skills
   - Détecter les skills contextuelles ("expérience en ingénierie de données" → `Data Engineering`)
   - `confidence_score = 0.70-0.90` pour les matchs contextuels

3. **Phase 3 — Enrichissement par contexte (optionnel)** :
   - Utiliser un modèle de classification simple (TF-IDF + LogisticRegression) pour prédire des skills à partir du texte
   - `confidence_score = 0.50-0.70` pour les prédictions

**Fichier attendu : `nlp/skills_extractor.py`**
```python
# Squelette
class SkillsExtractor:
    def __init__(self, db_connection):
        """Charger le référentiel de skills depuis dim_skill."""
    
    def extract_from_text(self, text: str) -> list[dict]:
        """Retourner [{"skill_name": "Python", "skill_id": 1, "confidence": 1.0}, ...]"""
    
    def process_offer(self, offer_id: int, description: str) -> int:
        """Extraire et insérer dans bridge_offer_skill. Retourner le nombre de skills trouvées."""
    
    def process_all_offers(self) -> dict:
        """Traiter toutes les offres en base. Retourner des stats."""
```

**Dépendances Python** : `spacy`, `psycopg2-binary`

---

#### A1.3 — Title Normaliser (`nlp/title_normaliser.py`)

**Objectif** : Mapper les titres bruts chaotiques vers des `job_family` standardisées.

**Mapping attendu :**

| Pattern dans le titre | `job_family` | `seniority_level` |
|---|---|---|
| *data engineer*, *ingénieur données*, *data eng* | `Data Engineer` | extrait du titre |
| *data scientist*, *data science* | `Data Scientist` | extrait du titre |
| *data analyst*, *analyste données* | `Data Analyst` | extrait du titre |
| *ml engineer*, *machine learning eng* | `ML Engineer` | extrait du titre |
| *bi developer*, *analytics engineer*, *power bi* | `BI Developer` | extrait du titre |
| *business analyst* | `Business Analyst` | extrait du titre |
| tout le reste data-related | `Other Data` | — |

**Méthode** :
1. Nettoyer le titre : retirer `(H/F)`, `(F/H)`, villes entre parenthèses, numéros
2. Lowercase + strip
3. Regex matching contre les patterns ci-dessus
4. Fallback : fuzzy matching avec `rapidfuzz` (ratio > 80%)
5. Extraction du seniority : chercher `"Senior"`, `"Junior"`, `"Lead"`, `"Alternance"`, `"Intern"`, `"Stage"` → sinon `"Mid"`

**Fichier attendu : `nlp/title_normaliser.py`**
```python
class TitleNormaliser:
    def normalise(self, raw_title: str) -> dict:
        """Retourner {"normalised_title": "...", "job_family": "...", "seniority_level": "..."}"""
```

> [!TIP]
> **Ce module est critique aussi pour ton ami** : il l'utilisera dans son ETL pour remplir `dim_job_title`. Livre-le en premier pour ne pas le bloquer.

---

## A2. Module NLP — Embeddings (`nlp/embeddings.py`)

### Objectif
Encoder chaque description d'offre en un vecteur 384-dimensions pour permettre la recherche sémantique et les recommandations.

### Sous-tâches détaillées

#### A2.1 — Choix du modèle
- **Recommandé** : `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
  - Supporte le français ET l'anglais (nos offres sont bilingues)
  - 384 dimensions, léger (~120 Mo)
  - Gratuit, open source (Hugging Face)

#### A2.2 — Stocker les embeddings

**Option recommandée** : Table séparée (ne pas surcharger `fact_job_offer`)

```sql
-- À ajouter dans db/init.sql ou via un script de migration
CREATE TABLE IF NOT EXISTS job_embeddings (
    offer_id    INTEGER PRIMARY KEY REFERENCES fact_job_offer(offer_id) ON DELETE CASCADE,
    embedding   FLOAT8[] NOT NULL,    -- tableau de 384 floats
    model_name  VARCHAR(100) NOT NULL DEFAULT 'paraphrase-multilingual-MiniLM-L12-v2',
    created_at  TIMESTAMP DEFAULT NOW()
);
```

> [!IMPORTANT]
> **Alternative plus performante** : Utiliser l'extension `pgvector` pour PostgreSQL, qui permet des requêtes `ORDER BY embedding <=> query_vector` optimisées. Cela nécessite de modifier l'image Docker du warehouse-db pour inclure pgvector.

#### A2.3 — Pipeline d'embedding

```python
class EmbeddingPipeline:
    def __init__(self, model_name="paraphrase-multilingual-MiniLM-L12-v2"):
        """Charger le modèle sentence-transformers."""
    
    def embed_text(self, text: str) -> list[float]:
        """Retourner un vecteur de 384 floats."""
    
    def embed_all_offers(self) -> int:
        """Lire description_clean depuis fact_job_offer, générer embeddings, insérer dans job_embeddings."""
```

**Dépendances Python** : `sentence-transformers`, `torch`

---

## A3. Module NLP — Recommender (`nlp/recommender.py`)

### Objectif
Accepter un profil candidat (skills + description libre) et retourner les top-K offres les plus pertinentes.

### Algorithme de scoring (hybride)

```
score_final = α × skill_overlap_score + β × semantic_similarity_score

où:
  α = 0.4  (poids des skills)
  β = 0.6  (poids de la similarité sémantique)
```

#### Skill Overlap Score
```
skill_overlap = |skills_candidat ∩ skills_offre| / |skills_candidat|
```
- Utilise `bridge_offer_skill` pour obtenir les skills de chaque offre
- Normalise entre 0 et 1

#### Semantic Similarity Score
```
semantic_sim = cosine_similarity(embedding_candidat, embedding_offre)
```
- L'embedding candidat est généré à la volée depuis sa description libre
- Comparaison contre tous les embeddings d'offres dans `job_embeddings`

### Fichier attendu : `nlp/recommender.py`
```python
class JobRecommender:
    def __init__(self, db_connection, embedding_pipeline, skills_extractor):
        """Initialiser avec les composants NLP."""
    
    def recommend(self, candidate_skills: list[str], candidate_description: str, top_k: int = 20) -> list[dict]:
        """
        Retourner les top_k offres triées par score.
        Chaque résultat : {offer_id, title, company, location, match_score, skill_matches, url}
        """
    
    def explain_match(self, offer_id: int, candidate_skills: list[str]) -> dict:
        """Expliquer pourquoi cette offre match : skills en commun, score détaillé."""
```

---

## A4. FastAPI Backend (`api/`)

### Objectif
Exposer le modèle NLP et les données du warehouse via une API REST, consommée par le frontend.

### Structure du dossier

```
api/
├── __init__.py
├── main.py                  # App FastAPI, CORS, lifespan
├── config.py                # Database URL, model config
├── database.py              # SQLAlchemy / psycopg2 connection pool
├── models.py                # Pydantic schemas (request/response)
├── routers/
│   ├── __init__.py
│   ├── jobs.py              # GET /jobs — recherche et filtres
│   ├── recommend.py         # POST /recommend — recommandations
│   ├── skills.py            # GET /skills — liste des skills
│   └── stats.py             # GET /stats — KPIs pour le dashboard web
└── requirements.txt
```

### Endpoints détaillés

#### `GET /api/jobs` — Recherche d'offres
```
Query params:
  - q (str)           : Recherche texte libre dans titre + description
  - job_family (str)  : Filtrer par famille de métiers
  - location (str)    : Filtrer par ville/pays
  - skills (str[])    : Filtrer par skills requises
  - contract (str)    : Filtrer par type de contrat
  - salary_min (int)  : Salaire minimum
  - page (int)        : Pagination (default: 1)
  - limit (int)       : Résultats par page (default: 20)

Response: {
  "total": 150,
  "page": 1,
  "items": [
    {
      "offer_id": 42,
      "title": "Senior Data Engineer",
      "company": "DataCorp",
      "location": "Paris, France",
      "job_family": "Data Engineer",
      "seniority": "Senior",
      "salary_min": 55000,
      "salary_max": 75000,
      "skills": ["Python", "Spark", "AWS"],
      "source": "LinkedIn",
      "url": "https://...",
      "posted_date": "2026-04-15"
    }
  ]
}
```

#### `POST /api/recommend` — Recommandations NLP
```
Request body: {
  "skills": ["Python", "SQL", "Spark", "Airflow"],
  "description": "Je suis un data engineer avec 3 ans d'expérience en pipelines de données...",
  "top_k": 10
}

Response: {
  "recommendations": [
    {
      "offer_id": 42,
      "title": "Senior Data Engineer",
      "company": "DataCorp",
      "match_score": 0.87,
      "skill_overlap": 0.75,
      "semantic_score": 0.94,
      "matched_skills": ["Python", "Spark", "Airflow"],
      "missing_skills": ["Kafka"],
      ...
    }
  ]
}
```

#### `GET /api/skills` — Référentiel de skills
```
Response: {
  "skills": [
    {"skill_id": 1, "name": "Python", "category": "Programming"},
    ...
  ]
}
```

#### `GET /api/stats` — Statistiques globales
```
Response: {
  "total_offers": 3997,
  "total_companies": 1800,
  "total_skills": 98,
  "offers_by_family": {"Data Engineer": 1200, "Data Scientist": 800, ...},
  "top_skills": [{"name": "Python", "count": 2500}, ...],
  "offers_by_source": {"linkedin": 2500, "france_travail": 996, ...}
}
```

### Docker
Ajouter au `docker-compose.yml` :
```yaml
  api:
    build: ./api
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://warehouse:warehouse@warehouse-db:5432/jobs_dw
    depends_on:
      - warehouse-db
    volumes:
      - ./nlp:/app/nlp
      - ./api:/app/api
```

**Dépendances** : `fastapi`, `uvicorn`, `psycopg2-binary`, `sqlalchemy`, `sentence-transformers`, `spacy`

---

## A5. Frontend Website (`frontend/`)

### Objectif
Interface web moderne permettant aux candidats de chercher des offres, obtenir des recommandations NLP, et explorer le marché.

### Pages à développer

#### Page 1 — Landing / Dashboard Home
- KPIs animés : total offres, total entreprises, top city, top skill
- Graphiques résumés (utilisent `GET /api/stats`)
- Barre de recherche rapide
- Call-to-action vers le recommandeur

#### Page 2 — Recherche d'offres (`/jobs`)
- Barre de recherche avec suggestions
- Filtres latéraux : job_family, location, contract, skills (multi-select), salary range
- Liste de résultats avec cards (titre, entreprise, lieu, skills tags, salaire)
- Pagination
- Cliquer sur une offre → Page détail

#### Page 3 — Détail d'une offre (`/jobs/:id`)
- Titre, entreprise, lieu, type contrat, salaire
- Description complète (formatée)
- Skills requises (tags colorés par catégorie)
- Lien vers l'offre originale (source)
- Bouton "Trouver des offres similaires"

#### Page 4 — Recommandeur NLP (`/recommend`)
- **Étape 1** : Sélection de skills (tag input — chercher et sélectionner parmi les skills disponibles)
- **Étape 2** : Texte libre — décrire son profil / métier idéal
- **Étape 3** : Résultats — liste d'offres triées par match_score avec barre de progression
- Pour chaque résultat : skills en commun (vert), skills manquantes (rouge), score détaillé
- Animation de chargement pendant le calcul NLP

### Stack technique suggérée
- **Option simple** : HTML + Vanilla JS + CSS (pas besoin de framework)
- **Option avancée** : Vite + Vanilla JS (ou React si tu es à l'aise)
- Design : dark mode, glassmorphism, micro-animations, palette cohérente

### Docker
```yaml
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - api
```

---

# 👤 PART B — TON AMI : ETL + Power BI

---

## B1. ETL Pipeline — Extract (`etl/extract.py`)

### Objectif
Lire les données brutes du Bronze Data Lake (fichiers JSONL) et les charger en mémoire de manière structurée.

### Sous-tâches détaillées

#### B1.1 — Scanner le data lake
- Parcourir `data_lake/bronze/{source}/` pour chaque source
- Lire tous les fichiers `.jsonl` (un record par ligne)
- Parser chaque ligne en dict Python

#### B1.2 — Validation de schéma
- Vérifier que les champs obligatoires existent : `title_raw` (ou `title`), `company_name`, `source`
- Logger les records invalides (ne pas les supprimer, les mettre de côté)
- Harmoniser les noms de champs (chaque source a des noms légèrement différents)

#### B1.3 — Unification des schémas
Chaque source a un format différent. L'extracteur doit tout convertir vers un schéma unifié :

```python
unified_record = {
    "source": "linkedin",                     # nom de la source
    "source_job_id": "abc123",                # ID original
    "title_raw": "Senior Data Engineer",      # titre brut
    "company_name": "DataCorp",               # entreprise
    "location_raw": "Paris, France",          # localisation brute
    "employment_type": "full_time",           # type contrat (ou None)
    "salary_min": None,                       # salaire min (ou None)
    "salary_max": None,                       # salaire max (ou None)
    "description": "...",                     # description brute
    "skills": ["Python", "SQL"],              # skills brutes (ou [])
    "url": "https://...",                     # lien offre
    "posted_at": "2026-04-15",               # date publication (ou None)
    "ingestion_ts": "2026-04-15T09:45:03Z"   # timestamp d'ingestion
}
```

**Fichier attendu : `etl/extract.py`**
```python
class BronzeExtractor:
    def __init__(self, data_lake_path="data_lake/bronze"):
        """Scanner le data lake."""
    
    def extract_all(self) -> list[dict]:
        """Retourner tous les records unifiés de toutes les sources."""
    
    def extract_source(self, source_name: str) -> list[dict]:
        """Retourner les records d'une seule source."""
```

---

## B2. ETL Pipeline — Transform (`etl/transform.py`)

### Objectif
Nettoyer, normaliser et enrichir les données brutes pour les préparer au chargement dans le star schema.

### Sous-tâches détaillées

#### B2.1 — Nettoyage des descriptions
- Retirer le HTML (BeautifulSoup `get_text()`)
- Normaliser les espaces (retirer les `\n\n\n`, `\t`, espaces multiples)
- Retirer les emojis inutiles
- Produire `description_raw` (original) et `description_clean` (nettoyé)

#### B2.2 — Normalisation des titres
> [!IMPORTANT]
> **Utiliser le module `nlp/title_normaliser.py` fourni par ton binôme.** C'est le module de Part A, tâche A1.3. Coordonnez-vous pour qu'il soit prêt en premier.

```python
from nlp.title_normaliser import TitleNormaliser
normaliser = TitleNormaliser()
result = normaliser.normalise("Data Scientist - Risque - Fraude (H/F)")
# → {"normalised_title": "Data Scientist", "job_family": "Data Scientist", "seniority_level": "Mid"}
```

#### B2.3 — Parsing des localisations
- Séparer `location_raw` en `city`, `region`, `country`, `country_code`
- Cas spéciaux à gérer :
  - `"Paris"` → `city=Paris, country=France, country_code=FR`
  - `"New York, New York, États-Unis"` → `city=New York, region=New York, country=États-Unis, country_code=US`
  - `"Remote"` → `city=NULL, country=NULL, country_code=NULL` (remote)
  - `"Atlanta, GA, Boston, MA, ..."` → prendre la première ville
- Enrichir avec `latitude`, `longitude` via un fichier de lookup (CSV de villes → coordonnées)
- Utiliser `geopy` pour les villes non trouvées dans le lookup

#### B2.4 — Normalisation du type de contrat
- Mapper vers les `contract_label` du seed data de `dim_contract_type` :
  - `"freelance"` → `"Freelance"`
  - `"full_time"` → `"Full-time"`
  - `"Senior Level"` (The Muse) → ignorer (c'est un seniority, pas un contrat) → `"Unknown"`
  - `None` → `"Unknown"`

#### B2.5 — Extraction de salaire par regex
- Chercher dans les descriptions des patterns comme :
  - `"60K-80K€"`, `"60 000 - 80 000 EUR"`, `"$120,000 - $150,000"`
  - `"45000€ brut annuel"`
- Regex suggérées à développer
- Extraire `salary_min`, `salary_max`, `currency`

#### B2.6 — Déduplication
- Identifier les doublons via `(source_job_id, source)` — même offre sur même plateforme
- Garder le record le plus récent (par `ingestion_ts`)

**Fichier attendu : `etl/transform.py`**
```python
class DataTransformer:
    def __init__(self, title_normaliser=None):
        """Initialiser avec le normaliseur de titres."""
    
    def transform_all(self, raw_records: list[dict]) -> list[dict]:
        """Appliquer toutes les transformations. Retourner les records transformés."""
    
    def clean_description(self, text: str) -> str: ...
    def parse_location(self, raw_location: str) -> dict: ...
    def normalise_contract(self, employment_type: str) -> str: ...
    def extract_salary(self, description: str) -> dict: ...
    def deduplicate(self, records: list[dict]) -> list[dict]: ...
```

---

## B3. ETL Pipeline — Load (`etl/load.py`)

### Objectif
Charger les données transformées dans le star schema PostgreSQL, en respectant l'ordre des dépendances.

### Ordre de chargement (CRITIQUE)

```
1. dim_company       (pas de dépendance)
2. dim_location      (pas de dépendance)
3. dim_job_title     (pas de dépendance)
4. dim_contract_type (déjà seed, juste lookup)
5. dim_source        (déjà seed, juste lookup)
6. dim_date          (déjà seed, juste lookup)
7. fact_job_offer    (dépend de toutes les dims ci-dessus)
8. bridge_offer_skill (dépend de fact_job_offer + dim_skill)
```

### Stratégie d'UPSERT pour les dimensions

Pour chaque dimension, utiliser `INSERT ... ON CONFLICT DO UPDATE` (SCD Type 1) :

```sql
-- Exemple dim_company
INSERT INTO dim_company (company_name)
VALUES (%s)
ON CONFLICT (company_name) DO NOTHING
RETURNING company_id;
```

**Attention** : `dim_company` n'a pas de contrainte `UNIQUE` sur `company_name` dans le DDL actuel. Il faudra en ajouter une, ou utiliser un `SELECT` préalable pour vérifier l'existence.

### Chargement du fait

```sql
INSERT INTO fact_job_offer (dim_company_id, dim_location_id, dim_title_id, dim_source_id, dim_date_id, dim_contract_id, salary_min, salary_max, currency, description_raw, description_clean, url, source_job_id)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (source_job_id, dim_source_id) DO UPDATE SET
    description_raw = EXCLUDED.description_raw,
    description_clean = EXCLUDED.description_clean,
    salary_min = COALESCE(EXCLUDED.salary_min, fact_job_offer.salary_min),
    salary_max = COALESCE(EXCLUDED.salary_max, fact_job_offer.salary_max);
```

### Chargement du bridge (skills brutes)

- Pour les sources qui fournissent des skills (Remotive, The Muse, Indeed) :
  1. Lookup `skill_id` dans `dim_skill` (ou insérer si nouvelle)
  2. Insert dans `bridge_offer_skill` avec `confidence_score = 1.00`

**Fichier attendu : `etl/load.py`**
```python
class WarehouseLoader:
    def __init__(self, db_url):
        """Connexion au warehouse-db."""
    
    def load_all(self, transformed_records: list[dict]) -> dict:
        """Charger tout. Retourner {companies: N, locations: N, offers: N, ...}"""
    
    def upsert_company(self, name: str) -> int: ...
    def upsert_location(self, loc: dict) -> int: ...
    def upsert_job_title(self, title_data: dict) -> int: ...
    def insert_fact(self, record: dict, dim_ids: dict) -> int: ...
    def insert_skills(self, offer_id: int, skills: list[str]) -> int: ...
```

---

## B4. Airflow DAG ETL (`ingestion/orchestration/etl_pipeline_dag.py`)

### Objectif
Orchestrer le pipeline ETL complet via Airflow, exécuté après l'ingestion.

```python
# Nouveau DAG : etl_pipeline_dag.py
# Tasks: extract_bronze → transform → load_warehouse → data_quality_check
```

### Flow du DAG

```
extract_bronze → transform_data → load_dimensions → load_facts → load_bridge_skills → quality_checks
```

### Data Quality Checks (fin du DAG)
- `COUNT(*)` sur `fact_job_offer` > 0
- Pas de `dim_company_id` orphelins
- `salary_min <= salary_max` quand les deux sont non-NULL
- Au moins 80% des offres ont un `job_family` != 'Other Data'

---

## B5. Power BI Dashboard (`dashboard/`)

### Objectif
Créer un dashboard Power BI de 6 pages connecté au warehouse PostgreSQL.

### Connexion
- **Méthode** : Power BI Desktop → Get Data → PostgreSQL
- **Serveur** : `localhost:5433`
- **Base** : `jobs_dw`
- **User/Pass** : `warehouse/warehouse`
- **Mode** : Import (pas DirectQuery — plus rapide pour un petit volume)

### Modèle de données dans Power BI
- Importer toutes les tables du star schema
- Vérifier que Power BI détecte les relations (sinon les créer manuellement)
- Le modèle doit ressembler à l'étoile du `modelisation.md`

### Pages détaillées

#### Page 1 — 📊 Market Overview
| Visual | Source | Mesure |
|--------|--------|--------|
| KPI Card : Total Offres | `fact_job_offer` | `COUNT(offer_id)` |
| KPI Card : Offres cette semaine | `fact_job_offer` + `dim_date` | `COUNT WHERE week = current` |
| KPI Card : Salaire moyen | `fact_job_offer` | `AVG(salary_min)` (where not null) |
| KPI Card : Top Ville | `dim_location` | `TOPN(1, ...)` |
| Line Chart : Tendance temporelle | `dim_date.full_date` × `COUNT(offer_id)` | Trend par mois |
| Bar Chart : Distribution par job_family | `dim_job_title.job_family` × `COUNT` | Horizontal bar |
| Slicers : Période, Source | `dim_date`, `dim_source` | Filters |

#### Page 2 — 🛠️ Skills Analysis
| Visual | Source | Mesure |
|--------|--------|--------|
| Horizontal Bar : Top 20 Skills | `dim_skill` via bridge | `COUNT(DISTINCT offer_id)` |
| Treemap : Skills par catégorie | `dim_skill.skill_category` | `COUNT` |
| Matrix : Skills × Job Family | `dim_skill` + `dim_job_title` | Heatmap |
| Slicer : Job Family | `dim_job_title.job_family` | Filter |

#### Page 3 — 🗺️ Geographic View
| Visual | Source | Mesure |
|--------|--------|--------|
| Map : Offres par ville | `dim_location.latitude/longitude` | Bubble size = `COUNT` |
| Filled Map : Offres par pays | `dim_location.country_code` | Color = `COUNT` |
| Bar Chart : Top 10 villes | `dim_location.city` | `COUNT(offer_id)` |
| Slicer : Country, Job Family | `dim_location`, `dim_job_title` | Filters |

#### Page 4 — 💰 Salary Intelligence
| Visual | Source | Mesure |
|--------|--------|--------|
| Column Chart : Salaire par job_family | `dim_job_title.job_family` | `AVG(salary_min)`, `AVG(salary_max)` |
| Column Chart : Salaire par seniority | `dim_job_title.seniority_level` | `AVG(salary_min)` |
| Column Chart : Salaire par région | `dim_location.country` | `AVG(salary_min)` |
| Card : Salaire médian global | `fact_job_offer` | `MEDIAN(salary_min)` |
| Note textuelle | — | "⚠️ Données salariales disponibles pour X% des offres" |

> [!WARNING]
> Les données salariales sont très rares (0% dans le bronze actuel). La page 4 sera probablement vide ou quasi-vide tant que l'extraction de salaire par regex (tâche B2.5) n'améliore pas la couverture. Prévoir un message d'avertissement dans le dashboard.

#### Page 5 — 📡 Source Comparison
| Visual | Source | Mesure |
|--------|--------|--------|
| Stacked Bar : Volume par source | `dim_source.platform_name` | `COUNT(offer_id)` |
| Table : Stats par source | `dim_source` | Volume, % du total, unique companies, avg skills/offer |
| Donut Chart : Répartition | `dim_source` | `COUNT(offer_id)` / total |
| Bar Chart : Skills coverage par source | `dim_source` via bridge | `% offers with ≥1 skill` |

#### Page 6 — 🎯 Job Recommender (Power BI)
| Visual | Source | Mesure |
|--------|--------|--------|
| Slicer multi-select : Skills | `dim_skill` | Filter |
| Slicer : Job Family | `dim_job_title.job_family` | Filter |
| Slicer : Location | `dim_location.city` | Filter |
| Table : Offres filtrées | `fact_job_offer` + toutes dims | `title, company, location, skills, url` |

### Thème & Polish
- Palette sombre (dark mode) cohérente
- Police : Segoe UI ou DIN
- Couleurs : palette de bleus/cyans pour les data, orange pour les accents
- Tooltips personnalisés sur tous les visuels
- Navigation par onglets en haut

---

# 📅 Timeline & Points de Synchronisation

## Calendrier proposé

```
Semaine 1 (Jours 1-4):
┌──────────────────────────────┬──────────────────────────────┐
│        TOI (Part A)          │      TON AMI (Part B)        │
├──────────────────────────────┼──────────────────────────────┤
│ A1.1 Structure nlp/          │ B1 Extract (lire bronze)     │
│ A1.3 Title Normaliser ⚡     │ B2.1 Clean descriptions      │
│      (prioritaire — livrer   │ B2.3 Parse locations         │
│       à ton ami)             │ B2.4 Normalise contracts     │
└──────────────────────────────┴──────────────────────────────┘
       
  🔄 SYNC Point 1 (fin J4):
     - Toi → Livrer title_normaliser.py à ton ami
     - Ami → Valider que l'extract fonctionne sur les 5 sources

Semaine 2 (Jours 5-8):
┌──────────────────────────────┬──────────────────────────────┐
│        TOI (Part A)          │      TON AMI (Part B)        │
├──────────────────────────────┼──────────────────────────────┤
│ A1.2 Skills Extractor        │ B2.2 Utiliser title_normalis.│
│ A2 Embeddings Pipeline       │ B2.5 Salary regex extraction │
│                              │ B2.6 Déduplication           │
│                              │ B3 Load (all dimensions +    │
│                              │     fact + bridge)            │
└──────────────────────────────┴──────────────────────────────┘

  🔄 SYNC Point 2 (fin J8):
     - Ami → Le warehouse est rempli (fact_job_offer a des données)
     - Toi → Skills extractor + embeddings fonctionnent
     - Ensemble → Lancer le skills extraction NLP sur les offres en base

Semaine 3 (Jours 9-12):
┌──────────────────────────────┬──────────────────────────────┐
│        TOI (Part A)          │      TON AMI (Part B)        │
├──────────────────────────────┼──────────────────────────────┤
│ A3 Recommender               │ B4 Airflow DAG ETL           │
│ A4 FastAPI Backend           │ B5 Power BI (Pages 1-3)      │
│    (endpoints jobs, skills,  │                              │
│     recommend, stats)        │                              │
└──────────────────────────────┴──────────────────────────────┘

  🔄 SYNC Point 3 (fin J12):
     - Toi → API tourne, /recommend retourne des résultats
     - Ami → Power BI Pages 1-3 fonctionnelles avec données réelles

Semaine 4 (Jours 13-16):
┌──────────────────────────────┬──────────────────────────────┐
│        TOI (Part A)          │      TON AMI (Part B)        │
├──────────────────────────────┼──────────────────────────────┤
│ A5 Frontend Website          │ B5 Power BI (Pages 4-6)      │
│    (pages + design)          │ B5 Thème, polish, tooltips   │
│ Docker (api + frontend)      │ DAG tests & documentation    │
└──────────────────────────────┴──────────────────────────────┘

  🔄 SYNC Point Final (fin J16):
     - Intégration complète
     - Tests end-to-end
     - Documentation & rapport
```

---

## ⚠️ Dépendances critiques entre les parties

```mermaid
flowchart TD
    A1["A1.3 Title Normaliser<br/>(TOI)"] -->|"livrer en J4"| B2["B2.2 Transform Titles<br/>(AMI)"]
    B3["B3 Load to Warehouse<br/>(AMI)"] -->|"données en base J8"| A2["A2 Embeddings<br/>(TOI)"]
    B3 -->|"données en base J8"| A1b["A1.2 Skills Extraction<br/>(TOI - sur données réelles)"]
    B3 -->|"données en base J8"| A4["A4 FastAPI<br/>(TOI)"]
    A1b -->|"bridge_offer_skill rempli"| B5["B5 Power BI Page 2<br/>(AMI - Skills Analysis)"]

    style A1 fill:#4CAF50,color:#fff
    style A2 fill:#4CAF50,color:#fff
    style A1b fill:#4CAF50,color:#fff
    style A4 fill:#4CAF50,color:#fff
    style B2 fill:#2196F3,color:#fff
    style B3 fill:#2196F3,color:#fff
    style B5 fill:#2196F3,color:#fff
```

> [!CAUTION]
> **Blocage potentiel** : Si le Title Normaliser (A1.3) est en retard, ton ami ne pourra pas remplir correctement `dim_job_title`. C'est **ta première priorité absolue** — livre-le avant tout le reste.

---

## 📁 Structure finale du projet (après complétion)

```
DataWarehouseProj/
├── README.md
├── docker-compose.yml
├── .env / .env.example
├── .gitignore
│
├── ingestion/                    # ✅ FAIT
│   ├── collectors/               # 6 collectors
│   └── orchestration/
│       ├── job_ingestion_dag.py  # ✅ FAIT
│       └── etl_pipeline_dag.py   # 👤 AMI (B4)
│
├── etl/                          # 👤 AMI (B1-B3)
│   ├── __init__.py
│   ├── extract.py
│   ├── transform.py
│   └── load.py
│
├── nlp/                          # 🧑 TOI (A1-A3)
│   ├── __init__.py
│   ├── skills_extractor.py
│   ├── title_normaliser.py
│   ├── embeddings.py
│   ├── recommender.py
│   └── config.py
│
├── api/                          # 🧑 TOI (A4)
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── routers/
│   │   ├── jobs.py
│   │   ├── recommend.py
│   │   ├── skills.py
│   │   └── stats.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                     # 🧑 TOI (A5)
│   ├── index.html
│   ├── css/
│   ├── js/
│   └── Dockerfile
│
├── dashboard/                    # 👤 AMI (B5)
│   ├── JobIntelligent.pbix
│   ├── screenshots/
│   └── theme.json
│
├── db/                           # ✅ FAIT
│   └── init.sql
│
├── docs/                         # ✅ FAIT (partiel)
│   ├── modelisation.md
│   ├── architecture.md
│   ├── schemas/
│   └── api-contracts/
│
├── notebooks/                    # ✅ FAIT
│   └── 01_data_exploration.ipynb
│
└── data_lake/                    # ✅ FAIT
    └── bronze/
        ├── france_travail/
        ├── linkedin/
        ├── remotive/
        ├── the_muse/
        └── indeed/
```

---

## ✅ Checklist de vérification finale

### Ensemble (les deux)
- [ ] `docker-compose up` démarre tous les services sans erreur
- [ ] Le warehouse contient des données (`SELECT COUNT(*) FROM fact_job_offer` > 3000)
- [ ] `bridge_offer_skill` contient des skills (sources brutes + NLP)
- [ ] L'API répond sur `http://localhost:8000/api/jobs`
- [ ] Le frontend s'affiche sur `http://localhost:3000`
- [ ] Power BI se connecte et affiche les 6 pages
- [ ] Documentation à jour (README, architecture, modelisation)

### Toi uniquement
- [ ] Le title normaliser fonctionne sur les 5 sources
- [ ] Le skills extractor détecte ≥ 5 skills par offre en moyenne
- [ ] Les embeddings sont générés pour toutes les offres
- [ ] `/recommend` retourne des résultats pertinents (test avec 5 profils)
- [ ] Le frontend a un design soigné (dark mode, animations, responsive)

### Ton ami uniquement
- [ ] L'ETL charge les 5 sources sans erreur
- [ ] Les dimensions sont correctement peuplées (pas de doublons)
- [ ] Le DAG Airflow ETL s'exécute end-to-end
- [ ] Power BI : les 6 pages affichent des données réelles
- [ ] Les data quality checks passent (pas d'orphelins, pas de NULL sur les FKs)
