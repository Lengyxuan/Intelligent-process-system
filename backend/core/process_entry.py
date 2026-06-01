"""
Lightweight entry for Zhijiang industrial process planning mode.

This PR only isolates the route entry. Process parsing, retrieval,
simulation, scoring, and expert review are intentionally left for later PRs.
"""
from datetime import datetime


PENDING_MODULES = {
    "process_parser": "pending",
    "process_query_enhancer": "pending",
    "process_retriever": "pending",
    "process_scorer": "pending",
    "process_evaluator": "pending",
}


PLACEHOLDER_REPLY = (
    "智匠工业模式后端入口已启用。本版本已完成工业模式与原 ARPM 链路的路由隔离。"
    "后续 PR 将接入工艺需求结构化解析、工艺查询增强、ProcessRetriever、"
    "ProcessSim 工艺相似度重排、方案生成与专家审核闭环。"
)


def handle_process_entry(request_data: dict) -> dict:
    """Return a frontend-compatible placeholder response for process mode."""
    data = request_data or {}
    session_id = data.get("session_id")
    current_round = data.get("round", 1)
    raw_message = data.get("message", "")

    print(
        "[ProcessEntry] "
        "mode=process_planning "
        "process_entry_enabled=true "
        f"session_id={session_id} "
        f"round={current_round} "
        f"raw_message={raw_message!r} "
        f"pending_modules={PENDING_MODULES}"
    )

    process_meta = {
        "mode": "process_planning",
        "process_entry_enabled": True,
        "raw_message": raw_message,
        "pending_modules": PENDING_MODULES,
        "created_at": datetime.now().isoformat(),
    }

    return {
        "session_id": session_id,
        "round": current_round,
        "status": "success",
        "reply": PLACEHOLDER_REPLY,
        "analysis": "",
        "config": {},
        "rag_context": {
            "knowledge_count": 0,
            "chat_count": 0,
            "rag_enabled": False,
            "kb_enabled": False,
            "chat_enabled": False,
            "temporal_enabled": False,
            "knowledge_blocks": [],
            "chat_blocks": [],
            "process_meta": process_meta,
        },
        "regeneration_info": None,
        "protocol_info": None,
        "process_meta": process_meta,
    }
