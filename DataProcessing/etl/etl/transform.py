"""
ETL Transform Module
===================
Cleans, normalizes, and deduplicates job records from the extract stage.

Processing steps:
  1. HTML stripping from descriptions
  2. Location parsing (city, region, country extraction)
  3. Employment type normalization
  4. Salary extraction from text (fallback if not already extracted)
  5. Skill normalization and deduplication
  6. Record deduplication (intra-source by source_job_id)
  7. Preparation for NLP pipeline (title normalization via friend's module)

Input:  Normalized records from extract.py
Output: Clean, deduplicated records ready for warehouse load
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict
from html.parser import HTMLParser
from io import StringIO

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HTMLStripper(HTMLParser):
    """Strip HTML tags and decode HTML entities."""
    
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = StringIO()
    
    def handle_data(self, data):
        self.text.write(data)
    
    def get_data(self):
        return self.text.getvalue()
    
    @staticmethod
    def strip(html: str) -> str:
        """Strip HTML tags from string."""
        if not html or not isinstance(html, str):
            return ""
        try:
            stripper = HTMLStripper()
            stripper.feed(html)
            return stripper.get_data().strip()
        except Exception:
            # Fallback: simple regex stripping if HTMLParser fails
            text = re.sub('<[^<]+?>', '', html)
            return text.strip()


class DescriptionCleaner:
    """Normalize description text and drop known placeholder values."""

    PLACEHOLDER_PATTERNS = [
        r'^description\s+non\s+extraite',
        r'^description\s+not\s+extracted',
        r'^description\s+unavailable',
        r'^no\s+description\s+available',
        r'^n/?a$',
    ]

    @staticmethod
    def normalize(text: str) -> str:
        if not text:
            return ""

        cleaned = re.sub(r'\s+', ' ', text).strip()
        if not cleaned:
            return ""

        cleaned_lower = cleaned.lower()
        for pattern in DescriptionCleaner.PLACEHOLDER_PATTERNS:
            if re.search(pattern, cleaned_lower):
                return ""

        return cleaned


class LocationParser:
    """Parse and normalize location strings into components."""
    
    # Common country mappings
    COUNTRY_MAPPING = {
        'france': 'France',
        'paris': 'France',
        'lyon': 'France',
        'marseille': 'France',
        'toulouse': 'France',
        'bordeaux': 'France',
        'lille': 'France',
        'nice': 'France',
        'nantes': 'France',
        'strasbourg': 'France',
        'montpellier': 'France',
        'rennes': 'France',
        'reims': 'France',
        'usa': 'United States',
        'united states': 'United States',
        'us': 'United States',
        'uk': 'United Kingdom',
        'united kingdom': 'United Kingdom',
        'germany': 'Germany',
        'germany': 'Germany',
        'spain': 'Spain',
        'italy': 'Italy',
        'canada': 'Canada',
        'australia': 'Australia',
        'india': 'India',
        'remote': 'Remote',
        'anywhere': 'Remote',
    }
    
    # French regions
    FRENCH_REGIONS = {
        'ile-de-france': 'Île-de-France',
        'rhone-alpes': 'Auvergne-Rhône-Alpes',
        'aquitaine': 'Nouvelle-Aquitaine',
        'languedoc': 'Occitanie',
        'provence': 'Provence-Alpes-Côte d\'Azur',
        'alsace': 'Grand Est',
        'brittany': 'Brittany',
        'normandy': 'Normandy',
    }
    
    @staticmethod
    def parse(location_raw: str) -> Dict[str, Optional[str]]:
        """
        Parse location string into components.
        
        Args:
            location_raw: Raw location string (e.g., "Paris, France")
        
        Returns:
            Dict with parsed components: {city, region, country}
        """
        if not location_raw:
            return {'city': None, 'region': None, 'country': None}
        
        location_clean = location_raw.strip()
        result = {'city': None, 'region': None, 'country': None}
        
        # Handle "Remote" explicitly
        if location_clean.lower() in ['remote', 'anywhere', 'wfh']:
            result['country'] = 'Remote'
            return result
        
        # Split by common delimiters
        parts = [p.strip() for p in re.split(r'[,;]', location_clean) if p.strip()]
        
        if not parts:
            return result
        
        # Try to match against known countries (last part usually country)
        if parts:
            last_part_lower = parts[-1].lower()
            for key, country in LocationParser.COUNTRY_MAPPING.items():
                if key in last_part_lower:
                    result['country'] = country
                    parts = parts[:-1]
                    break
        
        # Remaining parts: city and/or region
        if len(parts) >= 2:
            result['city'] = parts[0]
            result['region'] = parts[1]
        elif len(parts) == 1:
            result['city'] = parts[0]
        
        return result


class SalaryExtractor:
    """Extract salary information from text or structured fields."""
    
    # Regex patterns for salary extraction from text
    SALARY_PATTERNS = [
        r'(\d+(?:[.,]\d+)?)\s*(?:k|K)\s*(?:€|EUR|euros?)',  # 50k EUR
        r'(\d+(?:[.,]\d+)?)\s*(?:k|K)\s*(?:\$|USD)',  # 50k USD
        r'(?:€|EUR)\s*(\d+(?:[.,]\d+)?)\s*(?:k|K)?',  # EUR 50k
        r'(\d+(?:[.,]\d{3})?)\s*(?:€|EUR)',  # 50000 EUR
        r'(\d+(?:[.,]\d{3})?)\s*(?:\$|USD)',  # 50000 USD
    ]
    
    @staticmethod
    def extract(description: str, salary_min: Optional[float] = None, 
                salary_max: Optional[float] = None) -> Tuple[Optional[float], Optional[float]]:
        """
        Extract salary range from description or use provided values.
        
        Args:
            description: Job description text
            salary_min: Already-extracted salary minimum
            salary_max: Already-extracted salary maximum
        
        Returns:
            Tuple of (salary_min, salary_max)
        """
        # If already provided, use those
        if salary_min and salary_max:
            return (salary_min, salary_max)
        
        if not description or not isinstance(description, str):
            return (salary_min, salary_max)
        
        # Search for salary patterns in description
        found_salaries = []
        for pattern in SalaryExtractor.SALARY_PATTERNS:
            matches = re.finditer(pattern, description, re.IGNORECASE)
            for match in matches:
                try:
                    amount = match.group(1).replace(',', '.').replace(' ', '')
                    salary = float(amount)
                    # If amount is < 1000, assume it's in thousands (e.g., "50k" = 50000)
                    if salary < 1000:
                        salary *= 1000
                    found_salaries.append(salary)
                except (ValueError, AttributeError):
                    pass
        
        # If we found salaries, use min/max
        if found_salaries:
            found_salaries = sorted(set(found_salaries))
            return (found_salaries[0], found_salaries[-1])
        
        return (salary_min, salary_max)


class EmploymentTypeNormalizer:
    """Normalize employment type/contract variations."""
    
    EMPLOYMENT_TYPES = {
        'permanent': ['permanent', 'cdi', 'full-time', 'fulltime', 'temps plein', 'indefinite'],
        'contract': ['contract', 'cdd', 'fixed-term', 'fixed term', 'contrat', 'temporary'],
        'freelance': ['freelance', 'self-employed', 'contractor', 'independant'],
        'internship': ['internship', 'stage', 'apprenticeship', 'intern'],
        'part-time': ['part-time', 'parttime', 'temps partiel'],
        'temporary': ['temporary', 'temp', 'interim'],
    }
    
    @staticmethod
    def normalize(employment_type: str) -> str:
        """
        Normalize employment type string to standard category.
        
        Args:
            employment_type: Raw employment type string
        
        Returns:
            Normalized employment type
        """
        if not employment_type:
            return 'Unknown'
        
        employment_lower = employment_type.lower().strip()
        
        for standard_type, variations in EmploymentTypeNormalizer.EMPLOYMENT_TYPES.items():
            for variation in variations:
                if variation in employment_lower:
                    return standard_type
        
        # If no match found, return original (capitalized)
        return employment_type.capitalize()


class SkillNormalizer:
    """Normalize and deduplicate skills."""

    SKILL_PATTERNS = {
        'python': [r'\bpython\b'],
        'sql': [r'\bsql\b'],
        'airflow': [r'\bairflow\b'],
        'dbt': [r'\bdbt\b'],
        'spark': [r'\bspark\b'],
        'kafka': [r'\bkafka\b'],
        'aws': [r'\baws\b'],
        'azure': [r'\bazure\b'],
        'gcp': [r'\bgcp\b', r'\bgoogle\s+cloud\b'],
        'snowflake': [r'\bsnowflake\b'],
        'bigquery': [r'\bbigquery\b'],
        'databricks': [r'\bdatabricks\b'],
        'postgresql': [r'\bpostgres(?:ql)?\b'],
        'mysql': [r'\bmysql\b'],
        'mongodb': [r'\bmongodb\b'],
        'docker': [r'\bdocker\b'],
        'kubernetes': [r'\bkubernetes\b', r'\bk8s\b'],
        'git': [r'\bgit\b'],
        'power bi': [r'\bpower\s*bi\b', r'\bpowerbi\b'],
        'tableau': [r'\btableau\b'],
        'looker': [r'\blooker\b'],
        'excel': [r'\bexcel\b'],
        'pandas': [r'\bpandas\b'],
        'numpy': [r'\bnumpy\b'],
        'pyspark': [r'\bpyspark\b'],
        'tensorflow': [r'\btensorflow\b'],
        'pytorch': [r'\bpytorch\b'],
        'scikit-learn': [r'\bscikit\s*-?\s*learn\b', r'\bsklearn\b'],
        'machine learning': [r'\bmachine\s+learning\b'],
        'deep learning': [r'\bdeep\s+learning\b'],
        'llm': [r'\bllm\b', r'\blarge\s+language\s+model'],
        'nlp': [r'\bnlp\b', r'\bnatural\s+language\s+processing\b'],
        'api': [r'\bapi\b'],
        'rest': [r'\brest\b'],
        'graphql': [r'\bgraphql\b'],
        'talend': [r'\btalend\b'],
    }
    
    @staticmethod
    def normalize_skill(skill: str) -> str:
        """Normalize a single skill string."""
        if not skill:
            return ""
        return skill.strip().lower()
    
    @staticmethod
    def deduplicate_skills(skills: List[str]) -> List[str]:
        """Deduplicate and normalize skills list."""
        if not skills:
            return []
        
        normalized = set()
        for skill in skills:
            normalized_skill = SkillNormalizer.normalize_skill(skill)
            if normalized_skill:
                normalized.add(normalized_skill)
        
        return sorted(list(normalized))

    @staticmethod
    def infer_from_text(text: str) -> List[str]:
        """Infer skills from job title + description text."""
        if not text:
            return []

        text_lower = text.lower()
        inferred = set()

        for canonical, patterns in SkillNormalizer.SKILL_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    inferred.add(canonical)
                    break

        return sorted(list(inferred))


class TitleEnricher:
    """Infer lightweight title metadata for BI segmentation."""

    @staticmethod
    def normalize_title(title_raw: str) -> str:
        if not title_raw:
            return ""
        return re.sub(r'\s+', ' ', title_raw).strip()

    @staticmethod
    def infer_job_family(title: str) -> str:
        if not title:
            return 'Unknown'

        t = title.lower()
        if 'architect' in t and 'data' in t:
            return 'Data Architecture'
        if 'analytics engineer' in t:
            return 'Analytics Engineering'
        if 'machine learning' in t or 'ml engineer' in t or 'ai engineer' in t:
            return 'Machine Learning'
        if 'data scientist' in t:
            return 'Data Science'
        if 'data analyst' in t or 'bi analyst' in t:
            return 'Data Analysis'
        if 'data engineer' in t or 'etl' in t:
            return 'Data Engineering'
        if 'bi' in t or 'business intelligence' in t:
            return 'Business Intelligence'
        if 'analyst' in t or 'analytics' in t:
            return 'Analytics'
        return 'Unknown'

    @staticmethod
    def infer_seniority(title: str) -> str:
        if not title:
            return 'Unknown'

        t = title.lower()
        if re.search(r'\b(intern|internship|stage|alternance|apprentice)\b', t):
            return 'Intern'
        if re.search(r'\b(junior|jr|entry)\b', t):
            return 'Junior'
        if re.search(r'\b(senior|sr)\b', t):
            return 'Senior'
        if re.search(r'\b(lead|principal|head|director|vp)\b', t):
            return 'Lead'
        return 'Mid'


class RecordDeduplicator:
    """Deduplicate records within a source."""
    
    @staticmethod
    def deduplicate_intra_source(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Deduplicate records within each source.
        
        Records are considered duplicates if they have:
        - Same source_job_id AND same source
        
        Args:
            records: List of normalized records
        
        Returns:
            Tuple of (deduplicated_records, dedup_stats)
        """
        seen_keys: Dict[str, int] = defaultdict(int)
        deduplicated = []
        duplicates_by_source = defaultdict(int)
        
        for record in records:
            source = record.get('source', 'Unknown')
            source_job_id = record.get('source_job_id', '')
            
            dedup_key = f"{source}::{source_job_id}"
            
            if dedup_key not in seen_keys:
                deduplicated.append(record)
                seen_keys[dedup_key] = 1
            else:
                seen_keys[dedup_key] += 1
                duplicates_by_source[source] += 1
        
        stats = {
            'original_count': len(records),
            'deduplicated_count': len(deduplicated),
            'duplicates_removed': len(records) - len(deduplicated),
            'duplicates_by_source': dict(duplicates_by_source),
        }
        
        logger.info(f"Deduplication: {stats['original_count']} → {stats['deduplicated_count']} records")
        
        return deduplicated, stats


