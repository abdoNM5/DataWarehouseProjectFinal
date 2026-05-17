-- ============================================================
-- MOCK DATA for NLP development (while ETL is not ready)
-- Run AFTER init.sql has created the schema
-- ============================================================

-- ── Companies ───────────────────────────────────────────────
INSERT INTO dim_company (company_name, industry) VALUES
('Capgemini', 'IT Consulting'),
('BNP Paribas', 'Banking'),
('Société Générale', 'Banking'),
('Thales', 'Defense & Aerospace'),
('Orange', 'Telecommunications'),
('Airbus', 'Aerospace'),
('Doctolib', 'Health Tech'),
('Datadog', 'Cloud Monitoring'),
('OVHcloud', 'Cloud Provider'),
('Criteo', 'AdTech'),
('Dassault Systèmes', 'Software'),
('Atos', 'IT Services'),
('Ubisoft', 'Gaming'),
('Blablacar', 'Transportation'),
('Veepee', 'E-commerce'),
('Renault', 'Automotive'),
('TotalEnergies', 'Energy'),
('Schneider Electric', 'Energy Management'),
('L''Oréal', 'Consumer Goods'),
('Sanofi', 'Pharmaceuticals')
ON CONFLICT DO NOTHING;

-- ── Locations ───────────────────────────────────────────────
INSERT INTO dim_location (raw_location, city, region, country, country_code, latitude, longitude) VALUES
('Paris, France', 'Paris', 'Île-de-France', 'France', 'FR', 48.8566, 2.3522),
('Lyon, France', 'Lyon', 'Auvergne-Rhône-Alpes', 'France', 'FR', 45.7640, 4.8357),
('Toulouse, France', 'Toulouse', 'Occitanie', 'France', 'FR', 43.6047, 1.4442),
('London, UK', 'London', 'England', 'United Kingdom', 'GB', 51.5074, -0.1278),
('Berlin, Germany', 'Berlin', 'Berlin', 'Germany', 'DE', 52.5200, 13.4050),
('New York, USA', 'New York', 'New York', 'United States', 'US', 40.7128, -74.0060),
('San Francisco, USA', 'San Francisco', 'California', 'United States', 'US', 37.7749, -122.4194),
('Remote', 'Remote', NULL, NULL, NULL, NULL, NULL),
('Nantes, France', 'Nantes', 'Pays de la Loire', 'France', 'FR', 47.2184, -1.5536),
('Bordeaux, France', 'Bordeaux', 'Nouvelle-Aquitaine', 'France', 'FR', 44.8378, -0.5792)
ON CONFLICT DO NOTHING;

-- ── Job Titles ──────────────────────────────────────────────
INSERT INTO dim_job_title (raw_title, normalised_title, job_family, seniority_level) VALUES
('Data Engineer (H/F)', 'Data Engineer', 'Data Engineer', 'Mid'),
('Senior Data Engineer', 'Senior Data Engineer', 'Data Engineer', 'Senior'),
('Junior Data Engineer - Python/SQL', 'Junior Data Engineer', 'Data Engineer', 'Junior'),
('Data Scientist (H/F)', 'Data Scientist', 'Data Scientist', 'Mid'),
('Senior Data Scientist - NLP', 'Senior Data Scientist NLP', 'Data Scientist', 'Senior'),
('Data Analyst (F/H)', 'Data Analyst', 'Data Analyst', 'Mid'),
('Business Analyst - Finance', 'Business Analyst Finance', 'Business Analyst', 'Mid'),
('Machine Learning Engineer', 'ML Engineer', 'ML Engineer', 'Mid'),
('Senior ML Engineer - Computer Vision', 'Senior ML Engineer CV', 'ML Engineer', 'Senior'),
('Alternance - Data Analyst (H/F)', 'Data Analyst Alternance', 'Data Analyst', 'Junior'),
('Lead Data Engineer', 'Lead Data Engineer', 'Data Engineer', 'Lead'),
('Analytics Engineer - dbt', 'Analytics Engineer', 'BI Developer / Analytics Engineer', 'Mid'),
('BI Developer Power BI (H/F)', 'BI Developer', 'BI Developer / Analytics Engineer', 'Mid'),
('Ingénieur Données Cloud (H/F)', 'Cloud Data Engineer', 'Data Engineer', 'Mid'),
('DevOps / MLOps Engineer', 'MLOps Engineer', 'ML Engineer', 'Mid')
ON CONFLICT DO NOTHING;

