"""
Rule-based process plan evaluation for Zhijiang industrial mode.

This module evaluates a generated process_plan without regenerating it. The
scores are intentionally deterministic and dependency-free so PR8 stays isolated
from expert review, knowledge feedback, and multimodal file handling.
"""
from __future__ import annotations

from typing import Any, Dict, List


RISK_MESSAGES = {
    "missing_material": "材料信息未知，需要补充材料牌号、热处理状态和切削特性。",
    "missing_equipment": "设备信息未知，需要确认可用设备型号、行程和加工能力。",
    "missing_process_type": "工艺类型未知，需要明确铣削、车削、钻孔或其他加工方式。",
    "no_reference_cases": "缺少候选案例支撑，当前方案需要专家重点复核。",
    "thin_wall_deformation": "薄壁件存在加工变形风险，需要重点控制装夹和切削参数。",
    "high_precision_risk": "高精度加工对基准、刀具、检测和环境控制要求较高。",
    "high_rework_reference": "引用案例存在高返工风险，需要复核其适用性。",
    "incomplete_inspection": "缺少检测标准，质量达成风险较高。",
    "incomplete_route": "工艺路线不完整，无法充分判断制造可行性。",
    "incomplete_operation_card": "工序卡片不完整，现场执行风险较高。",
}


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, round(float(value), 4)))


