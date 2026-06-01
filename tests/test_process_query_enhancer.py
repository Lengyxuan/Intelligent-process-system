import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from core.process_query_enhancer import build_process_query


def _full_vector():
    return {
        "feature": "薄壁件",
        "material": "铝合金",
        "batch": "小批量",
        "quality": "高精度",
        "equipment": "三轴数控铣床",
        "cost_limit": "unknown",
        "time_limit": "unknown",
        "process_type": "数控铣削",
        "raw_query": "请为小批量铝合金薄壁件生成数控铣削工艺路线，要求高精度，设备为三轴数控铣床。",
        "missing_fields": ["cost_limit", "time_limit"],
    }


def test_build_process_query_from_complete_requirement_vector():
    raw_query = _full_vector()["raw_query"]
    result = build_process_query(raw_query, _full_vector())

    assert result["raw_query"] == raw_query
    assert result["query_tags"]["industry"] == "机械加工"
    assert result["query_tags"]["task"] == "工艺规划"
    assert result["query_tags"]["material"] == "铝合金"
    assert result["query_tags"]["batch"] == "小批量"
    assert result["query_tags"]["feature"] == "薄壁件"
    assert result["query_tags"]["equipment"] == "三轴数控铣床"
    assert result["query_tags"]["quality"] == "高精度"
    assert result["query_tags"]["process_type"] == "数控铣削"


def test_process_query_contains_retrieval_tags():
    result = build_process_query(_full_vector()["raw_query"], _full_vector())
    process_query = result["process_query"]

    assert "[行业=机械加工]" in process_query
    assert "[任务=工艺规划]" in process_query
    assert "[材料=铝合金]" in process_query
    assert "[批量=小批量]" in process_query
    assert "[结构特征=薄壁件]" in process_query
    assert "[设备资源=三轴数控铣床]" in process_query
    assert "[质量要求=高精度]" in process_query
    assert "[工艺类型=数控铣削]" in process_query


def test_unknown_fields_are_stable_and_tagged():
    vector = _full_vector()
    vector["equipment"] = "unknown"
    vector["missing_fields"] = ["equipment", "cost_limit", "time_limit"]

    result = build_process_query(vector["raw_query"], vector)

    assert result["query_tags"]["equipment"] == "unknown"
    assert "[设备资源=unknown]" in result["process_query"]
    assert "equipment" in result["missing_fields"]


def test_empty_requirement_vector_does_not_crash():
    result = build_process_query("", {})

    assert result["raw_query"] == ""
    assert result["query_tags"]["material"] == "unknown"
    assert "[材料=unknown]" in result["process_query"]
    assert "material" in result["missing_fields"]


def test_raw_query_is_preserved():
    raw_query = "请为一个不锈钢零件生成加工方案。"
    result = build_process_query(raw_query, {"material": "不锈钢"})

    assert result["raw_query"] == raw_query
    assert f"原始需求：{raw_query}" in result["process_query"]


def test_process_query_does_not_contain_legacy_role_prompt_terms():
    result = build_process_query(
        "请生成工艺路线",
        {
            "material": "铝合金",
            "feature": "薄壁件",
            "batch": "小批量",
            "equipment": "三轴数控铣床",
            "quality": "高精度",
            "process_type": "数控铣削",
        },
    )

    assert "角色扮演" not in result["process_query"]
    assert "角色设定" not in result["process_query"]
    assert "ARPM" not in result["process_query"]