-- ── Fact: Job Offers with realistic descriptions ────────────
-- We reference IDs by position (company_id=1..20, location_id=1..10, title_id=1..15)

INSERT INTO fact_job_offer (dim_company_id, dim_location_id, dim_title_id, dim_source_id, dim_date_id, dim_contract_id, salary_min, salary_max, currency, description_raw, description_clean, source_job_id) VALUES

-- Offer 1: Data Engineer at Capgemini
(1, 1, 1, 2, 20260401, 1, 45000, 55000, 'EUR',
'<p>Data Engineer position</p>',
'We are looking for a Data Engineer to join our team in Paris. You will design, build, and maintain data pipelines using Python, SQL, and Apache Spark. Experience with Airflow for orchestration and PostgreSQL or MongoDB for data storage is required. Knowledge of Docker and Kubernetes for containerization is a plus. You will work in an Agile/Scrum environment with CI/CD pipelines on AWS.',
'LI-001'),

-- Offer 2: Senior Data Engineer at BNP Paribas
(2, 1, 2, 2, 20260402, 2, 60000, 75000, 'EUR',
'Senior Data Engineer role',
'BNP Paribas recherche un Senior Data Engineer pour renforcer son équipe Data. Vous serez responsable de la conception et du développement de pipelines de données à grande échelle avec Spark et Kafka. Compétences requises : Python, Scala, SQL, PostgreSQL, et expérience avec des plateformes cloud (AWS ou GCP). Maîtrise de Docker, Git, et des méthodologies Agile. Connaissance de Hadoop et Hive appréciée.',
'LI-002'),

-- Offer 3: Data Scientist at Société Générale
(3, 1, 4, 2, 20260403, 1, 50000, 65000, 'EUR',
'Data Scientist position',
'Société Générale is hiring a Data Scientist for its risk analytics team. You will develop machine learning models using Python, scikit-learn, and TensorFlow. Strong skills in SQL, Pandas, and NumPy are essential. Experience with NLP techniques, Deep Learning frameworks like PyTorch, and cloud platforms (Azure) is valued. You will use Git for version control and work with Jupyter notebooks for prototyping.',
'LI-003'),

-- Offer 4: ML Engineer at Datadog
(8, 7, 8, 2, 20260404, 1, 90000, 120000, 'USD',
'ML Engineer at Datadog',
'Join Datadog as a Machine Learning Engineer. Build and deploy ML models at scale using Python, PyTorch, and Kubernetes. You will work with large datasets, implement NLP and Computer Vision solutions, and optimize model inference with TensorFlow Serving. Requirements: Python, Docker, AWS, CI/CD (GitHub Actions), scikit-learn, and experience with MLflow for experiment tracking. Strong communication skills are essential.',
'LI-004'),

-- Offer 5: Data Analyst at Orange
(5, 2, 6, 3, 20260405, 1, 35000, 42000, 'EUR',
'Data Analyst chez Orange',
'Orange recrute un Data Analyst à Lyon. Vous analyserez les données clients avec SQL et Python. Compétences en Power BI et Tableau pour la création de dashboards interactifs. Maîtrise de Excel et des outils statistiques. Connaissance de PostgreSQL et des méthodes Agile. Vous travaillerez en équipe avec une forte composante Communication et Teamwork.',
'FT-001'),

-- Offer 6: Junior Data Engineer at Doctolib
(7, 1, 3, 1, 20260406, 8, 32000, 38000, 'EUR',
'Alternance Data Engineer Doctolib',
'Doctolib recherche un Junior Data Engineer en alternance. Vous apprendrez à construire des pipelines ETL avec Python et SQL. Technologies utilisées : PostgreSQL, Redis, Docker, Git. Introduction à Spark et Airflow. Environnement Linux. Méthodologies Scrum avec des sprints de deux semaines.',
'IN-001'),

