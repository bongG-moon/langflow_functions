from __future__ import annotations

"""03 AI 에이전트 설계 프롬프트 준비 노드.

앞 노드들이 만든 업무 요청, 업무 구조화 결과, 기능 카탈로그, 출력 스키마를
하나의 완성 프롬프트로 묶습니다. 사용자는 00 업무 설명만 입력하고,
나머지 지침과 카탈로그는 이 노드 내부 프롬프트에 포함됩니다.
"""

import json
from copy import deepcopy
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, Output
from lfx.schema.message import Message


def build_agent_design_prompt(payload_value: Any) -> dict[str, Any]:
    """LLM에 바로 전달할 업무 AI 에이전트 설계 프롬프트를 만듭니다."""

    payload = _payload(payload_value)
    request = _dict(payload.get("business_request"))
    profile = _dict(payload.get("process_profile"))
    catalog = _dict(payload.get("agent_capability_catalog"))
    context = {
        "business_request": request,
        "process_profile": profile,
        "agent_capability_catalog": _compact_catalog(catalog),
        "writing_rules": _writing_rules(),
        "output_schema": _output_schema(),
    }
    prompt = _compose_prompt(context)
    return {
        "prompt_type": "business_agent_design",
        "prompt": prompt,
        "prompt_context": context,
        "payload": payload,
        "schema_hint": context["output_schema"],
    }


def build_agent_design_prompt_variables(payload_value: Any, extra_instruction: str = "") -> dict[str, Any]:
    """이전 버전과의 호환을 위해 단일 컨텍스트 변수도 함께 반환합니다."""

    result = build_agent_design_prompt(payload_value)
    context = deepcopy(result["prompt_context"])
    if extra_instruction:
        context["business_request"]["additional_instructions"] = str(extra_instruction).strip()
        result["prompt"] = _compose_prompt(context)
    return {
        "prompt_type": "business_agent_design",
        "prompt": result["prompt"],
        "prompt_variables": {
            "설계_컨텍스트_JSON": _json_text(context),
        },
        "prompt_variable_names": ["설계_컨텍스트_JSON"],
        "payload": result["payload"],
        "schema_hint": context["output_schema"],
    }


