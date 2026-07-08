from __future__ import annotations

"""02 카드뉴스 덱 자동 기획 노드.

페이지 내용, 이미지 배치, 꾸미기 asset을 바탕으로 템플릿과 캐릭터 배치를
규칙 기반으로 자동 결정합니다.
"""

import re
from copy import deepcopy
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, MessageTextInput, Output
from lfx.schema.data import Data


ALLOWED_ROLES = {"cover", "why", "case", "tip", "checklist", "security", "workflow", "metric", "recap", "closing"}
ALLOWED_LAYOUTS = {"cover", "text_focus", "image_side", "image_focus", "checklist", "notice", "metric", "closing"}
SECURITY_WORDS = ("보안", "개인정보", "기밀", "민감", "사내", "주의", "금지", "외부")
TIP_WORDS = ("팁", "방법", "체크", "실천", "가이드", "프롬프트", "작성")
WORKFLOW_WORDS = ("자동화", "업무", "프로세스", "흐름", "단계", "절차")
METRIC_WORDS = ("%", "건", "명", "회", "지표", "수치", "증가", "감소", "효율")


def build_card_news_deck_plan(image_payload_value: Any, character_placement_mode: Any = "auto_rule") -> dict[str, Any]:
    """요청/이미지/캐릭터 정보를 합쳐 최종 렌더링 계획을 만듭니다."""

    payload = _payload(image_payload_value)
    request = _dict(payload.get("deck_request"))
    total_pages = max(_positive_int(request.get("requested_page_count"), 0), 3)
    page_specs = _page_spec_map(request)
    image_assets = _image_asset_map(payload)
    placements = _placements_by_page(payload)
    character_manifest = _dict(payload.get("character_assets"))
    character_assets = _character_assets(character_manifest)
    role_defaults = _dict(character_manifest.get("slide_role_defaults"))
    used_character_ids: list[str] = []

    slides = []
    for page_no in range(1, total_pages + 1):
        spec = page_specs.get(page_no, {})
        if page_no == 1:
            slide = _cover_slide(page_no, total_pages, request, spec)
        elif page_no == total_pages:
            slide = _closing_slide(page_no, total_pages, request, spec)
        else:
            slide = _middle_slide(page_no, total_pages, request, spec)

        image = _image_for_page(page_no, total_pages, placements, image_assets, slide["role"], slide["layout"])
        if image:
            slide["image"] = image
            slide["layout"] = _layout_with_image(slide["role"], slide["layout"], image)

        # 캐릭터는 페이지 역할과 이미지 유무를 보고 겹치지 않는 위치로 배치합니다.
        if _clean(character_placement_mode) != "manual":
            character = _select_character(slide, character_assets, role_defaults, used_character_ids)
            if character:
                character["placement"] = _character_placement(slide, image)
                character["size"] = _character_size(slide)
                used_character_ids.append(character["asset_id"])
                slide["character"] = character

        slides.append(slide)

    result = deepcopy(payload)
    result["card_news_plan"] = {
        "plan_version": "card-news-ver2-plan",
        "title": _clean(_dict(request.get("cover")).get("title")) or "카드뉴스",
        "series_title": _clean(request.get("series_title")) or "P&T AI INSIGHT",
        "issue_label": _clean(request.get("issue_label")),
        "issue_no": _clean(request.get("issue_no")),
        "publisher": _clean(request.get("publisher")) or "SK hynix",
        "page_count": len(slides),
        "aspect_ratio": "16:9",
        "slides": slides,
        "used_character_assets": _dedupe(used_character_ids),
        "navigation": {"mode": "screen_transition", "one_file_html": True},
    }
    result["trace"] = _merge_trace(result.get("trace"), [], [])
    return result


