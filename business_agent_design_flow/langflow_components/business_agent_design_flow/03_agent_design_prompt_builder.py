from __future__ import annotations

"""03 AI 에이전트 설계 프롬프트 변수 준비 노드.

Langflow 기본 프롬프트 템플릿 노드에 연결할 변수를 만듭니다.
LLM은 업무 설명을 바탕으로 프로세스 로직, AI 에이전트화 아이디어, 초보자용 구현 순서,
사용자에게 보기 좋은 요약 구조를 JSON으로 반환해야 합니다.
"""

import json
from copy import deepcopy
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, MessageTextInput, Output
from lfx.schema.message import Message


def build_agent_design_prompt_variables(payload_value: Any, extra_instruction: str = "") -> dict[str, Any]:
    """프롬프트 템플릿에 연결할 변수 dict를 만듭니다."""

    payload = _payload(payload_value)
    request = _dict(payload.get("business_request"))
    profile = _dict(payload.get("process_profile"))
    catalog = _dict(payload.get("agent_capability_catalog"))
    variables = {
        "업무_요청_JSON": _json_text(request),
        "업무_프로세스_컨텍스트_JSON": _json_text(profile),
        "에이전트_기능_카탈로그_JSON": _json_text(_compact_catalog(catalog)),
        "추가_지시사항": str(extra_instruction or "").strip() or "(none)",
        "작성_규칙": _writing_rules(),
        "출력_스키마_JSON": _json_text(_output_schema()),
    }
    return {
        "prompt_type": "business_agent_design",
        "prompt_variables": variables,
        "prompt_variable_names": list(variables.keys()),
        "payload": payload,
        "schema_hint": _output_schema(),
    }


def _compact_catalog(catalog: dict[str, Any]) -> dict[str, Any]:
    """프롬프트가 너무 길어지지 않도록 카탈로그 핵심만 남깁니다."""

    capabilities = []
    for item in _list(catalog.get("capabilities")):
        if not isinstance(item, dict):
            continue
        capabilities.append(
            {
                "capability_id": item.get("capability_id"),
                "display_name": item.get("display_name"),
                "category": item.get("category"),
                "beginner_use_case": item.get("beginner_use_case"),
                "when_to_use": item.get("when_to_use"),
                "needed_inputs": _list(item.get("needed_inputs")),
                "typical_outputs": _list(item.get("typical_outputs")),
                "difficulty": item.get("difficulty"),
                "implementation_hint": item.get("implementation_hint"),
            }
        )
    return {
        "catalog_notes": _list(catalog.get("catalog_notes")),
        "reference_information": _list(catalog.get("reference_information")),
        "capabilities": capabilities,
        "agent_design_patterns": _list(catalog.get("agent_design_patterns")),
    }


