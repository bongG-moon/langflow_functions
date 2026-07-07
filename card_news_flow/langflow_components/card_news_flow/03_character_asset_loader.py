from __future__ import annotations

"""03 캐릭터 자산 불러오기 노드.

하냥이/하댕이처럼 사전에 승인된 브랜드 캐릭터 포즈팩을 읽고,
LLM에는 base64 원문 없이 자산 요약만 전달합니다.
이미 카드뉴스 계획이 들어온 경우에는 slide 역할과 본문 키워드에 맞춰
각 slide의 character.asset_id를 자동 보강합니다.
"""

import base64
import json
from copy import deepcopy
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, MessageTextInput, Output
from lfx.schema.data import Data


ALLOWED_IMAGE_PREFIXES = ("data:image/png;base64,", "data:image/jpeg;base64,", "data:image/webp;base64,")
PLACEHOLDER_MARKERS = ("PUT_BASE64", "PUT_APPROVED_BASE64", "...")

DEFAULT_MANIFEST: dict[str, Any] = {
    "asset_family": "sk_hynix_hayangi_hadaengi_ai_pose_pack",
    "version": "0.2.0",
    "default_asset_id": "duo_ai_welcome",
    "usage_scope": "internal_card_news",
    "approval": {
        "status": "placeholder",
        "owner": "brand_or_corp_comm_team",
        "note": "실제 운영 전 승인된 base64 이미지 manifest를 연결하세요.",
    },
    "slide_role_defaults": {
        "cover": ["duo_ai_welcome", "hayangi_ai_hello"],
        "intro": ["hayangi_ai_guide_pointer", "duo_ai_welcome"],
        "why": ["hadaengi_idea_bulb", "hayangi_question_mark"],
        "case": ["hadaengi_ai_helper", "hadaengi_data_scan"],
        "workflow": ["hadaengi_workflow_blocks", "duo_before_after"],
        "tip": ["hayangi_prompt_note", "hayangi_prompt_magic", "hadaengi_toolbox"],
        "checklist": ["hayangi_checklist", "hayangi_good_example"],
        "security": ["hayangi_security_shield", "hayangi_private_data_stop"],
        "caution": ["hayangi_warning_sign", "duo_security_promise"],
        "quiz": ["hayangi_question_mark", "duo_quiz_answer"],
        "recap": ["duo_monthly_recap", "hayangi_thumbs_up"],
        "cta": ["hadaengi_cta_point", "duo_training_invite"],
        "closing": ["duo_ai_team", "duo_download_ready"],
    },
    "selection_rules": [
        {
            "rule_id": "security_terms_prefer_guard_assets",
            "when_keywords": ["보안", "개인정보", "기밀", "민감정보", "외부 AI", "주의"],
            "prefer_ai_contexts": ["security_notice", "privacy_warning", "caution"],
            "avoid_ai_contexts": ["celebration", "cta"],
        },
        {
            "rule_id": "prompt_terms_prefer_note_assets",
            "when_keywords": ["프롬프트", "질문", "작성 팁", "명령어", "예시"],
            "prefer_ai_contexts": ["prompt_tip", "prompt_builder", "best_practice"],
            "avoid_ai_contexts": ["security_notice"],
        },
        {
            "rule_id": "automation_terms_prefer_hadaengi_assets",
            "when_keywords": ["자동화", "업무 흐름", "데이터", "리포트", "분석", "반복 업무"],
            "prefer_character_keys": ["hadaengi", "duo"],
            "prefer_ai_contexts": ["automation_case", "data_workflow", "workflow"],
        },
        {
            "rule_id": "closing_terms_prefer_duo_or_cta_assets",
            "when_keywords": ["신청", "문의", "다운로드", "다음", "교육", "참여"],
            "prefer_ai_contexts": ["cta", "training", "download", "closing"],
            "prefer_character_keys": ["hadaengi", "duo"],
        },
    ],
    "assets": [
        {
            "asset_id": "duo_ai_welcome",
            "character_key": "duo",
            "display_name": "하냥이와 하댕이 AI 환영 포즈",
            "pose": "welcome",
            "ai_context": "cover_intro",
            "mood_tags": ["welcome", "team", "bright"],
            "recommended_slide_roles": ["cover", "intro"],
            "recommended_layouts": ["cover_character"],
            "placement_hints": ["center", "bottom_right"],
            "animation_hints": ["float_in", "fade_up"],
            "mime_type": "image/png",
            "data_uri": "data:image/png;base64,PUT_APPROVED_BASE64_IMAGE_HERE",
            "alt": "AI 카드뉴스 시작을 함께 환영하는 하냥이와 하댕이",
        },
        {
            "asset_id": "hayangi_security_shield",
            "character_key": "hayangi",
            "display_name": "하냥이 보안 방패 포즈",
            "pose": "security_shield",
            "ai_context": "security_notice",
            "mood_tags": ["careful", "trustworthy", "security"],
            "recommended_slide_roles": ["caution", "security"],
            "recommended_layouts": ["character_speech", "notice_board"],
            "placement_hints": ["bottom_right", "right"],
            "animation_hints": ["fade_up", "slide_in"],
            "mime_type": "image/png",
            "data_uri": "data:image/png;base64,PUT_APPROVED_BASE64_IMAGE_HERE",
            "alt": "AI 보안 수칙을 안내하는 하냥이",
        },
        {
            "asset_id": "hadaengi_toolbox",
            "character_key": "hadaengi",
            "display_name": "하댕이 AI 도구상자 포즈",
            "pose": "toolbox",
            "ai_context": "tool_usage",
            "mood_tags": ["tools", "practical", "how_to"],
            "recommended_slide_roles": ["tip", "workflow", "checklist"],
            "recommended_layouts": ["checklist_note", "sticker_grid"],
            "placement_hints": ["bottom_right", "left"],
            "animation_hints": ["fade_up", "stagger"],
            "mime_type": "image/png",
            "data_uri": "data:image/png;base64,PUT_APPROVED_BASE64_IMAGE_HERE",
            "alt": "AI 도구 활용 방법을 알려주는 하댕이",
        },
        {
            "asset_id": "hadaengi_cta_point",
            "character_key": "hadaengi",
            "display_name": "하댕이 CTA 안내 포즈",
            "pose": "pointing",
            "ai_context": "cta",
            "mood_tags": ["cta", "action", "friendly"],
            "recommended_slide_roles": ["closing", "cta"],
            "recommended_layouts": ["cta_character"],
            "placement_hints": ["bottom_right", "right"],
            "animation_hints": ["pulse_soft", "float_in"],
            "mime_type": "image/png",
            "data_uri": "data:image/png;base64,PUT_APPROVED_BASE64_IMAGE_HERE",
            "alt": "교육 신청 버튼을 가리키는 하댕이",
        },
    ],
}