def _compose_prompt(context: dict[str, Any]) -> str:
    """프롬프트 본문을 한 번에 조립합니다."""

    return "\n".join(
        [
            "당신은 초보 Langflow 개발자를 위한 업무 AI 에이전트 설계 코치입니다.",
            "사용자가 자연어로 설명한 업무를 읽고, 업무 프로세스 로직을 보기 좋게 구조화한 뒤,",
            "이 업무를 AI 에이전트로 만든다면 어떤 영역을 어떻게 개선할 수 있는지 제안하세요.",
            "",
            "중요한 전제:",
            "- 사용자는 00 업무 설명 입력에 모든 내용을 한 번에 적습니다.",
            "- 업무 목적, 데이터/시스템, 제약, 원하는 결과, 추가 기능이 본문 안에 섞여 있을 수 있습니다.",
            "- 아래 컨텍스트에 있는 기본 기능 카탈로그와 사용자가 본문에 적은 추가 기능 후보를 함께 참고하세요.",
            "- 입력에 없는 시스템, 데이터 컬럼, 자동화 가능성을 과장해서 만들지 마세요.",
            "- 보안, 승인, 고객 발송, 시스템 등록/수정처럼 위험한 작업은 자동 실행보다 사람 검토 또는 승인 Gate를 우선 제안하세요.",
            "",
            "설계 컨텍스트 JSON:",
            _json_text(
                {
                    "business_request": context.get("business_request", {}),
                    "process_profile": context.get("process_profile", {}),
                    "agent_capability_catalog": context.get("agent_capability_catalog", {}),
                }
            ),
            "",
            "작성 규칙:",
            context.get("writing_rules", ""),
            "",
            "반환해야 하는 JSON 구조:",
            _json_text(context.get("output_schema", {})),
            "",
            "출력 규칙:",
            "- 오직 하나의 JSON object만 반환하세요.",
            "- markdown 코드블록으로 감싸지 마세요.",
            "- JSON 밖에 설명 문장을 쓰지 마세요.",
            "- suggested_capabilities에는 설계 컨텍스트의 agent_capability_catalog.capabilities에 있는 capability_id만 사용하세요.",
            "- 초보자가 바로 따라 만들 수 있게 recommended_flow_architecture.nodes와 beginner_build_plan을 구체적으로 작성하세요.",
            "- user_friendly_view.card_sections, user_friendly_view.process_table, user_friendly_view.roadmap을 반드시 채우세요.",
            "- reference_information은 한글 설명과 source_link를 함께 넣어 작성하세요.",
        ]
    )


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
    """LLM이 설계 결과를 작성할 때 지켜야 하는 규칙입니다."""

    return "\n".join(
        [
            "역할:",
            "- 당신은 초보 Langflow 개발자를 돕는 업무 AI 에이전트 설계 코치입니다.",
            "- 업무를 시작 조건, 입력 데이터, 처리 단계, 판단 기준, 산출물, 전달/승인 단계로 나누어 설명합니다.",
            "- 실제 구현 가능한 Langflow flow 관점으로 설명하되, 초보자가 바로 이해할 수 있는 표현을 사용합니다.",
            "",
            "사용자 요구 반영:",
            "- 00 업무 설명의 원문 표현을 가장 중요한 요구사항으로 취급하세요.",
            "- 사용자가 원하는 출력 형태, UI, 리포트, 승인 방식, 자동화 제외 범위를 구체적으로 적었다면 반드시 반영하세요.",
            "- 사용자가 본문 안에 '기존 기능', '사내 API', '이미 만든 flow'를 언급했다면 카탈로그의 user_added_* 기능 후보를 우선 검토하세요.",
            "- 정보가 부족하면 임의로 단정하지 말고 required_information.missing_information에 질문으로 남기세요.",
            "",
            "설계 기준:",
            "- 반복, 수동 복사, 조회, 비교, 조건 판단, 요약, 알림, 보고가 있으면 AI 에이전트화 후보입니다.",
            "- 데이터 조회가 핵심이면 reusable_data_flow를 추천하세요.",
            "- 조회/분석 결과를 사람이 보기 좋게 보여줘야 하면 html_report_flow를 추천하세요.",
            "- 여러 외부 도구 호출이 필요하면 agent_with_tools 또는 mcp_tools를 2차 확장안으로 제안하세요.",
            "- 고객 발송, 승인, 시스템 업데이트, 민감 데이터 처리는 human_review_gate를 우선 제안하세요.",
            "",
            "사용자용 출력 기준:",
            "- executive_summary는 3~5문장 이내로 명확하게 작성하세요.",
            "- process_logic.steps는 4~9개 정도로 정리하고, 각 단계에 actor/input/action/output/decision을 넣으세요.",
            "- agent_opportunities는 개선 영역, 현재 불편함, AI 지원 방식, 기대 효과, 주의사항을 함께 적으세요.",
            "- beginner_build_plan은 초보자가 Langflow에서 노드를 연결하는 순서대로 작성하세요.",
            "- user_friendly_view는 최종 Markdown 출력이 보기 좋게 카드, 표, 로드맵 형태로 채우세요.",
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
            "flow_summary": "권장 Langflow 구조 요약",
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
            "nice_to_have": ["있으면 설계가 좋아지는 정보"],
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
                "used_for": "이 설계에서 참고할 이유",
                "source_link": "참조 링크",
            }
        ],
        "warnings": ["주의사항"],
    }


def _json_text(value: Any) -> str:
    """프롬프트에 넣을 값을 읽기 좋은 JSON 문자열로 변환합니다."""

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
    description = "업무 요청, 구조화 결과, 기능 카탈로그, 작성 규칙을 합쳐 LLM에 바로 넣을 프롬프트 하나를 만듭니다."
    icon = "Sparkles"
    inputs = [
        DataInput(name="payload", display_name="기능 카탈로그 결과", required=True),
    ]
    outputs = [
        Output(name="design_prompt", display_name="LLM 설계 프롬프트", method="build_design_prompt"),
    ]

    def build_design_prompt(self) -> Message:
        """LLM input에 직접 연결할 프롬프트 Message를 만듭니다."""

        result = build_agent_design_prompt(payload_value=getattr(self, "payload", None))
        context = result.get("prompt_context", {})
        catalog = _dict(context.get("agent_capability_catalog"))
        self.status = {
            "프롬프트 글자 수": len(result.get("prompt", "")),
            "기능 수": len(_list(catalog.get("capabilities"))),
            "출력 방식": "LLM에 바로 연결",
        }
        return Message(text=str(result.get("prompt") or ""))
