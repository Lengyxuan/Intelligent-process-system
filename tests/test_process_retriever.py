import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from core.process_retriever import ProcessRetriever
from storage.process_case_store import ProcessCaseStore


PROCESS_QUERY = """[行业=机械加工]
[任务=工艺规划]
[材料=铝合金]
[批量=小批量]
[结构特征=薄壁件]
[设备资源=三轴数控铣床]
[质量要求=高精度]
[工艺类型=数控铣削]
原始需求：请为小批量铝合金薄壁件生成数控铣削工艺路线，要求高精度，设备为三轴数控铣床。"""


REQUIREMENT_VECTOR = {
    "material": "铝合金",
    "batch": "小批量",
    "feature": "薄壁件",
    "equipment": "三轴数控铣床",
    "quality": "高精度",
    "process_type": "数控铣削",
}


def _store(tmp_path):
    return ProcessCaseStore(tmp_path / "process_cases.json")


def _retriever(tmp_path):
    return ProcessRetriever(case_store=_store(tmp_path), top_k=5)


def _add_aluminum_case(store):
    return store.add_case(
        {
            "case_id": "CASE_AL_001",
            "title": "铝合金薄壁件 CNC 铣削案例",
            "material": "6061铝合金",
            "structure_type": "薄壁件",
            "process_type": "CNC铣削",
            "equipment": "三轴数控铣床",
            "quality": "高精度",
            "batch": "小批量",
            "tolerance": "IT7",
            "surface_roughness": "Ra1.6",
            "expert_score": 0.9,
            "success_rate": 0.85,
            "usage_frequency": 0.7,
            "rework_rate": 0.1,
            "text": "采用粗铣、半精铣、精铣的路线，注意薄壁变形控制。",
        }
    )


def _add_steel_case(store):
    return store.add_case(
        {
            "case_id": "CASE_ST_001",
            "title": "不锈钢轴类件车削案例",
            "material": "不锈钢",
            "structure_type": "轴类件",
            "process_type": "车削",
            "equipment": "数控车床",
            "quality": "一般精度",
            "batch": "中批量",
            "text": "采用粗车、半精车、精车的路线。",
        }
    )


def test_empty_case_store_does_not_crash(tmp_path):
    retriever = _retriever(tmp_path)

    result = retriever.retrieve(PROCESS_QUERY, REQUIREMENT_VECTOR)

    assert result["retriever_enabled"] is True
    assert result["total_cases"] == 0
    assert result["results"] == []
    assert result["note"] == "no process cases available"
    assert result["retrieval_status"]["process_sim"] == "pending"


def test_single_matching_case_is_retrieved(tmp_path):
    store = _store(tmp_path)
    _add_aluminum_case(store)
    retriever = ProcessRetriever(case_store=store)

    result = retriever.retrieve(PROCESS_QUERY, REQUIREMENT_VECTOR)

    assert len(result["results"]) == 1
    first = result["results"][0]
    assert first["case_id"] == "CASE_AL_001"
    assert first["title"] == "铝合金薄壁件 CNC 铣削案例"
    assert first["score"] > 0
    assert first["keyword_score"] > 0
    assert first["semantic_score"] == 0.0
    assert first["matched_fields"]["material"] is True
    assert first["matched_fields"]["equipment"] is True
    assert first["matched_fields"]["batch"] is True
    assert first["text_preview"].startswith("采用粗铣")


def test_multiple_cases_are_sorted_by_keyword_score(tmp_path):
    store = _store(tmp_path)
    _add_steel_case(store)
    _add_aluminum_case(store)
    retriever = ProcessRetriever(case_store=store)

    result = retriever.retrieve(PROCESS_QUERY, REQUIREMENT_VECTOR)

    assert [item["case_id"] for item in result["results"]] == ["CASE_AL_001", "CASE_ST_001"]
    assert result["results"][0]["keyword_score"] > result["results"][1]["keyword_score"]


def test_top_k_is_respected(tmp_path):
    store = _store(tmp_path)
    _add_aluminum_case(store)
    _add_steel_case(store)
    store.add_case(
        {
            "case_id": "CASE_003",
            "title": "45钢支架钻孔案例",
            "material": "45钢",
            "structure_type": "支架",
            "process_type": "钻孔",
            "equipment": "钻床",
            "text": "采用定位、钻孔、倒角的路线。",
        }
    )
    retriever = ProcessRetriever(case_store=store)

    result = retriever.retrieve(PROCESS_QUERY, REQUIREMENT_VECTOR, top_k=2)

    assert result["top_k"] == 2
    assert len(result["results"]) == 2


def test_empty_or_unknown_query_does_not_crash(tmp_path):
    store = _store(tmp_path)
    _add_aluminum_case(store)
    retriever = ProcessRetriever(case_store=store)

    result = retriever.retrieve("", {"material": "unknown"})

    assert result["retriever_enabled"] is True
    assert result["total_cases"] == 1
    assert result["results"] == []


def test_return_structure_contains_required_keys(tmp_path):
    store = _store(tmp_path)
    _add_aluminum_case(store)
    retriever = ProcessRetriever(case_store=store)

    result = retriever.retrieve(PROCESS_QUERY, REQUIREMENT_VECTOR)
    first = result["results"][0]

    assert set(["retriever_enabled", "results", "retrieval_status"]).issubset(result)
    assert result["retrieval_status"]["text_vector"] == "pending"
    assert result["retrieval_status"]["bm25"] == "fallback"
    assert result["retrieval_status"]["process_sim"] == "pending"
    assert set(
        [
            "case_id",
            "title",
            "score",
            "keyword_score",
            "matched_fields",
            "text_preview",
        ]
    ).issubset(first)


def test_results_do_not_include_process_sim_field(tmp_path):
    store = _store(tmp_path)
    _add_aluminum_case(store)
    retriever = ProcessRetriever(case_store=store)

    result = retriever.retrieve(PROCESS_QUERY, REQUIREMENT_VECTOR)

    assert "process_sim" not in result["results"][0]
