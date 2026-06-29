from __future__ import annotations

"""02-1 추가 기능 JSON 변환 프롬프트 준비 노드.

사용자가 자연어로 적은 "우리 팀에서 쓸 수 있는 기능" 설명을 LLM이 기능 카탈로그
JSON으로 바꿀 수 있도록 프롬프트 템플릿 변수를 준비합니다.
"""

import json
from copy import deepcopy
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, MessageTextInput, Output
from lfx.schema.message import Message


def build_feature_catalog_prompt_variables(payload_value: Any = None, feature_description: str = "") -> dict[str, Any]:
    """프롬프트 템플릿에 연결할 변수 dict를 만듭니다."""

    payload = _payload(payload_value)
    profile = _dict(payload.get("process_profile"))
    request = _dict(payload.get("business_request"))
    variables = {
        "추가_기능_자연어": str(feature_description or "").strip() or "(none)",
        "업무_컨텍스트_JSON": _json_text(
            {
                "business_request": request,
                "process_profile": profile,
            }
        ),
        "기능_JSON_작성_규칙": _writing_rules(),
        "기능_JSON_스키마": _json_text(_output_schema()),
    }
    return {
        "prompt_type": "feature_catalog_json_conversion",
        "prompt_variables": variables,
        "prompt_variable_names": list(variables.keys()),
        "payload": payload,
        "schema_hint": _output_schema(),
    }


def _writing_rules() -> str:
    """LLM이 자연어 기능 설명을 JSON으로 변환할 때 지킬 규칙입니다."""

    return "\n".join(
        [
            "역할:",
            "- 당신은 초보 Langflow 개발자를 돕는 기능 카탈로그 변환기입니다.",
            "- 사용자가 자연어로 적은 사내 기능, 기존 flow, API, 데이터 조회 기능, 리포트 기능을 기능 카탈로그 JSON으로 바꿉니다.",
            "",
            "반드시 지킬 규칙:",
            "- 오직 하나의 JSON object만 반환하세요.",
            "- markdown 코드블록으로 감싸지 마세요.",
            "- JSON 밖에 설명 문장을 쓰지 마세요.",
            "- 사용자가 적지 않은 시스템명, API명, 권한, 자동 실행 가능성을 지어내지 마세요.",
            "- 기능명은 display_name에 사람이 읽기 좋은 한글명으로 적으세요.",
            "- capability_id는 비워도 됩니다. 비어 있으면 다음 노드가 자동 생성합니다.",
            "- needed_inputs와 typical_outputs는 반드시 배열로 작성하세요.",
            "- 위험한 실행, 발송, 등록, 수정 기능은 implementation_hint에 사람 검토 또는 승인 단계를 포함하세요.",
            "- source_reference는 문서 링크가 있으면 링크를 넣고, 없으면 user_input:natural_language를 넣으세요.",
            "",
            "추천 category:",
            "- data_lookup: 데이터 조회",
            "- reporting: 리포트/대시보드",
            "- communication: 메일/메시지 초안",
            "- integration: 외부 시스템/API/MCP 연동",
            "- governance: 검토/승인/보안",
            "- local_feature_flow: 이미 구현된 기능flow",
            "- user_added: 위에 맞지 않는 사용자 추가 기능",
        ]
    )


def _output_schema() -> dict[str, Any]:
    """LLM이 반환해야 하는 기능 카탈로그 JSON 구조입니다."""

    return {
        "catalog_notes": ["사용자 자연어 설명을 기반으로 추가한 기능입니다."],
        "capabilities": [
            {
                "capability_id": "",
                "display_name": "기능명",
                "category": "data_lookup | reporting | communication | integration | governance | local_feature_flow | user_added",
                "beginner_use_case": "초보자가 이해할 수 있는 기능 설명",
                "when_to_use": "어떤 업무 상황에서 쓰면 좋은지",
                "needed_inputs": ["필요 입력 1", "필요 입력 2"],
                "typical_outputs": ["산출물 1", "산출물 2"],
                "difficulty": "초급 | 중급 | 고급 | 초급-중급 | 중급-고급",
                "implementation_hint": "처음 구현할 때의 주의사항과 권장 연결 방식",
                "source_reference": "참고 링크 또는 user_input:natural_language",
            }
        ],
    }


