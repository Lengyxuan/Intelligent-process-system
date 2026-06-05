import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from core.process_evaluator import ProcessPlanEvaluator
from core.process_entry import handle_process_entry


def _plan(**overrides):
    base = {
        "route": [
            {"step": 1, "name": "工艺准备"},
            {"step": 2, "name": "粗加工"},
            {"step": 3, "name": "精加工与检测"},
        ],
        "operation_card": [
            {"operation": "粗加工", "equipment": "三轴数控铣床"},
            {"operation": "精加工", "equipment": "三轴数控铣床"},
        ],
        "parameter_set": {
            "material": "铝合金",
            "process_type": "数控铣削",
            "equipment": "三轴数控铣床",
            "batch": "小批量",
            "quality": "高精度",
            "tolerance": "IT7",
            "surface_roughness": "Ra1.6",
        },
        "equipment_plan": [{"equipment": "三轴数控铣床"}],
        "inspection_standard": ["尺寸精度检测", "表面粗糙度检测"],
        "risk_notes": ["薄壁件存在加工变形风险，需要控制装夹和切削参数。"],
        "reference_cases": [{"case_id": "CASE_001", "title": "铝合金薄壁件 CNC 铣削案例"}],
    }
    base.update(overrides)
    return base


def _vector(**overrides):
    base = {
        "material": "铝合金",
        "batch": "小批量",
        "feature": "薄壁件",
        "equipment": "三轴数控铣床",
        "quality": "高精度",
        "process_type": "数控铣削",
    }
    base.update(overrides)
    return base


def _evaluate(plan=None, vector=None, retrieval=None):
    return ProcessPlanEvaluator().evaluate(
        _plan() if plan is None else plan,
        _vector() if vector is None else vector,
        {"results": []} if retrieval is None else retrieval,
    )


def _flag_types(result):
    return {item["type"] for item in result["risk_flags"]}


def test_complete_process_plan_scores_high():
    result = _evaluate()

    assert result["evaluator_enabled"] is True
    assert result["feasibility_score"] >= 0.8
    assert result["quality_score"] >= 0.8
    assert result["plan_score"] >= 0.7
    assert result["evaluation_status"]["process_evaluator"] == "available"


def test_missing_route_lowers_feasibility_and_flags_incomplete_route():
    plan = _plan(route=[])

    result = _evaluate(plan=plan)

    assert result["feasibility_score"] < _evaluate()["feasibility_score"]
    assert "incomplete_route" in _flag_types(result)


def test_missing_operation_card_flags_incomplete_operation_card():
    result = _evaluate(plan=_plan(operation_card=[]))

    assert "incomplete_operation_card" in _flag_types(result)


def test_missing_inspection_standard_flags_incomplete_inspection():
    result = _evaluate(plan=_plan(inspection_standard=[]))

    assert "incomplete_inspection" in _flag_types(result)


def test_high_precision_without_inspection_lowers_quality_score():
    complete = _evaluate()
    incomplete = _evaluate(plan=_plan(inspection_standard=[]))

    assert incomplete["quality_score"] < complete["quality_score"]
    assert "high_precision_risk" in _flag_types(incomplete)


def test_thin_wall_requirement_creates_deformation_risk():
    result = _evaluate(vector=_vector(feature="薄壁件"))

    assert "thin_wall_deformation" in _flag_types(result)


def test_no_reference_cases_creates_no_reference_cases_risk():
    result = _evaluate(plan=_plan(reference_cases=[]), retrieval={"results": []})

    assert "no_reference_cases" in _flag_types(result)
    assert result["risk_score"] < _evaluate()["risk_score"]


def test_high_rework_reference_creates_high_rework_flag():
    retrieval = {
        "results": [
            {"case_id": "CASE_BAD", "title": "高返工率案例", "rework_rate": 0.8},
        ]
    }

    result = _evaluate(retrieval=retrieval)

    assert "high_rework_reference" in _flag_types(result)


def test_plan_score_is_clamped_to_zero_one():
    result = _evaluate()

    assert 0.0 <= result["plan_score"] <= 1.0


def test_empty_process_plan_does_not_crash():
    result = _evaluate(plan={}, vector={"material": "unknown"}, retrieval={"results": []})

    assert result["evaluator_enabled"] is False
    assert 0.0 <= result["plan_score"] <= 1.0
    assert "incomplete_route" in _flag_types(result)
    assert "incomplete_operation_card" in _flag_types(result)


def test_missing_material_equipment_and_process_type_are_flagged():
    result = _evaluate(
        plan=_plan(
            parameter_set={
                "material": "unknown",
                "equipment": "unknown",
                "process_type": "unknown",
                "quality": "一般精度",
            }
        ),
        vector=_vector(material="unknown", equipment="unknown", process_type="unknown"),
    )

    flags = _flag_types(result)
    assert "missing_material" in flags
    assert "missing_equipment" in flags
    assert "missing_process_type" in flags


def test_process_entry_returns_process_evaluation():
    result = handle_process_entry(
        {
            "message": "请为小批量铝合金薄壁件生成数控铣削工艺路线，要求高精度，设备为三轴数控铣床。",
            "mode": "process_planning",
        }
    )

    evaluation = result["process_evaluation"]
    assert result["status"] == "success"
    assert "process_plan" in result
    assert evaluation["evaluation_status"]["process_evaluator"] == "available"
    assert 0.0 <= evaluation["plan_score"] <= 1.0