def load_character_assets(payload_value: Any, asset_manifest_json: Any = "", auto_assign: Any = "true") -> dict[str, Any]:
    """입력 payload에 캐릭터 자산 manifest와 LLM용 요약을 추가합니다."""

    payload = _payload(payload_value)
    manifest = _resolve_manifest(payload, asset_manifest_json)
    manifest = _normalize_manifest(manifest)
    validation = _validate_manifest(manifest)
    context = _asset_context(manifest, validation)
    result = deepcopy(payload)
    result["character_assets"] = manifest
    result["character_asset_context"] = context
    if _truthy(auto_assign):
        result = _assign_assets_to_plan(result, manifest)
    return result


def select_character_asset(slide: dict[str, Any], manifest: dict[str, Any], used_asset_ids: list[str] | None = None) -> dict[str, Any]:
    """slide의 role, layout, 본문 키워드를 기준으로 가장 적합한 캐릭터 자산을 선택합니다."""

    used_asset_ids = used_asset_ids or []
    assets = _list(manifest.get("assets"))
    selectable_assets = [asset for asset in assets if isinstance(asset, dict) and _clean(asset.get("asset_id"))]
    if not selectable_assets:
        return {}

    role = _clean(slide.get("role")).lower()
    layout = _clean(slide.get("layout")).lower()
    slide_text = _slide_text(slide)
    defaults = _strings(_dict(manifest.get("slide_role_defaults")).get(role))
    scored = []
    for index, asset in enumerate(selectable_assets):
        score, reasons = _score_asset(asset, role, layout, slide_text, manifest, defaults, used_asset_ids)
        scored.append((score, -index, asset, reasons))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    best_score, _, best_asset, reasons = scored[0]
    if best_score <= -999:
        return _asset_by_id(selectable_assets, _clean(manifest.get("default_asset_id"))) or selectable_assets[0]
    result = _asset_summary(best_asset)
    result["selection_score"] = best_score
    result["selection_reasons"] = reasons[:6]
    return result


