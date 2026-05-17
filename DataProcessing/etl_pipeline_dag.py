"""
Airflow DAG: ETL Pipeline Orchestration
========================================
Orchestrates the complete ETL workflow:
  1. Extract data from bronze layer (JSONL files)
  2. Transform: clean, parse, deduplicate
  3. Load to Neon PostgreSQL warehouse
  4. Validate data quality

Schedule: Daily at 02:00 UTC (configurable)
Retries: 2 attempts with 5-minute backoff
Timeout: 30 minutes
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.task_group import TaskGroup
from airflow.exceptions import AirflowException
import logging
import sys
from pathlib import Path

# Setup logging
logger = logging.getLogger(__name__)

# ── DAG Configuration ───────────────────────────────────
default_args = {
    'owner': 'data-ami',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2026, 4, 22),
    'email_on_failure': False,
    'email_on_retry': False,
}

dag = DAG(
    dag_id='etl_pipeline_jobs',
    default_args=default_args,
    description='ETL pipeline: Extract → Transform → Load job data to Neon warehouse',
    schedule_interval='0 2 * * *',  # Daily at 02:00 UTC
    catchup=False,
    tags=['etl', 'jobs', 'neon'],
    max_active_runs=1,  # Only one instance at a time
)


# ── Global Configuration ────────────────────────────────
BRONZE_PATH = '/opt/airflow/project/bronze'  # Path mounted in Airflow container
NEON_CONFIG = {
    'host': 'ep-solitary-cherry-a4st8g9y-pooler.us-east-1.aws.neon.tech',
    'port': 5432,
    'database': 'neondb',
    'user': 'neondb_owner',
    'password': 'npg_6VqjWpLH8kxw',
    'sslmode': 'require',
}


# ── ETL Functions ──────────────────────────────────────

def extract_data(**context):
    """
    Extract raw data from bronze layer.
    
    Returns:
        dict with extraction statistics
    """
    logger.info("Starting data extraction from bronze layer...")
    
    try:
        from etl.extract import extract_and_validate
        
        records, validation = extract_and_validate(BRONZE_PATH)
        
        stats = {
            'total_records': validation['total_records'],
            'extraction_status': validation['validation_status'],
            'errors': validation.get('issues', []),
        }
        
        logger.info(f"✓ Extraction complete: {stats['total_records']} records")
        
        # Push to XCom for downstream tasks
        context['task_instance'].xcom_push(key='records_extracted', value=len(records))
        context['task_instance'].xcom_push(key='extraction_stats', value=stats)
        
        return stats
        
    except Exception as e:
        logger.error(f"Extraction failed: {str(e)}", exc_info=True)
        raise AirflowException(f"Extract task failed: {str(e)}")


def transform_data(**context):
    """
    Transform and clean extracted data.
    
    Returns:
        dict with transformation statistics
    """
    logger.info("Starting data transformation...")
    
    try:
        from etl.extract import extract_and_validate
        from etl.transform import transform_records
        
        # Re-extract (in production, could store intermediate data)
        records, _ = extract_and_validate(BRONZE_PATH)
        logger.info(f"Re-extracted {len(records)} records for transformation")
        
        # Transform
        transformed, transform_stats = transform_records(records, deduplicate=True)
        
        stats = {
            'records_input': transform_stats['total_transformed'],
            'records_after_dedup': transform_stats['deduplicated_count'],
            'duplicates_removed': transform_stats['duplicates_removed'],
            'description_clean_pct': transform_stats['data_quality'].get('description_clean_coverage_pct', 0),
            'location_parsed_pct': transform_stats['data_quality'].get('location_parsed_coverage_pct', 0),
            'salary_extracted_pct': transform_stats['data_quality'].get('salary_extracted_coverage_pct', 0),
            'transformation_status': 'SUCCESS',
        }
        
        logger.info(f"✓ Transformation complete: {stats['records_after_dedup']} records ready for load")
        
        context['task_instance'].xcom_push(key='records_transformed', value=len(transformed))
        context['task_instance'].xcom_push(key='transform_stats', value=stats)
        
        return stats
        
    except Exception as e:
        logger.error(f"Transformation failed: {str(e)}", exc_info=True)
        raise AirflowException(f"Transform task failed: {str(e)}")


def load_data_to_warehouse(**context):
    """
    Load transformed data to Neon PostgreSQL warehouse.
    
    Returns:
        dict with load statistics
    """
    logger.info("Starting data load to Neon warehouse...")
    
    try:
        from etl.extract import extract_and_validate
        from etl.transform import transform_records
        from etl.load import load_to_warehouse
        
        # Re-extract and transform (in production, use intermediate storage)
        records, _ = extract_and_validate(BRONZE_PATH)
        transformed, _ = transform_records(records, deduplicate=True)
        
        logger.info(f"Loading {len(transformed)} records to warehouse...")
        
        # Load to Neon
        load_stats = load_to_warehouse(
            transformed,
            host=NEON_CONFIG['host'],
            port=NEON_CONFIG['port'],
            database=NEON_CONFIG['database'],
            user=NEON_CONFIG['user'],
            password=NEON_CONFIG['password'],
            sslmode=NEON_CONFIG['sslmode'],
        )

        if load_stats.get('errors'):
            raise AirflowException(
                f"Load task failed: {str(load_stats['errors']).strip()}"
            )
        
        logger.info(f"✓ Load complete: {load_stats['offers_loaded']} offers loaded")
        
        context['task_instance'].xcom_push(key='load_stats', value=load_stats)
        
        return load_stats
        
    except Exception as e:
        logger.error(f"Load failed: {str(e)}", exc_info=True)
        raise AirflowException(f"Load task failed: {str(e)}")


def validate_warehouse_data(**context):
    """
    Validate data quality in warehouse after load.
    
    Returns:
        dict with validation results
    """
    logger.info("Validating warehouse data...")
    
    try:
        import psycopg2
        
        conn = psycopg2.connect(
            host=NEON_CONFIG['host'],
            port=NEON_CONFIG['port'],
            database=NEON_CONFIG['database'],
            user=NEON_CONFIG['user'],
            password=NEON_CONFIG['password'],
            sslmode=NEON_CONFIG['sslmode'],
        )
        cursor = conn.cursor()
        
        # Check record counts
        cursor.execute("SELECT COUNT(*) FROM fact_job_offer")
        offers_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM dim_company")
        companies_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM dim_location")
        locations_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM dim_job_title")
        titles_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM bridge_offer_skill")
        skills_count = cursor.fetchone()[0]
        
        # Check for orphaned records
        cursor.execute("""
            SELECT COUNT(*) FROM fact_job_offer f
            WHERE f.dim_company_id IS NULL 
               OR f.dim_location_id IS NULL
               OR f.dim_title_id IS NULL
        """)
        orphaned = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        validation = {
            'offers_count': offers_count,
            'companies_count': companies_count,
            'locations_count': locations_count,
            'titles_count': titles_count,
            'skills_count': skills_count,
            'orphaned_records': orphaned,
            'status': 'PASS' if orphaned == 0 and offers_count > 0 else 'WARNING',
        }
        
        logger.info(f"✓ Validation complete: {offers_count} offers, {companies_count} companies, {locations_count} locations")
        
        if orphaned > 0:
            logger.warning(f"⚠ Found {orphaned} orphaned records!")
        
        if validation['status'] == 'PASS':
            logger.info("✓ Warehouse validation PASSED")
        else:
            logger.warning(f"⚠ Warehouse validation returned WARNING: {validation}")
        
        context['task_instance'].xcom_push(key='validation_results', value=validation)
        
        return validation
        
    except Exception as e:
        logger.error(f"Validation failed: {str(e)}", exc_info=True)
        raise AirflowException(f"Validation task failed: {str(e)}")


def generate_execution_summary(**context):
    """
    Generate summary of ETL execution.
    """
    logger.info("Generating execution summary...")
    
    ti = context['task_instance']
    
    # Pull results from all tasks
    extract_stats = ti.xcom_pull(task_ids='extract', key='extraction_stats') or {}
    transform_stats = ti.xcom_pull(task_ids='transform', key='transform_stats') or {}
    load_stats = ti.xcom_pull(task_ids='load', key='load_stats') or {}
    validation = ti.xcom_pull(task_ids='validate', key='validation_results') or {}
    
    summary = {
        'extraction': extract_stats,
        'transformation': transform_stats,
        'loading': load_stats,
        'validation': validation,
    }
    
    logger.info("="*60)
    logger.info("ETL EXECUTION SUMMARY")
    logger.info("="*60)
    logger.info(f"Extracted: {extract_stats.get('total_records', 'N/A')} records")
    logger.info(f"Transformed: {transform_stats.get('records_after_dedup', 'N/A')} records (after dedup)")
    logger.info(f"Loaded: {load_stats.get('offers_loaded', 'N/A')} offers")
    logger.info(f"Validation Status: {validation.get('status', 'N/A')}")
    logger.info("="*60)
    
    return summary


# ── DAG Tasks ──────────────────────────────────────────

with dag:
    
    # Task 1: Extract
    extract = PythonOperator(
        task_id='extract',
        python_callable=extract_data,
        provide_context=True,
        doc='Extract raw data from bronze layer (JSONL files)',
    )
    
    # Task 2: Transform
    transform = PythonOperator(
        task_id='transform',
        python_callable=transform_data,
        provide_context=True,
        doc='Transform: clean HTML, parse locations, normalize contracts, deduplicate',
    )
    
    # Task 3: Load
    load = PythonOperator(
        task_id='load',
        python_callable=load_data_to_warehouse,
        provide_context=True,
        doc='Load to Neon warehouse: dimensions → fact → bridge',
    )
    
    # Task 4: Validate
    validate = PythonOperator(
        task_id='validate',
        python_callable=validate_warehouse_data,
        provide_context=True,
        doc='Validate warehouse data quality (row counts, referential integrity)',
    )
    
    # Task 5: Summary
    summary = PythonOperator(
        task_id='summary',
        python_callable=generate_execution_summary,
        provide_context=True,
        trigger_rule='all_done',  # Run even if previous tasks fail
        doc='Generate execution summary',
    )
    
    # ── Task Dependencies ────────────────────────────────
    extract >> transform >> load >> validate >> summary
