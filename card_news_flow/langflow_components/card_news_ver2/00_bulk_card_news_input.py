from __future__ import annotations

"""00 전체 카드뉴스 입력 정리 노드.

사용자가 JSON 또는 마크다운/자연어로 전체 카드뉴스 내용을 한 번에 넣으면,
뒤 노드들이 공통으로 사용할 수 있는 표준 payload로 정리합니다.
"""

import hashlib
import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, MessageTextInput, MultilineInput, Output
from lfx.schema.data import Data


DEFAULT_SERIES_TITLE = "P&T AI INSIGHT"
DEFAULT_PUBLISHER = "SK hynix"


def build_bulk_card_news_payload(
    deck_content: Any,
    issue_label: Any = "",
    issue_no: Any = "",
    series_title: Any = DEFAULT_SERIES_TITLE,
    requested_page_count: Any = "",
    target_audience: Any = "구성원",
    tone: Any = "친근하고 실무적인 카드뉴스",
    image_placement_instruction: Any = "",
    primary_cta_label: Any = "",
    primary_cta_url: Any = "",
    llm_structured_input: Any = None,
) -> dict[str, Any]:
    """전체 입력을 표준 요청 payload로 바꿉니다."""

    structured = _extract_structured_request(llm_structured_input)
    raw_text = json.dumps(structured, ensure_ascii=False) if structured else _clean_preserve(deck_content)
    parsed = structured or _parse_json_input(raw_text)
    request = _request_from_json(parsed) if parsed else _request_from_text(raw_text)

    # 입력창에 따로 적은 값은 본문에서 추출한 값보다 우선합니다.
    request["series_title"] = _clean(series_title) or request.get("series_title") or DEFAULT_SERIES_TITLE
    request["issue_label"] = _clean(issue_label) or request.get("issue_label", "")
    request["issue_no"] = _clean(issue_no) or request.get("issue_no", "")
    request["target_audience"] = _clean(target_audience) or request.get("target_audience", "구성원")
    request["tone"] = _clean(tone) or request.get("tone", "친근하고 실무적인 카드뉴스")
    request["image_placement_instruction"] = _clean_preserve(image_placement_instruction) or request.get("image_placement_instruction", "")

    requested_count = _positive_int(requested_page_count, 0) or _positive_int(request.get("requested_page_count"), 0)
    inferred_count = _infer_page_count(request)
    request["requested_page_count"] = max(requested_count, inferred_count, 3)

    cta = _dict(request.get("closing")).get("cta") or {}
    if not isinstance(cta, dict):
        cta = {}
    label = _clean(primary_cta_label) or _clean(cta.get("label"))
    url = _clean(primary_cta_url) or _clean(cta.get("url"))
    request["closing"] = {
        **_dict(request.get("closing")),
        "cta": {
            "label": label,
            "url": url if _safe_url(url) else "",
        },
    }

    warnings = []
    if url and not _safe_url(url):
        warnings.append("CTA URL은 http 또는 https만 사용할 수 있어 제거했습니다.")
    if not raw_text:
        warnings.append("카드뉴스 본문 입력이 비어 있습니다.")

    return {
        "payload_version": "card-news-ver2",
        "flow_type": "card_news_ver2",
        "request_id": _stable_id("card_news_v2", raw_text or _now_iso()),
        "deck_request": request,
        "image_assets": {"assets": []},
        "image_placements": [],
        "character_assets": {},
        "card_news_plan": {},
        "html_result": {},
        "trace": {
            "warnings": warnings,
            "errors": [],
            "created_at": _now_iso(),
        },
    }