def _cover_slide(page_no: int, total_pages: int, request: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    """첫 페이지는 발행 정보가 잘 보이는 표지 템플릿으로 고정합니다."""

    cover = _dict(request.get("cover"))
    title = _clean(spec.get("title")) or _clean(cover.get("title")) or "이번 달 AI 소식"
    subtitle = _clean(spec.get("content")) or _clean(cover.get("subtitle")) or "꼭 필요한 내용만 카드뉴스로 정리했습니다."
    return {
        "slide_id": f"slide-{page_no}",
        "page": page_no,
        "page_label": f"{page_no:02d} / {total_pages:02d}",
        "role": "cover",
        "layout": "cover",
        "title": title,
        "subtitle": subtitle,
        "body": "",
        "bullets": _strings(spec.get("bullets")),
        "badge": _issue_badge(request),
        "image_refs": _strings(spec.get("image_refs") or cover.get("image_ref")),
        "character": {},
    }


def _middle_slide(page_no: int, total_pages: int, request: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    """중간 페이지는 내용 성격에 따라 역할과 레이아웃을 고릅니다."""

    title = _clean(spec.get("title"))
    subtitle = _clean(spec.get("subtitle") or spec.get("sub_title") or spec.get("summary"))
    body = _clean_preserve(spec.get("body") or spec.get("content"))
    bullets = _strings(spec.get("bullets"))
    role = _safe_token(spec.get("role") or _infer_role(title, " ".join([subtitle, body]), bullets, page_no), ALLOWED_ROLES, "case")
    if role in {"cover", "closing"}:
        role = "case"
    layout = _safe_token(_layout_for_role(role, " ".join([subtitle, body]), bullets), ALLOWED_LAYOUTS, "text_focus")
    return {
        "slide_id": f"slide-{page_no}",
        "page": page_no,
        "page_label": f"{page_no:02d} / {total_pages:02d}",
        "role": role,
        "layout": layout,
        "title": title,
        "subtitle": subtitle,
        "body": body,
        "bullets": bullets,
        "links": _normalize_links(
            spec.get("links")
            or spec.get("hyperlinks")
            or spec.get("hyperlink")
            or spec.get("link")
            or spec.get("reference_link")
            or spec.get("reference_url")
            or spec.get("url")
        ),
        "badge": _role_badge(role),
        "image_refs": _strings(spec.get("image_refs")),
        "character_hint": _clean(spec.get("character_hint")),
        "character": {},
    }


def _closing_slide(page_no: int, total_pages: int, request: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    """마지막 페이지는 CTA와 마무리 메시지가 중심인 별도 템플릿으로 고정합니다."""

    closing = _dict(request.get("closing"))
    cta = _dict(closing.get("cta"))
    title = _clean(spec.get("title")) or _clean(closing.get("title"))
    subtitle = _clean(spec.get("subtitle") or spec.get("sub_title") or closing.get("subtitle") or closing.get("summary"))
    # 마지막 페이지에 긴 소제목만 들어온 경우, 이를 큰 제목으로 올리면 화면이 쉽게 깨집니다.
    # 긴 문장은 소제목으로 내리고 제목은 짧은 기본 문구로 둡니다.
    if title and not subtitle and len(title) >= 28:
        subtitle = title
        title = ""
    return {
        "slide_id": f"slide-{page_no}",
        "page": page_no,
        "page_label": f"{page_no:02d} / {total_pages:02d}",
        "role": "closing",
        "layout": "closing",
        "title": title or "이번 달 마무리",
        "subtitle": subtitle,
        "body": _clean_preserve(spec.get("body") or spec.get("content")) or _clean_preserve(closing.get("body") or closing.get("content")) or "더 자세한 내용은 안내 링크를 확인해주세요.",
        "bullets": _strings(spec.get("bullets")),
        "links": _normalize_links(
            spec.get("links")
            or spec.get("hyperlinks")
            or spec.get("hyperlink")
            or spec.get("link")
            or closing.get("links")
            or closing.get("hyperlinks")
            or closing.get("hyperlink")
            or closing.get("link")
            or closing.get("reference_url")
            or closing.get("url")
        ),
        "badge": "마무리",
        "image_refs": _strings(spec.get("image_refs") or closing.get("image_ref")),
        "cta": {
            "label": _clean(cta.get("label")) or "처음으로",
            "url": _clean(cta.get("url")),
        },
        "character": {},
    }


def _image_for_page(
    page_no: int,
    total_pages: int,
    placements: dict[int, list[dict[str, Any]]],
    image_assets: dict[str, dict[str, Any]],
    role: str,
    layout: str,
) -> dict[str, Any]:
    """해당 페이지에 배정된 첫 번째 이미지를 계획에 붙입니다."""

    page_placements = placements.get(page_no, [])
    if not page_placements:
        return {}
    placement = page_placements[0]
    asset = image_assets.get(_clean(placement.get("image_id")), {})
    if not asset:
        return {}
    mode = _clean(placement.get("mode")) or _default_image_mode(page_no, total_pages, role, layout)
    return {
        "image_id": asset["image_id"],
        "data_uri": asset.get("data_uri", ""),
        "alt": _clean(placement.get("alt")) or _clean(asset.get("alt")) or "카드뉴스 이미지",
        "mode": mode,
        "fit": _safe_token(placement.get("fit"), {"contain", "cover", "fill"}, "contain"),
        "filename": asset.get("filename", ""),
        "width": asset.get("width", 0),
        "height": asset.get("height", 0),
    }


def _select_character(
    slide: dict[str, Any],
    assets: list[dict[str, Any]],
    role_defaults: dict[str, Any],
    used_ids: list[str],
) -> dict[str, Any]:
    """역할/힌트/반복 여부를 점수화해서 가장 알맞은 캐릭터를 고릅니다."""

    if not assets:
        return {}
    role = _clean(slide.get("role"))
    hint = _clean(slide.get("character_hint")).lower()
    text = " ".join([role, _clean(slide.get("title")), _clean(slide.get("body")), hint]).lower()
    defaults = _strings(role_defaults.get(role))
    scored = []
    for index, asset in enumerate(assets):
        asset_id = _clean(asset.get("asset_id"))
        ai_context = _clean(asset.get("ai_context")).lower()
        score = 0
        if role in _strings(asset.get("recommended_slide_roles")):
            score += 5
        if asset_id in defaults:
            score += max(1, 5 - defaults.index(asset_id))
        if hint and hint in ai_context:
            score += 4
        if role in {"security"} and "security" in ai_context:
            score += 5
        if role in {"tip", "checklist", "workflow"} and any(token in ai_context for token in ("helper", "tip", "automation")):
            score += 3
        if role == "closing" and any(token in ai_context for token in ("cta", "closing", "cover")):
            score += 3
        if any(word.lower() in text for word in SECURITY_WORDS) and "security" in ai_context:
            score += 4
        if asset_id in used_ids[-1:]:
            score -= 3
        scored.append((score, -index, asset))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    selected = deepcopy(scored[0][2])
    return {
        "asset_id": _clean(selected.get("asset_id")),
        "character_key": _clean(selected.get("character_key")),
        "pose": _clean(selected.get("pose")),
        "data_uri": _clean(selected.get("data_uri")),
        "alt": _clean(selected.get("alt") or selected.get("display_name")) or "카드뉴스 캐릭터",
    }


def _character_placement(slide: dict[str, Any], image: dict[str, Any]) -> str:
    """슬라이드 역할에 맞는 캐릭터 위치를 정합니다."""

    role = _clean(slide.get("role"))
    if role == "cover":
        return "bottom_right"
    if role == "closing":
        return "bottom_right"
    # 본문 페이지에서는 이미지 유무와 무관하게 오른쪽 빈 공간에 캐릭터를 둡니다.
    return "right_side"


def _character_size(slide: dict[str, Any]) -> str:
    role = _clean(slide.get("role"))
    if role in {"cover", "closing"}:
        return "large"
    return "small"


def _infer_role(title: str, body: str, bullets: list[str], page_no: int) -> str:
    text = " ".join([title, body, " ".join(bullets)]).lower()
    title_body = " ".join([title, body]).lower()
    security_score = sum(1 for word in SECURITY_WORDS if word.lower() in text)
    if page_no == 2 and ("왜" in title or "why" in title.lower()):
        return "why"
    if any(word.lower() in title_body for word in SECURITY_WORDS) or security_score >= 2:
        return "security"
    if any(word.lower() in text for word in TIP_WORDS):
        return "tip" if not bullets else "checklist"
    if any(word.lower() in text for word in WORKFLOW_WORDS):
        return "workflow"
    if any(word.lower() in text for word in METRIC_WORDS):
        return "metric"
    if page_no == 2:
        return "why"
    return "case"


def _layout_for_role(role: str, body: str, bullets: list[str]) -> str:
    if role == "security":
        return "notice"
    if role in {"tip", "checklist"} or bullets:
        return "checklist"
    if role == "metric":
        return "metric"
    if len(body) > 260:
        return "text_focus"
    return "text_focus"


def _layout_with_image(role: str, layout: str, image: dict[str, Any]) -> str:
    mode = _clean(image.get("mode"))
    if role == "cover":
        return "cover"
    if role == "closing":
        return "closing"
    if mode in {"image_focus", "cover_background"}:
        return "image_focus"
    if mode in {"content_area", "side_image"} and layout in {"checklist", "notice", "metric", "text_focus"}:
        return layout
    return "text_focus"


def _default_image_mode(page_no: int, total_pages: int, role: str, layout: str) -> str:
    if page_no == 1:
        return "cover_hero"
    if page_no == total_pages:
        return "closing_hero"
    if role == "metric":
        return "image_focus"
    return "content_area"


def _page_spec_map(request: dict[str, Any]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for item in _list(request.get("pages")):
        if isinstance(item, dict):
            page = _positive_int(item.get("page"), 0)
            if page:
                result[page] = deepcopy(item)
    return result


def _image_asset_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = {}
    for asset in _list(_dict(payload.get("image_assets")).get("assets")):
        if isinstance(asset, dict) and _clean(asset.get("image_id")):
            result[_clean(asset.get("image_id"))] = deepcopy(asset)
    return result


def _placements_by_page(payload: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    result: dict[int, list[dict[str, Any]]] = {}
    for item in _list(payload.get("image_placements")):
        if not isinstance(item, dict):
            continue
        page = _positive_int(item.get("page"), 0)
        if page:
            result.setdefault(page, []).append(deepcopy(item))
    return result


def _character_assets(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    assets = []
    for asset in _list(manifest.get("assets")):
        if isinstance(asset, dict) and _clean(asset.get("asset_id")) and _clean(asset.get("data_uri")):
            assets.append(deepcopy(asset))
    return assets


def _issue_badge(request: dict[str, Any]) -> str:
    parts = [_clean(request.get("issue_label")), _clean(request.get("issue_no"))]
    return " / ".join(part for part in parts if part) or "AI NEWS"


def _role_badge(role: str) -> str:
    return {
        "why": "WHY",
        "case": "사례",
        "tip": "TIP",
        "checklist": "CHECK",
        "security": "보안",
        "workflow": "흐름",
        "metric": "지표",
        "recap": "요약",
    }.get(role, "핵심")


def _safe_token(value: Any, allowed: set[str], default: str) -> str:
    text = _clean(value).lower().replace("-", "_")
    return text if text in allowed else default


def _merge_trace(trace_value: Any, warnings: list[str], errors: list[str]) -> dict[str, Any]:
    trace = _dict(trace_value)
    trace["warnings"] = _dedupe([*_list(trace.get("warnings")), *warnings])
    trace["errors"] = _dedupe([*_list(trace.get("errors")), *errors])
    return trace


def _payload(value: Any) -> dict[str, Any]:
    data = getattr(value, "data", value)
    return deepcopy(data) if isinstance(data, dict) else {}


def _dict(value: Any) -> dict[str, Any]:
    return deepcopy(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return deepcopy(value) if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    raw_items = value if isinstance(value, list) else ([value] if value not in (None, "") else [])
    return _dedupe(_clean(item) for item in raw_items)


def _normalize_links(value: Any) -> list[dict[str, str]]:
    """슬라이드 계획에 넣을 링크를 [{label, url}]로 통일합니다."""

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
    """dict/문자열 링크를 안전한 링크 dict로 바꿉니다."""

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


def _safe_url(value: str) -> bool:
    lowered = _clean(value).lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def _trim_url(value: str) -> str:
    return _clean(value).rstrip(".,;:!?)］】")


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


class CardNewsDeckPlanner(Component):
    """전체 카드뉴스 덱 계획을 만드는 Langflow 노드입니다."""

    display_name = "02 카드뉴스 전체 덱 기획"
    description = "첫/중간/마지막 페이지 템플릿을 나누고, 이미지와 캐릭터를 겹치지 않게 자동 배치합니다."
    icon = "LayoutTemplate"
    name = "CardNewsDeckPlanner"

    inputs = [
        DataInput(name="image_payload", display_name="이미지 포함 payload", required=True),
        MessageTextInput(
            name="character_placement_mode",
            display_name="캐릭터 배치 방식",
            value="auto_rule",
            info="auto_rule을 권장합니다. manual이면 입력 plan의 캐릭터 배치를 그대로 쓰는 확장용입니다.",
            required=False,
            advanced=True,
        ),
    ]
    outputs = [Output(name="card_news_plan", display_name="카드뉴스 전체 계획", method="build_payload", types=["Data"])]

    def build_payload(self) -> Data:
        result = build_card_news_deck_plan(
            getattr(self, "image_payload", None),
            getattr(self, "character_placement_mode", "auto_rule"),
        )
        plan = _dict(result.get("card_news_plan"))
        self.status = {
            "제목": plan.get("title"),
            "페이지 수": plan.get("page_count"),
            "캐릭터 사용 수": len(_list(plan.get("used_character_assets"))),
            "이동 방식": _dict(plan.get("navigation")).get("mode"),
        }
        return Data(data=result)
