"""
ETL Extract Module
================
Reads raw JSONL files from the bronze layer across 6 job sources,
normalizes them into a unified record structure, and validates completeness.

Input:  bronze/{source}/*.json files (JSONL format)
Output: List of normalized dictionaries with consistent field names

Sources handled:
  - LinkedIn
  - Indeed
  - FranceTravail
  - Remotive
  - TheMuse
  - Glassdoor (mocked)
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BronzeExtractor:
    """Extracts and normalizes job records from bronze JSONL files."""

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

    def __init__(self, bronze_base_path: str):
        """
        Initialize the extractor.
        
        Args:
            bronze_base_path: Path to bronze directory containing subdirectories by source
                             e.g., '/home/jovyan/data_lake' or 'c:\\path\\to\\bronze'
        """
        self.bronze_base_path = Path(bronze_base_path)
        if not self.bronze_base_path.exists():
            raise ValueError(f"Bronze path does not exist: {bronze_base_path}")
        logger.info(f"Extractor initialized with bronze path: {self.bronze_base_path}")

    def extract_all_sources(self) -> tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        Extract records from all source subdirectories.
        
        Returns:
            tuple: (normalized_records, stats)
                - normalized_records: List of normalized job record dictionaries
                - stats: Dict with counts by source (e.g., {'LinkedIn': 1000, 'Indeed': 500})
        """
        all_records = []
        stats = {name: 0 for name in self.SOURCE_MAPPING.values()}
        
        logger.info("Starting extraction from all sources...")
        
        for source_dir in self.bronze_base_path.iterdir():
            if not source_dir.is_dir():
                continue
            
            source_key = source_dir.name.lower()
            if source_key not in self.SOURCE_MAPPING:
                logger.warning(f"Unknown source directory: {source_dir.name}, skipping")
                continue
            
            source_name = self.SOURCE_MAPPING[source_key]
            records = self.extract_source(source_dir, source_name)
            all_records.extend(records)
            stats[source_name] = len(records)
            logger.info(f"Extracted {len(records)} records from {source_name}")
        
        logger.info(f"Total extracted: {len(all_records)} records across {len([v for v in stats.values() if v > 0])} sources")
        return all_records, stats

    def extract_source(self, source_path: Path, source_name: str) -> List[Dict[str, Any]]:
        """
        Extract records from a single source directory.
        
        Args:
            source_path: Path to source subdirectory
            source_name: Standardized source name (e.g., 'LinkedIn')
        
        Returns:
            List of normalized records from this source
        """
        records = []
        json_files = list(source_path.glob('*.json'))
        
        if not json_files:
            logger.warning(f"No JSON files found in {source_path}")
            return records
        
        logger.debug(f"Found {len(json_files)} JSON files in {source_path}")
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        if not line.strip():  # Skip empty lines
                            continue
                        try:
                            raw_record = json.loads(line)
                            normalized = self._normalize_record(raw_record, source_name)
                            if normalized:
                                records.append(normalized)
                        except json.JSONDecodeError as e:
                            logger.warning(f"Invalid JSON in {json_file.name}:{line_num} - {str(e)[:100]}")
                        except Exception as e:
                            logger.warning(f"Error processing {json_file.name}:{line_num} - {str(e)[:100]}")
            except Exception as e:
                logger.error(f"Failed to read {json_file}: {str(e)}")
        
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
            source_job_id = raw_record.get('id_offer') or raw_record.get('id')
            title = raw_record.get('title') or raw_record.get('title_raw')
            company = raw_record.get('company') or raw_record.get('company_name')
            location = raw_record.get('location') or raw_record.get('location_raw')
            description = raw_record.get('description') or raw_record.get('description_raw') or ''
            employment_type = raw_record.get('employment_type') or 'Unknown'
            url = raw_record.get('url') or ''
            posted_at = raw_record.get('posted_at')
            scraped_at = raw_record.get('scraped_at') or raw_record.get('ingestion_ts')
            
            # If critical fields are missing, skip this record
            if not source_job_id or not title or not company:
                logger.debug(f"Skipping record from {source_name}: missing id_offer, title, or company")
                return None
            
            # Extract skills (handle both list and comma-separated formats)
            skills = raw_record.get('skills', [])
            if isinstance(skills, str):
                skills = [s.strip() for s in skills.split(',') if s.strip()]
            elif not isinstance(skills, list):
                skills = []
            
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
                'location_raw': str(location).strip(),
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


def extract_and_validate(bronze_path: str) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Convenience function to extract and validate records in one call.
    
    Args:
        bronze_path: Path to bronze directory
    
    Returns:
        tuple: (records, validation_results)
    """
    extractor = BronzeExtractor(bronze_path)
    records, stats = extractor.extract_all_sources()
    validation = extractor.validate_records(records)
    
    logger.info(f"Extraction complete: {validation}")
    
    return records, validation


if __name__ == '__main__':
    # Example usage: python extract.py
    import sys
    
    # Default bronze path for docker container
    bronze_path = '/home/jovyan/data_lake/bronze' if os.path.exists('/home/jovyan/data_lake') else 'bronze'
    
    if len(sys.argv) > 1:
        bronze_path = sys.argv[1]
    
    print(f"\n{'='*60}")
    print("ETL Extract Module - Test Run")
    print(f"{'='*60}\n")
    
    try:
        records, validation = extract_and_validate(bronze_path)
        
        print(f"✓ Total Records Extracted: {validation['total_records']}")
        print(f"✓ Validation Status: {validation['validation_status']}")
        print(f"\nField Coverage (%):")
        for field, pct in sorted(validation['field_coverage_pct'].items()):
            status = "✓" if pct == 100 else "⚠" if pct >= 50 else "✗"
            print(f"  {status} {field:20s}: {pct:6.1f}%")
        
        if validation['issues']:
            print(f"\nIssues Found:")
            for issue in validation['issues']:
                print(f"  ⚠ {issue}")
        
        print(f"\n{'='*60}\n")
        
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        sys.exit(1)