def _is_known(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(text) and text.lower() not in {"unknown", "none", "null", "-"}


def _items(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    if _is_known(value):
        return [value]
    return []


def _text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_text(item) for item in value)
    return str(value or "")


def _contains(text: str, keywords: List[str]) -> bool:
    return any(keyword and keyword in text for keyword in keywords)


def _vector_value(
    process_plan: Dict[str, Any],
    requirement_vector: Dict[str, Any],
    key: str,
) -> Any:
    parameter_set = process_plan.get("parameter_set") or {}
    return parameter_set.get(key) or requirement_vector.get(key)


class ProcessPlanEvaluator:
    """Evaluate process plan completeness, controllability, and risk."""

    def evaluate(
        self,
        process_plan: Dict[str, Any] | None,
        requirement_vector: Dict[str, Any] | None = None,
        process_retrieval: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        plan = process_plan or {}
        vector = requirement_vector or {}
        retrieval = process_retrieval or {}
        results = list(retrieval.get("results") or [])

        route = _items(plan.get("route"))
        operation_card = _items(plan.get("operation_card"))
        equipment_plan = _items(plan.get("equipment_plan"))
        inspection_standard = _items(plan.get("inspection_standard"))
        risk_notes = _items(plan.get("risk_notes"))
        reference_cases = _items(plan.get("reference_cases")) or results

        material = _vector_value(plan, vector, "material")
        equipment = _vector_value(plan, vector, "equipment")
        process_type = _vector_value(plan, vector, "process_type")
        quality = _vector_value(plan, vector, "quality")
        batch = _vector_value(plan, vector, "batch")
        tolerance = _vector_value(plan, vector, "tolerance")
        surface_roughness = _vector_value(plan, vector, "surface_roughness")

        route_completeness = 1.0 if route else 0.0
        operation_completeness = 1.0 if operation_card else 0.0
        reference_case_support = min(1.0, len(reference_cases) / 2.0)
        risk_disclosure = 1.0 if risk_notes else 0.0

        feasibility_score = self._feasibility_score(
            route,
            operation_card,
            equipment_plan,
            risk_notes,
            material,
            equipment,
            process_type,
        )
        cost_score = self._cost_score(batch, equipment, risk_notes)
        time_score = self._time_score(route, inspection_standard, risk_notes)
        quality_score = self._quality_score(
            quality,
            inspection_standard,
            tolerance,
            surface_roughness,
            risk_notes,
        )
        risk_score = self._risk_score(
            risk_notes,
            reference_cases,
            material,
            equipment,
            process_type,
        )
        plan_score = _clamp(
            0.30 * feasibility_score
            + 0.20 * cost_score
            + 0.20 * time_score
            + 0.20 * quality_score
            + 0.10 * risk_score
        )

        return {
            "evaluator_enabled": bool(plan),
            "feasibility_score": feasibility_score,
            "cost_score": cost_score,
            "time_score": time_score,
            "quality_score": quality_score,
            "risk_score": risk_score,
            "plan_score": plan_score,
            "risk_flags": self._risk_flags(plan, vector, results, reference_cases),
            "score_breakdown": {
                "route_completeness": _clamp(route_completeness),
                "operation_completeness": _clamp(operation_completeness),
                "reference_case_support": _clamp(reference_case_support),
                "risk_disclosure": _clamp(risk_disclosure),
            },
            "evaluation_status": {
                "process_evaluator": "available",
                "expert_review": "pending",
                "knowledge_feedback": "pending",
            },
        }

    def _feasibility_score(
        self,
        route: List[Any],
        operation_card: List[Any],
        equipment_plan: List[Any],
        risk_notes: List[Any],
        material: Any,
        equipment: Any,
        process_type: Any,
    ) -> float:
        score = 0.1
        score += 0.22 if route else 0.0
        score += 0.22 if operation_card else 0.0
        score += 0.16 if equipment_plan else 0.0
        score += 0.10 if _is_known(material) else 0.0
        score += 0.10 if _is_known(equipment) else 0.0
        score += 0.10 if _is_known(process_type) else 0.0
        score += 0.10 if risk_notes else 0.0
        return _clamp(score)

    def _cost_score(self, batch: Any, equipment: Any, risk_notes: List[Any]) -> float:
        score = 0.78
        text = _text([batch, equipment, risk_notes])
        if _contains(text, ["小批量", "灏忔壒"]):
            score -= 0.08
        if _contains(text, ["五轴", "浜旇酱"]):
            score -= 0.18
        if _contains(text, ["三轴", "涓夎酱"]):
            score += 0.08
        if _contains(text, ["返工", "变形", "复杂装夹", "缺少参考案例", "繑宸", "彉褰", "澶嶆潅", "缂哄皯"]):
            score -= 0.14
        return _clamp(score)

    def _time_score(self, route: List[Any], inspection_standard: List[Any], risk_notes: List[Any]) -> float:
        score = 0.72
        if route:
            score += 0.10
        if inspection_standard:
            score += 0.06
        if len(route) > 6:
            score -= 0.10
        if _contains(_text(risk_notes), ["返工", "变形", "复杂装夹", "缺少参考案例", "繑宸", "彉褰", "澶嶆潅", "缂哄皯"]):
            score -= 0.14
        return _clamp(score)

    def _quality_score(
        self,
        quality: Any,
        inspection_standard: List[Any],
        tolerance: Any,
        surface_roughness: Any,
        risk_notes: List[Any],
    ) -> float:
        high_precision = _contains(_text(quality), ["高精度", "楂樼簿", "IT"])
        score = 0.64
        if inspection_standard:
            score += 0.16
        elif high_precision:
            score -= 0.18
        if _is_known(tolerance):
            score += 0.07
        if _is_known(surface_roughness):
            score += 0.07
        if _contains(_text(risk_notes), ["薄壁", "变形", "精度", "粗糙度", "钖勫", "彉褰", "绮惧害", "绮楃硻"]):
            score += 0.06
        return _clamp(score)

    def _risk_score(
        self,
        risk_notes: List[Any],
        reference_cases: List[Any],
        material: Any,
        equipment: Any,
        process_type: Any,
    ) -> float:
        score = 0.5
        score += 0.16 if risk_notes else -0.10
        score += 0.16 if reference_cases else -0.16
        score += 0.06 if _is_known(material) else -0.08
        score += 0.06 if _is_known(equipment) else -0.08
        score += 0.06 if _is_known(process_type) else -0.08
        return _clamp(score)

    def _risk_flags(
        self,
        process_plan: Dict[str, Any],
        requirement_vector: Dict[str, Any],
        retrieval_results: List[Dict[str, Any]],
        reference_cases: List[Any],
    ) -> List[Dict[str, str]]:
        flags: List[Dict[str, str]] = []
        text = _text([process_plan, requirement_vector])
        material = _vector_value(process_plan, requirement_vector, "material")
        equipment = _vector_value(process_plan, requirement_vector, "equipment")
        process_type = _vector_value(process_plan, requirement_vector, "process_type")
        quality = _vector_value(process_plan, requirement_vector, "quality")

        if not _is_known(material):
            self._add_flag(flags, "high", "missing_material")
        if not _is_known(equipment):
            self._add_flag(flags, "medium", "missing_equipment")
        if not _is_known(process_type):
            self._add_flag(flags, "medium", "missing_process_type")
        if not reference_cases:
            self._add_flag(flags, "medium", "no_reference_cases")
        if _contains(text, ["薄壁", "钖勫"]):
            self._add_flag(flags, "medium", "thin_wall_deformation")
        if _contains(_text(quality), ["高精度", "楂樼簿", "IT"]):
            self._add_flag(flags, "medium", "high_precision_risk")
        if any(float(case.get("rework_rate", 0.0) or 0.0) >= 0.5 for case in retrieval_results):
            self._add_flag(flags, "high", "high_rework_reference")
        if not _items(process_plan.get("inspection_standard")):
            self._add_flag(flags, "high", "incomplete_inspection")
        if not _items(process_plan.get("route")):
            self._add_flag(flags, "high", "incomplete_route")
        if not _items(process_plan.get("operation_card")):
            self._add_flag(flags, "high", "incomplete_operation_card")
        return flags

    def _add_flag(self, flags: List[Dict[str, str]], level: str, flag_type: str) -> None:
        if any(item["type"] == flag_type for item in flags):
            return
        flags.append(
            {
                "level": level,
                "type": flag_type,
                "message": RISK_MESSAGES[flag_type],
            }
        )
