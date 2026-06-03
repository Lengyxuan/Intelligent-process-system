import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from storage.process_schema import create_process_case


def test_create_complete_process_case():
    case = create_process_case(
        {
            "case_id": "CASE_001",
            "title": "铝合金薄壁件 CNC 铣削案例",
            "source": "manual",
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
            "metadata": {"owner": "process-team"},
        }
    )

    assert case["case_id"] == "CASE_001"
    assert case["title"] == "铝合金薄壁件 CNC 铣削案例"
    assert case["source_type"] == "process_case"
    assert case["material"] == "6061铝合金"
    assert case["equipment"] == "三轴数控铣床"
    assert case["expert_score"] == 0.9
    assert case["success_rate"] == 0.85
    assert case["usage_frequency"] == 0.7
    assert case["rework_rate"] == 0.1
    assert case["text"] == "采用粗铣、半精铣、精铣的路线，注意薄壁变形控制。"
    assert case["metadata"] == {"owner": "process-team"}
    assert case["created_at"] != "unknown"
    assert case["updated_at"] != "unknown"


def test_missing_fields_use_defaults():
    case = create_process_case({"title": "不完整工艺案例", "material": "45钢"})

    assert case["title"] == "不完整工艺案例"
    assert case["material"] == "45钢"
    assert case["source"] == "manual"
    assert case["source_type"] == "process_case"
    assert case["structure_type"] == "unknown"
    assert case["process_type"] == "unknown"
    assert case["equipment"] == "unknown"
    assert case["quality"] == "unknown"
    assert case["batch"] == "unknown"
    assert case["tolerance"] == "unknown"
    assert case["surface_roughness"] == "unknown"
    assert case["text"] == "unknown"
    assert case["expert_score"] == 0.5
    assert case["success_rate"] == 0.5
    assert case["usage_frequency"] == 0.0
    assert case["rework_rate"] == 0.0
    assert case["metadata"] == {}


def test_score_fields_are_clamped_to_zero_one():
    case = create_process_case(
        {
            "expert_score": 2,
            "success_rate": 1.5,
            "usage_frequency": -0.2,
            "rework_rate": -0.5,
        }
    )

    assert case["expert_score"] == 1.0
    assert case["success_rate"] == 1.0
    assert case["usage_frequency"] == 0.0
    assert case["rework_rate"] == 0.0


def test_source_type_is_always_process_case():
    case = create_process_case({"source_type": "knowledge", "text": "正文"})

    assert case["source_type"] == "process_case"
    assert case["text"] == "正文"
