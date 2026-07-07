from __future__ import annotations

"""02 카드뉴스 브리프 정리 노드."""

import json
import re
from copy import deepcopy
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, MessageTextInput, Output
from lfx.schema.data import Data


TEMPLATE_ID = "monthly_ai_news_standard"
STANDARD_MIDDLE_ROLES = ["why", "case", "tip", "security", "workflow", "checklist", "quiz", "recap", "case", "tip", "security", "recap", "closing"]
SECURITY_KEYWORDS = ("보안", "개인정보", "기밀", "민감정보", "외부 AI", "주의")


def normalize_card_news_brief(card_news_request_value: Any, llm_brief_response: Any = "") -> dict[str, Any]:
    """LLM 브리프 응답을 검증하고 없으면 요청 원문 기반 fallback 브리프를 만듭니다."""

    payload = _payload(card_news_request_value)
    request = _dict(payload.get("card_news_request"))
    parsed = _extract_json_object(llm_brief_response)
    brief = _dict(parsed.get("brief")) if parsed else {}
    warnings = _list(_dict(payload.get("trace")).get("warnings"))
    if not brief:
        brief = _fallback_brief(request)
        warnings.append("LLM 브리프 응답이 없어 fallback 브리프를 사용했습니다.")
    else:
        brief = _normalize_brief(brief, request)

    result = deepcopy(payload)
    result["brief"] = brief
    result["trace"] = {
        **_dict(result.get("trace")),
        "warnings": _dedupe(warnings),
        "errors": _list(_dict(result.get("trace")).get("errors")),
    }
    return result


def _fallback_brief(request: dict[str, Any]) -> dict[str, Any]:
    raw = _clean(request.get("raw_content"))
    title = _title_from_text(raw) or "월간 AI 카드뉴스"
    sentences = _sentences(raw)
    must_include = sentences[:6] or ["이번 달 핵심 소식을 정리합니다."]
    constraints = [item for item in must_include if any(keyword in item for keyword in SECURITY_KEYWORDS)]
    if any(keyword in raw for keyword in SECURITY_KEYWORDS) and not constraints:
        constraints.append("보안, 개인정보, 기밀 관련 주의사항을 반드시 포함합니다.")
    cta = _dict(request.get("primary_cta"))
    return {
        "campaign_title": title,
        "audience": _clean(request.get("target_audience")) or "전 직원",
        "communication_goal": "이번 달 핵심 내용을 직원들이 빠르게 이해하고 다음 행동으로 이어지게 합니다.",
        "tone_keywords": ["귀여운", "명확한", "실용적인", "브랜드 친화적인"],
        "must_include": must_include,
        "content_pillars": [
            {"pillar_id": f"P{index + 1}", "title": _short(item, 22), "summary": item, "priority": "high" if index < 2 else "medium"}
            for index, item in enumerate(must_include[:5])
        ],
        "cta": {
            "label": _clean(cta.get("label")) or _infer_cta_label(raw),
            "url": _clean(cta.get("url")),
        },
        "publication_info": _dict(request.get("publication_info")),
        "constraints": constraints,
        "template_id": _template_id(request),
        "fixed_structure": True,
        "suggested_slide_roles": _roles_for_request(raw, _positive_int(request.get("slide_count"), 6)),
    }