class BronzeTransformer:
    """Transform and clean extracted job records."""
    
    def __init__(self, skip_title_normalization: bool = True):
        """
        Initialize transformer.
        
        Args:
            skip_title_normalization: If True, skip title normalization (await friend's NLP module)
        """
        self.skip_title_normalization = skip_title_normalization
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a single record through all cleaning steps.
        
        Args:
            record: Normalized record from extract stage
        
        Returns:
            Transformed record
        """
        transformed = record.copy()
        
        # Step 1: Strip HTML + remove placeholder descriptions
        if 'description_raw' in transformed:
            description_clean = HTMLStripper.strip(transformed.get('description_raw', ''))
            transformed['description_clean'] = DescriptionCleaner.normalize(description_clean)
        
        # Step 2: Parse location
        location_parsed = LocationParser.parse(transformed.get('location_raw', ''))
        transformed.update({
            'location_city': location_parsed['city'],
            'location_region': location_parsed['region'],
            'location_country': location_parsed['country'],
        })
        
        # Step 3: Normalize employment type
        transformed['employment_type_normalized'] = EmploymentTypeNormalizer.normalize(
            transformed.get('employment_type', 'Unknown')
        )
        
        # Step 4: Extract/validate salary
        salary_min, salary_max = SalaryExtractor.extract(
            transformed.get('description_clean', ''),
            transformed.get('salary_min'),
            transformed.get('salary_max'),
        )
        transformed['salary_min_extracted'] = salary_min
        transformed['salary_max_extracted'] = salary_max
        
        # Step 5: Deduplicate source skills + infer missing skills from text
        source_skills = transformed.get('skills', [])
        text_for_skill_inference = (
            f"{transformed.get('title_raw', '')} {transformed.get('description_clean', '')}"
        )
        inferred_skills = SkillNormalizer.infer_from_text(text_for_skill_inference)
        transformed['skills_normalized'] = SkillNormalizer.deduplicate_skills(
            list(source_skills) + inferred_skills
        )
        
        # Step 6: Lightweight title enrichment (NLP module can override later)
        transformed['title_normalized'] = TitleEnricher.normalize_title(
            transformed.get('title_raw', '')
        )
        transformed['job_family'] = TitleEnricher.infer_job_family(
            transformed['title_normalized']
        )
        transformed['seniority_level'] = TitleEnricher.infer_seniority(
            transformed['title_normalized']
        )
        
        return transformed
    
    def transform_all(self, records: List[Dict[str, Any]], 
                     deduplicate: bool = True) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Transform all records through full cleaning pipeline.
        
        Args:
            records: List of records from extract stage
            deduplicate: Whether to deduplicate records (default: True)
        
        Returns:
            Tuple of (transformed_records, stats)
        """
        logger.info(f"Starting transform of {len(records)} records...")
        
        # Step 1: Transform each record
        transformed = []
        for i, record in enumerate(records):
            try:
                transformed_record = self.transform_record(record)
                transformed.append(transformed_record)
            except Exception as e:
                logger.warning(f"Error transforming record {i}: {str(e)[:100]}")
        
        logger.info(f"Transformed {len(transformed)} records")
        
        # Step 2: Deduplicate if requested
        stats = {'total_transformed': len(transformed)}
        if deduplicate:
            transformed, dedup_stats = RecordDeduplicator.deduplicate_intra_source(transformed)
            stats.update(dedup_stats)
        
        # Step 3: Collect data quality stats
        stats['data_quality'] = self._calculate_quality_metrics(transformed)
        
        logger.info(f"Transform complete: {stats}")
        
        return transformed, stats
    
    @staticmethod
    def _calculate_quality_metrics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate data quality metrics on transformed records."""
        if not records:
            return {}
        
        metrics = {
            'total_records': len(records),
            'description_clean_coverage': 0,
            'location_parsed_coverage': 0,
            'salary_extracted_coverage': 0,
            'skills_available_coverage': 0,
        }
        
        for record in records:
            if record.get('description_clean'):
                metrics['description_clean_coverage'] += 1
            if record.get('location_city') or record.get('location_country'):
                metrics['location_parsed_coverage'] += 1
            if record.get('salary_min_extracted') or record.get('salary_max_extracted'):
                metrics['salary_extracted_coverage'] += 1
            if record.get('skills_normalized'):
                metrics['skills_available_coverage'] += 1
        
        # Convert to percentages
        total = len(records)
        for key in ['description_clean_coverage', 'location_parsed_coverage', 
                    'salary_extracted_coverage', 'skills_available_coverage']:
            metrics[f"{key}_pct"] = (metrics[key] / total * 100) if total > 0 else 0
        
        return metrics


def transform_records(records: List[Dict[str, Any]], 
                     deduplicate: bool = True) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Convenience function to transform records in one call.
    
    Args:
        records: List of normalized records from extract stage
        deduplicate: Whether to deduplicate intra-source
    
    Returns:
        Tuple of (transformed_records, stats)
    """
    transformer = BronzeTransformer()
    return transformer.transform_all(records, deduplicate=deduplicate)


