"""
Local JSON store for expert process review records.

Review records are operational audit data. They are stored separately from
process cases so rejected plans never enter the case library by accident.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import DATA_DIR
from storage.process_review_schema import create_process_review


DEFAULT_PROCESS_REVIEWS_PATH = DATA_DIR / "process_reviews.json"


def _now_iso() -> str:
    return datetime.now().isoformat()


class ProcessReviewStore:
    """JSON-backed CRUD store for process review records."""

    def __init__(self, storage_path: str | os.PathLike | None = None):
        self.storage_path = Path(storage_path) if storage_path else DEFAULT_PROCESS_REVIEWS_PATH
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self._write_reviews([])

    def add_review(self, review_data: Dict[str, Any]) -> Dict[str, Any]:
        reviews = self._read_reviews()
        review = create_process_review(review_data)
        existing_index = self._find_review_index(reviews, review["review_id"])
        if existing_index is None:
            reviews.append(review)
        else:
            reviews[existing_index] = review
        self._write_reviews(reviews)
        return review

    def get_review(self, review_id: str) -> Optional[Dict[str, Any]]:
        target_id = str(review_id)
        for review in self._read_reviews():
            if review.get("review_id") == target_id:
                return review
        return None

    def list_reviews(self) -> List[Dict[str, Any]]:
        return self._read_reviews()

    def update_review(self, review_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        reviews = self._read_reviews()
        index = self._find_review_index(reviews, str(review_id))
        if index is None:
            return None

        updated = dict(reviews[index])
        updated.update(updates or {})
        updated["review_id"] = str(review_id)
        updated.setdefault("created_at", reviews[index].get("created_at", _now_iso()))
        updated["updated_at"] = _now_iso()
        review = create_process_review(updated)
        reviews[index] = review
        self._write_reviews(reviews)
        return review

    def delete_review(self, review_id: str) -> bool:
        reviews = self._read_reviews()
        original_count = len(reviews)
        reviews = [review for review in reviews if review.get("review_id") != str(review_id)]
        if len(reviews) == original_count:
            return False
        self._write_reviews(reviews)
        return True

    def _find_review_index(self, reviews: List[Dict[str, Any]], review_id: str) -> Optional[int]:
        for index, review in enumerate(reviews):
            if review.get("review_id") == review_id:
                return index
        return None

    def _read_reviews(self) -> List[Dict[str, Any]]:
        try:
            if not self.storage_path.exists() or self.storage_path.stat().st_size == 0:
                return []
            with self.storage_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return [create_process_review(item) for item in data if isinstance(item, dict)]
            if isinstance(data, dict) and isinstance(data.get("reviews"), list):
                return [create_process_review(item) for item in data["reviews"] if isinstance(item, dict)]
            print(f"[ProcessReviewStore] Unexpected storage shape: {self.storage_path}")
        except Exception as exc:
            print(f"[ProcessReviewStore] Failed to read {self.storage_path}: {exc}")
        return []

    def _write_reviews(self, reviews: List[Dict[str, Any]]) -> None:
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with self.storage_path.open("w", encoding="utf-8") as f:
                json.dump(reviews, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            print(f"[ProcessReviewStore] Failed to write {self.storage_path}: {exc}")