def _score_asset(
    asset: dict[str, Any],
    role: str,
    layout: str,
    slide_text: str,
    manifest: dict[str, Any],
    defaults: list[str],
    used_asset_ids: list[str],
) -> tuple[int, list[str]]:
    """자산 선택 점수와 근거를 계산합니다."""

    score = 0
    reasons: list[str] = []
    asset_id = _clean(asset.get("asset_id"))
    character_key = _clean(asset.get("character_key"))
    ai_context = _clean(asset.get("ai_context"))
    roles = _strings(asset.get("recommended_slide_roles"))
    layouts = _strings(asset.get("recommended_layouts"))
    mood_tags = _strings(asset.get("mood_tags"))
    avoid_when = _strings(asset.get("avoid_when"))

    if role and role in roles:
        score += 5
        reasons.append(f"role:{role}")
    if asset_id in defaults:
        score += max(1, 5 - defaults.index(asset_id))
        reasons.append("role_default")
    if layout and layout in layouts:
        score += 2
        reasons.append(f"layout:{layout}")
    if any(tag in slide_text for tag in mood_tags):
        score += 1
        reasons.append("mood_match")
    for item in avoid_when:
        if item and (item in role or item in layout or item in slide_text):
            score -= 5
            reasons.append(f"avoid:{item}")

    for rule in _list(manifest.get("selection_rules")):
        if not isinstance(rule, dict):
            continue
        keywords = _strings(rule.get("when_keywords"))
        if not any(keyword and keyword in slide_text for keyword in keywords):
            continue
        prefer_contexts = _strings(rule.get("prefer_ai_contexts"))
        prefer_characters = _strings(rule.get("prefer_character_keys"))
        avoid_contexts = _strings(rule.get("avoid_ai_contexts"))
        if ai_context in prefer_contexts:
            score += 4
            reasons.append(str(rule.get("rule_id") or "context_rule"))
        if character_key in prefer_characters:
            score += 2
            reasons.append(str(rule.get("rule_id") or "character_rule"))
        if ai_context in avoid_contexts:
            score -= 4
            reasons.append(f"rule_avoid:{ai_context}")

    if asset_id in used_asset_ids[-1:]:
        score -= 2
        reasons.append("avoid_immediate_repeat")
    elif asset_id in used_asset_ids:
        score -= 1
        reasons.append("avoid_overuse")

    return score, reasons