if __name__ == '__main__':
    # Example usage
    import sys
    sys.path.insert(0, '/home/jovyan/project')
    
    from etl.extract import extract_and_validate
    
    print(f"\n{'='*60}")
    print("ETL Transform Module - Test Run")
    print(f"{'='*60}\n")
    
    try:
        # Get data from extract stage
        bronze_path = '/home/jovyan/data_lake/bronze' if sys.argv[1:] and sys.argv[1] else 'bronze'
        if len(sys.argv) > 1:
            bronze_path = sys.argv[1]
        
        print(f"Extracting from: {bronze_path}")
        records, extract_val = extract_and_validate(bronze_path)
        print(f"✓ Extracted: {extract_val['total_records']} records\n")
        
        # Transform
        print("Transforming records...")
        transformed, transform_stats = transform_records(records, deduplicate=True)
        
        print(f"\n✓ Transformation Complete:")
        print(f"  - Records processed: {transform_stats['total_transformed']}")
        print(f"  - Records after dedup: {transform_stats['deduplicated_count']}")
        print(f"  - Duplicates removed: {transform_stats['duplicates_removed']}")
        
        print(f"\n✓ Data Quality Metrics:")
        quality = transform_stats['data_quality']
        print(f"  - Description cleaned: {quality.get('description_clean_coverage_pct', 0):.1f}%")
        print(f"  - Location parsed: {quality.get('location_parsed_coverage_pct', 0):.1f}%")
        print(f"  - Salary extracted: {quality.get('salary_extracted_coverage_pct', 0):.1f}%")
        print(f"  - Skills available: {quality.get('skills_available_coverage_pct', 0):.1f}%")
        
        # Show sample transformed record
        if transformed:
            print(f"\n✓ Sample transformed record:")
            sample = transformed[0]
            print(f"  Source: {sample['source']}")
            print(f"  Title: {sample['title_raw']}")
            print(f"  Company: {sample['company_name']}")
            print(f"  Location: {sample['location_city']}, {sample['location_country']}")
            print(f"  Employment Type: {sample['employment_type_normalized']}")
            print(f"  Description preview: {sample['description_clean'][:100]}...")
            print(f"  Skills: {sample['skills_normalized'][:3]}...")
        
        print(f"\n{'='*60}\n")
        
    except Exception as e:
        logger.error(f"Transform failed: {e}", exc_info=True)
        sys.exit(1)
