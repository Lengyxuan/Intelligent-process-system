"""
Process case schema utilities for Zhijiang industrial mode.

This module normalizes process case metadata into a stable dictionary shape.
It does not perform retrieval, embedding, scoring, or generation.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict


STRING_FIELDS = (
    "case_id",
    "title",
    "source",
    "source_type",
    "material",
    "structure_type",
    "process_type",
    "equipment",
    "quality",
    "batch",
    "tolerance",
    "surface_roughness",
    "text",
    "created_at",
    "updated_at",
)

SCORE_DEFAULTS = {
    "expert_score": 0.5,
    "success_rate": 0.5,
    "usage_frequency": 0.0,
    "rework_rate": 0.0,
}

DEFAULT_STRING_VALUE = "unknown"
PROCESS_CASE_SOURCE_TYPE = "process_case"


def _now_iso() -> str:
    return datetime.now().isoformat()


def _normalize_string(value: Any) -> str:
    if value is None:
        return DEFAULT_STRING_VALUE
    text = str(value).strip()
    return text or DEFAULT_STRING_VALUE


def _clamp_score(value: Any, default: float) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = default
    return max(0.0, min(1.0, score))


def create_process_case(case_data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Return a normalized process case dictionary with safe defaults."""
    raw = case_data or {}
    now = _now_iso()

    process_case = {}
    for field in STRING_FIELDS:
        if field in ("created_at", "updated_at"):
            process_case[field] = _normalize_string(raw.get(field, now))
        elif field == "source_type":
            process_case[field] = PROCESS_CASE_SOURCE_TYPE
        elif field == "source":
            process_case[field] = _normalize_string(raw.get(field, "manual"))
        else:
            process_case[field] = _normalize_string(raw.get(field))

    for field, default in SCORE_DEFAULTS.items():
        process_case[field] = _clamp_score(raw.get(field, default), default)

    metadata = raw.get("metadata")
    process_case["metadata"] = metadata if isinstance(metadata, dict) else {}
    return process_case


def validate_process_case(case_data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Compatibility alias for callers that prefer validation naming."""
    return create_process_case(case_data)
