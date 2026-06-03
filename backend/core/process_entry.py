"""
Lightweight entry for Zhijiang industrial process planning mode.

This entry keeps process planning isolated from the original ARPM role-chat
path. Expert review and knowledge feedback are intentionally left for later PRs.
"""
from datetime import datetime

from core.process_parser import parse_process_requirement
from core.process_query_enhancer import build_process_query
from core.process_retriever import ProcessRetriever
from core.process_generator import ProcessGenerator


PENDING_MODULES = {
    "process_knowledge_schema": "available",
    "process_retriever": "available",
    "process_scorer": "available",
    "process_prompt_builder": "available",
    "process_generator": "available",
    "process_evaluator": "pending",
    "expert_review": "pending",
    "knowledge_feedback": "pending",
    "file_type_router": "pending",
}


PLACEHOLDER_REPLY = (
    "智匠工业模式后端入口已启用，并已完成工艺需求结构化解析与工艺查询增强。"
    "本版本会提取材料、批量、结构特征、设备、质量要求和工艺类型等字段，"
    "并拼接面向工艺知识检索的 process_query。后续 PR 将接入 ProcessRetriever、"
    "ProcessSim 工艺相似度重排、方案生成与专家审核闭环。"
)


def handle_process_entry(request_data: dict) -> dict:
    """Return a frontend-compatible placeholder response for process mode."""
    data = request_data or {}
    session_id = data.get("session_id")
    current_round = data.get("round", 1)
    raw_message = data.get("message", "")
    requirement_vector = parse_process_requirement(raw_message)
    enhanced_query = build_process_query(
        requirement_vector.get("raw_query", raw_message),
        requirement_vector,
    )
    process_retrieval = ProcessRetriever().retrieve(
        enhanced_query.get("process_query", ""),
        requirement_vector,
        top_k=data.get("top_k"),
    )
    generation_result = ProcessGenerator().generate(
        raw_message,
        requirement_vector,
        enhanced_query,
        process_retrieval,
    )
    process_prompt = generation_result["process_prompt"]
    process_plan = generation_result["process_plan"]

    print(
        "[ProcessEntry] "
        "mode=process_planning "
        "process_entry_enabled=true "
        "requirement_parser_enabled=true "
        "process_query_enhancer_enabled=true "
        "process_retriever_enabled=true "
        "process_generation_enabled=true "
        f"session_id={session_id} "
        f"round={current_round} "
        f"raw_query={requirement_vector.get('raw_query')!r} "
        f"requirement_vector={requirement_vector} "
        f"process_query={enhanced_query.get('process_query')!r} "
        f"query_tags={enhanced_query.get('query_tags')} "
        f"process_retrieval_count={len(process_retrieval.get('results', []))} "
        f"process_plan_route_count={len(process_plan.get('route', []))} "
        f"missing_fields={requirement_vector.get('missing_fields', [])} "
        f"pending_modules={PENDING_MODULES}"
    )

    process_meta = {
        "mode": "process_planning",
        "process_entry_enabled": True,
        "requirement_parser_enabled": True,
        "process_query_enhancer_enabled": True,
        "process_retriever_enabled": True,
        "process_generation_enabled": True,
        "raw_message": raw_message,
        "raw_query": requirement_vector.get("raw_query", ""),
        "requirement_vector": requirement_vector,
        "enhanced_query": enhanced_query,
        "process_query": enhanced_query.get("process_query", ""),
        "query_tags": enhanced_query.get("query_tags", {}),
        "process_retrieval": process_retrieval,
        "process_prompt": process_prompt,
        "process_plan": process_plan,
        "missing_fields": requirement_vector.get("missing_fields", []),
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
            "process_retrieval": process_retrieval,
            "process_prompt": process_prompt,
            "process_plan": process_plan,
        },
        "regeneration_info": None,
        "protocol_info": None,
        "process_meta": process_meta,
        "process_retrieval": process_retrieval,
        "process_prompt": process_prompt,
        "process_plan": process_plan,
    }
