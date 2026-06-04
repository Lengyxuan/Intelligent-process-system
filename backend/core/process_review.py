"""
Expert review and feedback loop for Zhijiang industrial mode.

Pass and modify reviews can feed approved process plans back into the structured
process case store. Reject reviews are stored only as review records.
"""
from __future__ import annotations

from typing import Any, Dict, List

from storage.process_case_store import ProcessCaseStore
from storage.process_review_schema import VALID_REVIEW_STATUSES, create_process_review
from storage.process_review_store import ProcessReviewStore


def _known(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(text) and text.lower() not in {"unknown", "none", "null", "-"}


def _value(*values: Any, default: str = "unknown") -> str:
    for value in values:
        if _known(value):
            return str(value)
    return default


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _text_block(title: str, value: Any) -> str:
    if not value:
        return ""
    return f"{title}: {value}"


def _equipment_from_plan(plan: Dict[str, Any]) -> str:
    equipment_plan = _list(plan.get("equipment_plan"))
    for item in equipment_plan:
        if isinstance(item, dict) and _known(item.get("equipment")):
            return str(item.get("equipment"))
        if _known(item):
            return str(item)
    operation_card = _list(plan.get("operation_card"))
    for item in operation_card:
        if isinstance(item, dict) and _known(item.get("equipment")):
            return str(item.get("equipment"))
    return "unknown"


def build_case_from_plan(
    process_plan: Dict[str, Any],
    requirement_vector: Dict[str, Any] | None = None,
    process_evaluation: Dict[str, Any] | None = None,
    reference_cases: List[Dict[str, Any]] | None = None,
    review: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Convert an expert-approved process plan into a process_case payload."""
    vector = requirement_vector or {}
    plan = process_plan or {}
    evaluation = process_evaluation or {}
    parameter_set = plan.get("parameter_set") if isinstance(plan.get("parameter_set"), dict) else {}
    review_data = review or {}
    status = review_data.get("status", "pass")

    material = _value(vector.get("material"), parameter_set.get("material"))
    feature = _value(vector.get("feature"), parameter_set.get("feature"))
    process_type = _value(vector.get("process_type"), parameter_set.get("process_type"))
    equipment = _value(vector.get("equipment"), parameter_set.get("equipment"), _equipment_from_plan(plan))
    quality = _value(vector.get("quality"), parameter_set.get("quality"))
    batch = _value(vector.get("batch"), parameter_set.get("batch"))
    plan_score = evaluation.get("plan_score")
    default_expert_score = 0.85 if status == "modify" else 0.8

    text_parts = [
        _text_block("工艺路线", plan.get("route")),
        _text_block("工序卡片", plan.get("operation_card")),
        _text_block("检测标准", plan.get("inspection_standard")),
        _text_block("风险提示", plan.get("risk_notes")),
    ]
    text = "\n".join(part for part in text_parts if part) or "专家审核通过的工艺方案。"

    return {
        "title": f"{material}{feature} {process_type}审核案例",
        "source": "expert_review",
        "source_type": "process_case",
        "material": material,
        "structure_type": feature,
        "process_type": process_type,
        "equipment": equipment,
        "quality": quality,
        "batch": batch,
        "tolerance": _value(parameter_set.get("tolerance")),
        "surface_roughness": _value(parameter_set.get("surface_roughness")),
        "expert_score": plan_score if plan_score is not None else default_expert_score,
        "success_rate": 0.5,
        "usage_frequency": 0.0,
        "rework_rate": 0.0,
        "text": text,
        "metadata": {
            "review_id": review_data.get("review_id"),
            "review_status": status,
            "reviewer": review_data.get("reviewer", "expert"),
            "comments": review_data.get("comments", ""),
            "reference_cases": reference_cases or [],
            "process_evaluation": {
                "plan_score": evaluation.get("plan_score"),
                "feasibility_score": evaluation.get("feasibility_score"),
                "cost_score": evaluation.get("cost_score"),
                "time_score": evaluation.get("time_score"),
                "quality_score": evaluation.get("quality_score"),
                "risk_score": evaluation.get("risk_score"),
                "risk_flags": evaluation.get("risk_flags", []),
            },
        },
    }


class ExpertReviewService:
    """Submit expert reviews and optionally feed approved plans into cases."""

    def __init__(
        self,
        review_store: ProcessReviewStore | None = None,
        case_store: ProcessCaseStore | None = None,
    ):
        self.review_store = review_store or ProcessReviewStore()
        self.case_store = case_store or ProcessCaseStore()

    def submit_review(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = payload or {}
        status = str(data.get("status", "")).strip().lower()
        if status not in VALID_REVIEW_STATUSES:
            return {
                "success": False,
                "error": f"invalid review status: {status or 'missing'}",
                "feedback_status": "invalid_status",
            }

        if status == "modify" and not isinstance(data.get("modified_plan"), dict):
            return {
                "success": False,
                "error": "modified_plan is required for modify review",
                "feedback_status": "invalid_modified_plan",
            }

        try:
            review = create_process_review({**data, "status": status})
        except ValueError as exc:
            return {"success": False, "error": str(exc), "feedback_status": "invalid_status"}

        feedback_case = None
        feedback_status = "review_record_only"
        if status in {"pass", "modify"}:
            source_plan = review["modified_plan"] if status == "modify" else review["process_plan"]
            feedback_case = self.case_store.add_case(
                build_case_from_plan(
                    source_plan,
                    review["requirement_vector"],
                    review["process_evaluation"],
                    review["reference_cases"],
                    review,
                )
            )
            review["feedback_case_id"] = feedback_case["case_id"]
            feedback_status = (
                "modified_plan_saved_to_process_case"
                if status == "modify"
                else "saved_to_process_case"
            )
        else:
            review["feedback_case_id"] = None

        saved_review = self.review_store.add_review(review)
        return {
            "success": True,
            "review": saved_review,
            "feedback_case": feedback_case,
            "feedback_status": feedback_status,
        }