-- Offer 7: Senior Data Scientist NLP at Criteo
(10, 1, 5, 2, 20260407, 1, 65000, 85000, 'EUR',
'Senior DS NLP Criteo',
'Criteo is looking for a Senior Data Scientist specializing in NLP. You will build recommendation systems using Deep Learning, Hugging Face transformers, and spaCy for text processing. Tech stack: Python, PyTorch, TensorFlow, scikit-learn, Pandas. Infrastructure: Docker, Kubernetes, AWS (S3, Lambda). Experience with LLM and GenAI is a strong plus. RAG architectures knowledge appreciated.',
'LI-005'),

-- Offer 8: Analytics Engineer at OVHcloud
(9, 9, 12, 2, 20260408, 1, 45000, 55000, 'EUR',
'Analytics Engineer OVH',
'OVHcloud recherche un Analytics Engineer pour son équipe Data. Vous utiliserez dbt pour transformer les données dans Snowflake. Compétences requises : SQL avancé, Python, Git. Expérience avec Airflow ou Prefect pour l orchestration. Visualisation avec Metabase ou Looker. Environnement cloud (GCP ou AWS). Bonnes capacités de Communication et de Problem Solving.',
'LI-006'),

-- Offer 9: BI Developer at Renault
(16, 3, 13, 3, 20260409, 1, 38000, 48000, 'EUR',
'BI Developer Renault Toulouse',
'Renault recrute un BI Developer à Toulouse. Vous développerez des rapports et dashboards avec Power BI. Compétences en SQL, Excel, et Python pour l automatisation. Connaissance de PostgreSQL et Oracle. Expérience en modélisation dimensionnelle (star schema). Méthodologie Agile et Project Management.',
'FT-002'),

-- Offer 10: Cloud Data Engineer at TotalEnergies
(17, 1, 14, 2, 20260410, 2, 55000, 70000, 'EUR',
'Cloud Data Engineer Total',
'TotalEnergies is hiring a Cloud Data Engineer in Paris. Build scalable data pipelines on GCP using BigQuery, Dataflow (Apache Beam), and Cloud Storage. Required skills: Python, SQL, Spark, Docker, Terraform. Experience with Kafka for real-time streaming and Airflow for batch orchestration. Knowledge of Parquet and Avro data formats. CI/CD with GitHub Actions on Linux servers.',
'LI-007'),

-- Offer 11: Data Analyst Alternance at L'Oreal
(19, 1, 10, 1, 20260411, 8, 28000, 32000, 'EUR',
'Alternance Data Analyst L''Oréal',
'L''Oréal propose une alternance en Data Analyse. Vous créerez des dashboards avec Tableau et Power BI pour suivre les KPIs marketing. Utilisation de SQL pour extraire les données depuis MySQL. Analyse avec Python, Pandas, et Matplotlib. Capacités de Teamwork et Communication essentielles. Environnement Agile.',
'IN-002'),

-- Offer 12: MLOps Engineer at Thales
(4, 3, 15, 2, 20260412, 1, 50000, 65000, 'EUR',
'MLOps Engineer Thales',
'Thales recrute un ingénieur MLOps à Toulouse. Vous automatiserez le déploiement de modèles ML avec Docker, Kubernetes, et CI/CD. Compétences requises : Python, Terraform, Jenkins, Git, Linux. Expérience avec MLflow pour le tracking d expériences et scikit-learn pour le prototypage. Connaissance d AWS ou Azure appréciée.',
'LI-008'),

-- Offer 13: Lead Data Engineer at Airbus
(6, 3, 11, 2, 20260413, 2, 70000, 90000, 'EUR',
'Lead Data Engineer Airbus',
'Airbus is hiring a Lead Data Engineer in Toulouse. You will architect data platforms using Spark, Kafka, and Hadoop on AWS. Lead a team of 5 engineers. Requirements: 7+ years experience with Python, Scala, SQL, PostgreSQL, Redis. Strong knowledge of Docker, Kubernetes, Terraform, and CI/CD pipelines. Leadership and Project Management skills are essential. Agile methodology.',
'LI-009'),

