"""
Skills Taxonomy — mirrors dim_skill table from db/init.sql exactly.
Provides skill categories, aliases, and lookup structures.
"""

# ── Skills grouped by category (must match dim_skill.skill_name exactly) ──

SKILLS_BY_CATEGORY = {
    "Programming": [
        "Python", "R", "Java", "Scala", "SQL", "JavaScript",
        "C++", "Go", "Rust", "Shell", "Bash", "SAS", "MATLAB", "Julia",
    ],
    "Databases": [
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
        "Oracle", "SQL Server", "Cassandra", "DynamoDB", "Neo4j", "SQLite",
    ],
    "Cloud": [
        "AWS", "Azure", "GCP", "Databricks", "Snowflake",
        "BigQuery", "Redshift", "S3", "Lambda",
    ],
    "Big Data": [
        "Spark", "Kafka", "Hadoop", "Airflow", "Flink", "Hive",
        "Presto", "dbt", "NiFi", "Beam", "Prefect", "Luigi",
    ],
    "ML/AI": [
        "TensorFlow", "PyTorch", "scikit-learn", "Keras", "XGBoost",
        "LightGBM", "NLP", "Computer Vision", "Deep Learning",
        "Machine Learning", "MLflow", "Hugging Face", "OpenCV",
        "spaCy", "LLM", "GenAI", "RAG",
    ],
    "BI & Visualization": [
        "Power BI", "Tableau", "Looker", "Qlik", "Metabase",
        "Grafana", "D3.js", "Matplotlib", "Plotly", "Seaborn",
    ],
    "DevOps": [
        "Docker", "Kubernetes", "Git", "CI/CD", "Terraform",
        "Ansible", "Jenkins", "GitHub Actions", "Linux",
    ],
    "Data Tools": [
        "Pandas", "NumPy", "PySpark", "Excel", "JSON", "Parquet",
        "Avro", "CSV", "API", "REST", "GraphQL", "ETL",
    ],
    "Soft Skills": [
        "Agile", "Scrum", "Communication", "Leadership",
        "Problem Solving", "Teamwork", "Project Management",
    ],
}

# ── Aliases: common alternative spellings → canonical dim_skill name ──

SKILL_ALIASES = {
    # Programming
    "python3": "Python", "py": "Python",
    "r language": "R", "r-lang": "R",
    "js": "JavaScript", "node.js": "JavaScript", "nodejs": "JavaScript",
    "c/c++": "C++", "cpp": "C++",
    "golang": "Go",
    "shell scripting": "Shell",
    "bash scripting": "Bash",
    # Databases
    "postgres": "PostgreSQL", "pg": "PostgreSQL", "psql": "PostgreSQL",
    "mongo": "MongoDB",
    "elastic": "Elasticsearch",
    "mssql": "SQL Server", "ms sql": "SQL Server",
    # Cloud
    "amazon web services": "AWS", "amazon aws": "AWS",
    "google cloud": "GCP", "google cloud platform": "GCP",
    "microsoft azure": "Azure", "azure cloud": "Azure",
    "aws s3": "S3", "aws lambda": "Lambda",
    # Big Data
    "apache spark": "Spark", "pyspark": "Spark",
    "apache kafka": "Kafka",
    "apache airflow": "Airflow",
    "apache flink": "Flink",
    "apache hadoop": "Hadoop",
    "apache hive": "Hive",
    "apache beam": "Beam",
    "apache nifi": "NiFi",
    # ML/AI
    "tf": "TensorFlow", "tensorflow2": "TensorFlow",
    "sklearn": "scikit-learn", "sk-learn": "scikit-learn",
    "sci-kit learn": "scikit-learn",
    "xgb": "XGBoost",
    "lgbm": "LightGBM", "light gbm": "LightGBM",
    "natural language processing": "NLP",
    "cv": "Computer Vision",
    "dl": "Deep Learning",
    "ml": "Machine Learning",
    "mlops": "MLflow",
    "huggingface": "Hugging Face", "hf": "Hugging Face",
    "large language model": "LLM", "large language models": "LLM",
    "generative ai": "GenAI", "gen ai": "GenAI",
    "retrieval augmented generation": "RAG",
    # BI
    "powerbi": "Power BI", "power-bi": "Power BI",
    "d3": "D3.js",
    "mpl": "Matplotlib",
    # DevOps
    "k8s": "Kubernetes", "kube": "Kubernetes",
    "github": "Git", "gitlab": "Git",
    "ci cd": "CI/CD", "cicd": "CI/CD",
    "github-actions": "GitHub Actions",
    # Data Tools
    "pd": "Pandas",
    "np": "NumPy", "numpy": "NumPy",
    "restful": "REST", "rest api": "REST", "restful api": "REST",
}

# ── Flat lookup sets (built once at import time) ──

ALL_SKILLS = set()
for _cat, _skills in SKILLS_BY_CATEGORY.items():
    for _s in _skills:
        ALL_SKILLS.add(_s)

ALL_SKILL_NAMES_LOWER = {s.lower() for s in ALL_SKILLS}
