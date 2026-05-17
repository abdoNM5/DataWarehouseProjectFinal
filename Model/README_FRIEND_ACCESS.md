# Data Warehouse Access Guide for Friend

This guide will help you connect to the shared job market data warehouse hosted on Neon PostgreSQL.

---

## Quick Connection Info

```
Host: ep-solitary-cherry-a4st8g9y-pooler.us-east-1.aws.neon.tech
Port: 5432
Database: neondb
User: neondb_owner
Password: npg_6VqjWpLH8kxw
SSL Mode: require
```

**Full Connection String (psql):**
```bash
psql 'postgresql://neondb_owner:npg_6VqjWpLH8kxw@ep-solitary-cherry-a4st8g9y-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'
```

---

## Prerequisites

Choose your preferred tool below:

### Option 1: Command Line (psql)
- Install PostgreSQL client: https://www.postgresql.org/download/
- Or use: `choco install postgresql` (Windows) / `brew install postgresql` (Mac) / `apt install postgresql-client` (Linux)

### Option 2: Python
- Install: `pip install psycopg2-binary` or `pip install pandas sqlalchemy psycopg2-binary`

### Option 3: Power BI Desktop
- Already have it? Great! Just create a PostgreSQL connection.

### Option 4: DBeaver (GUI)
- Download: https://dbeaver.io/
- Free, cross-platform, easiest for beginners

---

## Connection Methods

### Method 1: Command Line (psql)

```bash
psql 'postgresql://neondb_owner:npg_6VqjWpLH8kxw@ep-solitary-cherry-a4st8g9y-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'
```

Once connected, try:
```sql
SELECT COUNT(*) as total_job_offers FROM fact_job_offer;
SELECT COUNT(*) as total_companies FROM dim_company;
SELECT * FROM dim_source;
```

---

### Method 2: Python

**Simple Query:**
```python
import psycopg2

conn = psycopg2.connect(
    host="ep-solitary-cherry-a4st8g9y-pooler.us-east-1.aws.neon.tech",
    port=5432,
    database="neondb",
    user="neondb_owner",
    password="npg_6VqjWpLH8kxw",
    sslmode="require"
)

cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM fact_job_offer;")
print(cursor.fetchone())
cursor.close()
conn.close()
```

**Using Pandas (easier):**
```python
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine(
    'postgresql://neondb_owner:npg_6VqjWpLH8kxw@ep-solitary-cherry-a4st8g9y-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require'
)

# Load all job offers
df = pd.read_sql("SELECT * FROM fact_job_offer;", engine)
print(df.head())
print(f"Total offers: {len(df)}")
```

---

### Method 3: Power BI Desktop

1. Open **Power BI Desktop**
2. Click **Get Data** → **PostgreSQL Database**
3. Enter:
   - **Server:** `ep-solitary-cherry-a4st8g9y-pooler.us-east-1.aws.neon.tech`
   - **Database:** `neondb`
4. Click **OK** → Select **Database**
5. Enter username: `neondb_owner`, password: `npg_6VqjWpLH8kxw`
6. Check **Encrypt connection** → Click **Connect**
7. Select tables you want (usually all of them)
8. Click **Load**

---

### Method 4: DBeaver (Easiest GUI)

1. Download & install: https://dbeaver.io/
2. Click **File** → **New Database Connection** → **PostgreSQL** → **Next**
3. Fill in:
   - **Server Host:** `ep-solitary-cherry-a4st8g9y-pooler.us-east-1.aws.neon.tech`
   - **Port:** `5432`
   - **Database:** `neondb`
   - **Username:** `neondb_owner`
   - **Password:** `npg_6VqjWpLH8kxw`
4. Click **Show all databases** checkbox
5. Click **Test Connection** (should say "Connected")
6. Click **Finish**
7. Expand the connection → Tables to browse data visually

---

## Database Schema

The warehouse contains a **Star Schema** with:

### Fact Table
- **fact_job_offer** (36,254+ records)
  - Columns: offer_id, company_id, location_id, title_id, source_id, date_id, contract_type_id, salary_min, salary_max, url, raw_description

### Dimension Tables
- **dim_company** — Company names & details
- **dim_location** — Cities & countries
- **dim_job_title** — Job titles, family, seniority level
- **dim_source** — Source platform (LinkedIn, Indeed, France Travail, Remotive, TheMuse)
- **dim_date** — Date dimensions (year, month, week)
- **dim_contract_type** — Employment types (Full-time, CDI, CDD, etc.)
- **dim_skill** — Technology skills
- **bridge_offer_skill** — Mapping of offers to skills

---

## Sample Queries

**Find all Python job offers:**
```sql
SELECT f.offer_id, c.company_name, t.job_title, l.city, l.country
FROM fact_job_offer f
JOIN dim_company c ON f.company_id = c.company_id
JOIN dim_job_title t ON f.title_id = t.title_id
JOIN dim_location l ON f.location_id = l.location_id
JOIN bridge_offer_skill bs ON f.offer_id = bs.offer_id
JOIN dim_skill s ON bs.skill_id = s.skill_id
WHERE s.skill_name = 'Python'
LIMIT 10;
```

**Average salary by job family:**
```sql
SELECT t.job_family, 
       ROUND(AVG(f.salary_min), 2) as avg_min_salary,
       ROUND(AVG(f.salary_max), 2) as avg_max_salary,
       COUNT(*) as offer_count
FROM fact_job_offer f
JOIN dim_job_title t ON f.title_id = t.title_id
WHERE f.salary_min > 0 AND f.salary_max > 0
GROUP BY t.job_family
ORDER BY avg_max_salary DESC;
```

**Jobs by country:**
```sql
SELECT l.country, COUNT(*) as offer_count
FROM fact_job_offer f
JOIN dim_location l ON f.location_id = l.location_id
GROUP BY l.country
ORDER BY offer_count DESC;
```

---

## Important Notes

⚠️ **SSL is Required** — The connection uses SSL encryption. All commands above include `sslmode=require`.

⚠️ **Channel Binding** — Some tools may need `channel_binding=require` in the connection string (psql does).

⚠️ **Read-Only Access** — You can only query (SELECT). You cannot modify data directly.

⚠️ **Credentials are Shared** — Keep these credentials private. Do not commit to public repos.

⚠️ **Network Access** — Connection requires internet. The database is hosted on Neon's cloud infrastructure.

---

## Troubleshooting

**"Connection refused"**
- Check internet connection
- Verify credentials are correct (copy-paste from above)
- Make sure you're using `sslmode=require`

**"FATAL: too many connections from same user"**
- You hit the connection limit. Wait a minute and retry.
- Close any other connections you have open.

**"SSL certificate problem"**
- Try adding `sslmode=require&channel_binding=disable` to the connection string
- Or use a tool that handles SSL better (DBeaver is usually reliable)

**"psql: command not found"**
- PostgreSQL client not installed. Install it from https://www.postgresql.org/download/

---

## Questions?

Ask the person who shared this with you! They can help with connection issues or data questions.

---

**Last Updated:** May 11, 2026
