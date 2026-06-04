"""API routes for Zhijiang process expert review."""
from flask import Blueprint, jsonify, request

from core.process_review import ExpertReviewService
from storage.process_review_store import ProcessReviewStore


process_review_bp = Blueprint("process_review", __name__)


@process_review_bp.route("/api/process/review", methods=["POST"])
def submit_process_review():
    data = request.get_json() or {}
    result = ExpertReviewService().submit_review(data)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@process_review_bp.route("/api/process/reviews", methods=["GET"])
def list_process_reviews():
    return jsonify({"success": True, "reviews": ProcessReviewStore().list_reviews()})


@process_review_bp.route("/api/process/reviews/<review_id>", methods=["GET"])
def get_process_review(review_id):
    review = ProcessReviewStore().get_review(review_id)
    if not review:
        return jsonify({"success": False, "error": "review not found"}), 404
    return jsonify({"success": True, "review": review})
