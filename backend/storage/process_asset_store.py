"""Local JSON store for uploaded process asset records."""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import DATA_DIR
from storage.process_asset_schema import create_process_asset


DEFAULT_PROCESS_ASSETS_PATH = DATA_DIR / "process_assets.json"


def _now_iso() -> str:
    return datetime.now().isoformat()


class ProcessAssetStore:
    """JSON-backed CRUD store for process asset metadata."""

    def __init__(self, storage_path: str | os.PathLike | None = None):
        self.storage_path = Path(storage_path) if storage_path else DEFAULT_PROCESS_ASSETS_PATH
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self._write_assets([])

    def add_asset(self, asset_data: Dict[str, Any]) -> Dict[str, Any]:
        assets = self._read_assets()
        asset = create_process_asset(asset_data)
        existing_index = self._find_asset_index(assets, asset["asset_id"])
        if existing_index is None:
            assets.append(asset)
        else:
            assets[existing_index] = asset
        self._write_assets(assets)
        return asset

    def get_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        target_id = str(asset_id)
        for asset in self._read_assets():
            if asset.get("asset_id") == target_id:
                return asset
        return None

    def list_assets(self) -> List[Dict[str, Any]]:
        return self._read_assets()

    def update_asset(self, asset_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        assets = self._read_assets()
        index = self._find_asset_index(assets, str(asset_id))
        if index is None:
            return None

        updated = dict(assets[index])
        updated.update(updates or {})
        updated["asset_id"] = str(asset_id)
        updated.setdefault("created_at", assets[index].get("created_at", _now_iso()))
        updated["updated_at"] = _now_iso()
        asset = create_process_asset(updated)
        assets[index] = asset
        self._write_assets(assets)
        return asset

    def delete_asset(self, asset_id: str) -> bool:
        assets = self._read_assets()
        original_count = len(assets)
        assets = [asset for asset in assets if asset.get("asset_id") != str(asset_id)]
        if len(assets) == original_count:
            return False
        self._write_assets(assets)
        return True

    def _find_asset_index(self, assets: List[Dict[str, Any]], asset_id: str) -> Optional[int]:
        for index, asset in enumerate(assets):
            if asset.get("asset_id") == asset_id:
                return index
        return None

    def _read_assets(self) -> List[Dict[str, Any]]:
        try:
            if not self.storage_path.exists() or self.storage_path.stat().st_size == 0:
                return []
            with self.storage_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return [create_process_asset(item) for item in data if isinstance(item, dict)]
            if isinstance(data, dict) and isinstance(data.get("assets"), list):
                return [create_process_asset(item) for item in data["assets"] if isinstance(item, dict)]
            print(f"[ProcessAssetStore] Unexpected storage shape: {self.storage_path}")
        except Exception as exc:
            print(f"[ProcessAssetStore] Failed to read {self.storage_path}: {exc}")
        return []

    def _write_assets(self, assets: List[Dict[str, Any]]) -> None:
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with self.storage_path.open("w", encoding="utf-8") as f:
                json.dump(assets, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            print(f"[ProcessAssetStore] Failed to write {self.storage_path}: {exc}")
