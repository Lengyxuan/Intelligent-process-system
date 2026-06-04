"""
Review schema utilities for Zhijiang expert review feedback.

The schema is intentionally dictionary-based to match the existing process case
storage style and keep the review loop independent from the original ARPM path.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict


VALID_REVIEW_STATUSES = {"pass", "modify", "reject"}


def _now_iso() -> str:
    return datetime.now().isoformat()


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list:
    return value if isinstance(value, list) else []


def create_process_review(review_data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Return a normalized review record or raise ValueError for invalid status."""
    raw = review_data or {}
    status = _text(raw.get("status")).lower()
    if status not in VALID_REVIEW_STATUSES:
        raise ValueError(f"invalid review status: {status or 'missing'}")

    now = _now_iso()
    return {
        "review_id": _text(raw.get("review_id"), f"REVIEW_{uuid.uuid4().hex[:12].upper()}"),
        "plan_id": _text(raw.get("plan_id"), f"PLAN_{uuid.uuid4().hex[:12].upper()}"),
        "status": status,
        "reviewer": _text(raw.get("reviewer"), "expert"),
        "comments": _text(raw.get("comments"), ""),
        "raw_query": _text(raw.get("raw_query"), ""),
        "requirement_vector": _dict(raw.get("requirement_vector")),
        "process_plan": _dict(raw.get("process_plan")),
        "modified_plan": _dict(raw.get("modified_plan")),
        "process_evaluation": _dict(raw.get("process_evaluation")),
        "reference_cases": _list(raw.get("reference_cases")),
        "feedback_case_id": raw.get("feedback_case_id"),
        "created_at": _text(raw.get("created_at"), now),
        "updated_at": _text(raw.get("updated_at"), now),
        "metadata": _dict(raw.get("metadata")),
    }


def validate_process_review(review_data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Compatibility alias for callers that prefer validation naming."""
    return create_process_review(review_data)
