"""
Structured process plan generation for Zhijiang industrial mode.

The first implementation uses a deterministic fallback template. This avoids
coupling process_planning to the role-chat generator, while preserving a prompt
builder output that can be wired to a process-specific LLM path later.
"""
from __future__ import annotations

from typing import Any, Dict, List

from core.process_prompt_builder import ProcessPromptBuilder


def _value(data: Dict[str, Any], key: str, default: str = "unknown") -> str:
    value = data.get(key)
    if value is None or str(value).strip() == "":
        return default
    return str(value)


def _known(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(text) and text.lower() != "unknown"


class ProcessGenerator:
    """Generate a structured fallback process plan from requirements and cases."""

    def __init__(self, prompt_builder: ProcessPromptBuilder | None = None):
        self.prompt_builder = prompt_builder or ProcessPromptBuilder()

    def generate(
        self,
        raw_query: str,
        requirement_vector: Dict[str, Any] | None,
        enhanced_query: Dict[str, Any] | None,
        process_retrieval: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        vector = requirement_vector or {}
        retrieval = process_retrieval or {}
        process_prompt = self.prompt_builder.build_prompt(
            raw_query=raw_query,
            requirement_vector=vector,
            enhanced_query=enhanced_query or {},
            retrieval_results=retrieval,
            top_k=3,
        )
        cases = list(retrieval.get("results") or [])
        top_cases = cases[:3]
        process_type = _value(vector, "process_type", self._first_known(top_cases, "process_type"))
        equipment = _value(vector, "equipment", self._first_known(top_cases, "equipment"))
        material = _value(vector, "material", self._first_known(top_cases, "material"))
        feature = _value(vector, "feature", self._first_known(top_cases, "structure_type"))
        quality = _value(vector, "quality", self._first_known(top_cases, "quality"))
        batch = _value(vector, "batch", self._first_known(top_cases, "batch"))

        process_plan = {
            "generation_enabled": True,
            "generation_mode": "fallback_template",
            "route": self._route(process_type, feature),
            "operation_card": self._operation_card(process_type, equipment, feature),
            "parameter_set": {
                "material": material,
                "process_type": process_type,
                "batch": batch,
                "quality": quality,
                "tolerance": self._first_known(top_cases, "tolerance"),
                "surface_roughness": self._first_known(top_cases, "surface_roughness"),
            },
            "equipment_plan": [
                {
                    "equipment": equipment,
                    "reason": "根据结构化需求和候选案例设备字段选取；如为 unknown，需要人工补充设备条件。",
                }
            ],
            "inspection_standard": self._inspection_standard(quality),
            "risk_notes": self._risk_notes(vector, top_cases, feature, equipment, material),
            "reference_cases": self._reference_cases(top_cases),
        }

        return {
            "generation_enabled": True,
            "generation_mode": "fallback_template",
            "process_prompt": {
                "prompt_builder_enabled": process_prompt["prompt_builder_enabled"],
                "prompt": process_prompt["prompt"],
                "prompt_sections": process_prompt["prompt_sections"],
                "used_case_ids": process_prompt["used_case_ids"],
                "top_k": process_prompt["top_k"],
            },
            "process_plan": process_plan,
        }

    def _route(self, process_type: str, feature: str) -> List[Dict[str, Any]]:
        return [
            {
                "step": 1,
                "name": "工艺准备",
                "description": f"确认{feature}的材料状态、毛坯余量、装夹基准和质量要求。",
            },
            {
                "step": 2,
                "name": "粗加工",
                "description": f"采用{process_type}进行主要余量去除，保留后续精加工余量。",
            },
            {
                "step": 3,
                "name": "半精加工",
                "description": "修正关键轮廓和基准面，复核装夹稳定性与变形趋势。",
            },
            {
                "step": 4,
                "name": "精加工与检测",
                "description": "完成关键尺寸、表面质量和形位要求，并按检测标准复核。",
            },
        ]

    def _operation_card(self, process_type: str, equipment: str, feature: str) -> List[Dict[str, Any]]:
        return [
            {
                "operation": "粗加工",
                "equipment": equipment,
                "key_points": ["控制切削负载", "保留均匀余量", "避免一次去除过多导致变形"],
            },
            {
                "operation": "半精加工",
                "equipment": equipment,
                "key_points": ["校正基准", f"关注{feature}的装夹稳定性", "复核关键尺寸余量"],
            },
            {
                "operation": "精加工",
                "equipment": equipment,
                "key_points": [f"按{process_type}完成最终轮廓", "控制表面质量", "加工后进行尺寸复检"],
            },
        ]

    def _inspection_standard(self, quality: str) -> List[str]:
        standards = ["尺寸精度检查", "外观与毛刺检查", "关键尺寸复测"]
        if "高精度" in quality or "IT" in quality.upper():
            standards.append("形位精度与公差等级检查")
        if "Ra" in quality or "粗糙" in quality:
            standards.append("表面粗糙度检查")
        else:
            standards.append("表面粗糙度抽检")
        return standards

    def _risk_notes(
        self,
        vector: Dict[str, Any],
        cases: List[Dict[str, Any]],
        feature: str,
        equipment: str,
        material: str,
    ) -> List[str]:
        notes = []
        if not cases:
            notes.append("缺少可参考工艺案例，当前方案可信度较低，需要人工复核。")
        if "薄壁" in feature:
            notes.append("薄壁件加工存在变形风险，需要控制装夹方式、切削负载和加工顺序。")
        if not _known(equipment):
            notes.append("设备条件不足，需补充可用设备型号和加工能力。")
        if not _known(material):
            notes.append("材料信息不足，需确认材料牌号、热处理状态和切削性能。")
        for field in ("cost_limit", "time_limit"):
            if vector.get(field) == "unknown":
                notes.append(f"{field} 未明确，后续排产和成本评估需要补充。")
        if not notes:
            notes.append("方案基于候选案例生成，关键参数仍需由工艺工程师复核。")
        return notes

    def _reference_cases(self, cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                "case_id": case.get("case_id", "unknown"),
                "title": case.get("title", "unknown"),
                "final_score": case.get("final_score", case.get("score", 0.0)),
            }
            for case in cases
        ]

    def _first_known(self, cases: List[Dict[str, Any]], field: str) -> str:
        for case in cases:
            value = case.get(field)
            if _known(value):
                return str(value)
        return "unknown"
