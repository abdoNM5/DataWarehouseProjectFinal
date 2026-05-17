"""
ETL Extract Module (MinIO-backed)
==================================
Reads raw JSONL files from the MinIO bronze bucket across job sources,
normalizes them into a unified record structure, and validates completeness.

Input:  MinIO bronze bucket: {source}/[migrated|YYYY-MM-DD]/*.jsonl files
Output: List of normalized dictionaries with consistent field names

Sources handled:
  - LinkedIn
  - Indeed
  - FranceTravail
  - Remotive
  - TheMuse
  - Glassdoor (mocked)
"""

import io
import json
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ── MinIO configuration (from env vars set in docker-compose) ──
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minio")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minio123")
MINIO_BUCKET_BRONZE = os.environ.get("MINIO_BUCKET_BRONZE", "bronze")


def _get_minio_client():
    """Create and return a MinIO client instance."""
    from minio import Minio
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
    )


class BronzeExtractor:
    """Extracts and normalizes job records from MinIO bronze bucket."""

    # Map bronze directory names to standardized source names
    SOURCE_MAPPING = {
        'linkedin': 'LinkedIn',
        'indeed': 'Indeed',
        'francetravail': 'FranceTravail',
        'remotive': 'Remotive',
        'themuse': 'TheMuse',
        'glassdoor': 'Glassdoor',
    }

    # Required fields that must exist in every normalized record
    REQUIRED_FIELDS = {
        'source', 'source_job_id', 'title_raw', 'company_name',
        'location_raw', 'employment_type', 'description_raw',
        'skills', 'url', 'posted_at', 'scraped_at'
    }

    # Optional numeric fields
    OPTIONAL_NUMERIC_FIELDS = {'salary_min', 'salary_max'}

    def __init__(self, bucket_name: str = None):
        """
        Initialize the extractor.

        Args:
            bucket_name: MinIO bucket name (defaults to MINIO_BUCKET_BRONZE env var)
        """
        self.bucket_name = bucket_name or MINIO_BUCKET_BRONZE
        self.client = _get_minio_client()

        if not self.client.bucket_exists(self.bucket_name):
            raise ValueError(f"MinIO bucket does not exist: {self.bucket_name}")
        logger.info(f"Extractor initialized with MinIO bucket: {self.bucket_name}")

    def _list_source_prefixes(self) -> List[str]:
        """Discover source prefixes (top-level directories) in the bronze bucket."""
        prefixes = set()
        objects = self.client.list_objects(self.bucket_name, prefix="", recursive=False)
        for obj in objects:
            if obj.is_dir:
                # obj.object_name looks like "indeed/" — strip the trailing slash
                source_key = obj.object_name.rstrip("/").lower()
                if source_key in self.SOURCE_MAPPING:
                    prefixes.add(source_key)
        return sorted(prefixes)

    def _list_jsonl_objects(self, source_prefix: str) -> List[str]:
        """List all JSONL/JSON objects under a source prefix in the bucket."""
        objects = self.client.list_objects(
            self.bucket_name,
            prefix=f"{source_prefix}/",
            recursive=True,
        )
        result = []
        for obj in objects:
            name = obj.object_name
            if name.endswith(".json") or name.endswith(".jsonl"):
                result.append(name)
        return sorted(result)

    def _read_object_lines(self, object_name: str) -> List[str]:
        """Read a MinIO object and return its lines."""
        try:
            response = self.client.get_object(self.bucket_name, object_name)
            content = response.read().decode("utf-8")
            response.close()
            response.release_conn()
            return content.splitlines()
        except Exception as e:
            logger.error(f"Failed to read object {object_name}: {e}")
            return []

    def extract_all_sources(self) -> tuple:
        """
        Extract records from all source prefixes in the MinIO bucket.

        Returns:
            tuple: (normalized_records, stats)
                - normalized_records: List of normalized job record dictionaries
                - stats: Dict with counts by source (e.g., {'LinkedIn': 1000, 'Indeed': 500})
        """
        all_records = []
        stats = {name: 0 for name in self.SOURCE_MAPPING.values()}

        logger.info("Starting extraction from MinIO bronze bucket...")
        source_prefixes = self._list_source_prefixes()
        logger.info(f"Found source prefixes: {source_prefixes}")

        for source_key in source_prefixes:
            source_name = self.SOURCE_MAPPING[source_key]
            records = self.extract_source(source_key, source_name)
            all_records.extend(records)
            stats[source_name] = len(records)
            logger.info(f"Extracted {len(records)} records from {source_name}")

        active_sources = len([v for v in stats.values() if v > 0])
        logger.info(f"Total extracted: {len(all_records)} records across {active_sources} sources")
        return all_records, stats

    def extract_source(self, source_prefix: str, source_name: str) -> List[Dict[str, Any]]:
        """
        Extract records from a single source prefix in MinIO.

        Args:
            source_prefix: Source prefix in bucket (e.g., 'indeed')
            source_name: Standardized source name (e.g., 'Indeed')

        Returns:
            List of normalized records from this source
        """
        records = []
        json_objects = self._list_jsonl_objects(source_prefix)

        if not json_objects:
            logger.warning(f"No JSON files found under {source_prefix}/ in bucket {self.bucket_name}")
            return records

        logger.debug(f"Found {len(json_objects)} JSON files under {source_prefix}/")

        for object_name in json_objects:
            lines = self._read_object_lines(object_name)
            for line_num, line in enumerate(lines, 1):
                if not line.strip():
                    continue
                try:
                    raw_record = json.loads(line)
                    normalized = self._normalize_record(raw_record, source_name)
                    if normalized:
                        records.append(normalized)
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON in {object_name}:{line_num} - {str(e)[:100]}")
                except Exception as e:
                    logger.warning(f"Error processing {object_name}:{line_num} - {str(e)[:100]}")

        return records

    def _normalize_record(self, raw_record: Dict[str, Any], source_name: str) -> Optional[Dict[str, Any]]:
        """
        Normalize a raw record from any source into unified structure.

        Args:
            raw_record: Raw job record from JSON
            source_name: Source identifier (LinkedIn, Indeed, etc.)

        Returns:
            Normalized record dict or None if critical fields missing
        """
        try:
            # Extract required fields (handle source-specific naming variations)
            source_job_id = raw_record.get('id_offer') or raw_record.get('id') or raw_record.get('source_job_id')
            title = raw_record.get('title') or raw_record.get('title_raw')
            company = raw_record.get('company') or raw_record.get('company_name')
            location = raw_record.get('location') or raw_record.get('location_raw')
            description = raw_record.get('description') or raw_record.get('description_raw') or ''
            employment_type = raw_record.get('employment_type') or raw_record.get('contract_type') or 'Unknown'
            url = raw_record.get('url') or ''
            posted_at = raw_record.get('posted_at') or raw_record.get('publication_date')
            scraped_at = raw_record.get('scraped_at') or raw_record.get('ingestion_ts')

            # If critical fields are missing, skip this record
            if not source_job_id or not title or not company:
                logger.debug(f"Skipping record from {source_name}: missing id, title, or company")
                return None

            # Extract skills (handle both list and comma-separated formats)
            skills = raw_record.get('skills', [])
            if isinstance(skills, str):
                skills = [s.strip() for s in skills.split(',') if s.strip()]
            elif not isinstance(skills, list):
                skills = []

            # Also try 'tags' field (used by Remotive)
            tags = raw_record.get('tags', [])
            if isinstance(tags, list):
                skills = list(set(skills + [str(t).strip() for t in tags if str(t).strip()]))

            # Extract optional salary fields (convert to float or None)
            salary_min = self._safe_float(raw_record.get('salary_min'))
            salary_max = self._safe_float(raw_record.get('salary_max'))
            currency = raw_record.get('currency') or 'EUR'

            # Build normalized record
            normalized = {
                'source': source_name,
                'source_job_id': str(source_job_id).strip(),
                'title_raw': str(title).strip(),
                'company_name': str(company).strip(),
                'location_raw': str(location).strip() if location else 'Unknown',
                'employment_type': str(employment_type).strip(),
                'description_raw': str(description).strip(),
                'skills': skills,
                'url': str(url).strip(),
                'posted_at': posted_at,
                'scraped_at': scraped_at,
            }

            # Add optional fields only if present
            if salary_min is not None:
                normalized['salary_min'] = salary_min
            if salary_max is not None:
                normalized['salary_max'] = salary_max

            normalized['currency'] = currency

            return normalized

        except Exception as e:
            logger.debug(f"Error normalizing record from {source_name}: {str(e)}")
            return None

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        """Safely convert value to float, return None if unable."""
        try:
            if value is None or value == '':
                return None
            return float(value)
        except (ValueError, TypeError):
            return None

    def validate_records(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate extracted records and return quality metrics.

        Args:
            records: List of normalized records

        Returns:
            Dict with validation metrics (completeness, missing fields, etc.)
        """
        if not records:
            return {
                'total_records': 0,
                'validation_status': 'EMPTY',
                'issues': ['No records extracted']
            }

        issues = []
        field_coverage = {field: 0 for field in self.REQUIRED_FIELDS}

        for record in records:
            for field in self.REQUIRED_FIELDS:
                if field in record and record[field]:
                    field_coverage[field] += 1

        # Calculate coverage percentages
        total = len(records)
        coverage_pct = {field: (count / total * 100) for field, count in field_coverage.items()}

        # Flag fields with low coverage
        low_coverage_fields = {field: pct for field, pct in coverage_pct.items() if pct < 50}
        if low_coverage_fields:
            issues.append(f"Fields with <50% coverage: {low_coverage_fields}")

        # Check salary consistency
        salary_pairs = [r for r in records if 'salary_min' in r and 'salary_max' in r]
        invalid_salary = [r for r in salary_pairs if r['salary_min'] > r['salary_max']]
        if invalid_salary:
            issues.append(f"{len(invalid_salary)} records with salary_min > salary_max")

        validation = {
            'total_records': total,
            'field_coverage_pct': coverage_pct,
            'validation_status': 'PASS' if not issues else 'WARNING',
            'issues': issues if issues else []
        }

        return validation


def extract_and_validate(bronze_source: str = None) -> tuple:
    """
    Convenience function to extract and validate records in one call.

    Args:
        bronze_source: MinIO bucket name (defaults to MINIO_BUCKET_BRONZE env var).
                       For backward compatibility, this parameter is accepted but
                       the extractor now always reads from MinIO.

    Returns:
        tuple: (records, validation_results)
    """
    bucket = bronze_source if bronze_source and not bronze_source.startswith("/") else None
    extractor = BronzeExtractor(bucket_name=bucket)
    records, stats = extractor.extract_all_sources()
    validation = extractor.validate_records(records)

    logger.info(f"Extraction complete: {validation}")

    return records, validation


if __name__ == '__main__':
    import sys

    print(f"\n{'='*60}")
    print("ETL Extract Module (MinIO) - Test Run")
    print(f"{'='*60}\n")

    try:
        bucket = sys.argv[1] if len(sys.argv) > 1 else None
        records, validation = extract_and_validate(bucket)

        print(f"Total Records Extracted: {validation['total_records']}")
        print(f"Validation Status: {validation['validation_status']}")
        print(f"\nField Coverage (%):")
        for field, pct in sorted(validation.get('field_coverage_pct', {}).items()):
            status = "OK" if pct == 100 else "WARN" if pct >= 50 else "FAIL"
            print(f"  {status} {field:20s}: {pct:6.1f}%")

        if validation['issues']:
            print(f"\nIssues Found:")
            for issue in validation['issues']:
                print(f"  WARNING: {issue}")

        print(f"\n{'='*60}\n")

    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        sys.exit(1)
