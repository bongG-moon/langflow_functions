from __future__ import annotations

"""05 카드뉴스 계획 검증 노드."""

import html
import json
import re
from copy import deepcopy
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, MessageTextInput, Output
from lfx.schema.data import Data


TEMPLATE_ID = "monthly_ai_news_standard"
STANDARD_MIDDLE_ROLES = ["why", "case", "tip", "security", "workflow", "checklist", "quiz", "recap", "case", "tip", "security", "recap", "closing"]
ALLOWED_ROLES = {"cover", "intro", "why", "case", "workflow", "tip", "checklist", "security", "caution", "quiz", "answer", "recap", "cta", "closing", "image"}
ALLOWED_LAYOUTS = {"cover_character", "character_speech", "sticker_grid", "checklist_note", "notice_board", "quiz_card", "cta_character", "image_full", "image_contain", "image_cover"}
ALLOWED_ANIMATIONS = {"none", "fade_up", "slide_in", "float_in", "pulse_soft", "stagger"}
ALLOWED_CONTENT_BLOCK_TYPES = {"lead", "highlight", "mini_cards", "steps", "checklist", "quote", "metric", "tag_row"}
ALLOWED_CONTENT_TONES = {"red", "orange", "soft", "blue", "green", "neutral"}
ALLOWED_IMAGE_PREFIXES = ("data:image/png;base64,", "data:image/jpeg;base64,", "data:image/webp;base64,")
PLACEHOLDER_MARKERS = ("PUT_BASE64", "PUT_APPROVED_BASE64", "...")
DEFAULT_STYLE = {
    "theme": "sk_cute_soft",
    "brand": "sk_hynix",
    "accent_color": "#EA002C",
    "secondary_color": "#F47725",
    "background_color": "#FFF7ED",
    "surface_color": "#FFFDF7",
    "density": "comfortable",
}
ROLE_LAYOUT = {
    "cover": "cover_character",
    "intro": "character_speech",
    "why": "character_speech",
    "case": "sticker_grid",
    "workflow": "sticker_grid",
    "tip": "checklist_note",
    "checklist": "checklist_note",
    "security": "character_speech",
    "caution": "notice_board",
    "quiz": "quiz_card",
    "answer": "quiz_card",
    "recap": "sticker_grid",
    "cta": "cta_character",
    "closing": "cta_character",
    "image": "image_full",
}
SECURITY_KEYWORDS = ("보안", "개인정보", "기밀", "민감정보", "외부 AI", "주의")


def normalize_card_news_plan(character_payload_value: Any, llm_plan_response: Any = "") -> dict[str, Any]:
    """LLM 카드뉴스 계획을 검증하고 renderer용 plan으로 정리합니다."""

    payload = _payload(character_payload_value)
    parsed = _extract_json_object(llm_plan_response)
    plan = _dict(parsed.get("card_news_plan")) if parsed else {}
    warnings = _list(_dict(payload.get("trace")).get("warnings"))
    if not plan:
        plan = _fallback_plan(payload)
        warnings.append("LLM 카드뉴스 계획 응답이 없어 fallback 계획을 사용했습니다.")
    plan, validation_warnings = _normalize_plan(plan, payload)
    warnings.extend(validation_warnings)

    result = deepcopy(payload)
    result["card_news_plan"] = plan
    result["trace"] = {
        **_dict(result.get("trace")),
        "warnings": _dedupe(warnings),
        "errors": _list(_dict(result.get("trace")).get("errors")),
    }
    return result


