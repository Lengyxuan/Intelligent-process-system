"""
Process case retriever adapter for Zhijiang industrial mode.

This module retrieves structured process cases from the PR4 local case store.
It intentionally avoids ProcessSim, case quality scoring, generation, and file
recognition. The current implementation uses deterministic field matching plus
a local BM25 fallback over process case text. text2vec/FAISS can be connected in
a later PR without changing the original ARPM retriever.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from storage.process_case_store import ProcessCaseStore
from utils.bm25_plus import BM25PlusScorer


CASE_TEXT_FIELDS = (
    "title",
    "material",
    "structure_type",
    "process_type",
    "equipment",
    "quality",
    "batch",
    "tolerance",
    "surface_roughness",
    "text",
)

MATCH_FIELDS = {
    "material": ("material",),
    "equipment": ("equipment",),
    "process_type": ("process_type",),
    "batch": ("batch",),
    "quality": ("quality", "tolerance", "surface_roughness"),
    "feature": ("structure_type", "title", "text"),
}

FIELD_WEIGHTS = {
    "material": 0.22,
    "equipment": 0.18,
    "process_type": 0.22,
    "batch": 0.12,
    "quality": 0.14,
    "feature": 0.16,
}


def _normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text.replace("cnc", "数控").replace(" ", "").replace("\n", "")


def _known(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(text) and text.lower() != "unknown"


def _contains_either(left: str, right: str) -> bool:
    if not left or not right:
        return False
    return left in right or right in left


class ProcessRetriever:
    """Retrieve Top-K process cases from the local process case store."""

    def __init__(self, case_store: ProcessCaseStore | None = None, top_k: int = 5):
        self.case_store = case_store or ProcessCaseStore()
        self.top_k = max(1, int(top_k or 5))

    def retrieve(
        self,
        process_query: str,
        requirement_vector: Dict[str, Any] | None = None,
        top_k: int | None = None,
    ) -> Dict[str, Any]:
        """Return ranked process case candidates for a process query."""
        query = str(process_query or "")
        vector = requirement_vector or {}
        limit = max(1, int(top_k or self.top_k))
        cases = self.case_store.list_cases()

        response = {
            "retriever_enabled": True,
            "query": query,
            "top_k": limit,
            "total_cases": len(cases),
            "results": [],
            "retrieval_status": {
                "text_vector": "pending",
                "bm25": "fallback",
                "process_sim": "pending",
            },
        }

        if not cases:
            response["note"] = "no process cases available"
            return response

        bm25_scores = self._bm25_scores(query, vector, cases)
        ranked = []
        for index, case in enumerate(cases):
            field_score, matched_fields = self._field_score(case, vector, query)
            bm25_score = bm25_scores.get(index, 0.0)
            keyword_score = self._clamp(field_score * 0.75 + bm25_score * 0.25)
            if keyword_score <= 0 and not query.strip() and not self._has_known_requirements(vector):
                continue
            ranked.append(
                {
                    "case": case,
                    "score": keyword_score,
                    "keyword_score": keyword_score,
                    "semantic_score": 0.0,
                    "matched_fields": matched_fields,
                }
            )

        ranked.sort(
            key=lambda item: (
                item["score"],
                item["case"].get("expert_score", 0.0),
                item["case"].get("success_rate", 0.0),
                item["case"].get("usage_frequency", 0.0),
            ),
            reverse=True,
        )

        response["results"] = [
            self._format_result(rank, item)
            for rank, item in enumerate(ranked[:limit], start=1)
        ]
        return response

    def _field_score(
        self,
        case: Dict[str, Any],
        requirement_vector: Dict[str, Any],
        process_query: str,
    ) -> Tuple[float, Dict[str, bool]]:
        matched_fields = {}
        total_weight = 0.0
        matched_weight = 0.0
        normalized_query = _normalize_text(process_query)

        for field, case_fields in MATCH_FIELDS.items():
            query_value = requirement_vector.get(field)
            values_to_match = []
            if _known(query_value):
                values_to_match.append(_normalize_text(query_value))
            if not values_to_match and normalized_query:
                values_to_match.append(normalized_query)

            case_texts = [_normalize_text(case.get(case_field)) for case_field in case_fields]
            matched = any(
                _contains_either(query_text, case_text)
                for query_text in values_to_match
                for case_text in case_texts
            )
            matched_fields[field] = matched

            weight = FIELD_WEIGHTS[field]
            total_weight += weight
            if matched:
                matched_weight += weight

        if total_weight <= 0:
            return 0.0, matched_fields
        return self._clamp(matched_weight / total_weight), matched_fields

    def _bm25_scores(
        self,
        process_query: str,
        requirement_vector: Dict[str, Any],
        cases: List[Dict[str, Any]],
    ) -> Dict[int, float]:
        documents = [self._case_document(case) for case in cases]
        query = self._bm25_query(process_query, requirement_vector)
        if not query.strip() or not documents:
            return {}

        scorer = BM25PlusScorer()
        scorer.index_documents(documents)
        raw_results = scorer.search(query, top_k=len(documents))
        if not raw_results:
            return {}

        max_score = max(result.get("score", 0.0) for result in raw_results)
        if max_score <= 0:
            return {}
        return {
            int(result["index"]): self._clamp(float(result.get("score", 0.0)) / max_score)
            for result in raw_results
        }

    def _bm25_query(self, process_query: str, requirement_vector: Dict[str, Any]) -> str:
        parts = [str(process_query or "")]
        for field in ("material", "batch", "feature", "equipment", "quality", "process_type"):
            value = requirement_vector.get(field)
            if _known(value):
                parts.append(str(value))
        return " ".join(parts)

    def _case_document(self, case: Dict[str, Any]) -> str:
        return " ".join(str(case.get(field, "")) for field in CASE_TEXT_FIELDS)

    def _format_result(self, rank: int, item: Dict[str, Any]) -> Dict[str, Any]:
        case = item["case"]
        text = str(case.get("text", ""))
        preview = text[:80]
        if len(text) > 80:
            preview += "..."
        return {
            "rank": rank,
            "case_id": case.get("case_id", "unknown"),
            "title": case.get("title", "unknown"),
            "source_type": case.get("source_type", "process_case"),
            "material": case.get("material", "unknown"),
            "structure_type": case.get("structure_type", "unknown"),
            "process_type": case.get("process_type", "unknown"),
            "equipment": case.get("equipment", "unknown"),
            "score": round(float(item["score"]), 4),
            "semantic_score": round(float(item["semantic_score"]), 4),
            "keyword_score": round(float(item["keyword_score"]), 4),
            "matched_fields": item["matched_fields"],
            "text_preview": preview,
        }

    def _has_known_requirements(self, requirement_vector: Dict[str, Any]) -> bool:
        return any(_known(requirement_vector.get(field)) for field in MATCH_FIELDS)

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, float(value)))
