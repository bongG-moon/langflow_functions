from __future__ import annotations

"""00-2 LLM 입력 정리 결과 검증 노드.

LLM이 만든 JSON 응답을 파싱하고, 00 또는 01 노드에 바로 연결할 수 있는
deck_request Data/Message 출력으로 정리합니다.
"""

import json
import re
from copy import deepcopy
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, MultilineInput, Output
from lfx.schema.data import Data
from lfx.schema.message import Message


def normalize_llm_input_response(llm_response: Any, fallback_raw_input: Any = "") -> dict[str, Any]:
    """LLM 응답에서 카드뉴스 요청 JSON을 추출하고 보정합니다."""

    parsed = _extract_json_object(llm_response)
    warnings: list[str] = []
    if not parsed:
        warnings.append("LLM 응답에서 JSON object를 찾지 못했습니다. fallback_raw_input만 보존합니다.")
        parsed = {"raw_content": _clean_preserve(fallback_raw_input)}

    normalized = _normalize_request(parsed)
    fallback_links = _links_by_page_from_raw_input(fallback_raw_input)
    if fallback_links:
        merged_count = _merge_missing_page_links(normalized, fallback_links)
        if merged_count:
            warnings.append(f"LLM 응답에서 누락된 페이지 하이퍼링크 {merged_count}개를 원본 입력에서 복구했습니다.")
    return {
        "deck_request": normalized,
        "normalization_report": {
            "status": "ok" if normalized else "error",
            "page_count": normalized.get("requested_page_count", 0),
            "middle_page_count": len(normalized.get("pages", [])),
            "warnings": warnings,
        },
    }


def _normalize_request(value: dict[str, Any]) -> dict[str, Any]:
    """LLM JSON을 ver2 deck_request 호환 스키마로 정리합니다."""

    source = _dict(value.get("deck_request") or value.get("card_news_request") or value)
    cover = _dict(source.get("cover") or source.get("first_page"))
    closing = _dict(source.get("closing") or source.get("last_page"))
    cta = _dict(closing.get("cta") or source.get("primary_cta"))
    pages = _normalize_pages(source.get("pages") or source.get("slides"))
    requested_page_count = _positive_int(source.get("page_count") or source.get("slide_count") or source.get("requested_page_count"), 0)
    if not requested_page_count:
        # page_count가 없으면 가장 큰 페이지 번호와 중간 페이지 수를 기준으로 전체 페이지 수를 추정합니다.
        # 리스트 자체와 숫자를 비교하지 않도록 페이지 번호 목록에서 먼저 최대값을 구합니다.
        max_page = max([_positive_int(page.get("page"), 0) for page in pages] or [0])
        requested_page_count = max(max_page, len(pages) + 2 if pages else 3)
    return {
        "input_mode": "llm_structured",
        "raw_content": _clean_preserve(source.get("raw_content")),
        "series_title": _clean(source.get("series_title")) or "P&T AI INSIGHT",
        "issue_label": _clean(source.get("issue_label") or source.get("issue")),
        "issue_no": _clean(source.get("issue_no") or source.get("vol") or source.get("volume")),
        "publisher": _clean(source.get("publisher")) or "SK hynix",
        "cover": {
            "title": _clean(source.get("cover_title") or cover.get("title") or source.get("title")),
            "subtitle": _clean(source.get("cover_subtitle") or cover.get("subtitle") or source.get("subtitle")),
            "image_ref": _clean(cover.get("image_ref") or source.get("cover_image_ref")),
        },
        "pages": pages,
        "closing": {
            "title": _clean(closing.get("title")),
            "subtitle": _clean(closing.get("subtitle") or closing.get("sub_title") or closing.get("summary")),
            "content": _clean_preserve(closing.get("content") or closing.get("body")),
            "image_ref": _clean(closing.get("image_ref")),
            "links": _normalize_links(
                closing.get("links")
                or closing.get("hyperlinks")
                or closing.get("hyperlink")
                or closing.get("link")
                or closing.get("reference_url")
                or closing.get("url")
            ),
            "cta": {
                "label": _clean(cta.get("label")),
                "url": _clean(cta.get("url")) if _safe_url(_clean(cta.get("url"))) else "",
            },
        },
        "requested_page_count": max(requested_page_count, 3),
        "image_placement_instruction": _clean_preserve(source.get("image_placement_instruction")),
    }