def _fallback_plan(payload: dict[str, Any]) -> dict[str, Any]:
    request = _dict(payload.get("card_news_request"))
    brief = _dict(payload.get("brief"))
    title = _clean(brief.get("campaign_title")) or "월간 AI 카드뉴스"
    must_include = _strings(brief.get("must_include"))
    pillars = [item for item in _list(brief.get("content_pillars")) if isinstance(item, dict)]
    slide_count = _positive_int(request.get("slide_count"), 6)
    roles = _template_roles(slide_count)

    slides = []
    for index, role in enumerate(roles):
        content = _content_for_role(role, title, brief, must_include, pillars, index)
        slides.append(
            {
                "slide_id": f"slide-{index + 1}",
                "role": role,
                "layout": ROLE_LAYOUT.get(role, "sticker_grid"),
                "headline": content["headline"],
                "body": content["body"],
                "bullets": content["bullets"],
                "content_blocks": _fallback_content_blocks(role, content),
                "animation": "fade_up" if index == 0 else ("stagger" if role in {"tip", "checklist"} else "slide_in"),
                "buttons": [],
            }
        )
    return {
        "title": title,
        "subtitle": _clean(brief.get("communication_goal")) or "이번 달 핵심 내용을 귀엽고 쉽게 정리했습니다.",
        "template_id": _template_id(request),
        "fixed_structure": True,
        "aspect_ratio": _clean(request.get("aspect_ratio")) or "16:9",
        "publication_info": _publication_info(request, brief, {}),
        "style": deepcopy(DEFAULT_STYLE),
        "slides": slides,
        "navigation": {"mode": "screen_transition", "show_progress": True, "show_home_button": True},
    }


def _template_roles(slide_count: int) -> list[str]:
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


def _content_for_role(role: str, title: str, brief: dict[str, Any], must_include: list[str], pillars: list[dict[str, Any]], index: int) -> dict[str, Any]:
    cta = _dict(brief.get("cta"))
    if role == "cover":
        return {"headline": title, "body": _clean(brief.get("communication_goal")) or "이번 달 소식을 한눈에 정리했어요.", "bullets": []}
    if role == "why":
        return {"headline": "왜 지금 중요할까요?", "body": must_include[0] if must_include else "이번 달 꼭 알아야 할 변화와 실천 포인트를 살펴봅니다.", "bullets": must_include[1:3]}
    if role in {"case", "workflow"}:
        item = pillars[min(max(index - 2, 0), len(pillars) - 1)] if pillars else {}
        return {
            "headline": _clean(item.get("title")) or "AI 활용 사례",
            "body": _clean(item.get("summary")) or (must_include[index % len(must_include)] if must_include else "반복 업무를 줄이는 활용 사례를 소개합니다."),
            "bullets": must_include[index : index + 2],
        }
    if role in {"tip", "checklist"}:
        return {"headline": "바로 써먹는 AI 팁", "body": "작게 시작하고, 결과를 확인하며, 보안 기준을 지키는 것이 좋아요.", "bullets": must_include[:3] or ["목적을 먼저 적기", "필요한 형식을 말하기", "민감정보는 넣지 않기"]}
    if role in {"security", "caution"}:
        bullets = [item for item in must_include if any(keyword in item for keyword in SECURITY_KEYWORDS)]
        return {"headline": "AI 사용 전 꼭 확인해요", "body": "회사 기밀과 개인정보는 외부 AI 도구에 입력하지 않도록 주의합니다.", "bullets": bullets[:3] or ["개인정보 입력 금지", "회사 기밀 입력 금지", "결과는 사람이 확인하기"]}
    if role == "quiz":
        return {"headline": "잠깐 퀴즈!", "body": "회사 기밀을 외부 AI 도구에 넣어도 될까요?", "bullets": ["정답은 다음 카드에서 확인해요."]}
    if role in {"recap", "closing"}:
        return {"headline": "이번 달 핵심만 다시 보기", "body": "AI는 편리하지만, 목적과 보안 기준을 함께 챙길 때 더 안전하게 쓸 수 있어요.", "bullets": must_include[:3]}
    return {"headline": _clean(cta.get("label")) or "다음 행동으로 이어가요", "body": "더 자세한 내용은 아래 버튼을 눌러 확인하세요.", "bullets": []}