def _request_from_json(value: dict[str, Any]) -> dict[str, Any]:
    """JSON 입력을 ver2 요청 스키마로 정리합니다."""

    pages = value.get("pages") or value.get("slides") or []
    if not isinstance(pages, list):
        pages = []
    normalized_pages = [_normalize_page(item, index + 1) for index, item in enumerate(pages) if isinstance(item, dict)]
    closing = _dict(value.get("closing") or value.get("last_page"))
    cover = _dict(value.get("cover") or value.get("first_page"))
    cover_title = _clean(value.get("cover_title") or cover.get("title") or value.get("title"))
    cover_subtitle = _clean(value.get("cover_subtitle") or cover.get("subtitle") or value.get("subtitle"))
    return {
        "input_mode": "json",
        "raw_content": json.dumps(value, ensure_ascii=False),
        "series_title": _clean(value.get("series_title")) or DEFAULT_SERIES_TITLE,
        "issue_label": _clean(value.get("issue_label") or value.get("issue")),
        "issue_no": _clean(value.get("issue_no") or value.get("vol") or value.get("volume")),
        "publisher": _clean(value.get("publisher")) or DEFAULT_PUBLISHER,
        "cover": {
            "title": cover_title,
            "subtitle": cover_subtitle,
            "image_ref": _clean(cover.get("image_ref") or value.get("cover_image_ref")),
        },
        "pages": normalized_pages,
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
            "cta": _dict(closing.get("cta")),
        },
        "requested_page_count": _positive_int(value.get("requested_page_count") or value.get("page_count") or value.get("slide_count"), 0),
        "image_placement_instruction": _clean_preserve(value.get("image_placement_instruction")),
    }


def _request_from_text(text: str) -> dict[str, Any]:
    """자연어/마크다운 입력에서 발행 정보와 페이지 섹션을 추출합니다."""

    meta = _extract_text_meta(text)
    pages = _extract_page_sections(text)
    cover_title = meta.get("cover_title") or meta.get("title") or _first_page_title(pages) or "이번 달 AI 소식"
    cover_subtitle = meta.get("cover_subtitle") or "꼭 필요한 내용만 카드뉴스로 정리했습니다."
    closing_title = meta.get("closing_title") or "다음 소식에서 만나요"
    closing_content = meta.get("closing_content") or "더 자세한 내용은 안내 링크를 확인해주세요."
    return {
        "input_mode": "text",
        "raw_content": text,
        "series_title": meta.get("series_title") or DEFAULT_SERIES_TITLE,
        "issue_label": meta.get("issue_label", ""),
        "issue_no": meta.get("issue_no", ""),
        "publisher": DEFAULT_PUBLISHER,
        "cover": {"title": cover_title, "subtitle": cover_subtitle, "image_ref": meta.get("cover_image_ref", "")},
        "pages": pages,
        "closing": {
            "title": closing_title,
            "content": closing_content,
            "image_ref": meta.get("closing_image_ref", ""),
            "cta": {"label": meta.get("cta_label", ""), "url": meta.get("cta_url", "")},
        },
        "requested_page_count": _positive_int(meta.get("page_count"), 0),
        "image_placement_instruction": meta.get("image_placement_instruction", ""),
    }


def _extract_text_meta(text: str) -> dict[str, str]:
    """줄 단위 메타 정보와 이미지 배치 지시를 읽습니다."""

    meta: dict[str, str] = {}
    key_map = {
        "소식지": "series_title",
        "시리즈": "series_title",
        "호수": "issue_label",
        "발행호": "issue_label",
        "vol": "issue_no",
        "표지 제목": "cover_title",
        "표지 부제": "cover_subtitle",
        "제목": "title",
        "마지막 제목": "closing_title",
        "마지막 내용": "closing_content",
        "cta": "cta_label",
        "cta url": "cta_url",
        "페이지수": "page_count",
        "페이지 수": "page_count",
        "이미지 배치": "image_placement_instruction",
    }
    for line in text.splitlines():
        match = re.match(r"^\s*([^:：]{1,20})\s*[:：]\s*(.+?)\s*$", line)
        if not match:
            continue
        label = match.group(1).strip().lower()
        value = match.group(2).strip()
        mapped = key_map.get(label)
        if mapped and value:
            meta[mapped] = value
    if not meta.get("issue_label"):
        match = re.search(r"(\d{4}\s*년\s*\d{1,2}\s*월호|vol\.?\s*\d+|\d+\s*호)", text, flags=re.IGNORECASE)
        if match:
            meta["issue_label"] = match.group(1).strip()
    if not meta.get("image_placement_instruction"):
        for line in text.splitlines():
            if "이미지" in line and "페이지" in line and re.search(r"\d", line):
                meta["image_placement_instruction"] = line.strip()
                break
    return meta


