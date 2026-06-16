"""
Scoring engine for facility trust assessment.

This module is the single source of truth for scoring logic.
Used by both the batch script (one-time ingestion) and the app (on-demand re-score).
"""

import json
import re
from .keywords import CAPABILITY_KEYWORDS


def _parse_json_array(raw: str) -> list[str]:
    """Parse a JSON array string into a list of strings. Handles nulls and malformed data."""
    if not raw or raw == "null" or raw == "[]":
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item) for item in parsed if item]
        return [str(parsed)]
    except (json.JSONDecodeError, TypeError):
        return [raw] if isinstance(raw, str) else []


def _find_matches(text_items: list[str], keywords: list[str]) -> list[str]:
    """
    Find which text items contain any of the keywords.
    Returns the full text items that matched (these become citations).
    """
    citations = []
    for item in text_items:
        item_lower = item.lower()
        for kw in keywords:
            if kw.lower() in item_lower:
                citations.append(item.strip())
                break
    return citations


def _find_specialty_matches(specialties_raw: str, target_specialties: list[str]) -> list[str]:
    """Check if any target specialties appear in the specialties array."""
    items = _parse_json_array(specialties_raw)
    matched = []
    target_set = set(target_specialties)
    for item in items:
        if item in target_set:
            matched.append(f"Specialty: {item}")
    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for m in matched:
        if m not in seen:
            seen.add(m)
            deduped.append(m)
    return deduped


def _determine_trust_level(fields_matched: list[str], match_count: int, has_quantitative: bool) -> str:
    """
    Determine trust level based on evidence strength.

    Rules:
    - strong_evidence: 3+ fields matched, OR 5+ total hits, OR quantitative claim present with 2+ fields
    - partial_evidence: 2 fields matched, OR 3-4 total hits
    - weak_evidence: 1 field matched, OR 1-2 total hits
    - no_claim: zero matches
    """
    num_fields = len(fields_matched)

    if match_count == 0:
        return "no_claim"

    if num_fields >= 3 or match_count >= 5 or (has_quantitative and num_fields >= 2):
        return "strong_evidence"

    if num_fields >= 2 or match_count >= 3:
        return "partial_evidence"

    return "weak_evidence"


def _has_quantitative_claim(citations: list[str]) -> bool:
    """Check if any citation contains numbers indicating capacity (beds, units, etc.)."""
    quant_pattern = re.compile(r'\d+[\s-]*(bed|unit|theatre|ot |ventilator|machine|doctor)', re.IGNORECASE)
    for cite in citations:
        if quant_pattern.search(cite):
            return True
    return False


def score_facility(capability: str, texts: dict) -> dict:
    """
    Score a single facility for a single capability.

    Args:
        capability: One of "ICU", "Maternity", "Emergency", "Oncology", "Trauma", "NICU"
        texts: Dict with keys: "capability", "procedure", "equipment", "specialties", "description"
               Values are raw strings (JSON arrays or plain text) as stored in the source table.

    Returns:
        {
            "trust_level": "strong_evidence" | "partial_evidence" | "weak_evidence" | "no_claim",
            "evidence_citations": [...],  # list of quoted text snippets
            "fields_matched": [...],      # which fields had hits
            "match_count": int            # total number of keyword hits
        }
    """
    if capability not in CAPABILITY_KEYWORDS:
        raise ValueError(f"Unknown capability: {capability}. Must be one of {list(CAPABILITY_KEYWORDS.keys())}")

    keywords_by_field = CAPABILITY_KEYWORDS[capability]
    all_citations = []
    fields_matched = []
    total_match_count = 0

    # Score text fields (capability, procedure, equipment, description)
    for field_name in ["capability", "procedure", "equipment", "description"]:
        raw_value = texts.get(field_name, "")
        if not raw_value or raw_value == "null":
            continue

        field_keywords = keywords_by_field.get(field_name, [])
        if not field_keywords:
            continue

        # Parse: description is plain text, others are JSON arrays
        if field_name == "description":
            items = [raw_value] if raw_value else []
        else:
            items = _parse_json_array(raw_value)

        matches = _find_matches(items, field_keywords)
        if matches:
            fields_matched.append(field_name)
            total_match_count += len(matches)
            all_citations.extend(matches)

    # Score specialties (exact match, not keyword search)
    specialties_raw = texts.get("specialties", "")
    specialty_keywords = keywords_by_field.get("specialties", [])
    if specialties_raw and specialties_raw != "null" and specialty_keywords:
        specialty_matches = _find_specialty_matches(specialties_raw, specialty_keywords)
        if specialty_matches:
            fields_matched.append("specialties")
            total_match_count += len(specialty_matches)
            all_citations.extend(specialty_matches)

    # Determine trust level
    has_quantitative = _has_quantitative_claim(all_citations)
    trust_level = _determine_trust_level(fields_matched, total_match_count, has_quantitative)

    # Deduplicate citations while preserving order
    seen = set()
    unique_citations = []
    for c in all_citations:
        if c not in seen:
            seen.add(c)
            unique_citations.append(c)

    return {
        "trust_level": trust_level,
        "evidence_citations": unique_citations,
        "fields_matched": fields_matched,
        "match_count": total_match_count,
    }


def score_facility_all_capabilities(texts: dict) -> dict[str, dict]:
    """
    Score a facility across all 6 capabilities at once.

    Args:
        texts: Same as score_facility

    Returns:
        Dict keyed by capability name, values are score results.
        {"ICU": {...}, "Maternity": {...}, ...}
    """
    results = {}
    for capability in CAPABILITY_KEYWORDS:
        results[capability] = score_facility(capability, texts)
    return results
