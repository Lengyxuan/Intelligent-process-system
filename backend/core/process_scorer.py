"""
Process similarity and quality scoring for Zhijiang industrial mode.

This module scores already-retrieved process case candidates. It does not
generate process plans, evaluate generated plans, call LLMs, or touch the
original ARPM retrieval stack.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List


PROCESS_SIM_WEIGHTS = {
    "material": 0.25,
    "structure_type": 0.20,
    "process_type": 0.20,
    "equipment": 0.15,
    "quality": 0.10,
    "batch": 0.10,
}

CASE_QUALITY_WEIGHTS = {
    "expert_score": 0.35,
    "success_rate": 0.35,
    "usage_frequency": 0.20,
    "rework_rate": 0.10,
}

FINAL_SCORE_WEIGHTS = {
    "retrieval_score": 0.40,
    "process_sim": 0.40,
    "fresh_quality": 0.20,
}

FRESH_QUALITY_RHO = 0.35

SYNONYMS = {
    "cnc": "数控",
    "數控": "数控",
    "铣": "铣削",
    "铣削加工": "铣削",
    "数控铣削": "数控铣削",
    "cnc铣削": "数控铣削",
    "cnc铣": "数控铣削",
    "高精密": "高精度",
    "一般精密": "一般精度",
}


def _clamp(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(0.0, min(1.0, number))


def _known(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(text) and text.lower() != "unknown"


def _normalize(value: Any) -> str:
    text = str(value or "").strip().lower().replace(" ", "")
    for source, target in SYNONYMS.items():
        text = text.replace(source, target)
    return text


class ProcessScorer:
    """Score process candidates with process similarity and quality signals."""

    def score_case(
        self,
        requirement_vector: Dict[str, Any] | None,
        case: Dict[str, Any],
        retrieval_score: float = 0.0,
    ) -> Dict[str, Any]:
        vector = requirement_vector or {}
        process_sim_details = self.process_sim_details(vector, case)
        process_sim = self.weighted_process_sim(process_sim_details)
        case_quality_details = self.case_quality_details(case)
        case_quality = self.case_quality(case_quality_details)
        time_decay = self.time_decay(case)
        fresh_quality = self.fresh_quality(time_decay, case_quality)
        normalized_retrieval = _clamp(retrieval_score)
        final_score = self.final_score(normalized_retrieval, process_sim, fresh_quality)

        return {
            "process_sim": round(process_sim, 4),
            "process_sim_details": {
                key: round(value, 4) for key, value in process_sim_details.items()
            },
            "case_quality": round(case_quality, 4),
            "case_quality_details": case_quality_details,
            "time_decay": round(time_decay, 4),
            "fresh_quality": round(fresh_quality, 4),
            "final_score": round(final_score, 4),
            "score_breakdown": {
                "retrieval_score": round(normalized_retrieval, 4),
                "process_sim": round(process_sim, 4),
                "fresh_quality": round(fresh_quality, 4),
            },
        }

    def score_results(
        self,
        requirement_vector: Dict[str, Any] | None,
        retrieval_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        scored = []
        for result in retrieval_results:
            retrieval_score = result.get("score", result.get("keyword_score", 0.0))
            scored_result = dict(result)
            scored_result.update(
                self.score_case(requirement_vector, result, retrieval_score=retrieval_score)
            )
            scored.append(scored_result)
        scored.sort(key=lambda item: item.get("final_score", 0.0), reverse=True)
        for rank, result in enumerate(scored, start=1):
            result["rank"] = rank
        return scored

    def process_sim_details(
        self,
        requirement_vector: Dict[str, Any],
        case: Dict[str, Any],
    ) -> Dict[str, float]:
        return {
            "material": self.field_similarity(requirement_vector.get("material"), case.get("material")),
            "structure_type": self.field_similarity(
                requirement_vector.get("feature") or requirement_vector.get("structure_type"),
                case.get("structure_type"),
            ),
            "process_type": self.field_similarity(
                requirement_vector.get("process_type"),
                case.get("process_type"),
            ),
            "equipment": self.field_similarity(requirement_vector.get("equipment"), case.get("equipment")),
            "quality": self.field_similarity(requirement_vector.get("quality"), case.get("quality")),
            "batch": self.field_similarity(requirement_vector.get("batch"), case.get("batch")),
        }

    def weighted_process_sim(self, details: Dict[str, float]) -> float:
        return _clamp(
            sum(details.get(field, 0.0) * weight for field, weight in PROCESS_SIM_WEIGHTS.items())
        )

    def field_similarity(self, requirement_value: Any, case_value: Any) -> float:
        if not _known(requirement_value) or not _known(case_value):
            return 0.5

        req = _normalize(requirement_value)
        case = _normalize(case_value)
        if req == case:
            return 1.0
        if req in case or case in req:
            return 0.8
        return 0.0

    def case_quality_details(self, case: Dict[str, Any]) -> Dict[str, float]:
        return {
            "expert_score": _clamp(case.get("expert_score", 0.5), 0.5),
            "success_rate": _clamp(case.get("success_rate", 0.5), 0.5),
            "usage_frequency": _clamp(case.get("usage_frequency", 0.0), 0.0),
            "rework_rate": _clamp(case.get("rework_rate", 0.0), 0.0),
        }

    def case_quality(self, details: Dict[str, float]) -> float:
        score = (
            CASE_QUALITY_WEIGHTS["expert_score"] * details.get("expert_score", 0.5)
            + CASE_QUALITY_WEIGHTS["success_rate"] * details.get("success_rate", 0.5)
            + CASE_QUALITY_WEIGHTS["usage_frequency"] * details.get("usage_frequency", 0.0)
            - CASE_QUALITY_WEIGHTS["rework_rate"] * details.get("rework_rate", 0.0)
        )
        return _clamp(score)

    def time_decay(self, case: Dict[str, Any]) -> float:
        timestamp = case.get("updated_at") or case.get("created_at")
        if not _known(timestamp):
            return 0.6

        try:
            parsed = datetime.fromisoformat(str(timestamp))
        except ValueError:
            return 0.6

        age_days = max(0, (datetime.now() - parsed).days)
        if age_days <= 30:
            return 1.0
        if age_days <= 90:
            return 0.85
        if age_days <= 180:
            return 0.7
        if age_days <= 365:
            return 0.55
        return 0.4

    def fresh_quality(self, time_decay: float, case_quality: float) -> float:
        return _clamp(FRESH_QUALITY_RHO * time_decay + (1 - FRESH_QUALITY_RHO) * case_quality)

    def final_score(self, retrieval_score: float, process_sim: float, fresh_quality: float) -> float:
        return _clamp(
            FINAL_SCORE_WEIGHTS["retrieval_score"] * _clamp(retrieval_score)
            + FINAL_SCORE_WEIGHTS["process_sim"] * _clamp(process_sim)
            + FINAL_SCORE_WEIGHTS["fresh_quality"] * _clamp(fresh_quality)
        )