def _extract_page_sections(text: str) -> list[dict[str, Any]]:
    """[2페이지] 같은 헤더를 기준으로 각 페이지 내용을 분리합니다."""

    pattern = re.compile(r"(?im)^\s*(?:#{1,4}\s*)?\[?\s*(\d{1,2})\s*(?:페이지|page|p|카드|화면)\s*\]?\s*[:.)-]?\s*(.*)$")
    matches = list(pattern.finditer(text))
    if not matches:
        return _fallback_pages_from_text(text)

    pages: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        page_no = _positive_int(match.group(1), index + 1)
        inline_title = _clean(match.group(2))
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[start:end].strip()
        page = _parse_page_section(section, page_no, inline_title)
        pages.append(page)
    return pages


def _parse_page_section(section: str, page_no: int, inline_title: str = "") -> dict[str, Any]:
    """페이지 섹션 안의 제목/소제목/본문/이미지/하이퍼링크를 정리합니다."""

    title = inline_title
    subtitle = ""
    body_lines: list[str] = []
    bullets: list[str] = []
    image_refs: list[str] = []
    links: list[Any] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped:
            body_lines.append("")
            continue
        key_match = re.match(
            r"^\s*(제목|타이틀|title|소제목|부제|요약|subtitle|sub_title|본문|내용|body|이미지|image|하이퍼링크|링크|참고링크|hyperlink|link|url|bullet|bullets|항목)\s*[:：]\s*(.*)$",
            stripped,
            flags=re.IGNORECASE,
        )
        if key_match:
            key = key_match.group(1).lower()
            value = key_match.group(2).strip()
            if key in {"제목", "타이틀", "title"}:
                title = value
            elif key in {"소제목", "부제", "요약", "subtitle", "sub_title"}:
                subtitle = value
            elif key in {"이미지", "image"}:
                image_refs.extend(_split_refs(value))
            elif key in {"하이퍼링크", "링크", "참고링크", "hyperlink", "link", "url"}:
                links.append(value)
            elif key in {"bullet", "bullets", "항목"}:
                bullets.extend(_split_refs(value))
            else:
                body_lines.append(value)
            continue
        if re.match(r"^\s*[-*]\s+", stripped):
            bullets.append(re.sub(r"^\s*[-*]\s+", "", stripped).strip())
        else:
            body_lines.append(stripped)
    return _normalize_page(
        {
            "page": page_no,
            "title": title,
            "subtitle": subtitle,
            "content": _clean_preserve("\n".join(body_lines)),
            "bullets": bullets,
            "image_refs": image_refs,
            "links": links,
        },
        page_no,
    )


def _fallback_pages_from_text(text: str) -> list[dict[str, Any]]:
    """페이지 구분이 없을 때는 문단을 2~4개의 중간 페이지로 나눕니다."""

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not paragraphs:
        return []
    pages = []
    for index, paragraph in enumerate(paragraphs[:4], start=2):
        first_line = paragraph.splitlines()[0].strip()
        title = first_line[:36] if len(first_line) <= 36 else f"{first_line[:33]}..."
        pages.append(_normalize_page({"page": index, "title": title, "content": paragraph}, index))
    return pages


