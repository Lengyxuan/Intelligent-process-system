"""
Local JSON store for structured process cases.

This store persists normalized process case metadata only. It intentionally
does not connect to FAISS, BM25, embeddings, retrieval, or process scoring.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import DATA_DIR
from storage.process_schema import create_process_case


DEFAULT_PROCESS_CASES_PATH = DATA_DIR / "process_cases.json"


def _now_iso() -> str:
    return datetime.now().isoformat()


class ProcessCaseStore:
    """JSON-backed CRUD store for process case metadata."""

    def __init__(self, storage_path: str | os.PathLike | None = None):
        self.storage_path = Path(storage_path) if storage_path else DEFAULT_PROCESS_CASES_PATH
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self._write_cases([])

    def add_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        cases = self._read_cases()
        data = dict(case_data or {})
        data["case_id"] = self._ensure_case_id(data.get("case_id"))
        now = _now_iso()
        data.setdefault("created_at", now)
        data["updated_at"] = data.get("updated_at") or data["created_at"]

        process_case = create_process_case(data)
        existing_index = self._find_case_index(cases, process_case["case_id"])
        if existing_index is None:
            cases.append(process_case)
        else:
            cases[existing_index] = process_case
        self._write_cases(cases)
        return process_case

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        target_id = str(case_id)
        for case in self._read_cases():
            if case.get("case_id") == target_id:
                return case
        return None

    def list_cases(self) -> List[Dict[str, Any]]:
        return self._read_cases()

    def update_case(self, case_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        cases = self._read_cases()
        index = self._find_case_index(cases, str(case_id))
        if index is None:
            return None

        updated = dict(cases[index])
        updated.update(updates or {})
        updated["case_id"] = str(case_id)
        updated.setdefault("created_at", cases[index].get("created_at", _now_iso()))
        updated["updated_at"] = _now_iso()
        updated_case = create_process_case(updated)
        cases[index] = updated_case
        self._write_cases(cases)
        return updated_case

    def delete_case(self, case_id: str) -> bool:
        cases = self._read_cases()
        original_count = len(cases)
        cases = [case for case in cases if case.get("case_id") != str(case_id)]
        if len(cases) == original_count:
            return False
        self._write_cases(cases)
        return True

    def _ensure_case_id(self, case_id: Any) -> str:
        case_id_text = str(case_id).strip() if case_id is not None else ""
        return case_id_text or f"CASE_{uuid.uuid4().hex[:12].upper()}"

    def _find_case_index(self, cases: List[Dict[str, Any]], case_id: str) -> Optional[int]:
        for index, case in enumerate(cases):
            if case.get("case_id") == case_id:
                return index
        return None

    def _read_cases(self) -> List[Dict[str, Any]]:
        try:
            if not self.storage_path.exists() or self.storage_path.stat().st_size == 0:
                return []
            with self.storage_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return [create_process_case(item) for item in data if isinstance(item, dict)]
            if isinstance(data, dict) and isinstance(data.get("cases"), list):
                return [create_process_case(item) for item in data["cases"] if isinstance(item, dict)]
            print(f"[ProcessCaseStore] Unexpected storage shape: {self.storage_path}")
        except Exception as exc:
            print(f"[ProcessCaseStore] Failed to read {self.storage_path}: {exc}")
        return []

    def _write_cases(self, cases: List[Dict[str, Any]]) -> None:
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with self.storage_path.open("w", encoding="utf-8") as f:
                json.dump(cases, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            print(f"[ProcessCaseStore] Failed to write {self.storage_path}: {exc}")
