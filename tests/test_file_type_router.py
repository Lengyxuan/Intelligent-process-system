import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from core.file_type_router import FileTypeRouter


def _classify(filename, mime_type=None):
    return FileTypeRouter().classify(filename, mime_type, 123)


def test_png_and_jpg_are_image_candidates_not_engineering_drawings():
    for filename in ("drawing.png", "photo.jpg", "render.jpeg"):
        result = _classify(filename)

        assert result["asset_type"] == "image_candidate"
        assert result["asset_category"] == "image"
        assert result["manual_confirmation_required"] is True
        assert result["asset_type"] != "engineering_drawing"
        assert "2d" not in result["asset_type"].lower()


def test_pdf_is_pdf_candidate_not_engineering_drawing():
    result = _classify("process.pdf", "application/pdf")

    assert result["asset_type"] == "pdf_candidate"
    assert result["asset_category"] == "document"
    assert result["manual_confirmation_required"] is True
    assert result["asset_type"] != "engineering_drawing"


def test_step_stl_obj_are_3d_cad_candidates():
    for filename in ("part.step", "part.stp", "model.stl", "mesh.obj", "part.iges", "part.igs", "part.3mf"):
        result = _classify(filename)

        assert result["asset_type"] == "cad_3d_candidate"
        assert result["asset_category"] == "cad"


def test_dxf_and_dwg_are_ambiguous_cad_candidates_not_hard_3d():
    for filename in ("drawing.dxf", "model.dwg"):
        result = _classify(filename)

        assert result["asset_type"] == "cad_2d_or_3d_candidate"
        assert result["asset_category"] == "cad"
        assert result["content_route"] == "manual_confirm_required"
        assert result["asset_type"] != "cad_3d_candidate"
        assert result["asset_type"] != "engineering_drawing"


def test_text_document_extensions_are_process_document_candidates():
    for filename in ("note.txt", "guide.md", "case.doc", "case.docx", "table.xls", "table.xlsx", "data.csv"):
        result = _classify(filename)

        assert result["asset_type"] == "process_document_candidate"
        assert result["asset_category"] == "document"


def test_unknown_extension_is_unsupported():
    result = _classify("unknown.exe", "application/octet-stream")

    assert result["asset_type"] == "unsupported"
    assert result["asset_category"] == "unknown"
    assert result["is_supported"] is False
    assert result["warnings"]
