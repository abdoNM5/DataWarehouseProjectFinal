"""
ETL Load Module
===============
Loads transformed job records into PostgreSQL data warehouse (star schema).

Processing steps:
  1. Connect to warehouse database
  2. Upsert dimensions in dependency order:
     - dim_company
     - dim_location
     - dim_job_title
     - dim_contract_type
     - dim_source (pre-seeded)
     - dim_date (pre-seeded)
  3. Load fact_job_offer with all foreign keys
  4. Load bridge_offer_skill for many-to-many skills relationships
  5. Validate referential integrity

Input:  Transformed records from transform.py
Output: Records loaded into warehouse; validation report
"""

import psycopg2
from psycopg2.extras import execute_batch, execute_values
from psycopg2.pool import SimpleConnectionPool
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WarehouseConnection:
    """Manages PostgreSQL warehouse connections with pooling."""
    
    def __init__(self, host: str = 'ep-solitary-cherry-a4st8g9y-pooler.us-east-1.aws.neon.tech', 
                 port: int = 5432, 
                 database: str = 'neondb', 
                 user: str = 'neondb_owner', 
                 password: str = 'npg_6VqjWpLH8kxw', 
                 sslmode: str = 'require',
                 pool_size: int = 3):
        """
        Initialize connection pool.
        
        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            database: Database name
            user: Username
            password: Password
            sslmode: SSL mode (required for Neon)
            pool_size: Number of connections in pool
        """
        self.connection_params = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password,
            'sslmode': sslmode,
        }
        
        try:
            self.pool = SimpleConnectionPool(1, pool_size, **self.connection_params)
            logger.info(f"Connection pool created: {host}:{port}/{database}")
        except psycopg2.Error as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Get connection from pool."""
        conn = self.pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction rolled back: {e}")
            raise
        finally:
            self.pool.putconn(conn)
    
    def close_all(self):
        """Close all connections in pool."""
        self.pool.closeall()


class WarehouseLoader:
    """Loads transformed records into warehouse."""
    
    def __init__(self, warehouse_conn: WarehouseConnection):
        """
        Initialize loader.
        
        Args:
            warehouse_conn: WarehouseConnection instance
        """
        self.warehouse_conn = warehouse_conn
        self.load_stats = {
            'companies_loaded': 0,
            'locations_loaded': 0,
            'titles_loaded': 0,
            'contracts_loaded': 0,
            'offers_loaded': 0,
            'skills_bridge_loaded': 0,
        }
    
    def load_all(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Load all records through full pipeline.
        
        Args:
            records: List of transformed records
        
        Returns:
            Dict with load statistics and validation results
        """
        logger.info(f"Starting warehouse load for {len(records)} records...")
        
        try:
            with self.warehouse_conn.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build lookup caches and load dimensions
                logger.info("Loading dimensions...")
                company_map = self._load_companies(cursor, records)
                location_map = self._load_locations(cursor, records)
                title_map = self._load_titles(cursor, records)
                contract_map = self._load_contracts(cursor, records)
                source_map = self._load_sources(cursor)  # Read pre-seeded
                date_map = self._load_dates(cursor)  # Read pre-seeded
                
                # Load facts
                logger.info("Loading fact table...")
                self._load_fact_offers(cursor, records, company_map, location_map, 
                                      title_map, contract_map, source_map, date_map)
                
                # Load bridge table
                logger.info("Loading bridge table...")
                self._load_bridge_skills(cursor, records, source_map)
                
                cursor.close()
        
        except Exception as e:
            logger.error(f"Load failed: {e}", exc_info=True)
            self.load_stats['errors'] = str(e)
            return self.load_stats
        
        # Validate
        logger.info("Validating loaded data...")
        validation = self._validate_load(records)
        self.load_stats['validation'] = validation
        
        logger.info(f"Load complete: {self.load_stats}")
        return self.load_stats
    
    def _load_companies(self, cursor, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """Load and cache company dimension."""
        companies = set()
        for record in records:
            company = record.get('company_name', '').strip()
            if company:
                companies.add(company)
        
        company_map = {}
        cursor.execute(
            """
            SELECT company_id, company_name
            FROM dim_company
            WHERE company_name IS NOT NULL
            ORDER BY company_id
            """
        )
        for company_id, company_name in cursor.fetchall():
            key = company_name.strip()
            if key and key not in company_map:
                company_map[key] = company_id

        for company in sorted(companies):
            if company in company_map:
                continue

            cursor.execute(
                """
                INSERT INTO dim_company (company_name) 
                VALUES (%s)
                RETURNING company_id;
                """,
                (company,)
            )
            company_map[company] = cursor.fetchone()[0]
        
        self.load_stats['companies_loaded'] = len(company_map)
        logger.info(f"Loaded {len(company_map)} companies")
        return company_map
    
    def _load_locations(self, cursor, records: List[Dict[str, Any]]) -> Dict[Tuple, int]:
        """Load and cache location dimension."""
        locations = set()
        for record in records:
            raw_location = record.get('location_raw', '').strip()
            if raw_location:
                city = (record.get('location_city') or '').strip()
                country = (record.get('location_country') or '').strip()
                locations.add((raw_location, city, country))
        
        location_map = {}
        cursor.execute(
            """
            SELECT location_id, raw_location, city, country
            FROM dim_location
            WHERE raw_location IS NOT NULL
            ORDER BY location_id
            """
        )
        for location_id, raw_location, city, country in cursor.fetchall():
            key = (raw_location.strip(), (city or '').strip(), (country or '').strip())
            if key not in location_map:
                location_map[key] = location_id

        for raw_location, city, country in sorted(locations):
            key = (raw_location, city, country)
            if key in location_map:
                continue

            cursor.execute(
                """
                INSERT INTO dim_location (raw_location, city, country)
                VALUES (%s, %s, %s)
                RETURNING location_id;
                """,
                (raw_location, city or None, country or None)
            )
            location_map[key] = cursor.fetchone()[0]
        
        self.load_stats['locations_loaded'] = len(location_map)
        logger.info(f"Loaded {len(location_map)} locations")
        return location_map
    
    def _load_titles(self, cursor, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """Load and cache job title dimension."""
        titles: Dict[str, Tuple[str, str, Optional[str]]] = {}
        for record in records:
            title = record.get('title_raw', '').strip()
            if title:
                normalized_title = (record.get('title_normalized') or title).strip()
                job_family = (record.get('job_family') or 'Unknown').strip() or 'Unknown'
                seniority_level = record.get('seniority_level') or None

                existing = titles.get(title)
                if not existing:
                    titles[title] = (normalized_title, job_family, seniority_level)
                else:
                    prev_norm, prev_family, prev_seniority = existing
                    merged_family = prev_family if prev_family != 'Unknown' else job_family
                    merged_seniority = prev_seniority or seniority_level
                    titles[title] = (prev_norm or normalized_title, merged_family, merged_seniority)
        
        title_map = {}
        cursor.execute(
            """
            SELECT title_id, raw_title
            FROM dim_job_title
            WHERE raw_title IS NOT NULL
            ORDER BY title_id
            """
        )
        for title_id, raw_title in cursor.fetchall():
            key = raw_title.strip()
            if key and key not in title_map:
                title_map[key] = title_id

        for title in sorted(titles.keys()):
            if title in title_map:
                continue

            normalized_title, job_family, seniority_level = titles[title]

            cursor.execute(
                """
                INSERT INTO dim_job_title (raw_title, normalised_title, job_family, seniority_level)
                VALUES (%s, %s, %s, %s)
                RETURNING title_id;
                """,
                (title, normalized_title, job_family, seniority_level)
            )
            title_map[title] = cursor.fetchone()[0]
        
        self.load_stats['titles_loaded'] = len(title_map)
        logger.info(f"Loaded {len(title_map)} job titles")
        return title_map
    
    def _load_contracts(self, cursor, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """Load and cache contract type dimension."""
        contracts = set()
        for record in records:
            contract = record.get('employment_type_normalized', 'Unknown').strip()
            if contract:
                contracts.add(contract)
        
        contract_map = {}
        for contract in sorted(contracts):
            # Try to find existing contract type
            cursor.execute(
                "SELECT contract_id FROM dim_contract_type WHERE contract_label = %s",
                (contract,)
            )
            result = cursor.fetchone()
            if result:
                contract_map[contract] = result[0]
            else:
                # Insert if doesn't exist
                cursor.execute(
                    """
                    INSERT INTO dim_contract_type (contract_label, contract_category)
                    VALUES (%s, %s)
                    RETURNING contract_id;
                    """,
                    (contract, contract)
                )
                contract_map[contract] = cursor.fetchone()[0]
        
        self.load_stats['contracts_loaded'] = len(contract_map)
        logger.info(f"Loaded {len(contract_map)} contract types")
        return contract_map
    
    def _load_sources(self, cursor) -> Dict[str, int]:
        """Load and cache source dimension (pre-seeded)."""
        source_map = {}
        cursor.execute("SELECT source_id, platform_name FROM dim_source")
        for source_id, platform_name in cursor.fetchall():
            # Map normalized source names to dim_source entries
            source_map[platform_name] = source_id
            source_map[platform_name.lower()] = source_id
            normalized = ''.join(ch for ch in platform_name.lower() if ch.isalnum())
            source_map[normalized] = source_id
        
        logger.info(f"Loaded {len(source_map)} source mappings")
        return source_map
    
    def _load_dates(self, cursor) -> Dict[int, int]:
        """Load and cache date dimension (pre-seeded)."""
        date_map = {}
        cursor.execute("SELECT date_id FROM dim_date")
        for (date_id,) in cursor.fetchall():
            date_map[date_id] = date_id
        
        logger.info(f"Loaded {len(date_map)} date mappings")
        return date_map
    
    def _get_source_id(self, source_name: str, source_map: Dict[str, int]) -> Optional[int]:
        """Get source_id from map, handling name variations."""
        if not source_name:
            return None

        # Try exact match
        if source_name in source_map:
            return source_map[source_name]
        
        # Try lowercase
        source_lower = source_name.lower()
        if source_lower in source_map:
            return source_map[source_lower]

        # Try strict alphanumeric normalization (e.g. TheMuse -> the_muse)
        normalized = ''.join(ch for ch in source_lower if ch.isalnum())
        if normalized in source_map:
            return source_map[normalized]
        
        # Try substring matching
        source_lower_parts = source_lower.replace('_', ' ').replace('-', ' ').split()
        for key, value in source_map.items():
            key_parts = str(key).lower().replace('_', ' ').replace('-', ' ').split()
            if any(part in key_parts for part in source_lower_parts):
                return value
        
        logger.warning(f"Could not map source '{source_name}' to dim_source")
        return None
    
    def _get_date_id(self, timestamp_str: Optional[str]) -> Optional[int]:
        """Convert timestamp to date_id (YYYYMMDD format)."""
        try:
            if not timestamp_str:
                return None
            
            # Parse various date formats
            if isinstance(timestamp_str, str):
                # Try ISO format first
                for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                    try:
                        dt = datetime.strptime(timestamp_str[:10], fmt[:10])
                        return int(dt.strftime('%Y%m%d'))
                    except ValueError:
                        continue
        except Exception as e:
            logger.debug(f"Could not parse date {timestamp_str}: {e}")
        
        # Default to today if parsing fails
        return int(datetime.now().strftime('%Y%m%d'))
    
    def _load_fact_offers(self, cursor, records: List[Dict[str, Any]], 
                         company_map: Dict[str, int], location_map: Dict[Tuple, int],
                         title_map: Dict[str, int], contract_map: Dict[str, int],
                         source_map: Dict[str, int], date_map: Dict[int, int]):
        """Load fact_job_offer table."""
        batch_size = 1000
        batch = []
        errors = 0
        
        for record in records:
            try:
                # Get foreign keys
                company_id = company_map.get(record.get('company_name', '').strip())
                
                location_key = (
                    record.get('location_raw', '').strip(),
                    (record.get('location_city') or '').strip(),
                    (record.get('location_country') or '').strip()
                )
                location_id = location_map.get(location_key)
                
                title_id = title_map.get(record.get('title_raw', '').strip())
                contract_id = contract_map.get(record.get('employment_type_normalized', 'Unknown'))
                source_id = self._get_source_id(record.get('source', 'Unknown'), source_map)
                date_id = self._get_date_id(record.get('scraped_at'))
                
                # Skip if critical FKs missing
                if not all([company_id, location_id, title_id, contract_id, source_id, date_id]):
                    logger.warning(f"Skipping offer: missing foreign keys")
                    continue
                
                # Build fact record
                fact_record = (
                    company_id,
                    location_id,
                    title_id,
                    source_id,
                    date_id,
                    contract_id,
                    float(record.get('salary_min_extracted')) if record.get('salary_min_extracted') else None,
                    float(record.get('salary_max_extracted')) if record.get('salary_max_extracted') else None,
                    record.get('currency', 'EUR'),
                    record.get('description_raw', ''),
                    record.get('description_clean', ''),
                    record.get('url', ''),
                    str(record.get('source_job_id', '')),
                )
                
                batch.append(fact_record)
                
                if len(batch) >= batch_size:
                    execute_values(
                        cursor,
                        """
                        INSERT INTO fact_job_offer 
                        (dim_company_id, dim_location_id, dim_title_id, dim_source_id, 
                         dim_date_id, dim_contract_id, salary_min, salary_max, currency,
                         description_raw, description_clean, url, source_job_id)
                        VALUES %s
                        ON CONFLICT DO NOTHING
                        """,
                        batch,
                        page_size=batch_size
                    )
                    batch = []
            
            except Exception as e:
                errors += 1
                logger.debug(f"Error loading fact record: {str(e)[:100]}")
        
        # Load remaining batch
        if batch:
            execute_values(
                cursor,
                """
                INSERT INTO fact_job_offer 
                (dim_company_id, dim_location_id, dim_title_id, dim_source_id, 
                 dim_date_id, dim_contract_id, salary_min, salary_max, currency,
                 description_raw, description_clean, url, source_job_id)
                VALUES %s
                ON CONFLICT DO NOTHING
                """,
                batch,
                page_size=batch_size
            )
        
        # Count loaded
        cursor.execute("SELECT COUNT(*) FROM fact_job_offer")
        self.load_stats['offers_loaded'] = cursor.fetchone()[0]
        
        if errors > 0:
            logger.warning(f"Skipped {errors} fact records due to errors")
        
        logger.info(f"Loaded {self.load_stats['offers_loaded']} offers into fact table")
    
    def _load_bridge_skills(self, cursor, records: List[Dict[str, Any]], source_map: Dict[str, int]):
        """Load bridge_offer_skill table."""
        if not any(record.get('skills_normalized') for record in records):
            self.load_stats['skills_bridge_loaded'] = 0
            logger.info("No normalized skills found in records; skipping bridge_offer_skill load")
            return

        batch = []
        
        # Get offer IDs for skill matching
        cursor.execute("""
            SELECT offer_id, source_job_id, dim_source_id 
            FROM fact_job_offer
        """)
        offers = {(row[1], row[2]): row[0] for row in cursor.fetchall()}
        
        # Get skill IDs
        cursor.execute("SELECT skill_id, skill_name FROM dim_skill")
        skills = {row[1].lower(): row[0] for row in cursor.fetchall()}
        
        skills_loaded = 0
        
        for record in records:
            # Skip fast when a record has no skills to bridge.
            offer_skills = record.get('skills_normalized', [])
            if not offer_skills:
                continue

            source_job_id = str(record.get('source_job_id', '')).strip()
            source_name = record.get('source', 'Unknown')
            source_id = self._get_source_id(source_name, source_map)
            
            if not source_id:
                continue
            
            offer_key = (source_job_id, source_id)
            offer_id = offers.get(offer_key)
            
            if not offer_id:
                continue
            
            for skill_name in offer_skills:
                skill_name_lower = skill_name.lower().strip()
                skill_id = skills.get(skill_name_lower)
                
                # If skill not in dim_skill, insert it
                if not skill_id:
                    cursor.execute(
                        """
                        INSERT INTO dim_skill (skill_name, skill_category)
                        VALUES (%s, %s)
                        ON CONFLICT (skill_name) DO UPDATE SET skill_name = EXCLUDED.skill_name
                        RETURNING skill_id;
                        """,
                        (skill_name, 'Other')
                    )
                    result = cursor.fetchone()
                    if result:
                        skill_id = result[0]
                        skills[skill_name_lower] = skill_id
                
                if skill_id:
                    batch.append((offer_id, skill_id, 1.00))
                    skills_loaded += 1
            
            if len(batch) >= 10000:
                execute_values(
                    cursor,
                    """
                    INSERT INTO bridge_offer_skill (offer_id, skill_id, confidence_score)
                    VALUES %s
                    ON CONFLICT DO NOTHING
                    """,
                    batch,
                    page_size=10000
                )
                batch = []
        
        # Load remaining batch
        if batch:
            execute_values(
                cursor,
                """
                INSERT INTO bridge_offer_skill (offer_id, skill_id, confidence_score)
                VALUES %s
                ON CONFLICT DO NOTHING
                """,
                batch,
                page_size=10000
            )
        
        self.load_stats['skills_bridge_loaded'] = skills_loaded
        logger.info(f"Loaded {skills_loaded} skill relationships into bridge table")
    
    def _validate_load(self, original_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate loaded data."""
        validation = {
            'total_records_input': len(original_records),
            'errors': [],
        }
        
        try:
            with self.warehouse_conn.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check fact table row count
                cursor.execute("SELECT COUNT(*) FROM fact_job_offer")
                offers_count = cursor.fetchone()[0]
                validation['offers_in_warehouse'] = offers_count
                
                # Check for orphaned facts
                cursor.execute("""
                    SELECT COUNT(*) FROM fact_job_offer f
                    WHERE f.dim_company_id IS NULL 
                       OR f.dim_location_id IS NULL
                       OR f.dim_title_id IS NULL
                       OR f.dim_source_id IS NULL
                       OR f.dim_date_id IS NULL
                       OR f.dim_contract_id IS NULL
                """)
                orphaned = cursor.fetchone()[0]
                if orphaned > 0:
                    validation['errors'].append(f"{orphaned} offers with NULL foreign keys")
                
                # Check salary consistency
                cursor.execute("""
                    SELECT COUNT(*) FROM fact_job_offer 
                    WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL 
                    AND salary_min > salary_max
                """)
                bad_salary = cursor.fetchone()[0]
                if bad_salary > 0:
                    validation['errors'].append(f"{bad_salary} offers with salary_min > salary_max")
                
                # Check dimension counts
                cursor.execute("SELECT COUNT(*) FROM dim_company")
                validation['companies_in_warehouse'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM dim_location")
                validation['locations_in_warehouse'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM dim_job_title")
                validation['titles_in_warehouse'] = cursor.fetchone()[0]
                
                # Check bridge table
                cursor.execute("SELECT COUNT(*) FROM bridge_offer_skill")
                validation['skill_relationships'] = cursor.fetchone()[0]
                
                cursor.close()
        
        except Exception as e:
            validation['errors'].append(f"Validation error: {str(e)}")
        
        validation['status'] = 'PASS' if not validation['errors'] else 'WARNING'
        return validation


def load_to_warehouse(records: List[Dict[str, Any]], 
                      host: str = 'ep-solitary-cherry-a4st8g9y-pooler.us-east-1.aws.neon.tech',
                      port: int = 5432,
                      database: str = 'neondb', 
                      user: str = 'neondb_owner',
                      password: str = 'npg_6VqjWpLH8kxw',
                      sslmode: str = 'require') -> Dict[str, Any]:
    """
    Convenience function to load records to warehouse (Neon PostgreSQL).
    
    Args:
        records: List of transformed records
        host: PostgreSQL host (Neon endpoint)
        port: PostgreSQL port
        database: Database name
        user: Username
        password: Password
        sslmode: SSL mode
    
    Returns:
        Load statistics and validation results
    """
    conn = WarehouseConnection(host, port, database, user, password, sslmode)
    try:
        loader = WarehouseLoader(conn)
        return loader.load_all(records)
    finally:
        conn.close_all()


if __name__ == '__main__':
    # Example usage
    import sys
    sys.path.insert(0, '/home/jovyan/project')
    
    from etl.extract import extract_and_validate
    from etl.transform import transform_records
    
    print(f"\n{'='*60}")
    print("ETL Load Module - Test Run")
    print(f"{'='*60}\n")
    
    try:
        bronze_path = '/home/jovyan/data_lake/bronze' if sys.argv[1:] and sys.argv[1] else 'bronze'
        if len(sys.argv) > 1:
            bronze_path = sys.argv[1]
        
        # Extract → Transform
        print("Step 1: Extract from bronze...")
        records, extract_val = extract_and_validate(bronze_path)
        print(f"✓ Extracted: {extract_val['total_records']} records")
        
        print("\nStep 2: Transform records...")
        transformed, transform_stats = transform_records(records, deduplicate=True)
        print(f"✓ Transformed: {transform_stats['total_transformed']} records")
        
        # Load
        print("\nStep 3: Load to warehouse...")
        load_stats = load_to_warehouse(transformed)
        
        print(f"\n✓ Load Statistics:")
        print(f"  - Companies loaded: {load_stats['companies_loaded']}")
        print(f"  - Locations loaded: {load_stats['locations_loaded']}")
        print(f"  - Titles loaded: {load_stats['titles_loaded']}")
        print(f"  - Contract types loaded: {load_stats['contracts_loaded']}")
        print(f"  - Offers loaded: {load_stats['offers_loaded']}")
        print(f"  - Skill relationships: {load_stats['skills_bridge_loaded']}")
        
        print(f"\n✓ Warehouse Validation:")
        val = load_stats.get('validation', {})
        print(f"  - Status: {val.get('status', 'UNKNOWN')}")
        print(f"  - Offers in warehouse: {val.get('offers_in_warehouse', 0)}")
        print(f"  - Companies in warehouse: {val.get('companies_in_warehouse', 0)}")
        print(f"  - Locations in warehouse: {val.get('locations_in_warehouse', 0)}")
        print(f"  - Titles in warehouse: {val.get('titles_in_warehouse', 0)}")
        print(f"  - Skill relationships: {val.get('skill_relationships', 0)}")
        
        if val.get('errors'):
            print(f"\n⚠ Issues:")
            for issue in val['errors']:
                print(f"  - {issue}")
        
        print(f"\n{'='*60}\n")
        
    except Exception as e:
        logger.error(f"Load failed: {e}", exc_info=True)
        sys.exit(1)
