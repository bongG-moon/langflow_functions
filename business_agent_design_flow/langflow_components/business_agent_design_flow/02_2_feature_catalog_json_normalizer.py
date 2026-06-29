from __future__ import annotations

"""02-2 추가 기능 JSON 정리 노드.

LLM이 반환한 추가 기능 카탈로그 JSON을 검증하고, 02 AI 에이전트 기능 카탈로그
노드의 `추가 기능 카탈로그 JSON` 입력에 바로 연결할 수 있는 JSON 문자열로 정리합니다.
"""

import hashlib
import json
import re
from copy import deepcopy
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import MessageTextInput, Output
from lfx.schema.message import Message


DIFFICULTIES = {"초급", "중급", "고급", "초급-중급", "중급-고급"}
CATEGORIES = {"data_lookup", "reporting", "communication", "integration", "governance", "local_feature_flow", "user_added"}


def normalize_feature_catalog_json(llm_response_value: Any = "") -> dict[str, Any]:
    """LLM 응답을 02 노드에 넣을 수 있는 기능 카탈로그 JSON으로 정리합니다."""

    text = _text(llm_response_value)
    parsed = _extract_json(text)
    warnings = []
    if not parsed:
        warnings.append("LLM 응답에서 기능 카탈로그 JSON을 찾지 못했습니다.")
        return {
            "catalog_notes": ["추가 기능 JSON 변환에 실패했습니다. 자연어 설명을 다시 구체적으로 작성하거나 LLM 응답을 확인하세요."],
            "capabilities": [],
            "normalizer_warnings": warnings,
        }

    capabilities = _normalize_capabilities(parsed)
    if not capabilities:
        warnings.append("LLM 응답에 사용할 수 있는 capabilities 항목이 없습니다.")

    result = {
        "catalog_notes": _string_list(parsed.get("catalog_notes"), 6, 180)
        or ["사용자 자연어 설명을 LLM이 변환한 추가 기능입니다."],
        "capabilities": capabilities,
    }
    if warnings:
        result["normalizer_warnings"] = warnings
    return result


def build_feature_catalog_json_text(llm_response_value: Any = "") -> str:
    """02 노드에 연결할 JSON 문자열을 만듭니다."""

    return json.dumps(normalize_feature_catalog_json(llm_response_value), ensure_ascii=False, indent=2, default=str)


def _normalize_capabilities(parsed: dict[str, Any]) -> list[dict[str, Any]]:
    """capabilities 목록을 02 노드가 이해하는 형태로 맞춥니다."""

    raw_items = parsed.get("capabilities")
    if isinstance(raw_items, dict):
        raw_items = [raw_items]
    if not isinstance(raw_items, list):
        raw_items = []

    result = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        display_name = _short(_pick(item, "display_name", "name", "title", "기능명"), "사용자 추가 기능", 80)
        when_to_use = _short(_pick(item, "when_to_use", "usage", "사용 상황", "언제 사용"), "", 220)
        beginner_use_case = _short(_pick(item, "beginner_use_case", "description", "설명", "use_case"), "", 220)
        if not beginner_use_case:
            beginner_use_case = f"{display_name} 기능을 업무 AI 에이전트 설계 후보로 추가합니다."
        if not when_to_use:
            when_to_use = "업무 설명에 이 기능과 관련된 조회, 판단, 생성, 공유 단계가 있을 때"

        capability_id = _short(_pick(item, "capability_id", "id", "기능 ID"), "", 100)
        if not capability_id:
            capability_id = _capability_id(display_name, when_to_use)

        category = _choice(_pick(item, "category", "분류"), CATEGORIES, "user_added")
        difficulty = _choice(_pick(item, "difficulty", "난이도"), DIFFICULTIES, "중급")
        source_reference = _short(
            _pick(item, "source_reference", "source_link", "reference", "참고 링크"),
            "user_input:natural_language",
            260,
        )
        implementation_hint = _short(
            _pick(item, "implementation_hint", "hint", "구현 힌트"),
            "처음에는 읽기 전용 또는 초안 생성 용도로 연결하고, 실제 실행은 사람 검토 뒤 진행합니다.",
            260,
        )

        result.append(
            {
                "capability_id": capability_id,
                "display_name": display_name,
                "category": category,
                "beginner_use_case": beginner_use_case,
                "when_to_use": when_to_use,
                "needed_inputs": _string_list(_pick(item, "needed_inputs", "inputs", "필요 입력"), 12, 80)
                or ["사용자 요청", "필요 데이터"],
                "typical_outputs": _string_list(_pick(item, "typical_outputs", "outputs", "산출물"), 12, 80)
                or ["처리 결과"],
                "difficulty": difficulty,
                "implementation_hint": implementation_hint,
                "source_reference": source_reference,
            }
        )
    return result[:30]


