import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from core.process_parser import parse_process_requirement


def test_parse_typical_process_requirement():
    result = parse_process_requirement(
        "请为小批量铝合金薄壁件生成数控铣削工艺路线，要求高精度，设备为三轴数控铣床。"
    )

    assert result["material"] == "铝合金"
    assert result["batch"] == "小批量"
    assert result["feature"] == "薄壁件"
    assert result["process_type"] == "数控铣削"
    assert result["quality"] == "高精度"
    assert result["equipment"] == "三轴数控铣床"
    assert result["cost_limit"] == "unknown"
    assert result["time_limit"] == "unknown"
    assert "cost_limit" in result["missing_fields"]
    assert "time_limit" in result["missing_fields"]


def test_parse_material_variants():
    assert parse_process_requirement("45钢轴类件车削")["material"] == "45钢"
    assert parse_process_requirement("不锈钢支架钻孔")["material"] == "不锈钢"


def test_parse_batch_variants():
    assert parse_process_requirement("小批量箱体件")["batch"] == "小批量"
    assert parse_process_requirement("大批量板件")["batch"] == "大批量"


def test_parse_equipment_variants():
    assert parse_process_requirement("设备为三轴数控铣床")["equipment"] == "三轴数控铣床"
    assert parse_process_requirement("使用五轴加工中心完成")["equipment"] == "五轴加工中心"


def test_parse_quality_variants():
    assert parse_process_requirement("要求高精度")["quality"] == "高精度"
    assert parse_process_requirement("孔加工达到IT7")["quality"] == "IT7"
    assert parse_process_requirement("表面达到Ra1.6")["quality"] == "Ra1.6"


def test_parse_process_type_variants():
    assert parse_process_requirement("数控铣削工艺")["process_type"] == "数控铣削"
    assert parse_process_requirement("轴类件车削")["process_type"] == "车削"
    assert parse_process_requirement("表面磨削")["process_type"] == "磨削"


def test_unknown_fields_are_reported_as_missing():
    result = parse_process_requirement("做一个零件")

    assert result["material"] == "unknown"
    assert result["equipment"] == "unknown"
    assert result["process_type"] == "unknown"
    assert "material" in result["missing_fields"]
    assert "equipment" in result["missing_fields"]
    assert "process_type" in result["missing_fields"]


def test_empty_or_none_input_does_not_crash():
    empty_result = parse_process_requirement("")
    none_result = parse_process_requirement(None)

    assert empty_result["raw_query"] == ""
    assert none_result["raw_query"] == ""
    assert set(empty_result["missing_fields"]) == {
        "feature",
        "material",
        "batch",
        "quality",
        "equipment",
        "cost_limit",
        "time_limit",
        "process_type",
    }