def _writing_rules() -> str:
    """LLM이 결과를 작성할 때 지켜야 하는 규칙입니다."""

    return "\n".join(
        [
            "역할:",
            "- 당신은 초보 Langflow 개발자를 돕는 업무 AI 에이전트 설계 코치입니다.",
            "- 사용자가 자연어로 설명한 업무를 읽고, 업무 프로세스 로직과 AI 에이전트화 개선 아이디어를 구조화합니다.",
            "- 실제 구현 가능한 Langflow flow 관점으로 설명하되, 초보자가 바로 이해할 수 있게 쉬운 표현을 사용합니다.",
            "",
            "반드시 지킬 규칙:",
            "- 오직 하나의 엄격한 JSON object만 반환하세요. markdown 코드블록, HTML, 설명 문장을 JSON 밖에 쓰지 마세요.",
            "- 입력에 없는 사실, 시스템명, 데이터 컬럼, 자동화 가능성을 과장하지 마세요.",
            "- 자동 실행이 위험한 구간은 human_review_gate 또는 사람 검토 단계로 남기세요.",
            "- 기존 기능flow를 제안할 때는 reusable_data_flow, html_report_flow처럼 실제 카탈로그에 있는 기능 ID만 사용하세요.",
            "- 초보 개발자에게 필요한 입력 정보가 부족하면 missing_information에 질문 형태로 적으세요.",
            "- 결과는 기계가 읽는 JSON이면서도 최종 Markdown 출력 노드가 보기 좋게 렌더링할 수 있는 구조여야 합니다.",
            "",
            "분석 관점:",
            "- 업무를 시작 조건, 입력 데이터, 처리 단계, 판단 기준, 산출물, 전달/승인 단계로 나눠보세요.",
            "- 반복, 수동 복사, 조회, 비교, 조건 판단, 요약, 알림, 보고가 있으면 AI 에이전트화 후보입니다.",
            "- 보안, 승인, 고객 발송, 시스템 업데이트는 완전 자동화보다 검토 후 실행 패턴을 우선 제안하세요.",
            "- 업무 결과를 사람이 읽어야 하면 html_report_flow 또는 Markdown 출력이 적합합니다.",
            "- 데이터 조회가 필요하면 reusable_data_flow를 후보로 제안하세요.",
            "- 여러 외부 도구가 필요하면 에이전트와 도구 또는 MCP 도구를 후보로 제안하되, 초보자에게는 2단계 확장안으로 설명하세요.",
            "",
            "사용자 보기 좋은 출력 기준:",
            "- executive_summary는 3~5문장 이내로 명확하게 작성하세요.",
            "- process_logic.steps는 4~9개 정도로 정리하고, 각 단계에 actor/input/action/output/decision을 넣으세요.",
            "- agent_opportunities는 기대 효과, 난이도, 추천 기능, 주의사항을 포함하세요.",
            "- beginner_build_plan은 초보자가 Langflow에서 노드를 연결하는 순서대로 작성하세요.",
            "- user_friendly_view에는 card_sections, process_table, roadmap을 포함해 최종 출력 노드가 보기 좋은 Markdown으로 만들 수 있게 하세요.",
            "- reference_information에는 참고한 Langflow 기능을 한글 설명과 source_link가 함께 있는 형태로 작성하세요.",
        ]
    )


