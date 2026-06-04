import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from core.process_review import ExpertReviewService, build_case_from_plan
from storage.process_case_store import ProcessCaseStore
from storage.process_review_store import ProcessReviewStore


def _plan(label="原方案"):
    return {
        "route": [{"step": 1, "name": label}, {"step": 2, "name": "精加工"}],
        "operation_card": [{"operation": label, "equipment": "三轴数控铣床"}],
        "parameter_set": {
            "material": "铝合金",
            "process_type": "数控铣削",
            "equipment": "三轴数控铣床",
            "tolerance": "IT7",
            "surface_roughness": "Ra1.6",
        },
        "equipment_plan": [{"equipment": "三轴数控铣床"}],
        "inspection_standard": ["尺寸检测"],
        "risk_notes": ["薄壁变形风险"],
        "reference_cases": [{"case_id": "CASE_001"}],
    }


def _vector():
    return {
        "material": "铝合金",
        "feature": "薄壁件",
        "process_type": "数控铣削",
        "equipment": "三轴数控铣床",
        "quality": "高精度",
        "batch": "小批量",
    }


def _payload(status="pass", **overrides):
    data = {
        "status": status,
        "reviewer": "expert",
        "comments": "方案可用，建议补充装夹风险控制。",
        "raw_query": "请为小批量铝合金薄壁件生成数控铣削工艺路线。",
        "requirement_vector": _vector(),
        "process_plan": _plan(),
        "modified_plan": {},
        "process_evaluation": {"plan_score": 0.82, "risk_flags": []},
        "reference_cases": [{"case_id": "CASE_001", "title": "参考案例"}],
    }
    data.update(overrides)
    return data


def _service(tmp_path):
    return ExpertReviewService(
        review_store=ProcessReviewStore(tmp_path / "process_reviews.json"),
        case_store=ProcessCaseStore(tmp_path / "process_cases.json"),
    )


def test_pass_saves_review_and_process_case(tmp_path):
    service = _service(tmp_path)

    result = service.submit_review(_payload("pass"))

    assert result["success"] is True
    assert result["feedback_status"] == "saved_to_process_case"
    assert result["review"]["feedback_case_id"]
    assert result["feedback_case"]["source"] == "expert_review"
    assert result["feedback_case"]["metadata"]["review_status"] == "pass"


def test_modify_uses_modified_plan_for_feedback_case(tmp_path):
    service = _service(tmp_path)
    modified_plan = _plan("修改后精加工")

    result = service.submit_review(_payload("modify", modified_plan=modified_plan))

    assert result["success"] is True
    assert result["feedback_status"] == "modified_plan_saved_to_process_case"
    assert "修改后精加工" in result["feedback_case"]["text"]
    assert result["feedback_case"]["metadata"]["review_status"] == "modify"


def test_reject_saves_review_without_process_case(tmp_path):
    service = _service(tmp_path)

    result = service.submit_review(_payload("reject", comments="案例支撑不足"))

    assert result["success"] is True
    assert result["feedback_status"] == "review_record_only"
    assert result["review"]["feedback_case_id"] is None
    assert result["feedback_case"] is None
    assert service.case_store.list_cases() == []


def test_invalid_status_does_not_write_process_case(tmp_path):
    service = _service(tmp_path)

    result = service.submit_review(_payload("invalid"))

    assert result["success"] is False
    assert result["feedback_status"] == "invalid_status"
    assert service.case_store.list_cases() == []
    assert service.review_store.list_reviews() == []


def test_modify_requires_modified_plan_and_does_not_write_case(tmp_path):
    service = _service(tmp_path)

    result = service.submit_review(_payload("modify", modified_plan=None))

    assert result["success"] is False
    assert result["feedback_status"] == "invalid_modified_plan"
    assert service.case_store.list_cases() == []


def test_feedback_case_id_is_written_back_to_review(tmp_path):
    service = _service(tmp_path)

    result = service.submit_review(_payload("pass"))

    saved_review = service.review_store.get_review(result["review"]["review_id"])
    assert saved_review["feedback_case_id"] == result["feedback_case"]["case_id"]


def test_build_case_from_plan_generates_required_process_case_fields():
    review = {"review_id": "REVIEW_001", "status": "pass", "reviewer": "expert"}

    case = build_case_from_plan(_plan(), _vector(), {"plan_score": 0.9}, [], review)

    assert case["title"] == "铝合金薄壁件 数控铣削审核案例"
    assert case["source"] == "expert_review"
    assert case["source_type"] == "process_case"
    assert case["material"] == "铝合金"
    assert case["structure_type"] == "薄壁件"
    assert case["equipment"] == "三轴数控铣床"
    assert case["expert_score"] == 0.9
    assert case["success_rate"] == 0.5
    assert case["metadata"]["review_id"] == "REVIEW_001"


def test_feedback_does_not_overwrite_existing_process_case(tmp_path):
    service = _service(tmp_path)
    existing = service.case_store.add_case({"case_id": "CASE_EXISTING", "title": "旧案例", "text": "old"})

    result = service.submit_review(_payload("pass"))

    cases = service.case_store.list_cases()
    assert len(cases) == 2
    assert service.case_store.get_case(existing["case_id"])["title"] == "旧案例"
    assert result["feedback_case"]["case_id"] != existing["case_id"]


def test_api_submit_process_review_smoke(tmp_path, monkeypatch):
    import app
    import api.process_review as process_review_api

    def _temporary_service():
        return _service(tmp_path)

    monkeypatch.setattr(process_review_api, "ExpertReviewService", _temporary_service)

    client = app.app.test_client()
    response = client.post("/api/process/review", json=_payload("pass"))

    data = response.get_json()
    assert response.status_code == 200
    assert data["success"] is True
    assert data["feedback_status"] == "saved_to_process_case"