def _json_text(value: Any) -> str:
    """프롬프트 변수로 넘길 값을 읽기 좋은 JSON 문자열로 변환합니다."""

    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def _payload(value: Any) -> dict[str, Any]:
    """Langflow Data/Message/dict/JSON 문자열을 일반 dict로 맞춥니다."""

    if isinstance(value, dict):
        return deepcopy(value)
    data = getattr(value, "data", None)
    if isinstance(data, dict):
        return deepcopy(data)
    text = getattr(value, "text", None) or getattr(value, "content", None)
    if isinstance(text, str) and text.strip():
        try:
            parsed = json.loads(text)
        except Exception:
            return {"text": text}
        return deepcopy(parsed) if isinstance(parsed, dict) else {"text": text}
    return {}


def _dict(value: Any) -> dict[str, Any]:
    """dict면 복사본을, 아니면 빈 dict를 반환합니다."""

    return deepcopy(value) if isinstance(value, dict) else {}


class FeatureCatalogJsonPromptBuilder(Component):
    """Langflow 화면에 표시되는 02-1 커스텀 컴포넌트 클래스."""

    display_name = "02-1 추가 기능 JSON 프롬프트 준비"
    description = "자연어 추가 기능 설명을 LLM이 기능 카탈로그 JSON으로 바꿀 수 있게 프롬프트 변수를 준비합니다."
    icon = "FileJson"
    inputs = [
        DataInput(name="payload", display_name="업무 구조화 결과", required=False),
        MessageTextInput(
            name="feature_description",
            display_name="추가 기능 자연어 설명",
            required=True,
            info="사내에서 사용할 수 있는 기능, API, 기존 flow, 데이터 조회 기능 등을 자연어로 자유롭게 적습니다.",
        ),
    ]
    outputs = [
        Output(name="feature_description_text", display_name="추가_기능_자연어", method="build_feature_description", group_outputs=True),
        Output(name="work_context_json", display_name="업무_컨텍스트_JSON", method="build_work_context_json", group_outputs=True),
        Output(name="writing_rules", display_name="기능_JSON_작성_규칙", method="build_writing_rules", group_outputs=True),
        Output(name="schema_json", display_name="기능_JSON_스키마", method="build_schema_json", group_outputs=True),
    ]

    def build_feature_description(self) -> Message:
        """프롬프트 템플릿의 {추가_기능_자연어} 변수에 연결할 값을 만듭니다."""

        return self._variable_message("추가_기능_자연어")

    def build_work_context_json(self) -> Message:
        """프롬프트 템플릿의 {업무_컨텍스트_JSON} 변수에 연결할 값을 만듭니다."""

        return self._variable_message("업무_컨텍스트_JSON")

    def build_writing_rules(self) -> Message:
        """프롬프트 템플릿의 {기능_JSON_작성_규칙} 변수에 연결할 값을 만듭니다."""

        return self._variable_message("기능_JSON_작성_규칙")

    def build_schema_json(self) -> Message:
        """프롬프트 템플릿의 {기능_JSON_스키마} 변수에 연결할 값을 만듭니다."""

        return self._variable_message("기능_JSON_스키마")

    def _variable_message(self, key: str) -> Message:
        """공통 방식으로 프롬프트 변수 Message를 만듭니다."""

        result = build_feature_catalog_prompt_variables(
            payload_value=getattr(self, "payload", None),
            feature_description=getattr(self, "feature_description", ""),
        )
        variables = _dict(result.get("prompt_variables"))
        self.status = {"출력 변수": result.get("prompt_variable_names", [])}
        return Message(text=str(variables.get(key) or ""))
