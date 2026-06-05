"""Process asset schema utilities for uploaded manufacturing files."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict


DEFAULT_TEXT = "unknown"


def _now_iso() -> str:
    return datetime.now().isoformat()


def _text(value: Any, default: str = DEFAULT_TEXT) -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    return bool(value)


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def create_process_asset(asset_data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Return a normalized process asset record with stable defaults."""
    raw = asset_data or {}
    now = _now_iso()
    return {
        "asset_id": _text(raw.get("asset_id"), f"ASSET_{uuid.uuid4().hex[:12].upper()}"),
        "filename": _text(raw.get("filename"), ""),
        "saved_path": _text(raw.get("saved_path"), ""),
        "extension": _text(raw.get("extension"), ""),
        "mime_type": _text(raw.get("mime_type"), ""),
        "file_size": _int_or_none(raw.get("file_size")),
        "asset_type": _text(raw.get("asset_type")),
        "asset_category": _text(raw.get("asset_category")),
        "content_route": _text(raw.get("content_route")),
        "manual_confirmation_required": _bool(raw.get("manual_confirmation_required"), True),
        "confirmed_type": _text(raw.get("confirmed_type")),
        "confirmed_view_type": _text(raw.get("confirmed_view_type")),
        "linked_case_id": raw.get("linked_case_id"),
        "linked_model_id": raw.get("linked_model_id"),
        "created_at": _text(raw.get("created_at"), now),
        "updated_at": _text(raw.get("updated_at"), now),
        "metadata": _dict(raw.get("metadata")),
    }


def validate_process_asset(asset_data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Compatibility alias for callers that prefer validation naming."""
    return create_process_asset(asset_data)
