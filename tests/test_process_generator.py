import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from core.process_generator import ProcessGenerator


RAW_QUERY = "请为小批量铝合金薄壁件生成数控铣削工艺路线，要求高精度，设备为三轴数控铣床。"

REQUIREMENT_VECTOR = {
    "material": "铝合金",
    "batch": "小批量",
    "feature": "薄壁件",
    "equipment": "三轴数控铣床",
    "quality": "高精度",
    "process_type": "数控铣削",
    "cost_limit": "unknown",
    "time_limit": "unknown",
}

ENHANCED_QUERY = {"process_query": "[材料=铝合金]\n[结构特征=薄壁件]"}


def _retrieval_results():
    return {
        "results": [
            {
                "rank": 1,
                "case_id": "CASE_001",
                "title": "铝合金薄壁件 CNC 铣削案例",
                "material": "6061铝合金",
                "structure_type": "薄壁件",
                "process_type": "CNC铣削",
                "equipment": "三轴数控铣床",
                "quality": "高精度",
                "batch": "小批量",
                "tolerance": "IT7",
                "surface_roughness": "Ra1.6",
                "final_score": 0.9,
                "text_preview": "采用粗铣、半精铣、精铣的路线。",
            }
        ]
    }


def test_generate_returns_process_plan_with_candidate_cases():
    result = ProcessGenerator().generate(
        RAW_QUERY,
        REQUIREMENT_VECTOR,
        ENHANCED_QUERY,
        _retrieval_results(),
    )
    plan = result["process_plan"]

    assert result["generation_enabled"] is True
    assert result["generation_mode"] == "fallback_template"
    assert plan["route"]
    assert plan["operation_card"]
    assert plan["parameter_set"]["material"] == "铝合金"
    assert plan["equipment_plan"]
    assert plan["inspection_standard"]
    assert plan["risk_notes"]
    assert plan["reference_cases"][0]["case_id"] == "CASE_001"


def test_reference_cases_come_from_retrieval_results():
    result = ProcessGenerator().generate(
        RAW_QUERY,
        REQUIREMENT_VECTOR,
        ENHANCED_QUERY,
        _retrieval_results(),
    )

    assert result["process_prompt"]["used_case_ids"] == ["CASE_001"]
    assert result["process_plan"]["reference_cases"][0]["title"] == "铝合金薄壁件 CNC 铣削案例"


def test_no_candidate_cases_still_returns_plan_with_risk_note():
    result = ProcessGenerator().generate(
        "请为未知材料的复杂零件生成加工方案。",
        {"material": "unknown", "feature": "复杂零件", "process_type": "unknown"},
        {"process_query": ""},
        {"results": []},
    )
    plan = result["process_plan"]

    assert plan["route"]
    assert plan["operation_card"]
    assert plan["reference_cases"] == []
    assert any("缺少可参考工艺案例" in note for note in plan["risk_notes"])


def test_generation_mode_exists_and_no_future_fields_are_returned():
    result = ProcessGenerator().generate(
        RAW_QUERY,
        REQUIREMENT_VECTOR,
        ENHANCED_QUERY,
        _retrieval_results(),
    )
    plan = result["process_plan"]

    assert result["generation_mode"] == "fallback_template"
    assert "plan_score" not in plan
    assert "expert_review" not in plan
    assert "knowledge_feedback" not in plan
