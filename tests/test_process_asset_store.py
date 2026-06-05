import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from storage.process_asset_store import ProcessAssetStore


def _asset(**overrides):
    data = {
        "filename": "drawing.png",
        "saved_path": "runtime/arpm-app/uploads/process_assets/ASSET_001_drawing.png",
        "extension": ".png",
        "mime_type": "image/png",
        "file_size": 123,
        "asset_type": "image_candidate",
        "asset_category": "image",
        "content_route": "manual_confirm_or_future_image_inspection",
        "manual_confirmation_required": True,
    }
    data.update(overrides)
    return data


def test_add_asset_saves_asset(tmp_path):
    store = ProcessAssetStore(tmp_path / "process_assets.json")

    asset = store.add_asset(_asset())

    assert asset["asset_id"].startswith("ASSET_")
    assert asset["filename"] == "drawing.png"
    assert asset["asset_type"] == "image_candidate"
    assert asset["confirmed_type"] == "unknown"
    assert store.storage_path.exists()


def test_list_get_update_and_delete_asset(tmp_path):
    store = ProcessAssetStore(tmp_path / "process_assets.json")
    asset = store.add_asset(_asset(asset_id="ASSET_001"))

    assert store.list_assets()[0]["asset_id"] == "ASSET_001"
    assert store.get_asset(asset["asset_id"])["filename"] == "drawing.png"

    updated = store.update_asset(
        "ASSET_001",
        {"confirmed_type": "engineering_drawing", "confirmed_view_type": "front"},
    )

    assert updated["confirmed_type"] == "engineering_drawing"
    assert updated["confirmed_view_type"] == "front"
    assert updated["asset_type"] == "image_candidate"
    assert store.delete_asset("ASSET_001") is True
    assert store.get_asset("ASSET_001") is None
    assert store.delete_asset("ASSET_001") is False


def test_empty_file_does_not_crash(tmp_path):
    storage_path = tmp_path / "process_assets.json"
    storage_path.write_text("", encoding="utf-8")
    store = ProcessAssetStore(storage_path)

    assert store.list_assets() == []


def test_corrupted_file_does_not_crash(tmp_path):
    storage_path = tmp_path / "process_assets.json"
    storage_path.write_text("{bad json", encoding="utf-8")
    store = ProcessAssetStore(storage_path)

    assert store.list_assets() == []


def test_store_can_read_assets_wrapper_shape(tmp_path):
    storage_path = tmp_path / "process_assets.json"
    storage_path.write_text(
        json.dumps({"assets": [_asset(asset_id="ASSET_001")]}, ensure_ascii=False),
        encoding="utf-8",
    )
    store = ProcessAssetStore(storage_path)

    assert store.list_assets()[0]["asset_id"] == "ASSET_001"