def _assign_assets_to_plan(payload: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    """card_news_plan.slides에 캐릭터 선택값을 보강합니다."""

    result = deepcopy(payload)
    plan = _dict(result.get("card_news_plan"))
    slides = [slide for slide in _list(plan.get("slides")) if isinstance(slide, dict)]
    if not plan or not slides:
        return result

    valid_ids = {_clean(asset.get("asset_id")) for asset in _list(manifest.get("assets")) if isinstance(asset, dict)}
    used_asset_ids: list[str] = []
    next_slides = []
    for slide in slides:
        next_slide = deepcopy(slide)
        character = _dict(next_slide.get("character"))
        current_asset_id = _clean(character.get("asset_id"))
        if not current_asset_id or current_asset_id not in valid_ids:
            selected = select_character_asset(next_slide, manifest, used_asset_ids)
            if selected:
                character = {
                    "asset_id": selected.get("asset_id", ""),
                    "character_key": selected.get("character_key", ""),
                    "pose": selected.get("pose", ""),
                    "placement": _first(_list(selected.get("placement_hints")), "bottom_right"),
                    "animation": _first(_list(selected.get("animation_hints")), "float_in"),
                    "selection_score": selected.get("selection_score"),
                    "selection_reasons": selected.get("selection_reasons", []),
                }
                next_slide["character"] = character
        if _clean(character.get("asset_id")):
            used_asset_ids.append(_clean(character.get("asset_id")))
        next_slides.append(next_slide)

    plan["slides"] = next_slides
    result["card_news_plan"] = plan
    result["character_asset_context"] = {
        **_dict(result.get("character_asset_context")),
        "auto_assignment": {"status": "applied", "used_asset_ids": used_asset_ids},
    }
    return result


def _resolve_manifest(payload: dict[str, Any], asset_manifest_json: Any) -> dict[str, Any]:
    """입력 텍스트, payload 내 manifest, 기본 manifest 순서로 자산 manifest를 찾습니다."""

    parsed = _parse_json_object(asset_manifest_json)
    if parsed:
        return parsed
    for key in ("character_assets", "character_asset_manifest", "asset_manifest"):
        value = payload.get(key)
        if isinstance(value, dict):
            return deepcopy(value)
        parsed = _parse_json_object(value)
        if parsed:
            return parsed
    return deepcopy(DEFAULT_MANIFEST)


def _normalize_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """legacy characters 키를 assets로 맞추고 필수 top-level key를 보강합니다."""

    result = deepcopy(manifest) if isinstance(manifest, dict) else deepcopy(DEFAULT_MANIFEST)
    if not isinstance(result.get("assets"), list) and isinstance(result.get("characters"), list):
        result["assets"] = deepcopy(result.get("characters"))
    result.setdefault("asset_family", "character_pose_pack")
    result.setdefault("version", "0.1.0")
    result.setdefault("default_asset_id", _first([_clean(asset.get("asset_id")) for asset in _list(result.get("assets")) if isinstance(asset, dict)], ""))
    result.setdefault("slide_role_defaults", {})
    result.setdefault("selection_rules", [])
    return result


def _validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """자산 manifest의 기본 유효성을 검사합니다."""

    errors: list[str] = []
    warnings: list[str] = []
    assets = [asset for asset in _list(manifest.get("assets")) if isinstance(asset, dict)]
    ids: set[str] = set()
    valid_assets = 0
    placeholder_assets = 0
    for asset in assets:
        asset_id = _clean(asset.get("asset_id"))
        if not asset_id:
            errors.append("asset without asset_id")
            continue
        if asset_id in ids:
            errors.append(f"duplicated asset_id: {asset_id}")
        ids.add(asset_id)
        data_uri = _clean(asset.get("data_uri"))
        uri_status = _data_uri_status(data_uri)
        if uri_status == "valid":
            valid_assets += 1
        elif uri_status == "placeholder":
            placeholder_assets += 1
            warnings.append(f"placeholder data_uri: {asset_id}")
        else:
            errors.append(f"invalid data_uri: {asset_id}")

    default_asset_id = _clean(manifest.get("default_asset_id"))
    if default_asset_id and default_asset_id not in ids:
        warnings.append(f"default_asset_id not found: {default_asset_id}")
    approval = _dict(manifest.get("approval"))
    if _clean(approval.get("status")).lower() != "approved":
        warnings.append("approval.status is not approved")

    return {
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
        "asset_count": len(assets),
        "valid_asset_count": valid_assets,
        "placeholder_asset_count": placeholder_assets,
    }


def _asset_context(manifest: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    """LLM/prompt에 전달하기 좋은 base64 없는 자산 요약을 만듭니다."""

    assets = [_asset_summary(asset) for asset in _list(manifest.get("assets")) if isinstance(asset, dict)]
    return {
        "asset_family": manifest.get("asset_family", ""),
        "version": manifest.get("version", ""),
        "default_asset_id": manifest.get("default_asset_id", ""),
        "usage_scope": manifest.get("usage_scope", ""),
        "approval": _dict(manifest.get("approval")),
        "pose_groups": _list(manifest.get("pose_groups")),
        "slide_role_defaults": _dict(manifest.get("slide_role_defaults")),
        "selection_rules": _list(manifest.get("selection_rules")),
        "available_character_assets": assets,
        "validation_report": validation,
    }


def _asset_summary(asset: dict[str, Any]) -> dict[str, Any]:
    """base64를 제외한 자산 메타데이터를 반환합니다."""

    keys = [
        "asset_id",
        "character_key",
        "display_name",
        "pose",
        "ai_context",
        "mood_tags",
        "recommended_slide_roles",
        "recommended_layouts",
        "placement_hints",
        "animation_hints",
        "avoid_when",
        "alt",
        "width",
        "height",
    ]
    return {key: deepcopy(asset[key]) for key in keys if key in asset}


def _data_uri_status(data_uri: str) -> str:
    """data URI가 렌더링 가능한지, placeholder인지, 잘못됐는지 판단합니다."""

    if not data_uri:
        return "missing"
    if any(marker in data_uri for marker in PLACEHOLDER_MARKERS):
        return "placeholder"
    if not data_uri.startswith(ALLOWED_IMAGE_PREFIXES):
        return "invalid"
    try:
        base64_part = data_uri.split(",", 1)[1]
        base64.b64decode(base64_part, validate=True)
    except Exception:
        return "invalid"
    return "valid"


def _asset_by_id(assets: list[dict[str, Any]], asset_id: str) -> dict[str, Any]:
    """asset_id가 일치하는 자산을 찾습니다."""

    for asset in assets:
        if _clean(asset.get("asset_id")) == asset_id:
            return asset
    return {}


def _slide_text(slide: dict[str, Any]) -> str:
    """slide 안의 텍스트 필드를 선택 규칙용 문자열로 합칩니다."""

    parts: list[str] = []
    for key in ("role", "layout", "headline", "title", "body", "caption"):
        if slide.get(key):
            parts.append(str(slide.get(key)))
    for key in ("bullets", "items", "tags"):
        for item in _list(slide.get(key)):
            parts.append(json.dumps(item, ensure_ascii=False, default=str) if isinstance(item, (dict, list)) else str(item))
    return " ".join(parts).lower()


def _payload(value: Any) -> dict[str, Any]:
    """Langflow Data/Message/dict/JSON 문자열을 일반 dict로 맞춥니다."""

    if isinstance(value, dict):
        return deepcopy(value)
    data = getattr(value, "data", None)
    if isinstance(data, dict):
        return deepcopy(data)
    text = getattr(value, "text", None) or getattr(value, "content", None)
    parsed = _parse_json_object(text)
    return parsed if parsed else ({"text": text} if isinstance(text, str) and text.strip() else {})


def _parse_json_object(value: Any) -> dict[str, Any]:
    """문자열 JSON object를 dict로 파싱합니다."""

    if isinstance(value, dict):
        return deepcopy(value)
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except Exception:
        return {}
    return deepcopy(parsed) if isinstance(parsed, dict) else {}


def _dict(value: Any) -> dict[str, Any]:
    """dict면 복사본을, 아니면 빈 dict를 반환합니다."""

    return deepcopy(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    """list면 복사본을, 아니면 빈 list를 반환합니다."""

    return deepcopy(value) if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    """list 또는 단일 값을 문자열 목록으로 정리합니다."""

    raw_items = value if isinstance(value, list) else ([value] if value not in (None, "") else [])
    result = []
    for item in raw_items:
        text = _clean(item).lower()
        if text and text not in result:
            result.append(text)
    return result


def _clean(value: Any) -> str:
    """값을 문자열로 바꾸고 앞뒤 공백을 제거합니다."""

    return str(value or "").strip()


def _truthy(value: Any) -> bool:
    """문자열/불리언 입력을 bool로 변환합니다."""

    if isinstance(value, bool):
        return value
    return _clean(value).lower() not in {"", "0", "false", "no", "off"}


def _first(items: list[Any], default: Any = "") -> Any:
    """첫 번째 truthy 값을 반환합니다."""

    for item in items:
        if item:
            return item
    return default


class CharacterAssetLoader(Component):
    """Langflow 화면에 표시되는 03번 커스텀 컴포넌트 클래스."""

    display_name = "03 캐릭터 자산 불러오기"
    description = "하냥이/하댕이 AI 포즈팩을 읽고 카드 역할에 맞는 asset_id 선택 컨텍스트를 만듭니다."
    icon = "Image"
    inputs = [
        DataInput(
            name="payload",
            display_name="카드뉴스 payload",
            info="02 브리프 정리 출력 또는 10 업로드 캐릭터 이미지 자산 등록 출력을 연결합니다.",
            input_types=["Data", "JSON", "StructuredContent", "Structured Content"],
            required=True,
        ),
        MessageTextInput(
            name="asset_manifest_json",
            display_name="캐릭터 자산 JSON",
            info="직접 manifest JSON을 붙여넣을 때 사용합니다. 업로드 방식은 10번 노드의 자산 등록 payload를 이 노드의 카드뉴스 브리프/계획 입력에 연결하세요.",
            required=False,
        ),
        MessageTextInput(name="auto_assign", display_name="계획에 자동 배정", value="true", advanced=True),
    ]
    outputs = [Output(name="payload_out", display_name="캐릭터 자산 포함 브리프", method="build_payload", types=["Data"])]

    def build_payload(self) -> Data:
        """캐릭터 자산 manifest와 선택 컨텍스트를 payload에 추가합니다."""

        result = load_character_assets(
            getattr(self, "payload", None),
            getattr(self, "asset_manifest_json", ""),
            getattr(self, "auto_assign", "true"),
        )
        context = _dict(result.get("character_asset_context"))
        validation = _dict(context.get("validation_report"))
        self.status = {
            "asset_family": context.get("asset_family"),
            "asset_count": validation.get("asset_count", 0),
            "valid_assets": validation.get("valid_asset_count", 0),
            "placeholder_assets": validation.get("placeholder_asset_count", 0),
            "warnings": len(_list(validation.get("warnings"))),
            "errors": len(_list(validation.get("errors"))),
        }
        return Data(data=result)