def _output_schema() -> dict[str, Any]:
    """LLM이 반환해야 하는 JSON 구조입니다."""

    return {
        "title": "업무 AI 에이전트 설계 제목",
        "executive_summary": [
            "업무가 무엇인지",
            "AI 에이전트화하면 좋아지는 부분",
            "주의해야 할 부분",
        ],
        "process_logic": {
            "trigger": "업무 시작 조건",
            "main_inputs": ["입력 데이터/시스템/사람 입력"],
            "main_outputs": ["산출물"],
            "steps": [
                {
                    "step_no": 1,
                    "step_name": "단계명",
                    "actor": "human | llm | tool | system | reviewer",
                    "input": "이 단계의 입력",
                    "action": "수행 작업",
                    "output": "이 단계의 출력",
                    "decision": "판단 기준 또는 조건",
                    "automation_level": "manual | assist | semi_auto | auto",
                }
            ],
            "decision_points": ["조건/판단 기준"],
            "human_checkpoints": ["사람 검토/승인 구간"],
        },
        "agent_opportunities": [
            {
                "area": "개선 영역",
                "current_pain": "현재 불편함",
                "agent_idea": "AI 에이전트가 도울 방식",
                "expected_impact": "기대 효과",
                "suggested_capabilities": ["카탈로그 기능 ID"],
                "difficulty": "초급 | 중급 | 고급",
                "guardrail": "보안/검토/승인 주의사항",
            }
        ],
        "recommended_flow_architecture": {
            "flow_summary": "권장 Langflow 구조 한 줄 요약",
            "nodes": [
                {
                    "order": 1,
                    "node_name": "노드명",
                    "role": "노드 역할",
                    "input": "연결할 입력",
                    "output": "다음 노드로 넘길 출력",
                    "beginner_tip": "초보자 팁",
                }
            ],
            "reuse_existing_flows": [
                {
                    "flow_name": "reusable_data_flow | html_report_flow",
                    "where_to_use": "어느 단계에서 쓰는지",
                    "why": "왜 필요한지",
                }
            ],
        },
        "required_information": {
            "must_have": ["구현 전에 반드시 필요한 정보"],
            "nice_to_have": ["있으면 품질이 좋아지는 정보"],
            "missing_information": ["사용자에게 추가로 물어볼 질문"],
        },
        "beginner_build_plan": [
            {
                "step_no": 1,
                "task": "초보자가 Langflow에서 할 일",
                "result": "완료 후 보이는 결과",
                "check_method": "정상 동작 확인 방법",
            }
        ],
        "user_friendly_view": {
            "card_sections": [
                {"title": "카드 제목", "body": "짧은 설명", "tone": "info | success | warning | danger"}
            ],
            "process_table": [
                {"step": "단계", "human_work": "사람 업무", "agent_support": "AI 에이전트 지원", "output": "산출물"}
            ],
            "roadmap": [
                {"phase": "1단계", "goal": "목표", "deliverable": "산출물"}
            ],
        },
        "reference_information": [
            {
                "title": "참조 기능 또는 문서명",
                "description": "초보자가 이해할 수 있는 한글 설명",
                "used_for": "이 설계에서 참고한 이유",
                "source_link": "참조 링크",
            }
        ],
        "warnings": ["주의사항"],
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


def _list(value: Any) -> list[Any]:
    """list면 복사본을, 아니면 빈 list를 반환합니다."""

    return deepcopy(value) if isinstance(value, list) else []


class AgentDesignPromptBuilder(Component):
    """Langflow 화면에 표시되는 03 커스텀 컴포넌트 클래스."""

    display_name = "03 AI 에이전트 설계 프롬프트 준비"
    description = "Langflow 기본 프롬프트 템플릿에 연결할 업무 AI 에이전트 설계 변수들을 준비합니다."
    icon = "Sparkles"
    inputs = [
        DataInput(name="payload", display_name="기능 카탈로그 결과", required=True),
        MessageTextInput(
            name="extra_instruction",
            display_name="추가 설계 지시사항",
            required=False,
            info="특정 팀 기준, 보안 기준, 우선순위, 출력 톤을 추가로 적습니다.",
        ),
    ]
    outputs = [
        Output(name="business_request_json", display_name="업무_요청_JSON", method="build_business_request_json", group_outputs=True),
        Output(name="process_context_json", display_name="업무_프로세스_컨텍스트_JSON", method="build_process_context_json", group_outputs=True),
        Output(name="capability_catalog_json", display_name="에이전트_기능_카탈로그_JSON", method="build_capability_catalog_json", group_outputs=True),
        Output(name="extra_instruction_text", display_name="추가_지시사항", method="build_extra_instruction_text", group_outputs=True),
        Output(name="writing_rules", display_name="작성_규칙", method="build_writing_rules", group_outputs=True),
        Output(name="output_schema_json", display_name="출력_스키마_JSON", method="build_output_schema_json", group_outputs=True),
    ]

    def build_business_request_json(self) -> Message:
        """프롬프트 템플릿의 {업무_요청_JSON} 변수에 연결할 값을 만듭니다."""

        return self._variable_message("업무_요청_JSON")

    def build_process_context_json(self) -> Message:
        """프롬프트 템플릿의 {업무_프로세스_컨텍스트_JSON} 변수에 연결할 값을 만듭니다."""

        return self._variable_message("업무_프로세스_컨텍스트_JSON")

    def build_capability_catalog_json(self) -> Message:
        """프롬프트 템플릿의 {에이전트_기능_카탈로그_JSON} 변수에 연결할 값을 만듭니다."""

        return self._variable_message("에이전트_기능_카탈로그_JSON")

    def build_extra_instruction_text(self) -> Message:
        """프롬프트 템플릿의 {추가_지시사항} 변수에 연결할 값을 만듭니다."""

        return self._variable_message("추가_지시사항")

    def build_writing_rules(self) -> Message:
        """프롬프트 템플릿의 {작성_규칙} 변수에 연결할 값을 만듭니다."""

        return self._variable_message("작성_규칙")

    def build_output_schema_json(self) -> Message:
        """프롬프트 템플릿의 {출력_스키마_JSON} 변수에 연결할 값을 만듭니다."""

        return self._variable_message("출력_스키마_JSON")

    def _variable_message(self, key: str) -> Message:
        """공통 방식으로 prompt variable Message를 만듭니다."""

        result = build_agent_design_prompt_variables(
            payload_value=getattr(self, "payload", None),
            extra_instruction=getattr(self, "extra_instruction", ""),
        )
        variables = _dict(result.get("prompt_variables"))
        self.status = {"출력 변수": result.get("prompt_variable_names", [])}
        return Message(text=str(variables.get(key) or ""))
