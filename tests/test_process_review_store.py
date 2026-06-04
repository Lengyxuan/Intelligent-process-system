import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from storage.process_review_store import ProcessReviewStore


def _review(**overrides):
    data = {
        "status": "pass",
        "reviewer": "expert",
        "comments": "方案可用",
        "raw_query": "请生成工艺方案",
        "requirement_vector": {"material": "铝合金"},
        "process_plan": {"route": [{"step": 1, "name": "粗加工"}]},
        "process_evaluation": {"plan_score": 0.82},
        "reference_cases": [],
    }
    data.update(overrides)
    return data


def test_add_review_saves_review_record(tmp_path):
    store = ProcessReviewStore(tmp_path / "process_reviews.json")

    review = store.add_review(_review())

    assert review["review_id"].startswith("REVIEW_")
    assert review["plan_id"].startswith("PLAN_")
    assert review["status"] == "pass"
    assert review["reviewer"] == "expert"


def test_list_reviews_returns_records(tmp_path):
    store = ProcessReviewStore(tmp_path / "process_reviews.json")
    store.add_review(_review(comments="one"))
    store.add_review(_review(status="reject", comments="two"))

    reviews = store.list_reviews()

    assert len(reviews) == 2
    assert {item["comments"] for item in reviews} == {"one", "two"}


def test_get_review_by_id(tmp_path):
    store = ProcessReviewStore(tmp_path / "process_reviews.json")
    review = store.add_review(_review())

    found = store.get_review(review["review_id"])

    assert found["review_id"] == review["review_id"]


def test_update_review_updates_comments_and_status(tmp_path):
    store = ProcessReviewStore(tmp_path / "process_reviews.json")
    review = store.add_review(_review(status="pass"))

    updated = store.update_review(review["review_id"], {"status": "reject", "comments": "驳回"})

    assert updated["status"] == "reject"
    assert updated["comments"] == "驳回"
    assert updated["updated_at"] != ""


def test_delete_review_removes_record(tmp_path):
    store = ProcessReviewStore(tmp_path / "process_reviews.json")
    review = store.add_review(_review())

    assert store.delete_review(review["review_id"]) is True
    assert store.get_review(review["review_id"]) is None


def test_empty_file_does_not_crash(tmp_path):
    path = tmp_path / "process_reviews.json"
    path.write_text("", encoding="utf-8")
    store = ProcessReviewStore(path)

    assert store.list_reviews() == []


def test_corrupted_file_does_not_crash(tmp_path):
    path = tmp_path / "process_reviews.json"
    path.write_text("{bad json", encoding="utf-8")
    store = ProcessReviewStore(path)

    assert store.list_reviews() == []


def test_invalid_status_raises_error(tmp_path):
    store = ProcessReviewStore(tmp_path / "process_reviews.json")

    try:
        store.add_review(_review(status="bad"))
    except ValueError as exc:
        assert "invalid review status" in str(exc)
    else:
        raise AssertionError("invalid status should raise ValueError")
