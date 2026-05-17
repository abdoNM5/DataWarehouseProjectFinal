"""
Skills Extractor — extracts skills from job descriptions using
keyword matching with word boundaries + alias resolution.
"""

import re
from nlp.skills_taxonomy import SKILLS_BY_CATEGORY, SKILL_ALIASES


def _build_pattern(term: str) -> re.Pattern:
    """Build a regex pattern with word boundaries for a skill term."""
    escaped = re.escape(term)
    # Single/two-char skills (e.g. "R", "Go") need strict letter boundaries
    # to avoid matching inside words like "Required" or "Google"
    if len(term) <= 2:
        return re.compile(rf'(?<![a-zA-Z]){escaped}(?![a-zA-Z])', re.IGNORECASE)
    return re.compile(rf'\b{escaped}\b', re.IGNORECASE)


# ── Pre-compile all patterns at module load ──

# canonical_skill → (pattern, canonical_skill)
_SKILL_PATTERNS: dict[str, re.Pattern] = {}
for _cat, _skills in SKILLS_BY_CATEGORY.items():
    for _skill in _skills:
        _SKILL_PATTERNS[_skill] = _build_pattern(_skill)

# alias_key → (pattern, canonical_skill)
_ALIAS_PATTERNS: dict[str, tuple[re.Pattern, str]] = {}
for _alias, _canonical in SKILL_ALIASES.items():
    _ALIAS_PATTERNS[_alias] = (_build_pattern(_alias), _canonical)


def extract_skills(description: str) -> list[tuple[str, float]]:
    """
    Extract skills from a job description using keyword + alias matching.

    Args:
        description: cleaned job description text

    Returns:
        Sorted list of (canonical_skill_name, confidence_score) tuples.
        confidence_score = 1.0 for exact keyword match.
    """
    if not description or not description.strip():
        return []

    found: dict[str, float] = {}

    # 1. Check canonical skill names
    for canonical, pattern in _SKILL_PATTERNS.items():
        if pattern.search(description):
            found[canonical] = 1.0

    # 2. Check aliases (only if canonical not already found)
    for alias_key, (pattern, canonical) in _ALIAS_PATTERNS.items():
        if canonical not in found and pattern.search(description):
            found[canonical] = 1.0

    # 3. Sort alphabetically for consistent output
    return sorted(found.items(), key=lambda x: x[0])