def _normalize_page(item: dict[str, Any], fallback_page: int) -> dict[str, Any]:
    """입력 페이지 객체를 renderer가 쓰기 좋은 형태로 통일합니다."""

    page = _positive_int(item.get("page") or item.get("slide") or item.get("index"), fallback_page)
    content = _clean_preserve(item.get("content") or item.get("body") or item.get("text"))
    image_refs = _strings(item.get("image_refs") or item.get("images"))
    single_ref = _clean(item.get("image_ref") or item.get("image"))
    if single_ref:
        image_refs.insert(0, single_ref)
    return {
        "page": page,
        "role": _clean(item.get("role")),
        "title": _clean(item.get("title") or item.get("headline")),
        "subtitle": _clean(item.get("subtitle") or item.get("sub_title") or item.get("subheadline") or item.get("summary") or item.get("lead")),
        "content": content,
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


def _infer_page_count(request: dict[str, Any]) -> int:
    """명시 페이지 번호와 페이지 목록을 보고 전체 페이지 수를 추정합니다."""

    pages = [page for page in _list(request.get("pages")) if isinstance(page, dict)]
    max_page = max([_positive_int(page.get("page"), 0) for page in pages] or [0])
    # 표지와 마지막 페이지가 별도 템플릿이므로 최소 3페이지를 보장합니다.
    return max(max_page, len(pages) + 2 if pages else 3)


def _parse_json_input(text: str) -> dict[str, Any]:
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:
        return {}
    return deepcopy(parsed) if isinstance(parsed, dict) else {}


def _extract_structured_request(value: Any) -> dict[str, Any]:
    """LLM 정리 노드가 넘긴 Data/Message/JSON 문자열에서 요청 JSON을 꺼냅니다."""

    if value is None:
        return {}
    if isinstance(value, dict):
        data = deepcopy(value)
    else:
        data_attr = getattr(value, "data", None)
        value_attr = getattr(value, "value", None)
        text_attr = getattr(value, "text", None) or getattr(value, "content", None)
        if isinstance(data_attr, dict):
            data = deepcopy(data_attr)
        elif isinstance(value_attr, dict):
            data = deepcopy(value_attr)
        elif isinstance(text_attr, str):
            data = _parse_json_input(_extract_json_text(text_attr))
        elif isinstance(value, str):
            data = _parse_json_input(_extract_json_text(value))
        else:
            data = {}
    if not isinstance(data, dict):
        return {}
    if isinstance(data.get("deck_request"), dict):
        return deepcopy(data["deck_request"])
    if isinstance(data.get("card_news_request"), dict):
        return deepcopy(data["card_news_request"])
    return data if any(key in data for key in ("pages", "cover_title", "cover", "closing", "series_title")) else {}


def _extract_json_text(text: str) -> str:
    """LLM이 코드블록으로 감싼 JSON도 파싱할 수 있게 JSON 본문만 자릅니다."""

    cleaned = _clean_preserve(text)
    cleaned = re.sub(r"^```(?:json|text)?", "", cleaned.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"```$", "", cleaned.strip())
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        return cleaned[start : end + 1]
    return cleaned


def _stable_id(prefix: str, text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_url(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def _normalize_links(value: Any) -> list[dict[str, str]]:
    """링크 입력을 [{label, url}]로 통일합니다."""

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
        if not link or link["url"] in seen:
            continue
        seen.add(link["url"])
        result.append(link)
    return result[:3]


def _coerce_link(item: Any) -> dict[str, str]:
    """dict, 마크다운 링크, '표시문구 | URL' 문자열을 링크 dict로 바꿉니다."""

    if isinstance(item, dict):
        url = _clean(item.get("url") or item.get("href") or item.get("link"))
        label = _clean(item.get("label") or item.get("text") or item.get("title") or item.get("name")) or url
        return {"label": label, "url": url} if _safe_url(url) else {}

    text = _clean(item)
    if not text:
        return {}
    markdown = re.match(r"^\[([^\]]+)\]\((https?://[^)\s]+)\)$", text, flags=re.IGNORECASE)
    if markdown:
        url = _trim_url(markdown.group(2))
        return {"label": markdown.group(1).strip(), "url": url} if _safe_url(url) else {}

    url_match = re.search(r"https?://[^\s,;|)>\]]+", text, flags=re.IGNORECASE)
    if not url_match:
        return {}
    url = _trim_url(url_match.group(0))
    label = (text[: url_match.start()] + text[url_match.end() :]).strip(" \t-–—:：|,;()[]")
    return {"label": label or url, "url": url} if _safe_url(url) else {}


def _trim_url(value: str) -> str:
    return _clean(value).rstrip(".,;:!?)］】")


def _first_page_title(pages: list[dict[str, Any]]) -> str:
    for page in pages:
        title = _clean(page.get("title"))
        if title:
            return title
    return ""


def _split_refs(value: Any) -> list[str]:
    return [part.strip() for part in re.split(r"[,;/|]+", _clean(value)) if part.strip()]


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


def _dict(value: Any) -> dict[str, Any]:
    return deepcopy(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return deepcopy(value) if isinstance(value, list) else []


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _clean_preserve(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


class BulkCardNewsInput(Component):
    """전체 카드뉴스 입력을 받는 Langflow 노드입니다."""

    display_name = "00 카드뉴스 전체 입력"
    description = "전체 페이지 내용, 발행호, CTA, 이미지 배치 지시를 한 번에 받아 카드뉴스 ver2 표준 payload로 정리합니다."
    icon = "PanelsTopLeft"
    name = "BulkCardNewsInput"

    inputs = [
        MultilineInput(
            name="deck_content",
            display_name="전체 카드뉴스 내용",
            info="JSON 또는 [2페이지] 형식의 마크다운/자연어를 넣으세요. 첫 페이지와 마지막 페이지는 별도 템플릿으로 자동 구성됩니다.",
            required=False,
        ),
        DataInput(
            name="llm_structured_input",
            display_name="LLM 정리 JSON 입력",
            info="선택 입력입니다. 앞단 LLM 정규화 노드의 Data 출력을 연결하면 이 값이 전체 카드뉴스 내용보다 우선 적용됩니다.",
            input_types=["Data", "Message", "Text", "JSON", "StructuredContent", "Structured Content"],
            required=False,
        ),
        MessageTextInput(name="issue_label", display_name="발행호/월호", value="", required=False),
        MessageTextInput(name="issue_no", display_name="Vol/회차", value="", required=False),
        MessageTextInput(name="series_title", display_name="소식지명", value=DEFAULT_SERIES_TITLE, required=False),
        MessageTextInput(
            name="requested_page_count",
            display_name="전체 페이지 수",
            info="선택 입력입니다. 비워두면 입력된 페이지 번호와 페이지 목록을 보고 자동 계산합니다.",
            value="",
            required=False,
            advanced=True,
        ),
        MessageTextInput(name="target_audience", display_name="대상 독자", value="구성원", advanced=True),
        MessageTextInput(name="tone", display_name="톤앤매너", value="친근하고 실무적인 카드뉴스", advanced=True),
        MultilineInput(
            name="image_placement_instruction",
            display_name="이미지 배치 지시",
            info="예: 이미지 4개를 각각 1, 3, 4, 5페이지에 넣어줘",
            value="",
            required=False,
        ),
        MessageTextInput(name="primary_cta_label", display_name="마지막 CTA 문구", value="", required=False),
        MessageTextInput(name="primary_cta_url", display_name="마지막 CTA URL", value="", required=False),
    ]
    outputs = [Output(name="payload", display_name="카드뉴스 요청 payload", method="build_payload", types=["Data"])]

    def build_payload(self) -> Data:
        result = build_bulk_card_news_payload(
            getattr(self, "deck_content", ""),
            getattr(self, "issue_label", ""),
            getattr(self, "issue_no", ""),
            getattr(self, "series_title", DEFAULT_SERIES_TITLE),
            getattr(self, "requested_page_count", ""),
            getattr(self, "target_audience", "구성원"),
            getattr(self, "tone", "친근하고 실무적인 카드뉴스"),
            getattr(self, "image_placement_instruction", ""),
            getattr(self, "primary_cta_label", ""),
            getattr(self, "primary_cta_url", ""),
            getattr(self, "llm_structured_input", None),
        )
        request = result["deck_request"]
        self.status = {
            "소식지명": request.get("series_title"),
            "발행호": request.get("issue_label"),
            "Vol": request.get("issue_no"),
            "전체 페이지 수": request.get("requested_page_count"),
            "입력 페이지 수": len(request.get("pages", [])),
        }
        return Data(data=result)
