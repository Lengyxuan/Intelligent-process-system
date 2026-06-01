"""
Build retrieval-oriented process queries from parsed requirements.

This module only prepares a tagged query string for later process retrieval.
It does not call ARPM retrieval, scoring, generation, or any CAD/image logic.
"""


FIELD_LABELS = [
    ("material", "材料"),
    ("batch", "批量"),
    ("feature", "结构特征"),
    ("equipment", "设备资源"),
    ("quality", "质量要求"),
    ("process_type", "工艺类型"),
    ("cost_limit", "成本约束"),
    ("time_limit", "工期约束"),
]


LEGACY_PROMPT_TERMS = ["角色扮演", "角色设定", "ARPM"]


def _value(requirement_vector: dict, field: str) -> str:
    value = (requirement_vector or {}).get(field)
    if value is None or value == "":
        return "unknown"
    return str(value)


def build_process_query(raw_query: str, requirement_vector: dict) -> dict:
    """Build a tagged process query for future process knowledge retrieval."""
    vector = requirement_vector or {}
    normalized_raw_query = raw_query if raw_query is not None else vector.get("raw_query", "")
    normalized_raw_query = str(normalized_raw_query or "")

    query_tags = {
        "industry": "机械加工",
        "task": "工艺规划",
        "material": _value(vector, "material"),
        "batch": _value(vector, "batch"),
        "feature": _value(vector, "feature"),
        "equipment": _value(vector, "equipment"),
        "quality": _value(vector, "quality"),
        "process_type": _value(vector, "process_type"),
        "cost_limit": _value(vector, "cost_limit"),
        "time_limit": _value(vector, "time_limit"),
    }

    missing_fields = list(vector.get("missing_fields") or [])
    for field in [
        "material",
        "batch",
        "feature",
        "equipment",
        "quality",
        "process_type",
        "cost_limit",
        "time_limit",
    ]:
        if query_tags[field] == "unknown" and field not in missing_fields:
            missing_fields.append(field)

    lines = [
        "[行业=机械加工]",
        "[任务=工艺规划]",
    ]
    lines.extend(
        f"[{label}={query_tags[field]}]"
        for field, label in FIELD_LABELS
    )
    lines.append(f"原始需求：{normalized_raw_query}")
    process_query = "\n".join(lines)

    for term in LEGACY_PROMPT_TERMS:
        process_query = process_query.replace(term, "")

    return {
        "raw_query": normalized_raw_query,
        "process_query": process_query,
        "query_tags": query_tags,
        "missing_fields": missing_fields,
    }
