"""
Rule-based parser for Zhijiang process planning requirements.

The first MVP version intentionally uses deterministic keywords and regexes.
LLM parsing, query enhancement, retrieval, scoring, and generation belong to
later PRs.
"""
import re


FIELDS = [
    "feature",
    "material",
    "batch",
    "quality",
    "equipment",
    "cost_limit",
    "time_limit",
    "process_type",
]


KEYWORDS = {
    "material": [
        "6061铝合金",
        "7075铝合金",
        "铝合金",
        "6061",
        "7075",
        "45钢",
        "不锈钢",
        "钛合金",
        "铜合金",
    ],
    "batch": ["批量生产", "小批量", "中批量", "大批量", "单件"],
    "equipment": [
        "三轴数控铣床",
        "五轴加工中心",
        "数控铣床",
        "加工中心",
        "车床",
        "磨床",
        "钻床",
    ],
    "quality": ["表面粗糙度", "一般精度", "高精度", "IT7", "IT6", "Ra1.6", "公差"],
    "process_type": ["CNC铣削", "数控铣削", "铣削", "车削", "磨削", "钻孔", "热处理", "表面处理"],
    "feature": ["薄壁件", "轴类件", "箱体件", "孔槽结构", "孔槽", "支架", "曲面", "腔体", "板件"],
    "cost_limit": ["中低成本", "低成本", "预算有限", "控制成本", "成本受限", "成本优先"],
    "time_limit": ["交付周期短", "周期短", "工期紧", "尽快交付", "两周内", "一周内"],
}


TIME_PATTERNS = [
    re.compile(r"\d+\s*(?:天|日|周|个月|月)(?:内|以内)?"),
    re.compile(r"[一二两三四五六七八九十]+\s*(?:天|日|周|个月|月)(?:内|以内)?"),
]


QUALITY_PATTERNS = [
    re.compile(r"IT\s*\d+", re.IGNORECASE),
    re.compile(r"Ra\s*\d+(?:\.\d+)?", re.IGNORECASE),
]


def _normalize_message(raw_message) -> str:
    if raw_message is None:
        return ""
    return str(raw_message).strip()


def _first_keyword(text: str, field: str) -> str:
    for keyword in KEYWORDS.get(field, []):
        if keyword in text:
            return keyword
    return "unknown"


def _first_pattern(text: str, patterns: list[re.Pattern]) -> str:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match.group(0).replace(" ", "")
    return "unknown"


def _parse_quality(text: str) -> str:
    pattern_value = _first_pattern(text, QUALITY_PATTERNS)
    if pattern_value != "unknown":
        return pattern_value
    return _first_keyword(text, "quality")


def _parse_time_limit(text: str) -> str:
    pattern_value = _first_pattern(text, TIME_PATTERNS)
    if pattern_value != "unknown":
        return pattern_value
    return _first_keyword(text, "time_limit")


def parse_process_requirement(raw_message: str) -> dict:
    """Parse a natural-language process requirement into stable fields."""
    raw_query = _normalize_message(raw_message)
    result = {
        "feature": _first_keyword(raw_query, "feature"),
        "material": _first_keyword(raw_query, "material"),
        "batch": _first_keyword(raw_query, "batch"),
        "quality": _parse_quality(raw_query),
        "equipment": _first_keyword(raw_query, "equipment"),
        "cost_limit": _first_keyword(raw_query, "cost_limit"),
        "time_limit": _parse_time_limit(raw_query),
        "process_type": _first_keyword(raw_query, "process_type"),
        "raw_query": raw_query,
        "missing_fields": [],
    }
    result["missing_fields"] = [
        field for field in FIELDS
        if result.get(field) == "unknown"
    ]
    return result