def _normalize_plan(plan: dict[str, Any], payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    request = _dict(payload.get("card_news_request"))
    brief = _dict(payload.get("brief"))
    warnings: list[str] = []
    style = {**DEFAULT_STYLE, **_dict(plan.get("style"))}
    style["theme"] = _safe_token(style.get("theme"), {"sk_cute_soft", "cute_soft", "sticker_note", "mascot_bubble", "pastel_notice", "quiz_play"}, "sk_cute_soft")
    style["brand"] = _clean(style.get("brand")) or "sk_hynix"
    slides = [slide for slide in _list(plan.get("slides")) if isinstance(slide, dict)]
    target_count = min(max(_positive_int(request.get("slide_count"), len(slides) or 6), 3), 15)
    fallback_slides = _list(_fallback_plan(payload).get("slides"))
    if len(slides) < target_count:
        warnings.append(f"slide 수가 요청한 {target_count}장보다 적어 고정 템플릿 슬롯으로 보강했습니다.")
    if len(slides) > target_count:
        warnings.append(f"slide 수가 요청한 {target_count}장을 넘어 초과 slide를 제거했습니다.")
    slides = slides[:target_count]
    while len(slides) < target_count:
        fallback_index = len(slides)
        fallback_slide = fallback_slides[fallback_index] if fallback_index < len(fallback_slides) else {"slide_id": f"slide-{fallback_index + 1}"}
        slides.append(fallback_slide)

    template_roles = _template_roles(target_count)
    page_overrides, slide_id_overrides = _image_override_maps(payload)
    invalid_overrides = [
        str(key)
        for key, override in {**{f"page {key}": value for key, value in page_overrides.items()}, **slide_id_overrides}.items()
        if not override.get("valid_data_uri")
    ]
    if invalid_overrides:
        warnings.append("이미지 대체 data_uri가 비어 있거나 지원 형식이 아닙니다: " + ", ".join(invalid_overrides))
    normalized_slides = []
    used_asset_ids: list[str] = []
    for index, slide in enumerate(slides):
        candidate_slide_id = _clean(slide.get("slide_id")) or f"slide-{index + 1}"
        image_override = page_overrides.get(index + 1) or slide_id_overrides.get(candidate_slide_id)
        normalized = _normalize_slide(slide, index, target_count, payload, used_asset_ids, template_roles[index], image_override)
        asset_id = _clean(_dict(normalized.get("character")).get("asset_id"))
        if asset_id:
            used_asset_ids.append(asset_id)
        normalized_slides.append(normalized)

    publication_info = _publication_info(request, brief, plan)
    if normalized_slides and not _dict(normalized_slides[0].get("image_override")):
        normalized_slides[0]["publication_info"] = publication_info
        if publication_info.get("issue_label"):
            normalized_slides[0]["badge"] = publication_info["issue_label"]

    normalized_slides = _attach_navigation_buttons(normalized_slides, _dict(brief.get("cta")))
    return (
        {
            "title": _clean(plan.get("title")) or _clean(brief.get("campaign_title")) or "월간 AI 카드뉴스",
            "subtitle": _clean(plan.get("subtitle")) or _clean(brief.get("communication_goal")),
            "template_id": _template_id(request),
            "fixed_structure": True,
            "template_contract": "비이미지 slide는 topbar, 우측 character_area, 하단 action_area가 고정된 SNS 가로 카드 템플릿에 렌더링되며 content_area 내부는 허용된 content_blocks로 디자인할 수 있습니다.",
            "aspect_ratio": _safe_token(request.get("aspect_ratio") or plan.get("aspect_ratio"), {"16:9", "1:1", "4:5", "9:16"}, "16:9"),
            "publication_info": publication_info,
            "style": style,
            "slides": normalized_slides,
            "navigation": {
                "mode": "screen_transition",
                "show_progress": bool(_dict(plan.get("navigation")).get("show_progress", True)),
                "show_home_button": bool(_dict(plan.get("navigation")).get("show_home_button", True)),
            },
            "used_assets": used_asset_ids,
            "validation_report": {"passed": True, "warnings": warnings},
        },
        warnings,
    )


def _normalize_slide(
    slide: dict[str, Any],
    index: int,
    total: int,
    payload: dict[str, Any],
    used_asset_ids: list[str],
    expected_role: str,
    image_override: dict[str, Any] | None,
) -> dict[str, Any]:
    slide_id = _clean(slide.get("slide_id")) or f"slide-{index + 1}"
    if image_override:
        normalized_override = _normalize_image_override(image_override)
        if normalized_override.get("render_mode") != "full_card":
            role = _safe_token(expected_role, ALLOWED_ROLES, "case")
            layout = ROLE_LAYOUT.get(role, "sticker_grid")
            return {
                "slide_id": slide_id,
                "role": role,
                "template_role": role,
                "layout": layout,
                "headline": "",
                "body": "",
                "bullets": [],
                "content_blocks": [],
                "badge": _clean_text(slide.get("badge")) or "이미지 자료",
                "character": {},
                "animation": "fade_up",
                "buttons": [button for button in _list(slide.get("buttons")) if isinstance(button, dict)][:3],
                "click_target": _clean(slide.get("click_target")),
                "image_override": normalized_override,
            }
        return {
            "slide_id": slide_id,
            "role": "image",
            "template_role": expected_role,
            "layout": _image_layout(normalized_override.get("fit")),
            "headline": "",
            "body": "",
            "bullets": [],
            "content_blocks": [],
            "badge": "",
            "character": {},
            "animation": "fade_up",
            "buttons": [],
            "click_target": "",
            "image_override": normalized_override,
        }

    role = _safe_token(expected_role, ALLOWED_ROLES, "cover" if index == 0 else ("cta" if index == total - 1 else "case"))
    layout = ROLE_LAYOUT.get(role, "sticker_grid")
    animation = _safe_token(slide.get("animation"), ALLOWED_ANIMATIONS, "fade_up")
    character = _dict(slide.get("character"))
    asset_id = _clean(character.get("asset_id"))
    asset_context = _dict(payload.get("character_asset_context"))
    valid_ids = {_clean(asset.get("asset_id")) for asset in _list(asset_context.get("available_character_assets")) if isinstance(asset, dict)}
    if not asset_id or asset_id not in valid_ids:
        selected = _select_asset_for_slide({**slide, "role": role, "layout": layout}, asset_context, used_asset_ids)
        if selected:
            character = {
                "asset_id": selected.get("asset_id", ""),
                "character_key": selected.get("character_key", ""),
                "pose": selected.get("pose", ""),
                "placement": _first(_list(selected.get("placement_hints")), "bottom_right"),
                "animation": _first(_list(selected.get("animation_hints")), "float_in"),
            }
    headline = _clean_text(slide.get("headline") or slide.get("title")) or f"카드 {index + 1}"
    body = _clean_text(slide.get("body") or slide.get("description"))
    bullets = _text_items(slide.get("bullets") or slide.get("items"))[:5]
    return {
        "slide_id": slide_id,
        "role": role,
        "template_role": role,
        "layout": layout,
        "headline": headline,
        "body": body,
        "bullets": bullets,
        "content_blocks": _normalize_content_blocks(
            slide.get("content_blocks") or slide.get("content_design") or slide.get("blocks"),
            role,
            body,
            bullets,
        ),
        "badge": _clean_text(slide.get("badge")),
        "character": character,
        "animation": animation,
        "buttons": [button for button in _list(slide.get("buttons")) if isinstance(button, dict)][:3],
        "click_target": _clean(slide.get("click_target")),
        "image_override": {},
    }


def _select_asset_for_slide(slide: dict[str, Any], asset_context: dict[str, Any], used_asset_ids: list[str]) -> dict[str, Any]:
    assets = [asset for asset in _list(asset_context.get("available_character_assets")) if isinstance(asset, dict)]
    if not assets:
        return {}
    role = _clean(slide.get("role")).lower()
    layout = _clean(slide.get("layout")).lower()
    text = " ".join(str(slide.get(key) or "") for key in ("role", "layout", "headline", "body")).lower()
    defaults = _tokens(_dict(asset_context.get("slide_role_defaults")).get(role))
    scored = []
    for index, asset in enumerate(assets):
        asset_id = _clean(asset.get("asset_id"))
        score = 0
        if role in _tokens(asset.get("recommended_slide_roles")):
            score += 5
        if asset_id in defaults:
            score += max(1, 5 - defaults.index(asset_id))
        if layout in _tokens(asset.get("recommended_layouts")):
            score += 2
        ai_context = _clean(asset.get("ai_context")).lower()
        character_key = _clean(asset.get("character_key")).lower()
        for rule in _list(asset_context.get("selection_rules")):
            if not isinstance(rule, dict):
                continue
            if any(keyword and keyword in text for keyword in _tokens(rule.get("when_keywords"))):
                if ai_context in _tokens(rule.get("prefer_ai_contexts")):
                    score += 4
                if character_key in _tokens(rule.get("prefer_character_keys")):
                    score += 2
                if ai_context in _tokens(rule.get("avoid_ai_contexts")):
                    score -= 4
        if asset_id in used_asset_ids[-1:]:
            score -= 2
        scored.append((score, -index, asset))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return deepcopy(scored[0][2]) if scored else {}


def _normalize_content_blocks(value: Any, role: str, body: str, bullets: list[str]) -> list[dict[str, Any]]:
    raw_blocks = value if isinstance(value, list) else []
    result: list[dict[str, Any]] = []
    for block in raw_blocks:
        if not isinstance(block, dict):
            continue
        block_type = _safe_token(block.get("type") or block.get("block_type"), ALLOWED_CONTENT_BLOCK_TYPES, "")
        tone = _safe_token(block.get("tone"), ALLOWED_CONTENT_TONES, _tone_for_role(role))
        title = _clean_text(block.get("title") or block.get("label"))
        text = _clean_text(block.get("text") or block.get("body") or block.get("description"))
        items = _normalize_block_items(block.get("items"))
        if block_type == "lead" and text:
            result.append({"type": "lead", "text": text, "tone": tone})
        elif block_type == "highlight" and (title or text):
            result.append({"type": "highlight", "title": title, "text": text, "tone": tone})
        elif block_type == "mini_cards" and items:
            result.append({"type": "mini_cards", "items": items[:3], "tone": tone})
        elif block_type == "steps" and items:
            result.append({"type": "steps", "items": items[:4], "tone": tone})
        elif block_type == "checklist" and items:
            result.append({"type": "checklist", "items": [item["text"] for item in items if item.get("text")][:5], "tone": tone})
        elif block_type == "quote" and text:
            source = _clean_text(block.get("source"))
            result.append({"type": "quote", "text": text, "source": source, "tone": tone})
        elif block_type == "metric":
            value_text = _clean_text(block.get("value"))
            label = _clean_text(block.get("label") or block.get("title"))
            caption = _clean_text(block.get("caption") or block.get("text"))
            if value_text or label:
                result.append({"type": "metric", "value": value_text, "label": label, "caption": caption, "tone": tone})
        elif block_type == "tag_row" and items:
            result.append({"type": "tag_row", "items": [item["text"] for item in items if item.get("text")][:6], "tone": tone})
    return result[:4] or _fallback_content_blocks(role, {"body": body, "bullets": bullets})


def _normalize_block_items(value: Any) -> list[dict[str, str]]:
    raw_items = value if isinstance(value, list) else ([value] if value not in (None, "") else [])
    result: list[dict[str, str]] = []
    for index, item in enumerate(raw_items, start=1):
        if isinstance(item, dict):
            title = _clean_text(item.get("title") or item.get("label") or item.get("name"))
            text = _clean_text(item.get("text") or item.get("body") or item.get("description") or item.get("value"))
        else:
            title = ""
            text = _clean_text(item)
        if title or text:
            result.append({"title": title, "text": text or title, "label": str(index)})
    return result


def _fallback_content_blocks(role: str, content: dict[str, Any]) -> list[dict[str, Any]]:
    body = _clean_text(content.get("body"))
    bullets = _text_items(content.get("bullets"))[:5]
    tone = _tone_for_role(role)
    blocks: list[dict[str, Any]] = []
    if role in {"cover", "intro"}:
        if body:
            blocks.append({"type": "lead", "text": body, "tone": tone})
        if bullets:
            blocks.append({"type": "tag_row", "items": bullets[:4], "tone": tone})
    elif role in {"tip", "checklist", "security", "caution"}:
        if body:
            blocks.append({"type": "highlight", "title": "핵심 포인트", "text": body, "tone": tone})
        if bullets:
            blocks.append({"type": "checklist", "items": bullets, "tone": tone})
    elif role in {"workflow"} and bullets:
        blocks.append({"type": "steps", "items": [{"title": item, "text": ""} for item in bullets[:4]], "tone": tone})
    elif role in {"case", "why", "recap"} and bullets:
        blocks.append({"type": "mini_cards", "items": [{"title": item, "text": ""} for item in bullets[:3]], "tone": tone})
    elif role in {"cta", "closing"}:
        if body:
            blocks.append({"type": "highlight", "title": "다음 행동", "text": body, "tone": tone})
        if bullets:
            blocks.append({"type": "tag_row", "items": bullets[:4], "tone": tone})
    if not blocks and body:
        blocks.append({"type": "lead", "text": body, "tone": tone})
    if not blocks and bullets:
        blocks.append({"type": "tag_row", "items": bullets[:5], "tone": tone})
    return blocks[:3]


def _tone_for_role(role: str) -> str:
    if role in {"security", "caution"}:
        return "red"
    if role in {"tip", "checklist", "workflow"}:
        return "orange"
    if role in {"case", "recap"}:
        return "blue"
    return "soft"


def _image_override_maps(payload: dict[str, Any]) -> tuple[dict[int, dict[str, Any]], dict[str, dict[str, Any]]]:
    request = _dict(payload.get("card_news_request"))
    page_map: dict[int, dict[str, Any]] = {}
    slide_id_map: dict[str, dict[str, Any]] = {}
    for item in _list(request.get("page_image_overrides")):
        if not isinstance(item, dict):
            continue
        normalized = _normalize_image_override(item)
        page = _optional_page(item.get("page") or item.get("slide_index"))
        slide_id = _clean(item.get("slide_id"))
        if page:
            page_map[page] = normalized
        if slide_id:
            slide_id_map[slide_id] = normalized
    return page_map, slide_id_map


def _normalize_image_override(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "data_uri": _clean(item.get("data_uri")),
        "alt": _clean(item.get("alt")) or "사용자가 지정한 카드뉴스 이미지",
        "fit": _safe_token(item.get("fit"), {"contain", "cover", "fill"}, "contain"),
        "render_mode": _safe_token(item.get("render_mode"), {"content_area", "full_card"}, "content_area"),
        "background_color": _safe_color(item.get("background_color"), "#FFFDF7"),
        "source": _clean(item.get("source")) or "user_provided",
        "valid_data_uri": _valid_image_data_uri(_clean(item.get("data_uri"))),
    }


def _image_layout(fit: Any) -> str:
    mode = _safe_token(fit, {"contain", "cover", "fill"}, "contain")
    if mode == "cover":
        return "image_cover"
    if mode == "fill":
        return "image_full"
    return "image_contain"


def _attach_navigation_buttons(slides: list[dict[str, Any]], cta: dict[str, Any]) -> list[dict[str, Any]]:
    slide_ids = [_clean(slide.get("slide_id")) for slide in slides]
    result = []
    for index, slide in enumerate(slides):
        next_slide = deepcopy(slide)
        is_full_card_image_override = _is_full_card_image_override(slide)
        buttons = []
        if is_full_card_image_override:
            buttons = []
        elif index > 0:
            buttons.append({"label": "이전", "action_type": "anchor", "target": slide_ids[index - 1], "style": "secondary"})
        if not is_full_card_image_override and index < len(slides) - 1:
            buttons.append({"label": "다음", "action_type": "anchor", "target": slide_ids[index + 1], "style": "primary"})
        elif not is_full_card_image_override:
            label = _clean(cta.get("label")) or "처음으로"
            url = _clean(cta.get("url"))
            if url and _safe_url(url):
                buttons.append({"label": label, "action_type": "external_link", "target": url, "style": "primary"})
            buttons.append({"label": "처음", "action_type": "anchor", "target": slide_ids[0], "style": "secondary"})
        custom_buttons = _normalize_buttons(_list(slide.get("buttons")), slide_ids)
        next_slide["buttons"] = [] if is_full_card_image_override else (custom_buttons or buttons)
        if index < len(slides) - 1:
            next_slide["click_target"] = slide_ids[index + 1]
        else:
            next_slide["click_target"] = ""
        result.append(next_slide)
    return result


def _is_full_card_image_override(slide: dict[str, Any]) -> bool:
    image_override = _dict(slide.get("image_override"))
    return bool(image_override) and _safe_token(image_override.get("render_mode"), {"content_area", "full_card"}, "content_area") == "full_card"


def _publication_info(request: dict[str, Any], brief: dict[str, Any], plan: dict[str, Any]) -> dict[str, str]:
    """요청, 브리프, 계획에 흩어진 발간호 정보를 하나로 합칩니다."""

    merged = {
        **_dict(request.get("publication_info")),
        **_dict(brief.get("publication_info")),
        **_dict(plan.get("publication_info")),
    }
    series_name = _clean(merged.get("series_name")) or "AI 카드뉴스"
    issue_label = _clean(merged.get("issue_label"))
    issue_date = _clean(merged.get("issue_date"))
    publisher = _clean(merged.get("publisher")) or "SK hynix"
    return {
        "series_name": series_name,
        "issue_label": issue_label,
        "issue_date": issue_date,
        "publisher": publisher,
    }


def _normalize_buttons(buttons: list[Any], slide_ids: list[str]) -> list[dict[str, Any]]:
    result = []
    for button in buttons:
        if not isinstance(button, dict):
            continue
        label = _clean(button.get("label"))[:24]
        action_type = _safe_token(button.get("action_type"), {"anchor", "external_link"}, "anchor")
        target = _clean(button.get("target"))
        if action_type == "anchor" and target not in slide_ids:
            continue
        if action_type == "external_link" and not _safe_url(target):
            continue
        result.append({"label": label or "이동", "action_type": action_type, "target": target, "style": _safe_token(button.get("style"), {"primary", "secondary"}, "primary")})
    return result[:3]


def _extract_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return deepcopy(value)
    text = getattr(value, "text", None) or getattr(value, "content", None) or value
    if not isinstance(text, str) or not text.strip():
        return {}
    start = text.find("{")
    end = text.rfind("}")
    candidates = [text]
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


def _text_items(value: Any) -> list[str]:
    raw_items = value if isinstance(value, list) else ([value] if value not in (None, "") else [])
    result = []
    for item in raw_items:
        text = _clean_text(item)
        if text and text not in result:
            result.append(text)
    return result


def _tokens(value: Any) -> list[str]:
    return [item.lower() for item in _strings(value)]


def _positive_int(value: Any, default: int) -> int:
    try:
        return max(1, int(value))
    except Exception:
        return default


def _optional_page(value: Any) -> int:
    try:
        parsed = int(value)
    except Exception:
        return 0
    return max(0, parsed)


def _valid_image_data_uri(value: str) -> bool:
    return bool(value) and value.startswith(ALLOWED_IMAGE_PREFIXES) and not any(marker in value for marker in PLACEHOLDER_MARKERS)


def _safe_color(value: Any, default: str) -> str:
    text = _clean(value)
    if len(text) == 7 and text.startswith("#") and all(ch in "0123456789abcdefABCDEF" for ch in text[1:]):
        return text
    return default


def _safe_token(value: Any, allowed: set[str], default: str) -> str:
    text = _clean(value).lower().replace("-", "_")
    return text if text in allowed else default


def _safe_url(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _clean_text(value: Any) -> str:
    """LLM이 잘못 섞은 HTML/Markdown 태그를 일반 텍스트로 정리합니다."""

    text = html.unescape(_clean(value))
    text = re.sub(r"```(?:html|json|text)?", "", text, flags=re.IGNORECASE)
    text = text.replace("```", "")
    text = re.sub(r"</?[^>]+>", "", text)
    text = re.sub(r"^[`*_#\-\s]+", "", text)
    text = re.sub(r"[`*_\s]+$", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _first(items: list[Any], default: Any = "") -> Any:
    for item in items:
        if item:
            return item
    return default


def _dedupe(items: list[Any]) -> list[str]:
    result = []
    for item in items:
        text = _clean(item)
        if text and text not in result:
            result.append(text)
    return result


class CardNewsPlanNormalizer(Component):
    display_name = "05 카드뉴스 계획 검증"
    description = "LLM 카드뉴스 계획을 검증하고 하냥이/하댕이 포즈팩 asset_id를 보강합니다."
    icon = "BadgeCheck"
    inputs = [
        DataInput(name="character_payload", display_name="캐릭터 자산 포함 브리프", required=True),
        MessageTextInput(name="llm_plan_response", display_name="Agent/LLM 카드뉴스 응답", required=False),
    ]
    outputs = [Output(name="card_news_plan", display_name="카드뉴스 계획", method="build_payload", types=["Data"])]

    def build_payload(self) -> Data:
        result = normalize_card_news_plan(
            getattr(self, "character_payload", None),
            getattr(self, "llm_plan_response", ""),
        )
        plan = _dict(result.get("card_news_plan"))
        self.status = {
            "제목": plan.get("title"),
            "카드 수": len(_list(plan.get("slides"))),
            "사용 자산": len(_list(plan.get("used_assets"))),
            "테마": _dict(plan.get("style")).get("theme"),
        }
        return Data(data=result)
