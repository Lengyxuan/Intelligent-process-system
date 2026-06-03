import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from core.process_prompt_builder import ProcessPromptBuilder


RAW_QUERY = "请为小批量铝合金薄壁件生成数控铣削工艺路线，要求高精度，设备为三轴数控铣床。"

REQUIREMENT_VECTOR = {
    "material": "铝合金",
    "batch": "小批量",
    "feature": "薄壁件",
    "equipment": "三轴数控铣床",
    "quality": "高精度",
    "process_type": "数控铣削",
}

ENHANCED_QUERY = {
    "process_query": "[材料=铝合金]\n[结构特征=薄壁件]\n[设备资源=三轴数控铣床]",
    "query_tags": {"material": "铝合金"},
}


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
                "process_sim": 0.95,
                "case_quality": 0.82,
                "fresh_quality": 0.86,
                "final_score": 0.9,
                "text_preview": "采用粗铣、半精铣、精铣的路线。",
            }
        ]
    }


def test_build_prompt_contains_requirement_cases_and_output_schema():
    result = ProcessPromptBuilder().build_prompt(
        RAW_QUERY,
        REQUIREMENT_VECTOR,
        ENHANCED_QUERY,
        _retrieval_results(),
    )

    prompt = result["prompt"]
    assert result["prompt_builder_enabled"] is True
    assert RAW_QUERY in prompt
    assert "铝合金" in prompt
    assert "CASE_001" in prompt
    assert "铝合金薄壁件 CNC 铣削案例" in prompt
    assert "final_score=0.9" in prompt
    assert "route" in prompt
    assert "operation_card" in prompt
    assert "risk_notes" in prompt
    assert result["used_case_ids"] == ["CASE_001"]


def test_prompt_sections_are_structured():
    result = ProcessPromptBuilder().build_prompt(
        RAW_QUERY,
        REQUIREMENT_VECTOR,
        ENHANCED_QUERY,
        _retrieval_results(),
    )

    sections = result["prompt_sections"]
    assert sections["user_requirement"] == RAW_QUERY
    assert sections["structured_requirement"]["material"] == "铝合金"
    assert sections["retrieved_cases"][0]["case_id"] == "CASE_001"
    assert "reference_cases" in sections["output_schema"]
    assert sections["constraints"]


def test_prompt_does_not_contain_legacy_role_terms():
    result = ProcessPromptBuilder().build_prompt(
        RAW_QUERY,
        REQUIREMENT_VECTOR,
        ENHANCED_QUERY,
        _retrieval_results(),
    )

    prompt = result["prompt"]
    assert "角色扮演" not in prompt
    assert "角色一致性" not in prompt
    assert "ARPM" not in prompt


def test_empty_retrieval_results_do_not_crash():
    result = ProcessPromptBuilder().build_prompt(
        RAW_QUERY,
        REQUIREMENT_VECTOR,
        ENHANCED_QUERY,
        {"results": []},
    )

    assert result["used_case_ids"] == []
    assert result["top_k"] == 0
    assert "无候选案例" in result["prompt"]
