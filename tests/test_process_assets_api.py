import io
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def _client(tmp_path, monkeypatch):
    import app
    import api.process_assets as process_assets_api
    from storage.process_asset_store import ProcessAssetStore

    monkeypatch.setattr(process_assets_api, "DEFAULT_PROCESS_ASSET_UPLOAD_DIR", tmp_path / "uploads")

    def _temporary_store():
        return ProcessAssetStore(tmp_path / "process_assets.json")

    monkeypatch.setattr(process_assets_api, "ProcessAssetStore", _temporary_store)
    return app.app.test_client()


def _upload(client, filename, content=b"data"):
    return client.post(
        "/api/process/assets/upload",
        data={"file": (io.BytesIO(content), filename)},
        content_type="multipart/form-data",
    )


def test_upload_png_returns_image_candidate_without_recognition_fields(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    response = _upload(client, "drawing.png", b"\x89PNG\r\n")
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["classification"]["asset_type"] == "image_candidate"
    assert data["asset"]["asset_type"] == "image_candidate"
    assert data["asset"]["confirmed_type"] == "unknown"
    assert "view_embedding" not in data["asset"]
    assert "drawing_recognition" not in data["asset"]


def test_upload_pdf_returns_pdf_candidate(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    response = _upload(client, "process.pdf", b"%PDF-1.4")
    data = response.get_json()

    assert response.status_code == 200
    assert data["classification"]["asset_type"] == "pdf_candidate"
    assert data["classification"]["asset_type"] != "engineering_drawing"


def test_upload_step_returns_cad_3d_candidate(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    response = _upload(client, "part.step", b"ISO-10303")
    data = response.get_json()

    assert response.status_code == 200
    assert data["classification"]["asset_type"] == "cad_3d_candidate"


def test_upload_unsupported_extension_records_unsupported(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    response = _upload(client, "unknown.exe", b"MZ")
    data = response.get_json()

    assert response.status_code == 200
    assert data["classification"]["asset_type"] == "unsupported"
    assert data["classification"]["is_supported"] is False
    assert data["asset"]["asset_type"] == "unsupported"


def test_confirm_updates_manual_fields_but_keeps_original_asset_type(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    uploaded = _upload(client, "drawing.png").get_json()
    asset_id = uploaded["asset"]["asset_id"]

    response = client.patch(
        f"/api/process/assets/{asset_id}/confirm",
        json={"confirmed_type": "engineering_drawing", "confirmed_view_type": "front"},
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["asset"]["confirmed_type"] == "engineering_drawing"
    assert data["asset"]["confirmed_view_type"] == "front"
    assert data["asset"]["asset_type"] == "image_candidate"
    assert "view_embedding" not in data["asset"]
    assert "drawing_recognition" not in data["asset"]
