from __future__ import annotations

"""00 카드뉴스 요청 입력 노드."""

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import MessageTextInput, Output
from lfx.schema.data import Data


DEFAULT_BRAND_TONE = "SK하이닉스 사내 카드뉴스, 귀엽지만 정돈된 톤"
DEFAULT_TARGET_AUDIENCE = "전 직원"


def build_card_news_request(
    raw_content: Any,
    generation_instructions: Any = "",
    target_audience: Any = DEFAULT_TARGET_AUDIENCE,
    brand_tone: Any = DEFAULT_BRAND_TONE,
    slide_count: Any = "6",
    aspect_ratio: Any = "16:9",
    animation_level: Any = "standard",
    primary_cta_label: Any = "",
    primary_cta_url: Any = "",
    page_image_overrides_json: Any = "",
) -> dict[str, Any]:
    """사용자 입력을 Flow 전체에서 사용할 표준 카드뉴스 요청 payload로 변환합니다."""

    content = _clean(raw_content)
    instructions = _clean(generation_instructions)
    instruction_text = "\n".join(item for item in [content, instructions] if item)
    request_id = _stable_id("card_news_request", content or _now_iso())
    inferred_count = _extract_slide_count(instruction_text)
    count = _bounded_int(inferred_count or slide_count, default=6, minimum=3, maximum=15)
    publication_info = _extract_publication_info(instruction_text)
    cta_label = _clean(primary_cta_label)
    cta_url = _clean(primary_cta_url)
    page_image_overrides, override_warnings = _parse_page_image_overrides(page_image_overrides_json)
    warnings = [] if content else ["카드뉴스 내용이 비어 있습니다."]
    warnings.extend(override_warnings)
    if cta_url and not _safe_url(cta_url):
        warnings.append("CTA URL은 http 또는 https만 허용합니다. 잘못된 URL은 제거했습니다.")
        cta_url = ""

    return {
        "payload_version": "card-news-flow-v1",
        "flow_type": "card_news",
        "card_news_request": {
            "request_id": request_id,
            "raw_content": content,
            "generation_instructions": instructions,
            "target_audience": _clean(target_audience) or DEFAULT_TARGET_AUDIENCE,
            "brand_tone": _clean(brand_tone) or DEFAULT_BRAND_TONE,
            "slide_count": count,
            "publication_info": publication_info,
            "template": {
                "template_id": "monthly_ai_news_standard",
                "fixed_structure": True,
                "rule": "화면 수가 같으면 SNS 가로 카드 프레임, 역할 순서, 캐릭터/버튼 위치는 고정하고 중앙 내용 영역 안에서는 허용된 디자인 블록으로 구성합니다.",
                "fixed_slots": ["topbar", "content_area", "character_area", "action_area"],
                "content_area_design": ["lead", "highlight", "mini_cards", "steps", "checklist", "quote", "metric", "tag_row"],
            },
            "page_image_overrides": page_image_overrides,
            "instruction_derived": {
                "slide_count": inferred_count,
                "publication_info_found": bool(publication_info.get("issue_label") or publication_info.get("issue_date")),
            },
            "aspect_ratio": _safe_token(aspect_ratio, {"16:9", "1:1", "4:5", "9:16"}, "16:9"),
            "animation_level": _safe_token(animation_level, {"none", "subtle", "standard"}, "standard"),
            "primary_cta": {
                "label": cta_label,
                "url": cta_url,
            },
            "brand": "sk_hynix",
            "theme": "sk_cute_soft",
            "created_at": _now_iso(),
            "input_mode": "single_natural_language_text",
        },
        "brief": {},
        "character_assets": {},
        "character_asset_context": {},
        "card_news_plan": {},
        "html_result": {},
        "trace": {
            "warnings": warnings,
            "errors": [],
        },
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _stable_id(prefix: str, text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = default
    return max(minimum, min(maximum, parsed))


def _extract_slide_count(text: str) -> int | None:
    """지시사항에서 총 화면/페이지/장 수를 추출합니다."""

    patterns = [
        r"(?:총|전체)?\s*(\d{1,2})\s*(?:개\s*)?(?:화면|페이지|page|pages|screen|screens|장|컷|슬라이드)",
        r"(?:화면|페이지|page|pages|screen|screens|장|컷|슬라이드)\s*(?:수|개수|구성)?\s*[:=]?\s*(\d{1,2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except Exception:
                return None
    return None


def _extract_publication_info(text: str) -> dict[str, str]:
    """지시사항에서 발간호/호수/발행일 정보를 추출합니다."""

    issue_label = ""
    issue_patterns = [
        r"(제\s*\d+\s*호)",
        r"(\d{4}\s*년\s*\d{1,2}\s*월\s*호)",
        r"(\d{1,2}\s*월\s*호)",
        r"(?:발간호|발행호|호수|issue|vol\.?)\s*(?:는|은)?\s*[:=]?\s*([^\n,;/|]+)",
    ]
    for pattern in issue_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            issue_label = _clean(match.group(1))
            break

    issue_date = ""
    date_patterns = [
        r"(?:발행일|발간일|게시일|date)\s*[:=]?\s*([0-9]{4}[.\-/년\s]+[0-9]{1,2}(?:[.\-/월\s]+[0-9]{1,2})?)",
        r"([0-9]{4}\s*년\s*[0-9]{1,2}\s*월(?:\s*[0-9]{1,2}\s*일)?)",
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            issue_date = _clean(match.group(1))
            break

    return {
        "issue_label": issue_label,
        "issue_date": issue_date,
        "publisher": "SK hynix",
        "series_name": "AI 카드뉴스",
    }


def _parse_page_image_overrides(value: Any) -> tuple[list[dict[str, Any]], list[str]]:
    """특정 페이지를 사용자가 만든 이미지로 대체하는 JSON을 파싱합니다."""

    text = _clean(value)
    if not text:
        return [], []
    warnings: list[str] = []
    try:
        parsed = json.loads(text)
    except Exception as exc:
        return [], [f"페이지 이미지 JSON 파싱 실패: {exc}"]
    raw_items = parsed.get("overrides") if isinstance(parsed, dict) else parsed
    if isinstance(raw_items, dict):
        raw_items = [raw_items]
    if not isinstance(raw_items, list):
        return [], ["페이지 이미지 JSON은 list 또는 {\"overrides\": [...]} 형식이어야 합니다."]

    result = []
    for index, item in enumerate(raw_items, start=1):
        if not isinstance(item, dict):
            warnings.append(f"페이지 이미지 override #{index}가 object가 아니라 건너뛰었습니다.")
            continue
        page = _positive_int(item.get("page") or item.get("slide_index"), 0)
        slide_id = _clean(item.get("slide_id"))
        data_uri = _clean(item.get("data_uri"))
        if not page and not slide_id:
            warnings.append(f"페이지 이미지 override #{index}에 page 또는 slide_id가 없습니다.")
            continue
        if data_uri and not _looks_like_image_data_uri(data_uri):
            warnings.append(f"페이지 이미지 override #{index}의 data_uri가 이미지 data URI 형식이 아닙니다.")
        result.append(
            {
                "page": page,
                "slide_id": slide_id,
                "data_uri": data_uri,
                "alt": _clean(item.get("alt")) or "사용자가 지정한 카드뉴스 이미지",
                "fit": _safe_token(item.get("fit"), {"contain", "cover", "fill"}, "contain"),
                "render_mode": _safe_token(item.get("render_mode"), {"content_area", "full_card"}, "content_area"),
                "background_color": _safe_color(item.get("background_color"), "#FFFDF7"),
                "source": _clean(item.get("source")) or "user_provided",
            }
        )
    return result, warnings


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        return default
    return max(0, parsed)


def _looks_like_image_data_uri(value: str) -> bool:
    return value.startswith(("data:image/png;base64,", "data:image/jpeg;base64,", "data:image/webp;base64,"))


def _safe_color(value: Any, default: str) -> str:
    text = _clean(value)
    if len(text) == 7 and text.startswith("#") and all(ch in "0123456789abcdefABCDEF" for ch in text[1:]):
        return text
    return default


def _safe_token(value: Any, allowed: set[str], default: str) -> str:
    text = _clean(value).lower()
    return text if text in allowed else default


def _safe_url(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def _clean(value: Any) -> str:
    return str(value or "").strip()


class CardNewsRequestLoader(Component):
    display_name = "00 카드뉴스 요청 입력"
    description = "카드뉴스에 넣을 내용을 자연어 한 칸으로 받고 표준 요청 payload를 만듭니다."
    icon = "FileInput"
    inputs = [
        MessageTextInput(
            name="raw_content",
            display_name="카드뉴스 내용",
            info="이번 달 카드뉴스에 넣을 주제, 핵심 내용, 톤, CTA를 자연스럽게 적습니다.",
            required=True,
            tool_mode=True,
        ),
        MessageTextInput(
            name="generation_instructions",
            display_name="지시사항",
            info="총 몇 개 화면으로 구성할지, 발간호/호수/발행일, 페이지 이동 방식 같은 제작 지시를 적습니다.",
            required=False,
        ),
        MessageTextInput(name="target_audience", display_name="대상 독자", value=DEFAULT_TARGET_AUDIENCE, advanced=True),
        MessageTextInput(name="brand_tone", display_name="브랜드 톤", value=DEFAULT_BRAND_TONE, advanced=True),
        MessageTextInput(name="slide_count", display_name="카드 수", value="6", advanced=True),
        MessageTextInput(name="aspect_ratio", display_name="페이지 비율", value="16:9", advanced=True),
        MessageTextInput(name="animation_level", display_name="애니메이션 강도", value="standard", advanced=True),
        MessageTextInput(name="primary_cta_label", display_name="주요 CTA 문구", value="", advanced=True),
        MessageTextInput(name="primary_cta_url", display_name="주요 CTA URL", value="", advanced=True),
        MessageTextInput(name="page_image_overrides_json", display_name="페이지 이미지 대체 JSON", value="", required=False, advanced=True),
    ]
    outputs = [Output(name="card_news_request", display_name="카드뉴스 요청", method="build_payload", types=["Data"])]

    def build_payload(self) -> Data:
        result = build_card_news_request(
            getattr(self, "raw_content", ""),
            getattr(self, "generation_instructions", ""),
            getattr(self, "target_audience", DEFAULT_TARGET_AUDIENCE),
            getattr(self, "brand_tone", DEFAULT_BRAND_TONE),
            getattr(self, "slide_count", "6"),
            getattr(self, "aspect_ratio", "16:9"),
            getattr(self, "animation_level", "standard"),
            getattr(self, "primary_cta_label", ""),
            getattr(self, "primary_cta_url", ""),
            getattr(self, "page_image_overrides_json", ""),
        )
        request = result.get("card_news_request", {})
        self.status = {
            "요청 ID": request.get("request_id"),
            "입력 글자 수": len(request.get("raw_content", "")),
            "카드 수": request.get("slide_count"),
            "이미지 대체": len(request.get("page_image_overrides", [])),
            "테마": request.get("theme"),
        }
        return Data(data=result)