-- Offer 14: Data Scientist at Sanofi
(20, 2, 4, 2, 20260414, 1, 48000, 60000, 'EUR',
'Data Scientist Sanofi Lyon',
'Sanofi recrute un Data Scientist à Lyon pour l équipe R&D. Vous développerez des modèles prédictifs avec Python, scikit-learn, XGBoost, et LightGBM. Analyse exploratoire avec Pandas, NumPy, Seaborn, et Plotly. Accès aux données via SQL (PostgreSQL). Utilisation de Jupyter et Git. Connaissances en Machine Learning et statistiques avancées requises.',
'LI-010'),

-- Offer 15: Business Analyst at Schneider Electric
(18, 4, 7, 2, 20260415, 1, 55000, 70000, 'GBP',
'Business Analyst Schneider London',
'Schneider Electric is looking for a Business Analyst in London. You will analyze business data using SQL, Excel, and Power BI to support strategic decisions. Experience with Python for data manipulation (Pandas) and Tableau for advanced visualizations. Strong Communication, Problem Solving, and Project Management skills. Agile/Scrum methodology experience required.',
'LI-011'),

-- Offer 16: Data Engineer Remote at Blablacar
(14, 8, 1, 4, 20260416, 1, 50000, 65000, 'EUR',
'Data Engineer Remote Blablacar',
'Blablacar is hiring a Data Engineer (full remote). Design and maintain ETL pipelines with Python, Spark, and Airflow. Data storage on PostgreSQL and MongoDB with Redis caching. Deploy with Docker on AWS (S3, Lambda). Data formats: JSON, Parquet, CSV. Version control with Git. REST API integration. Linux environment. Agile team with Scrum ceremonies.',
'RE-001'),

-- Offer 17: Senior ML Engineer CV at Dassault
(11, 1, 9, 2, 20260417, 1, 60000, 80000, 'EUR',
'Senior ML Engineer CV Dassault',
'Dassault Systèmes recherche un Senior ML Engineer spécialisé en Computer Vision. Développement de modèles avec PyTorch et OpenCV. Entraînement sur GPU avec TensorFlow et Keras. Infrastructure : Docker, Kubernetes, AWS. Expérience avec Deep Learning, scikit-learn, et NumPy. Utilisation de MLflow et GitHub Actions pour le CI/CD. Anglais courant requis.',
'LI-012'),

-- Offer 18: Data Engineer at Atos Berlin
(12, 5, 1, 2, 20260418, 1, 55000, 70000, 'EUR',
'Data Engineer Atos Berlin',
'Atos is looking for a Data Engineer in Berlin. You will build real-time data streaming pipelines using Kafka, Flink, and Spark. Store and query data with Elasticsearch and PostgreSQL. Infrastructure on Azure with Terraform. Requirements: Python, Java, SQL, Docker, Git, Linux. Experience with Presto or Hive for data querying. CI/CD and Agile practices.',
'LI-013'),

-- Offer 19: Data Analyst at Veepee
(15, 1, 6, 1, 20260419, 1, 38000, 45000, 'EUR',
'Data Analyst Veepee Paris',
'Veepee recrute un Data Analyst à Paris. Missions : analyse des ventes et du comportement client avec SQL et Python. Création de dashboards avec Grafana et Plotly. Données stockées dans PostgreSQL et BigQuery. Utilisation de Pandas et NumPy pour l analyse. Bonne maîtrise d Excel. Compétences en Communication et Teamwork.',
'IN-003'),

-- Offer 20: Data Engineer at Ubisoft
(13, 1, 1, 2, 20260420, 1, 48000, 58000, 'EUR',
'Data Engineer Ubisoft Paris',
'Ubisoft Paris is hiring a Data Engineer to support game analytics. Build data pipelines with Python, Spark, and Airflow. Store player data in MongoDB and PostgreSQL. Real-time events with Kafka. Cloud infrastructure on GCP (BigQuery, Cloud Storage). Tools: Docker, Git, GraphQL APIs, REST APIs. Work in a creative Agile environment with strong Teamwork culture.',
'LI-014')

ON CONFLICT (source_job_id, dim_source_id) DO NOTHING;
