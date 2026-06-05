"""First-pass file type routing for Zhijiang process assets.

This module only classifies files by filename extension, MIME type, and basic
metadata. It intentionally does not inspect file contents.
"""
from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any, Dict


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
PDF_EXTENSIONS = {".pdf"}
CAD_3D_EXTENSIONS = {".step", ".stp", ".iges", ".igs", ".stl", ".obj", ".3mf"}
CAD_AMBIGUOUS_EXTENSIONS = {".dxf", ".dwg"}
DOCUMENT_EXTENSIONS = {".txt", ".md", ".doc", ".docx", ".xls", ".xlsx", ".csv"}


class FileTypeRouter:
    """Route uploaded process assets to a conservative first-pass asset type."""

    def classify(
        self,
        filename: str,
        mime_type: str | None = None,
        file_size: int | None = None,
    ) -> Dict[str, Any]:
        original_filename = str(filename or "")
        extension = Path(original_filename).suffix.lower()
        normalized_mime = (mime_type or mimetypes.guess_type(original_filename)[0] or "").strip()

        result: Dict[str, Any] = {
            "filename": original_filename,
            "extension": extension,
            "mime_type": normalized_mime,
            "file_size": file_size,
            "asset_type": "unsupported",
            "asset_category": "unknown",
            "content_route": "unsupported",
            "is_supported": False,
            "confidence": 0.0,
            "manual_confirmation_required": True,
            "warnings": [],
            "next_steps": [],
        }

        if extension in IMAGE_EXTENSIONS:
            result.update(
                {
                    "asset_type": "image_candidate",
                    "asset_category": "image",
                    "content_route": "manual_confirm_or_future_image_inspection",
                    "is_supported": True,
                    "confidence": 0.7,
                    "next_steps": ["后续需要进行图像内容检查或人工确认"],
                }
            )
            return result

        if extension in PDF_EXTENSIONS:
            result.update(
                {
                    "asset_type": "pdf_candidate",
                    "asset_category": "document",
                    "content_route": "needs_pdf_rasterization_or_manual_confirm",
                    "is_supported": True,
                    "confidence": 0.75,
                    "next_steps": ["后续需要进行 PDF 页面解析或人工确认"],
                }
            )
            return result

        if extension in CAD_3D_EXTENSIONS:
            result.update(
                {
                    "asset_type": "cad_3d_candidate",
                    "asset_category": "cad",
                    "content_route": "manual_confirm_or_future_cad_parser",
                    "is_supported": True,
                    "confidence": 0.75,
                    "next_steps": ["后续需要进行 CAD 解析或人工确认"],
                }
            )
            return result

        if extension in CAD_AMBIGUOUS_EXTENSIONS:
            result.update(
                {
                    "asset_type": "cad_2d_or_3d_candidate",
                    "asset_category": "cad",
                    "content_route": "manual_confirm_required",
                    "is_supported": True,
                    "confidence": 0.65,
                    "next_steps": ["后续需要人工确认 CAD 文件是 2D 图纸还是 3D 模型"],
                }
            )
            return result

        if extension in DOCUMENT_EXTENSIONS:
            result.update(
                {
                    "asset_type": "process_document_candidate",
                    "asset_category": "document",
                    "content_route": "manual_confirm_or_future_text_extraction",
                    "is_supported": True,
                    "confidence": 0.7,
                    "next_steps": ["后续需要进行文本提取或人工确认"],
                }
            )
            return result

        result["warnings"] = ["不支持的文件类型"]
        result["next_steps"] = ["请更换为 PNG、JPG、PDF、CAD 或常见文档格式"]
        return result
