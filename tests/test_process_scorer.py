import sys
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from core.process_scorer import ProcessScorer


def _requirement():
    return {
        "material": "铝合金",
        "feature": "薄壁件",
        "process_type": "数控铣削",
        "equipment": "三轴数控铣床",
        "quality": "高精度",
        "batch": "小批量",
    }


def _case(**overrides):
    base = {
        "material": "铝合金",
        "structure_type": "薄壁件",
        "process_type": "数控铣削",
        "equipment": "三轴数控铣床",
        "quality": "高精度",
        "batch": "小批量",
        "expert_score": 0.9,
        "success_rate": 0.9,
        "usage_frequency": 0.8,
        "rework_rate": 0.05,
        "updated_at": datetime.now().isoformat(),
    }
    base.update(overrides)
    return base


def test_process_sim_exact_match_is_high():
    scorer = ProcessScorer()

    result = scorer.score_case(_requirement(), _case(), retrieval_score=0.8)

    assert result["process_sim"] == 1.0
    assert result["process_sim_details"]["material"] == 1.0
    assert result["process_sim_details"]["equipment"] == 1.0


def test_material_contains_match_scores_high():
    scorer = ProcessScorer()

    result = scorer.score_case(_requirement(), _case(material="6061铝合金"), retrieval_score=0.8)

    assert result["process_sim_details"]["material"] == 0.8
    assert result["process_sim"] >= 0.9


def test_mismatched_material_scores_low_for_material_field():
    scorer = ProcessScorer()

    result = scorer.score_case(_requirement(), _case(material="钛合金"), retrieval_score=0.8)

    assert result["process_sim_details"]["material"] == 0.0
    assert result["process_sim"] < 0.8


def test_unknown_fields_do_not_crash_and_score_half():
    scorer = ProcessScorer()
    requirement = _requirement()
    requirement["equipment"] = "unknown"

    result = scorer.score_case(requirement, _case(equipment="unknown"), retrieval_score=0.8)

    assert result["process_sim_details"]["equipment"] == 0.5


def test_case_quality_uses_positive_and_negative_fields():
    scorer = ProcessScorer()

    result = scorer.score_case(_requirement(), _case(), retrieval_score=0.8)

    assert result["case_quality_details"]["expert_score"] == 0.9
    assert result["case_quality_details"]["success_rate"] == 0.9
    assert result["case_quality_details"]["usage_frequency"] == 0.8
    assert result["case_quality_details"]["rework_rate"] == 0.05
    assert result["case_quality"] > 0.75


def test_high_rework_rate_lowers_case_quality():
    scorer = ProcessScorer()

    low_rework = scorer.score_case(_requirement(), _case(rework_rate=0.05), retrieval_score=0.8)
    high_rework = scorer.score_case(_requirement(), _case(rework_rate=0.8), retrieval_score=0.8)

    assert high_rework["case_quality"] < low_rework["case_quality"]


def test_time_decay_returns_different_scores_for_new_and_old_cases():
    scorer = ProcessScorer()
    new_case = _case(updated_at=datetime.now().isoformat())
    old_case = _case(updated_at=(datetime.now() - timedelta(days=500)).isoformat())

    assert scorer.time_decay(new_case) == 1.0
    assert scorer.time_decay(old_case) == 0.4


def test_fresh_quality_does_not_destroy_high_quality_old_case():
    scorer = ProcessScorer()
    old_high_quality = scorer.score_case(
        _requirement(),
        _case(
            expert_score=1.0,
            success_rate=1.0,
            usage_frequency=1.0,
            rework_rate=0.0,
            updated_at=(datetime.now() - timedelta(days=500)).isoformat(),
        ),
        retrieval_score=0.8,
    )

    assert old_high_quality["time_decay"] == 0.4
    assert old_high_quality["case_quality"] >= 0.9
    assert old_high_quality["fresh_quality"] > 0.7


def test_final_score_combines_retrieval_process_sim_and_fresh_quality():
    scorer = ProcessScorer()

    result = scorer.score_case(_requirement(), _case(), retrieval_score=0.5)

    assert result["score_breakdown"]["retrieval_score"] == 0.5
    assert result["score_breakdown"]["process_sim"] == result["process_sim"]
    assert result["score_breakdown"]["fresh_quality"] == result["fresh_quality"]
    assert 0.0 <= result["final_score"] <= 1.0
