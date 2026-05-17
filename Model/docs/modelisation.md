# 📐 Modélisation du Data Warehouse — Projet Job Intelligent

## Table des Matières

1. [Choix de l'approche de modélisation](#1-choix-de-lapproche-de-modélisation)
2. [Analyse des données sources](#2-analyse-des-données-sources)
3. [Granularité (Grain)](#3-granularité-grain)
4. [Schéma en étoile — Vue d'ensemble](#4-schéma-en-étoile--vue-densemble)
5. [Tables de dimensions — Détails et justifications](#5-tables-de-dimensions--détails-et-justifications)
6. [Table de faits — Détails et justifications](#6-table-de-faits--détails-et-justifications)
7. [Table pont (Bridge) — Relation many-to-many](#7-table-pont-bridge--relation-many-to-many)
8. [Conventions de nommage](#8-conventions-de-nommage)
9. [Slowly Changing Dimensions (SCD)](#9-slowly-changing-dimensions-scd)
10. [Indexation et Performance](#10-indexation-et-performance)
11. [Mapping : Données Sources → Modèle](#11-mapping--données-sources--modèle)
12. [Mapping : Modèle → Visualisations Power BI](#12-mapping--modèle--visualisations-power-bi)


## 1. Choix de l'approche de modélisation

### Pourquoi un Schéma en Étoile (Star Schema) ?

Nous avons trois approches possibles pour structurer un data warehouse :

| Approche                  | Description                                                      | Avantages                                         | Inconvénients                                           |
| ------------------------- | ---------------------------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------- |
| **3NF (Inmon)**           | Tables normalisées en 3ème forme normale                         | Pas de redondance, intégrité forte                | Requêtes complexes (beaucoup de JOINs), lent pour la BI |
| **Star Schema (Kimball)** | Une table de faits centrale entourée de dimensions dénormalisées | Requêtes simples, performant pour la BI, intuitif | Redondance contrôlée dans les dimensions                |
| **Snowflake**             | Star schema avec dimensions normalisées (sous-tables)            | Moins de redondance que star                      | Plus de JOINs, plus complexe, gain souvent marginal     |

### ✅ Notre choix : **Star Schema (méthode Kimball)**

**Justification :**

1. **Power BI est optimisé pour le Star Schema.** Le moteur VertiPaq de Power BI compresse et indexe les données par colonne. Un star schema minimise le nombre de JOINs et maximise les performances des DAX queries.

2. **Requêtes analytiques simples.** Chaque question business se traduit en : `SELECT ... FROM fact JOIN dim ON ... WHERE ... GROUP BY ...`. Pas de sous-requêtes imbriquées.

3. **Compréhensible par les utilisateurs.** Le modèle est intuitif : un fait (offre d'emploi) est décrit par ses dimensions (qui ? où ? quand ? quoi ?).

4. **Volume adapté.** Avec ~4 000 offres actuelles et un objectif de ~50 000, le star schema sur PostgreSQL est largement suffisant. Pas besoin de snowflake ou de dénormalisation plus poussée.

---

## 2. Analyse des données sources

Avant de modéliser, nous avons analysé les données réellement collectées dans notre bronze layer. Voici le profil de chaque source :

| Source             | Records  | Titres uniques | Entreprises | Localisations | Salaire | Compétences | Date publication |
| ------------------ | -------- | -------------- | ----------- | ------------- | ------- | ----------- | ---------------- |
| **France Travail** | 996      | 69             | 79          | 12 villes FR  | ❌ 0%   | ❌ 0%       | ❌ 0%            |
| **Indeed**         | 5 (mock) | 1              | 5           | 1             | ❌ 0%   | ✅ 100%     | ❌ 0%            |
| **LinkedIn**       | 2 500    | 1 480          | 1 574       | 299           | ❌ 0%   | ❌ 0%       | ❌ 0%            |
| **Remotive**       | 20       | 20             | 16          | 7             | ❌ 0%   | ✅ 100%     | ✅ 100%          |
| **The Muse**       | 476      | 468            | 113         | 157           | ❌ 0%   | ✅ 35%      | ✅ 100%          |

### Observations clés qui influencent la modélisation :

1. **Le salaire est rarement disponible** → Les colonnes `salary_min` et `salary_max` doivent être `NULLABLE`. On ajoutera une extraction de salaire par regex dans l'ETL.

2. **Les compétences sont inégales** → Seulement 3 sources sur 5 fournissent des skills. L'ETL devra extraire les compétences depuis les descriptions via NLP. D'où la nécessité d'une **table pont** `bridge_offer_skill`.

3. **Les localisations sont hétérogènes** → "New York, New York, États-Unis" vs "Paris" vs "USA, Canada" vs "Atlanta, GA, Boston, MA, ...". Il faut une dimension Location **normalisée** avec `city`, `region`, `country` séparés.

4. **Les titres ne sont pas standardisés** → "Data Scientist - Risque - Fraude" vs "Data Science" vs "Senior Data Engineer". Il faut une dimension Job Title avec un champ `normalised_title` et `job_family`.

5. **Le type d'emploi varie** → Certaines sources donnent des niveaux ("Senior Level", "Entry Level"), d'autres des types de contrat ("freelance", "full_time"), et d'autres rien. Il faut normaliser dans une dimension contrat.

---

## 3. Granularité (Grain)

> **Le grain est la décision la plus importante en modélisation dimensionnelle.** Il définit ce que représente _une seule ligne_ de la table de faits.

### ✅ Notre grain : **Une offre d'emploi unique, provenant d'une source spécifique, à une date d'ingestion donnée.**

**Pourquoi ce grain ?**

- **Une offre par source** : La même offre peut apparaître sur Indeed et LinkedIn. Nous gardons les deux car elles peuvent avoir des descriptions différentes, et cela permet l'analyse comparative des sources (Page 5 du dashboard).
- **Par date d'ingestion** : On ne déduplique pas dans le temps. Si une offre est scrappée le 3 avril et le 5 avril, on garde les deux entrées. Cela permet de suivre l'évolution temporelle (offre toujours active ?).

**Ce grain détermine :**

- La clé primaire de `fact_job_offer` = `offer_id` (clé de substitution, surrogate key)
- Le nombre de lignes attendues ≈ nombre total de records dans le bronze layer

---

## 4. Schéma en étoile — Vue d'ensemble

```
                              ┌──────────────────┐
                              │   dim_company    │
                              │──────────────────│
                              │ company_id (PK)  │
                              │ company_name     │
                              │ industry         │
                              │ company_size     │
                              └────────┬─────────┘
                                       │
┌──────────────────┐          ┌────────┴─────────┐          ┌──────────────────┐
│   dim_source     │          │                  │          │   dim_location   │
│──────────────────│          │                  │          │──────────────────│
│ source_id (PK)   │──────────┤                  ├──────────│ location_id (PK) │
│ platform_name    │          │                  │          │ city             │
│ platform_url     │          │                  │          │ region           │
└──────────────────┘          │  fact_job_offer  │          │ country          │
                              │                  │          │ country_code     │
┌──────────────────┐          │  offer_id (PK)   │          └──────────────────┘
│   dim_date       │          │  dim_company_id  │
│──────────────────│          │  dim_location_id │          ┌──────────────────┐
│ date_id (PK)     │──────────┤  dim_title_id    ├──────────│  dim_job_title   │
│ full_date        │          │  dim_source_id   │          │──────────────────│
│ day              │          │  dim_date_id     │          │ title_id (PK)    │
│ month            │          │  dim_contract_id │          │ raw_title        │
│ year             │          │                  │          │ normalised_title │
│ quarter          │          │  salary_min      │          │ job_family       │
│ day_of_week      │          │  salary_max      │          │ seniority_level  │
│ week_number      │          │  currency        │          └──────────────────┘
│ is_weekend       │          │  description     │
└──────────────────┘          │  url             │          ┌──────────────────┐
                              │  ingestion_ts    │          │dim_contract_type │
                              │                  │          │──────────────────│
                              └────────┬─────────┘          │ contract_id (PK) │
                                       │                    │ contract_label   │
                                       │                    │ contract_category│
                              ┌────────┴─────────┐          └──────────────────┘
                              │bridge_offer_skill│
                              │──────────────────│
                              │ offer_id (FK)    │
                              │ skill_id (FK)    │          ┌──────────────────┐
                              │ confidence_score │──────────│   dim_skill      │
                              └──────────────────┘          │──────────────────│
                                                            │ skill_id (PK)    │
                                                            │ skill_name       │
                                                            │ skill_category   │
                                                            └──────────────────┘
```

### Pourquoi 6 dimensions + 1 bridge ?

| Dimension            | Répond à la question              | Justification                                                                                    |
| -------------------- | --------------------------------- | ------------------------------------------------------------------------------------------------ |
| `dim_company`        | **Qui** recrute ?                 | Permet le filtrage/regroupement par employeur, industrie                                         |
| `dim_location`       | **Où** se trouve le poste ?       | Essentiel pour la carte géographique (Page 3 Power BI)                                           |
| `dim_job_title`      | **Quel** poste ?                  | Permet la normalisation des titres et l'analyse par famille de métiers                           |
| `dim_source`         | D'où vient l'offre ?              | Comparaison entre plateformes (Page 5 Power BI)                                                  |
| `dim_date`           | **Quand** l'offre a été publiée ? | Analyse temporelle des tendances (Page 1 Power BI)                                               |
| `dim_contract_type`  | Quel type de contrat ?            | CDI, CDD, freelance, stage — filtrage essentiel                                                  |
| `dim_skill` + bridge | Quelles compétences ?             | Relation many-to-many : une offre nécessite N compétences, une compétence apparaît dans M offres |

---

## 5. Tables de dimensions — Détails et justifications

### 5.1 `dim_company`

```sql
CREATE TABLE dim_company (
    company_id    SERIAL PRIMARY KEY,
    company_name  VARCHAR(300) NOT NULL,
    industry      VARCHAR(150),           -- NULL : non fourni par les sources
    company_size  VARCHAR(50)             -- NULL : non fourni par les sources
);
```

**Décisions :**

- `company_id` est un **surrogate key** (clé de substitution auto-incrémentée), pas le nom. Pourquoi ? Parce que le même nom d'entreprise peut être écrit différemment ("JPMorgan Chase" vs "JP Morgan" vs "JPMORGAN CHASE & CO"). Le surrogate key permet de gérer les variantes.
- `industry` et `company_size` sont `NULL` pour l'instant car aucune source ne les fournit. On les garde pour un futur enrichissement (via API Crunchbase ou LinkedIn Company).
- `VARCHAR(300)` car nous avons vu des noms comme "INFORMATIS TECHNOLOGY SYSTM" — les noms peuvent être longs.

---

### 5.2 `dim_location`

```sql
CREATE TABLE dim_location (
    location_id   SERIAL PRIMARY KEY,
    raw_location  TEXT NOT NULL,           -- Valeur brute originale
    city          VARCHAR(150),
    region        VARCHAR(150),
    country       VARCHAR(100),
    country_code  CHAR(2),                 -- ISO 3166-1 alpha-2
    latitude      DECIMAL(9,6),
    longitude     DECIMAL(9,6)
);
```

**Décisions :**

- On conserve `raw_location` en plus des champs normalisés. Pourquoi ? Parce que nos données montrent une grande hétérogénéité :
  - `"Paris"` (France Travail — simple)
  - `"New York, New York, États-Unis"` (LinkedIn — verbeux)
  - `"USA, Canada, USA timezones"` (Remotive — multi-pays)
  - `"Atlanta, GA, Boston, MA, Chicago, IL, ..."` (The Muse — multi-villes)

  Garder le brut permet de debugger et re-parser si besoin.

- `latitude` / `longitude` pour la **visualisation cartographique** de Power BI (Page 3). Les coordonnées seront renseignées via un lookup table (ville → coordonnées) dans l'ETL.
- `country_code` CHAR(2) (ex: "FR", "US", "DE") pour les filtres et regroupements géographiques.
- **Décision sur les multi-localisations** : Quand une offre a plusieurs villes (ex: "Atlanta, GA, Boston, MA"), on crée **une seule entrée** dans `dim_location` avec la première ville, et on stocke le reste dans `raw_location`. Pourquoi ? Cela simplifie le modèle. Pour un projet académique, c'est suffisant.

---

### 5.3 `dim_job_title`

```sql
CREATE TABLE dim_job_title (
    title_id         SERIAL PRIMARY KEY,
    raw_title        TEXT NOT NULL,           -- Titre original exacte
    normalised_title VARCHAR(200) NOT NULL,   -- Titre nettoyé
    job_family       VARCHAR(100) NOT NULL,   -- Catégorie métier
    seniority_level  VARCHAR(50)              -- Junior, Mid, Senior, Lead
);
```

**Décisions :**

- C'est la dimension la plus **critique** pour répondre à la problématique du projet. Les titres bruts sont chaotiques :
  - `"Data Scientist - Risque - Fraude - Conformité Bancaire (H/F)"`
  - `"Data Science"` (sans le mot "Scientist")
  - `"Alternance - Data Analyst (F/H) (H/F)"`
  - `"Ingénieur-e données (H/F)"`
- `normalised_title` = version nettoyée (sans "(H/F)", sans ville, sans bruit).
- `job_family` = catégorie standardisée parmi un ensemble fini :
  - `Data Engineer`
  - `Data Scientist`
  - `Data Analyst`
  - `Business Analyst`
  - `ML Engineer`
  - `BI Developer / Analytics Engineer`
  - `Other Data`
  - `Non-Data` (offres qui ne correspondent pas au domaine data)

  Ce champ est **essentiel** pour la Page 1 ("distribution par famille de métiers") et la Page 2 ("skills par famille").

- `seniority_level` = extrait du titre ("Senior", "Junior", "Lead", "Alternance/Intern", "Mid"). Permet l'analyse par niveau d'expérience sur la Page 4 (Salary Intelligence).

---

### 5.4 `dim_source`

```sql
CREATE TABLE dim_source (
    source_id     SERIAL PRIMARY KEY,
    platform_name VARCHAR(100) NOT NULL UNIQUE,
    platform_url  VARCHAR(300)
);
```

**Décisions :**

- Table simple et petite (6 lignes seulement : indeed, linkedin, france_travail, remotive, the_muse, glassdoor).
- `UNIQUE` sur `platform_name` car il n'y aura jamais de doublons.
- Cette dimension est essentielle pour la **Page 5 du dashboard** (Source Comparison).

**Données pré-remplies (seed data) :**

| source_id | platform_name  | platform_url                      |
| --------- | -------------- | --------------------------------- |
| 1         | indeed         | https://www.indeed.com            |
| 2         | linkedin       | https://www.linkedin.com          |
| 3         | france_travail | https://candidat.francetravail.fr |
| 4         | remotive       | https://remotive.com              |
| 5         | the_muse       | https://www.themuse.com           |
| 6         | glassdoor      | https://www.glassdoor.com         |

---

### 5.5 `dim_date`

```sql
CREATE TABLE dim_date (
    date_id      INTEGER PRIMARY KEY,      -- Format YYYYMMDD (ex: 20260412)
    full_date    DATE NOT NULL UNIQUE,
    day          SMALLINT NOT NULL,         -- 1-31
    month        SMALLINT NOT NULL,         -- 1-12
    month_name   VARCHAR(20) NOT NULL,      -- "January", "Février"
    year         SMALLINT NOT NULL,
    quarter      SMALLINT NOT NULL,         -- 1-4
    week_number  SMALLINT NOT NULL,         -- 1-53
    day_of_week  VARCHAR(15) NOT NULL,      -- "Monday", "Lundi"
    is_weekend   BOOLEAN NOT NULL
);
```

**Décisions :**

- `date_id` est au format `YYYYMMDD` (entier), PAS un auto-increment. Pourquoi ?
  - C'est une **convention standard** en data warehousing (Ralph Kimball). Le format `20260412` est lisible par un humain et permet des comparaisons rapides (`WHERE date_id BETWEEN 20260101 AND 20260331`).
  - Power BI peut l'utiliser directement comme clé de relation sans conversion.
- Champs pré-calculés (`month_name`, `day_of_week`, `is_weekend`, `week_number`) : ils évitent de recalculer ces valeurs dans chaque requête Power BI. Cela suit le principe de **pré-agrégation** du data warehousing.
- On pré-remplit cette table avec **toutes les dates de 2024 à 2027** (~1 460 lignes). Cette table est générée une seule fois et ne change jamais.

- Pas de champ `hour` ou `minute` car notre grain est journalier — l'heure de publication n'a pas de valeur analytique.

---

### 5.6 `dim_contract_type`

```sql
CREATE TABLE dim_contract_type (
    contract_id       SERIAL PRIMARY KEY,
    contract_label    VARCHAR(100) NOT NULL UNIQUE,
    contract_category VARCHAR(50) NOT NULL
);
```

**Décisions :**

- Nos données sources montrent une grande disparité :
  - France Travail : `None` partout (pas fourni par le scraper)
  - Remotive : `"freelance"`, `"full_time"`, `"contract"`, `"part_time"`
  - The Muse : `"Senior Level"`, `"Entry Level"`, `"Mid Level"`, `"Internship"` (c'est un **niveau**, pas un type de contrat)
- On introduit deux niveaux : `contract_label` (valeur brute) et `contract_category` (regroupement standardisé : "Permanent", "Temporary", "Freelance", "Internship", "Unknown"). L'ETL fera la correspondance.

**Données pré-remplies :**

| contract_label          | contract_category |
| ----------------------- | ----------------- |
| CDI / Full-time         | Permanent         |
| CDD / Contract          | Temporary         |
| Freelance               | Freelance         |
| Internship / Alternance | Internship        |
| Part-time               | Part-time         |
| Unknown                 | Unknown           |

---

### 5.7 `dim_skill`

```sql
CREATE TABLE dim_skill (
    skill_id       SERIAL PRIMARY KEY,
    skill_name     VARCHAR(100) NOT NULL UNIQUE,
    skill_category VARCHAR(50) NOT NULL
);
```

**Décisions :**

- Les compétences sont au cœur du **système de recommandation** (objectif O2 du projet).
- `skill_category` permet de regrouper les compétences pour la **Page 2 du dashboard** (Treemap par catégorie). Catégories prévues :

| Catégorie          | Exemples                                  |
| ------------------ | ----------------------------------------- |
| Programming        | Python, R, Java, Scala, SQL               |
| Databases          | PostgreSQL, MongoDB, Redis, Elasticsearch |
| Cloud              | AWS, Azure, GCP, Databricks               |
| Big Data           | Spark, Kafka, Hadoop, Airflow             |
| ML/AI              | TensorFlow, PyTorch, scikit-learn, NLP    |
| BI & Visualization | Power BI, Tableau, Looker, Qlik           |
| DevOps             | Docker, Kubernetes, Git, CI/CD            |
| Soft Skills        | Communication, Leadership, Agile          |

- La table sera pré-remplie avec ~150 compétences connues, et l'ETL pourra ajouter de nouvelles compétences découvertes dans les descriptions.

---

## 6. Table de faits — Détails et justifications

```sql
CREATE TABLE fact_job_offer (
    offer_id          SERIAL PRIMARY KEY,

    -- Foreign Keys (les dimensions)
    dim_company_id    INTEGER NOT NULL REFERENCES dim_company(company_id),
    dim_location_id   INTEGER NOT NULL REFERENCES dim_location(location_id),
    dim_title_id      INTEGER NOT NULL REFERENCES dim_job_title(title_id),
    dim_source_id     INTEGER NOT NULL REFERENCES dim_source(source_id),
    dim_date_id       INTEGER NOT NULL REFERENCES dim_date(date_id),
    dim_contract_id   INTEGER NOT NULL REFERENCES dim_contract_type(contract_id),

    -- Mesures (Measures)
    salary_min        DECIMAL(12,2),        -- Nullable : souvent absent
    salary_max        DECIMAL(12,2),        -- Nullable : souvent absent
    currency          CHAR(3) DEFAULT 'EUR',

    -- Champs descriptifs (Degenerate Dimensions)
    description_raw   TEXT,                  -- Description originale
    description_clean TEXT,                  -- Description nettoyée (sans HTML)
    url               TEXT,                  -- Lien vers l'offre
    source_job_id     VARCHAR(200),          -- ID original sur la plateforme

    -- Métadonnées
    ingestion_ts      TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Contrainte d'unicité pour éviter les doublons
    UNIQUE (source_job_id, dim_source_id)
);
```

**Décisions :**

### Pourquoi `offer_id` est un Surrogate Key ?

- Le `job_id` source n'est pas fiable : Indeed utilise des IDs extraits du HTML, LinkedIn génère des UUIDs aléatoires, Remotive utilise des entiers. Un surrogate key auto-incrémenté est stable et prévisible.
- On conserve `source_job_id` pour la traçabilité vers la source originale.

### Pourquoi `salary_min` et `salary_max` sont NULLABLE ?

- Nos données montrent que **0%** des offres actuelles ont un salaire renseigné. L'ETL essaiera d'extraire les salaires depuis les descriptions via regex (ex: "60K-80K€"), mais beaucoup resteront NULL.
- On ne met pas `DEFAULT 0` car un salaire à 0 est sémantiquement incorrect — il vaut mieux avoir NULL que des faux zéros.

### Pourquoi garder `description_raw` ET `description_clean` ?

- `description_raw` = texte original (peut contenir du HTML comme dans Remotive et The Muse)
- `description_clean` = texte nettoyé utilisé pour le NLP (extraction de compétences, embeddings)
- Garder les deux permet de re-traiter les descriptions si on améliore l'algorithme de nettoyage.

### Pourquoi la contrainte `UNIQUE (source_job_id, dim_source_id)` ?

- Une même offre sur la même plateforme ne doit apparaître qu'une seule fois dans le warehouse.
- Mais la même offre sur Indeed ET LinkedIn = 2 lignes distinctes (des sources différentes), ce qui est le comportement voulu.

### Pourquoi pas de colonne `embedding` dans cette table ?

- Les embeddings vectoriels (384 dimensions) sont volumineux et ne sont pas nécessaires pour Power BI. Si on implémente les recommandations, on les stockera dans une table séparée (`job_embeddings`) ou via l'extension `pgvector`. Cela garde la table de faits légère et rapide.

---

## 7. Table pont (Bridge) — Relation many-to-many

```sql
CREATE TABLE bridge_offer_skill (
    offer_id         INTEGER NOT NULL REFERENCES fact_job_offer(offer_id),
    skill_id         INTEGER NOT NULL REFERENCES dim_skill(skill_id),
    confidence_score DECIMAL(3,2) DEFAULT 1.00,   -- 0.00 à 1.00

    PRIMARY KEY (offer_id, skill_id)
);
```

**Pourquoi une table bridge ?**

La relation entre offres et compétences est **many-to-many** :

- Une offre nécessite **plusieurs** compétences (Python + SQL + Spark)
- Une compétence est demandée par **plusieurs** offres

On ne peut pas stocker un `skill_id` dans `fact_job_offer` (quel skill choisir ?) ni un `offer_id` dans `dim_skill`. La table bridge résout ce problème.

**Pourquoi `confidence_score` ?**

- Les compétences seront extraites par NLP (regex + spaCy). Certaines détections sont plus fiables que d'autres.
- `confidence_score = 1.00` → compétence explicitement mentionnée ("Maîtrise de Python requise")
- `confidence_score = 0.70` → compétence suggérée par le contexte ("expérience en data engineering" → Python probable)
- Power BI peut filtrer sur `confidence_score >= 0.80` pour n'afficher que les compétences certaines.

---

## 8. Conventions de nommage

| Convention          | Règle                          | Exemple                                                                                     | Pourquoi                                                                                   |
| ------------------- | ------------------------------ | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| **Tables**          | snake_case, préfixe sémantique | `dim_company`, `fact_job_offer`, `bridge_offer_skill`                                       | Le préfixe (`dim_`, `fact_`, `bridge_`) permet d'identifier immédiatement le type de table |
| **Clés primaires**  | `{entity}_id`                  | `company_id`, `offer_id`                                                                    | Cohérent et lisible                                                                        |
| **Clés étrangères** | `dim_{entity}_id`              | `dim_company_id`, `dim_date_id`                                                             | Distingue clairement la FK de la PK dans la dimension                                      |
| **Colonnes**        | snake_case                     | `salary_min`, `raw_title`                                                                   | Standard PostgreSQL                                                                        |
| **Types**           | Spécifique au besoin           | `SERIAL` (PK), `VARCHAR(N)` (texte borné), `TEXT` (texte long), `DECIMAL(12,2)` (monétaire) | Pas de `TEXT` partout — on contraint la taille quand c'est possible                        |

---

## 9. Slowly Changing Dimensions (SCD)

Les SCD (Slowly Changing Dimensions) définissent comment gérer les mises à jour des dimensions dans le temps.

| Dimension           | Type SCD               | Comportement                                      | Justification                                            |
| ------------------- | ---------------------- | ------------------------------------------------- | -------------------------------------------------------- |
| `dim_company`       | **Type 1** (Overwrite) | Si le nom d'entreprise change, on écrase l'ancien | On n'a pas besoin de l'historique des noms d'entreprises |
| `dim_location`      | **Type 1**             | La localisation d'une ville ne change pas         | Coordonnées GPS sont stables                             |
| `dim_job_title`     | **Type 1**             | On normalise, on ne garde pas l'historique        | Le `raw_title` est dans la table de faits si besoin      |
| `dim_source`        | **Type 0** (Fixed)     | Jamais de modification                            | Les plateformes ne changent pas de nom                   |
| `dim_date`          | **Type 0** (Fixed)     | Pré-remplie, jamais modifiée                      | Les dates sont immuables                                 |
| `dim_contract_type` | **Type 1**             | On peut ajouter de nouveaux types                 | Rare, mais possible                                      |
| `dim_skill`         | **Type 1**             | On peut renommer/recatégoriser                    | La taxonomie évolue                                      |

**Pourquoi Type 1 et pas Type 2 ?**

Le Type 2 (SCD-2) crée de nouvelles lignes à chaque changement et conserve l'historique. C'est utile pour les dimensions qui changent fréquemment et dont l'historique a une valeur analytique (ex: prix, adresse client).

Pour notre cas, les dimensions sont soit **stables** (dates, sources), soit sans valeur historique (le nom d'une entreprise qui change d'orthographe n'a pas de valeur analytique). Le Type 1 est plus simple et suffisant.

---

## 10. Indexation et Performance

```sql
-- Index sur les clés étrangères (accélère les JOINs)
CREATE INDEX idx_fact_company    ON fact_job_offer(dim_company_id);
CREATE INDEX idx_fact_location   ON fact_job_offer(dim_location_id);
CREATE INDEX idx_fact_title      ON fact_job_offer(dim_title_id);
CREATE INDEX idx_fact_source     ON fact_job_offer(dim_source_id);
CREATE INDEX idx_fact_date       ON fact_job_offer(dim_date_id);
CREATE INDEX idx_fact_contract   ON fact_job_offer(dim_contract_id);

-- Index sur le bridge (accélère les requêtes skills)
CREATE INDEX idx_bridge_skill    ON bridge_offer_skill(skill_id);

-- Index pour la déduplication
CREATE INDEX idx_fact_source_job ON fact_job_offer(source_job_id, dim_source_id);

-- Index pour les recherches texte
CREATE INDEX idx_location_city   ON dim_location(city);
CREATE INDEX idx_location_country ON dim_location(country_code);
CREATE INDEX idx_skill_name      ON dim_skill(skill_name);
CREATE INDEX idx_title_family    ON dim_job_title(job_family);
```

**Pourquoi ces index ?**

- Power BI exécute des requêtes avec `WHERE` + `GROUP BY` sur les dimensions. Les index sur les FK accélèrent les JOINs.
- L'index sur `bridge_offer_skill(skill_id)` est crucial car la Page 2 du dashboard fera : "Pour chaque skill, compter les offres" (`GROUP BY skill_id`).
- L'index composite sur `(source_job_id, dim_source_id)` sert à la contrainte d'unicité et au `UPSERT` dans l'ETL.

---

## 11. Mapping : Données Sources → Modèle

Ce tableau montre comment chaque champ des données brutes (bronze) est transformé et chargé dans le star schema :

| Champ source (JSONL) | Transformation ETL                          | Table cible          | Colonne cible                    |
| -------------------- | ------------------------------------------- | -------------------- | -------------------------------- |
| `title_raw`          | Nettoyage (retrait H/F, parenthèses)        | `dim_job_title`      | `raw_title`                      |
| `title_raw`          | Regex + fuzzy matching → famille métier     | `dim_job_title`      | `normalised_title`, `job_family` |
| `title_raw`          | Extraction seniority ("Senior", "Junior")   | `dim_job_title`      | `seniority_level`                |
| `company_name`       | Trim, normalisation casse                   | `dim_company`        | `company_name`                   |
| `location_raw`       | Parsing ville/région/pays                   | `dim_location`       | `city`, `region`, `country`      |
| `location_raw`       | Lookup table → coordonnées                  | `dim_location`       | `latitude`, `longitude`          |
| `source`             | Mapping vers table existante                | `dim_source`         | lookup `source_id`               |
| `ingestion_ts`       | Parse → date → format YYYYMMDD              | `dim_date`           | lookup `date_id`                 |
| `employment_type`    | Normalisation vers catégories standards     | `dim_contract_type`  | `contract_label`                 |
| `salary_min`         | Direct (ou regex extraction de description) | `fact_job_offer`     | `salary_min`                     |
| `salary_max`         | Direct (ou regex extraction de description) | `fact_job_offer`     | `salary_max`                     |
| `description`        | Direct (brut)                               | `fact_job_offer`     | `description_raw`                |
| `description`        | Strip HTML, normalize whitespace            | `fact_job_offer`     | `description_clean`              |
| `skills[]`           | Lookup ou insert dans dim_skill             | `bridge_offer_skill` | `offer_id` + `skill_id`          |
| `description`        | NLP extraction → skills supplémentaires     | `bridge_offer_skill` | `offer_id` + `skill_id`          |
| `job_id`             | Direct                                      | `fact_job_offer`     | `source_job_id`                  |

---

## 12. Mapping : Modèle → Visualisations Power BI

Chaque page du dashboard Power BI utilise des dimensions et mesures spécifiques :

| Page Dashboard              | Dimensions utilisées                                                   | Mesures / Calculs                                             |
| --------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------- |
| **P1: Market Overview**     | `dim_date` (trend), `dim_job_title` (job_family)                       | `COUNT(offer_id)`, `AVG(salary_min)`, tendance temporelle     |
| **P2: Skills Analysis**     | `dim_skill` (skill_name, skill_category), `dim_job_title` (job_family) | `COUNT(bridge_offer_skill.offer_id)` par skill                |
| **P3: Geographic View**     | `dim_location` (city, country, lat/lng)                                | `COUNT(offer_id)` par ville, carte avec `lat/lng`             |
| **P4: Salary Intelligence** | `dim_job_title` (job_family, seniority), `dim_location` (region)       | `AVG(salary_min)`, `AVG(salary_max)`, `MEDIAN`                |
| **P5: Source Comparison**   | `dim_source` (platform_name)                                           | `COUNT(offer_id)` par source, `COUNT(DISTINCT source_job_id)` |
| **P6: Job Recommender**     | `dim_skill` (slicer), `dim_job_title`, `dim_location`                  | Filtre croisé, table d'offres filtrées                        |

---

## Résumé des tables

| Table                | Type      | Lignes estimées | Rôle               |
| -------------------- | --------- | --------------- | ------------------ |
| `dim_company`        | Dimension | ~1 800          | Qui recrute        |
| `dim_location`       | Dimension | ~500            | Où                 |
| `dim_job_title`      | Dimension | ~2 000          | Quel poste         |
| `dim_source`         | Dimension | 6               | D'où vient l'offre |
| `dim_date`           | Dimension | ~1 460          | Quand              |
| `dim_contract_type`  | Dimension | ~6-10           | Type de contrat    |
| `dim_skill`          | Dimension | ~150            | Compétences        |
| **`fact_job_offer`** | **Fait**  | **~4 000+**     | **Offre d'emploi** |
| `bridge_offer_skill` | Bridge    | ~10 000+        | Offre ↔ Compétence |