def _normalize_pages(value: Any) -> list[dict[str, Any]]:
    """LLM이 만든 pages/slides 값을 page 번호 기준으로 정리합니다."""

    if isinstance(value, dict):
        raw_pages = []
        for key, item in value.items():
            if isinstance(item, dict):
                raw = deepcopy(item)
                raw.setdefault("page", key)
                raw_pages.append(raw)
    elif isinstance(value, list):
        raw_pages = [item for item in value if isinstance(item, dict)]
    else:
        raw_pages = []

    pages: list[dict[str, Any]] = []
    for index, item in enumerate(raw_pages, start=2):
        page = _positive_int(item.get("page") or item.get("slide") or item.get("index"), index)
        image_refs = _strings(item.get("image_refs") or item.get("images"))
        image_ref = _clean(item.get("image_ref") or item.get("image"))
        if image_ref:
            image_refs.insert(0, image_ref)
        pages.append(
            {
                "page": page,
                "role": _clean(item.get("role")),
                "title": _clean(item.get("title") or item.get("headline")),
                "subtitle": _clean(item.get("subtitle") or item.get("sub_title") or item.get("subheadline") or item.get("summary") or item.get("lead")),
                "content": _clean_preserve(item.get("body") or item.get("content") or item.get("main_body") or item.get("text") or item.get("description")),
                "bullets": _strings(item.get("bullets") or item.get("items")),
                "links": _normalize_links(
                    item.get("links")
                    or item.get("hyperlinks")
                    or item.get("hyperlink")
                    or item.get("link")
                    or item.get("reference_link")
                    or item.get("reference_url")
                    or item.get("url")
                ),
                "image_refs": _dedupe(image_refs),
                "locked_text": bool(item.get("locked_text")),
            }
        )
    pages.sort(key=lambda item: item.get("page", 0))
    return pages


def _links_by_page_from_raw_input(value: Any) -> dict[int, list[dict[str, str]]]:
    """LLM이 링크를 빠뜨린 경우를 대비해 원본 입력에서 페이지별 하이퍼링크를 다시 읽습니다."""

    text = _clean_preserve(value)
    if not text:
        return {}
    pattern = re.compile(r"(?im)^\s*(?:#{1,4}\s*)?\[?\s*(\d{1,2})\s*(?:페이지|page|p|카드|화면)\s*\]?\s*[:.)-]?\s*(.*)$")
    matches = list(pattern.finditer(text))
    result: dict[int, list[dict[str, str]]] = {}
    for index, match in enumerate(matches):
        page = _positive_int(match.group(1), 0)
        if not page:
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[start:end]
        links: list[Any] = []
        for line in section.splitlines():
            key_match = re.match(
                r"^\s*(하이퍼링크|링크|참고링크|참고 URL|참고 url|hyperlink|link|url)\s*[:：]\s*(.+?)\s*$",
                line.strip(),
                flags=re.IGNORECASE,
            )
            if key_match:
                links.append(key_match.group(2).strip())
        normalized = _normalize_links(links)
        if normalized:
            result[page] = normalized
    return result


def _merge_missing_page_links(request: dict[str, Any], fallback_links: dict[int, list[dict[str, str]]]) -> int:
    """정규화된 페이지에 링크가 없을 때 원본 입력에서 복구한 링크를 병합합니다."""

    merged = 0
    pages = request.get("pages")
    if not isinstance(pages, list):
        return merged
    for page in pages:
        if not isinstance(page, dict):
            continue
        page_no = _positive_int(page.get("page"), 0)
        if not page_no or page.get("links"):
            continue
        links = fallback_links.get(page_no, [])
        if links:
            page["links"] = links
            merged += len(links)
    return merged


def _extract_json_object(value: Any) -> dict[str, Any]:
    """Message/Data/문자열에서 JSON object를 찾아 파싱합니다."""

    if isinstance(value, dict):
        return _extract_json_from_dict(value)
    data = getattr(value, "data", None)
    if data is not None:
        parsed = _extract_json_object(data)
        if parsed:
            return parsed
    value_attr = getattr(value, "value", None)
    if value_attr is not None and value_attr is not value:
        parsed = _extract_json_object(value_attr)
        if parsed:
            return parsed
    text = getattr(value, "text", None) or getattr(value, "content", None) or getattr(value, "message", None) or value
    return _extract_json_from_text(text)


def _extract_json_from_dict(value: dict[str, Any]) -> dict[str, Any]:
    """Langflow가 감싼 dict에서 실제 카드뉴스 JSON을 찾아냅니다."""

    data = deepcopy(value)
    if _looks_like_card_news_request(data):
        return data

    # LLM 노드가 {"text": "...json..."}, {"content": "...json..."}처럼 감싼 응답을 자주 반환합니다.
    for key in ("text", "content", "message", "output", "result", "response", "completion", "value"):
        if key in data:
            parsed = _extract_json_object(data[key])
            if parsed:
                return parsed

    # 일부 StructuredContent는 {"data": {...}} 또는 {"json": {...}} 형태로 들어옵니다.
    for key in ("data", "json", "payload"):
        nested = data.get(key)
        if nested is not None and nested is not value:
            parsed = _extract_json_object(nested)
            if parsed:
                return parsed

    return data


def _looks_like_card_news_request(value: dict[str, Any]) -> bool:
    """dict가 실제 카드뉴스 요청인지, 단순 wrapper인지 구분합니다."""

    request_keys = {
        "deck_request",
        "card_news_request",
        "series_title",
        "issue_label",
        "issue",
        "issue_no",
        "vol",
        "volume",
        "cover",
        "cover_title",
        "pages",
        "slides",
        "closing",
        "image_placement_instruction",
        "page_count",
        "requested_page_count",
    }
    return bool(request_keys.intersection(value.keys()))


