"""
Prompt builder for Zhijiang industrial process plan generation.

The builder only prepares a constrained prompt from parsed requirements and
retrieved process cases. It does not call LLMs or generate plans.
"""
from __future__ import annotations

from typing import Any, Dict, List


LEGACY_TERMS = ("ARPM", "角色扮演", "角色一致性")


class ProcessPromptBuilder:
    """Build auditable process-planning prompts from retrieval context."""

    def build_prompt(
        self,
        raw_query: str,
        requirement_vector: Dict[str, Any] | None,
        enhanced_query: Dict[str, Any] | None,
        retrieval_results: Dict[str, Any] | None,
        top_k: int = 3,
    ) -> Dict[str, Any]:
        vector = requirement_vector or {}
        enhanced = enhanced_query or {}
        retrieval = retrieval_results or {}
        cases = list(retrieval.get("results") or [])[: max(0, int(top_k or 3))]
        used_case_ids = [case.get("case_id", "unknown") for case in cases]

        role_instruction = (
            "你是智匠系统中的智能工艺规划助手，任务是基于用户工艺需求和已召回工艺案例，"
            "生成可审核的制造工艺方案。"
        )
        constraints = [
            "只基于提供的用户需求、结构化字段和候选工艺案例生成。",
            "不得编造未提供的材料、设备、标准或案例来源。",
            "缺失或不确定信息必须写入 risk_notes。",
            "输出必须为结构化对象，包含 route、operation_card、parameter_set、equipment_plan、inspection_standard、risk_notes、reference_cases。",
            "reference_cases 必须引用候选案例的 case_id 和 title。",
        ]
        output_schema = {
            "route": [],
            "operation_card": [],
            "parameter_set": {},
            "equipment_plan": [],
            "inspection_standard": [],
            "risk_notes": [],
            "reference_cases": [],
        }
        prompt_sections = {
            "role_instruction": role_instruction,
            "user_requirement": str(raw_query or ""),
            "structured_requirement": vector,
            "enhanced_query": enhanced,
            "retrieved_cases": [self._case_for_prompt(case) for case in cases],
            "output_schema": output_schema,
            "constraints": constraints,
        }

        prompt = self._render_prompt(prompt_sections)
        for term in LEGACY_TERMS:
            prompt = prompt.replace(term, "")

        return {
            "prompt_builder_enabled": True,
            "prompt": prompt,
            "prompt_sections": prompt_sections,
            "used_case_ids": used_case_ids,
            "top_k": len(cases),
        }

    def _case_for_prompt(self, case: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "rank": case.get("rank"),
            "case_id": case.get("case_id", "unknown"),
            "title": case.get("title", "unknown"),
            "material": case.get("material", "unknown"),
            "structure_type": case.get("structure_type", "unknown"),
            "process_type": case.get("process_type", "unknown"),
            "equipment": case.get("equipment", "unknown"),
            "quality": case.get("quality", "unknown"),
            "batch": case.get("batch", "unknown"),
            "process_sim": case.get("process_sim", 0.0),
            "case_quality": case.get("case_quality", 0.0),
            "fresh_quality": case.get("fresh_quality", 0.0),
            "final_score": case.get("final_score", case.get("score", 0.0)),
            "text_preview": case.get("text_preview", ""),
        }

    def _render_prompt(self, sections: Dict[str, Any]) -> str:
        case_lines = []
        for case in sections["retrieved_cases"]:
            case_lines.append(
                "- rank={rank}; case_id={case_id}; title={title}; material={material}; "
                "structure_type={structure_type}; process_type={process_type}; equipment={equipment}; "
                "quality={quality}; batch={batch}; process_sim={process_sim}; case_quality={case_quality}; "
                "fresh_quality={fresh_quality}; final_score={final_score}; text_preview={text_preview}".format(**case)
            )
        if not case_lines:
            case_lines.append("- 无候选案例。")

        return "\n".join(
            [
                sections["role_instruction"],
                "",
                "用户原始需求：",
                sections["user_requirement"],
                "",
                "结构化需求字段：",
                str(sections["structured_requirement"]),
                "",
                "增强查询：",
                str(sections["enhanced_query"].get("process_query", "")),
                "",
                "候选工艺案例：",
                "\n".join(case_lines),
                "",
                "生成约束：",
                "\n".join(f"- {item}" for item in sections["constraints"]),
                "",
                "输出格式：",
                str(sections["output_schema"]),
            ]
        )