def _normalize_brief(brief: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    raw = _clean(request.get("raw_content"))
    cta = _dict(brief.get("cta"))
    request_cta = _dict(request.get("primary_cta"))
    pillars = [item for item in _list(brief.get("content_pillars")) if isinstance(item, dict)]
    must_include = _strings(brief.get("must_include")) or _sentences(raw)[:6]
    if not pillars:
        pillars = [
            {"pillar_id": f"P{index + 1}", "title": _short(item, 22), "summary": item, "priority": "medium"}
            for index, item in enumerate(must_include[:5])
        ]
    constraints = _strings(brief.get("constraints"))
    if any(keyword in raw for keyword in SECURITY_KEYWORDS) and not any(any(keyword in item for keyword in SECURITY_KEYWORDS) for item in constraints):
        constraints.append("보안/개인정보/기밀 관련 주의사항을 포함합니다.")
    return {
        "campaign_title": _clean(brief.get("campaign_title")) or _title_from_text(raw) or "월간 AI 카드뉴스",
        "audience": _clean(brief.get("audience")) or _clean(request.get("target_audience")) or "전 직원",
        "communication_goal": _clean(brief.get("communication_goal")) or "핵심 내용을 쉽고 명확하게 전달합니다.",
        "tone_keywords": _strings(brief.get("tone_keywords")) or ["귀여운", "명확한", "실용적인"],
        "must_include": must_include,
        "content_pillars": pillars[:8],
        "cta": {
            "label": _clean(cta.get("label") or request_cta.get("label")) or _infer_cta_label(raw),
            "url": _safe_url(_clean(cta.get("url") or request_cta.get("url"))),
        },
        "publication_info": {**_dict(request.get("publication_info")), **_dict(brief.get("publication_info"))},
        "constraints": constraints,
        "template_id": _template_id(request),
        "fixed_structure": True,
        "suggested_slide_roles": _roles_for_request(raw, _positive_int(request.get("slide_count"), 6)),
    }


def _roles_for_request(raw: str, slide_count: int) -> list[str]:
    """월별 내용과 무관하게 같은 화면 수는 같은 역할 슬롯을 사용합니다."""

    _ = raw
    count = max(1, min(15, slide_count))
    if count == 1:
        return ["cover"]
    if count == 2:
        return ["cover", "cta"]
    middle_count = count - 2
    middle = STANDARD_MIDDLE_ROLES[:middle_count]
    return ["cover", *middle, "cta"]


def _template_id(request: dict[str, Any]) -> str:
    template = _dict(request.get("template"))
    return _clean(template.get("template_id")) or TEMPLATE_ID


def _infer_cta_label(raw: str) -> str:
    if "교육" in raw:
        return "교육 신청하기"
    if "문의" in raw:
        return "문의하기"
    if "다운로드" in raw:
        return "자료 다운로드"
    return "자세히 보기"


def _title_from_text(raw: str) -> str:
    for line in raw.splitlines():
        text = line.strip(" -#\t")
        if text:
            text = re.sub(r"^(이번 달|이번달|주제는|카드뉴스 주제는)\s*", "", text)
            return _short(text, 32)
    return ""


def _sentences(raw: str) -> list[str]:
    chunks = re.split(r"[\n\r]+|(?<=[.!?。])\s+|[①②③④⑤⑥⑦⑧⑨]|\d+\)", raw)
    result = []
    for chunk in chunks:
        text = chunk.strip(" -•\t")
        if text and text not in result:
            result.append(text)
    return result


def _extract_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return deepcopy(value)
    text = getattr(value, "text", None) or getattr(value, "content", None) or value
    if not isinstance(text, str) or not text.strip():
        return {}
    candidates = [text]
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidates.append(text[start : end + 1])
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except Exception:
            continue
        if isinstance(parsed, dict):
            return parsed
    return {}


def _payload(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return deepcopy(value)
    data = getattr(value, "data", value)
    return deepcopy(data) if isinstance(data, dict) else {}


def _dict(value: Any) -> dict[str, Any]:
    return deepcopy(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return deepcopy(value) if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    raw_items = value if isinstance(value, list) else ([value] if value not in (None, "") else [])
    result = []
    for item in raw_items:
        text = _clean(item)
        if text and text not in result:
            result.append(text)
    return result


def _positive_int(value: Any, default: int) -> int:
    try:
        return max(1, int(value))
    except Exception:
        return default


def _safe_url(value: str) -> str:
    lowered = value.lower()
    return value if not value or lowered.startswith("http://") or lowered.startswith("https://") else ""


def _short(value: Any, limit: int) -> str:
    text = _clean(value)
    return text if len(text) <= limit else text[: max(1, limit - 1)].rstrip() + "…"


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _dedupe(items: list[Any]) -> list[str]:
    result = []
    for item in items:
        text = _clean(item)
        if text and text not in result:
            result.append(text)
    return result


class CardNewsBriefNormalizer(Component):
    display_name = "02 카드뉴스 브리프 정리"
    description = "LLM 브리프 응답을 검증하고 카드뉴스 브리프 payload로 정리합니다."
    icon = "ListChecks"
    inputs = [
        DataInput(name="card_news_request", display_name="카드뉴스 요청", required=True),
        MessageTextInput(name="llm_brief_response", display_name="Agent/LLM 브리프 응답", required=False),
    ]
    outputs = [Output(name="brief_payload", display_name="카드뉴스 브리프", method="build_payload", types=["Data"])]

    def build_payload(self) -> Data:
        result = normalize_card_news_brief(
            getattr(self, "card_news_request", None),
            getattr(self, "llm_brief_response", ""),
        )
        brief = _dict(result.get("brief"))
        self.status = {
            "제목": brief.get("campaign_title"),
            "핵심 항목": len(_list(brief.get("must_include"))),
            "제약": len(_list(brief.get("constraints"))),
        }
        return Data(data=result)
