import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from storage.process_case_store import ProcessCaseStore


def _store(tmp_path):
    return ProcessCaseStore(tmp_path / "process_cases.json")


def test_add_case_saves_case(tmp_path):
    store = _store(tmp_path)

    case = store.add_case(
        {
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

    assert case["case_id"].startswith("CASE_")
    assert case["source_type"] == "process_case"
    assert case["material"] == "6061铝合金"
    assert case["equipment"] == "三轴数控铣床"
    assert store.storage_path.exists()


def test_list_and_get_cases(tmp_path):
    store = _store(tmp_path)
    case = store.add_case({"case_id": "CASE_001", "title": "案例 1", "text": "正文"})

    cases = store.list_cases()

    assert len(cases) == 1
    assert cases[0]["case_id"] == "CASE_001"
    assert store.get_case(case["case_id"])["title"] == "案例 1"
    assert store.get_case("missing") is None


def test_update_case_updates_fields_and_refreshed_updated_at(tmp_path):
    store = _store(tmp_path)
    case = store.add_case({"case_id": "CASE_001", "title": "旧标题", "text": "正文"})
    old_updated_at = case["updated_at"]

    time.sleep(0.001)
    updated = store.update_case("CASE_001", {"title": "新标题", "expert_score": 2})

    assert updated["title"] == "新标题"
    assert updated["expert_score"] == 1.0
    assert updated["case_id"] == "CASE_001"
    assert updated["updated_at"] != old_updated_at
    assert store.get_case("CASE_001")["title"] == "新标题"


def test_update_missing_case_returns_none(tmp_path):
    store = _store(tmp_path)

    assert store.update_case("missing", {"title": "新标题"}) is None


def test_delete_case_removes_case(tmp_path):
    store = _store(tmp_path)
    store.add_case({"case_id": "CASE_001", "title": "案例 1"})

    assert store.delete_case("CASE_001") is True
    assert store.get_case("CASE_001") is None
    assert store.list_cases() == []
    assert store.delete_case("CASE_001") is False


def test_empty_storage_file_does_not_crash(tmp_path):
    storage_path = tmp_path / "process_cases.json"
    storage_path.write_text("", encoding="utf-8")
    store = ProcessCaseStore(storage_path)

    assert store.list_cases() == []


def test_damaged_storage_file_does_not_crash(tmp_path):
    storage_path = tmp_path / "process_cases.json"
    storage_path.write_text("{bad json", encoding="utf-8")
    store = ProcessCaseStore(storage_path)

    assert store.list_cases() == []


def test_store_can_read_cases_wrapper_shape(tmp_path):
    storage_path = tmp_path / "process_cases.json"
    storage_path.write_text(
        json.dumps({"cases": [{"case_id": "CASE_001", "title": "案例 1"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    store = ProcessCaseStore(storage_path)

    assert store.list_cases()[0]["case_id"] == "CASE_001"