def _extract_json_from_text(text: Any) -> dict[str, Any]:
    """문자열 안의 JSON object를 코드블록 여부와 무관하게 파싱합니다."""

    if not isinstance(text, str) or not text.strip():
        return {}
    cleaned = re.sub(r"^```(?:json|text)?", "", text.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"```$", "", cleaned.strip())
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    candidates = [cleaned]
    if start >= 0 and end > start:
        candidates.append(cleaned[start : end + 1])
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except Exception:
            continue
        if isinstance(parsed, dict):
            return parsed
    return {}


def _safe_url(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def _normalize_links(value: Any) -> list[dict[str, str]]:
    """링크 입력을 [{label, url}] 형태로 통일하고 http/https URL만 남깁니다."""

    if value in (None, ""):
        return []
    if isinstance(value, dict):
        if any(key in value for key in ("url", "href", "link")):
            raw_items = [value]
        else:
            raw_items = [{"label": label, "url": url} for label, url in value.items()]
    elif isinstance(value, list):
        raw_items = value
    else:
        raw_items = [part for part in str(value).splitlines() if part.strip()]

    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw_items:
        link = _coerce_link(item)
        if not link:
            continue
        key = link["url"]
        if key in seen:
            continue
        seen.add(key)
        result.append(link)
    return result[:3]


def _coerce_link(item: Any) -> dict[str, str]:
    """dict/문자열/마크다운 링크를 안전한 링크 dict로 바꿉니다."""

    if isinstance(item, dict):
        url = _clean(item.get("url") or item.get("href") or item.get("link"))
        label = _clean(item.get("label") or item.get("text") or item.get("title") or item.get("name")) or url
        return {"label": label, "url": url} if _safe_url(url) else {}

    text = _clean(item)
    if not text:
        return {}
    markdown = re.match(r"^\[([^\]]+)\]\((https?://[^)\s]+)\)$", text, flags=re.IGNORECASE)
    if markdown:
        return {"label": markdown.group(1).strip(), "url": _trim_url(markdown.group(2))}

    url_match = re.search(r"https?://[^\s,;|)>\]]+", text, flags=re.IGNORECASE)
    if not url_match:
        return {}
    url = _trim_url(url_match.group(0))
    label = (text[: url_match.start()] + text[url_match.end() :]).strip(" \t-–—:：|,;()[]")
    return {"label": label or url, "url": url} if _safe_url(url) else {}


def _trim_url(value: str) -> str:
    return _clean(value).rstrip(".,;:!?)］】")


def _dict(value: Any) -> dict[str, Any]:
    return deepcopy(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return deepcopy(value) if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    raw_items = value if isinstance(value, list) else ([value] if value not in (None, "") else [])
    return _dedupe(_clean(item) for item in raw_items)


def _dedupe(items: Any) -> list[str]:
    result: list[str] = []
    for item in items:
        text = _clean(item)
        if text and text not in result:
            result.append(text)
    return result


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        return default
    return max(0, parsed)


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _clean_preserve(value: Any) -> str:
    text = str(value or "").strip()
    return re.sub(r"\n{3,}", "\n\n", text)


class LlmInputNormalizer(Component):
    """LLM 응답을 00 또는 01에 연결 가능한 deck_request로 정리하는 Langflow 노드입니다."""

    display_name = "00-2 LLM 입력 정리 결과 검증"
    description = "LLM이 만든 카드뉴스 JSON을 파싱/검증하고, 00 또는 01 노드에 연결 가능한 deck_request Data와 Message로 출력합니다."
    icon = "BadgeCheck"
    name = "LlmInputNormalizer"

    inputs = [
        DataInput(
            name="llm_response",
            display_name="LLM JSON 응답",
            input_types=["Data", "Message", "Text", "JSON", "StructuredContent", "Structured Content"],
            required=True,
        ),
        MultilineInput(
            name="fallback_raw_input",
            display_name="원본 입력 fallback",
            value="",
            required=False,
            advanced=True,
        ),
    ]
    outputs = [
        Output(name="structured_data", display_name="00/01 연결용 Data", method="build_data", types=["Data"]),
        Output(name="structured_message", display_name="00/01 연결용 JSON Message", method="build_message"),
    ]

    def _result(self) -> dict[str, Any]:
        cached = getattr(self, "_cached_result", None)
        if isinstance(cached, dict):
            return cached
        result = normalize_llm_input_response(
            getattr(self, "llm_response", None),
            getattr(self, "fallback_raw_input", ""),
        )
        self._cached_result = result
        return result

    def build_data(self) -> Data:
        result = self._result()
        request = _dict(result.get("deck_request"))
        report = _dict(result.get("normalization_report"))
        self.status = {
            "상태": report.get("status"),
            "전체 페이지 수": request.get("requested_page_count"),
            "중간 페이지 수": len(request.get("pages", [])),
        }
        return Data(data=request)

    def build_message(self) -> Message:
        result = self._result()
        request = _dict(result.get("deck_request"))
        return Message(text=json.dumps(request, ensure_ascii=False, indent=2))