def _extract_json(text: str) -> dict[str, Any]:
    """LLM 응답에서 JSON object를 추출합니다."""

    raw = str(text or "").strip()
    if not raw:
        return {}
    candidates = []
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, flags=re.S | re.I)
    if fenced:
        candidates.append(fenced.group(1))
    candidates.append(raw)
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        candidates.append(raw[start : end + 1])
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except Exception:
            continue
        if isinstance(parsed, dict):
            return deepcopy(parsed)
    return {}


def _capability_id(display_name: str, when_to_use: str) -> str:
    """기능명과 사용 상황으로 안정적인 기능 ID를 만듭니다."""

    digest = hashlib.sha1(f"{display_name}|{when_to_use}".encode("utf-8")).hexdigest()[:10]
    return f"user_added_{digest}"


def _text(value: Any) -> str:
    """Langflow Message/Data/dict 등에서 텍스트를 꺼냅니다."""

    if value is None:
        return ""
    if isinstance(value, str):
        return value
    data = getattr(value, "data", None)
    if isinstance(data, dict):
        for key in ("text", "content", "response", "message"):
            if isinstance(data.get(key), str):
                return data[key]
    for attr in ("text", "content"):
        text = getattr(value, attr, None)
        if isinstance(text, str):
            return text
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def _pick(mapping: dict[str, Any], *keys: str) -> Any:
    """여러 후보 key 중 먼저 존재하는 값을 반환합니다."""

    for key in keys:
        if key in mapping and mapping.get(key) not in (None, ""):
            return mapping.get(key)
    return ""


def _string_list(value: Any, limit: int, item_limit: int) -> list[str]:
    """문자열 또는 문자열 목록을 정리합니다."""

    if isinstance(value, list):
        values = value
    elif isinstance(value, str):
        text = value.strip()
        for sep in ("，", "、", ";", "/", "·"):
            text = text.replace(sep, ",")
        values = [part.strip() for part in text.split(",") if part.strip()]
    else:
        values = []
    result = []
    for item in values:
        text = str(item or "").strip()
        if text and text not in result:
            result.append(text[:item_limit])
        if len(result) >= limit:
            break
    return result


def _short(value: Any, fallback: str, limit: int) -> str:
    """짧은 문자열을 반환합니다."""

    text = str(value or fallback or "").strip()
    return text[:limit]


def _choice(value: Any, allowed: set[str], fallback: str) -> str:
    """허용된 값만 통과시킵니다."""

    text = str(value or "").strip()
    return text if text in allowed else fallback


class FeatureCatalogJsonNormalizer(Component):
    """Langflow 화면에 표시되는 02-2 커스텀 컴포넌트 클래스."""

    display_name = "02-2 추가 기능 JSON 정리"
    description = "LLM이 만든 추가 기능 JSON을 검증하고 02 노드에 연결할 수 있는 JSON 문자열로 정리합니다."
    icon = "Braces"
    inputs = [
        MessageTextInput(
            name="llm_response",
            display_name="LLM JSON 변환 응답",
            required=True,
            info="02-1 프롬프트를 받은 LLM의 응답을 연결합니다.",
        )
    ]
    outputs = [Output(name="feature_catalog_json", display_name="추가 기능 카탈로그 JSON", method="build_message")]

    def build_message(self) -> Message:
        """02 노드에 연결할 JSON Message를 생성합니다."""

        text = build_feature_catalog_json_text(getattr(self, "llm_response", ""))
        parsed = normalize_feature_catalog_json(getattr(self, "llm_response", ""))
        self.status = {
            "추가 기능 수": len(parsed.get("capabilities", [])),
            "경고 수": len(parsed.get("normalizer_warnings", [])),
        }
        return Message(text=text)
