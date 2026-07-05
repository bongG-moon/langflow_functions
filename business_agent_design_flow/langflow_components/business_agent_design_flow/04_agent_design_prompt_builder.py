from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, Output
from lfx.schema.message import Message


def build_agent_design_template_variables(catalog_context_value: Any) -> dict[str, str]:
    """Langflow 기본 Prompt Template에 연결할 AI Agent 설계 변수들을 만듭니다."""
    payload = _payload(catalog_context_value)
    context = _dict(payload.get("catalog_context"))

    design_instructions = "\n".join(
        [
            "- 사용자의 현재 업무를 먼저 존중하고, 어디가 자동화/보조/검토로 바뀌는지 구분하세요.",
            "- 추천 기능은 반드시 카탈로그에 있는 canonical_key를 catalog_id로 사용하세요.",
            "- 하나의 방식만 고집하지 말고, 가능하면 기본안과 확장안을 함께 제안하세요.",
            "- 자동 발송, 시스템 쓰기, 승인, 개인정보 처리처럼 위험한 작업은 반드시 사람 검토 gate를 넣으세요.",
            "- 초보 Langflow 개발자가 따라할 수 있도록 구현 순서를 구체적으로 작성하세요.",
            "- HTML 코드는 만들지 마세요. 아래 JSON 설계만 반환하세요.",
            "- JSON 외의 설명 문장은 반환하지 마세요.",
        ]
    )

    return {
        "business_profile_json": json.dumps(context.get("business_profile", {}), ensure_ascii=False, indent=2),
        "catalog_items_json": json.dumps(context.get("ranked_catalog_items", []), ensure_ascii=False, indent=2),
        "recommendation_trace_json": json.dumps(context.get("recommendation_trace", {}), ensure_ascii=False, indent=2),
        "design_instructions": design_instructions,
        "design_output_schema": json.dumps(_design_schema(), ensure_ascii=False, indent=2),
    }


def _design_schema() -> dict[str, Any]:
    return {
        "agent_design": {
            "report_title": "결과물 제목",
            "summary": "개선 방향 요약",
            "as_is_flow": [
                {
                    "step_id": "A1",
                    "title": "현재 단계",
                    "description": "현재 사람이 하는 일",
                    "actor": "담당자",
                    "systems": ["시스템"],
                }
            ],
            "to_be_flow": [
                {
                    "step_id": "T1",
                    "title": "개선 후 단계",
                    "description": "AI Agent 또는 사람이 하는 일",
                    "agent_role": "AI Agent | 사람 | 시스템",
                    "systems": ["시스템"],
                }
            ],
            "recommended_capabilities": [
                {
                    "catalog_id": "카탈로그 canonical_key",
                    "usage": "이 업무에서 쓰는 방식",
                    "reason": "추천 근거",
                    "implementation_hint": "Langflow 구현 힌트",
                }
            ],
            "implementation_roadmap": [
                {"phase": "1단계", "action": "구현 작업", "owner": "담당"}
            ],
            "risk_controls": [
                {"risk": "위험", "control": "통제 방안", "human_review_required": True}
            ],
            "alternative_options": [
                {"option": "다른 구현 방식", "tradeoff": "장단점"}
            ],
            "open_questions": ["추가 확인 질문"],
        }
    }


def _payload(value: Any) -> dict[str, Any]:
    data = getattr(value, "data", value)
    return deepcopy(data) if isinstance(data, dict) else {}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


class AgentDesignPromptBuilder(Component):
    display_name = "04 AI Agent 설계 프롬프트 변수 준비"
    description = "Langflow 기본 Prompt Template에 연결할 업무 프로필, 추천 카탈로그, 추천 근거, 설계 지침, 출력 스키마 변수를 제공합니다."
    icon = "Braces"
    inputs = [DataInput(name="catalog_context", display_name="추천 컨텍스트", required=True)]
    outputs = [
        Output(name="business_profile_json", display_name="업무 프로필 JSON", method="build_business_profile_json", types=["Message"], group_outputs=True),
        Output(name="catalog_items_json", display_name="추천 카탈로그 JSON", method="build_catalog_items_json", types=["Message"], group_outputs=True),
        Output(name="recommendation_trace_json", display_name="추천 근거 JSON", method="build_recommendation_trace_json", types=["Message"], group_outputs=True),
        Output(name="design_instructions", display_name="설계 지침", method="build_design_instructions", types=["Message"], group_outputs=True),
        Output(name="design_output_schema", display_name="출력 스키마 JSON", method="build_design_output_schema", types=["Message"], group_outputs=True),
    ]

    def build_business_profile_json(self) -> Message:
        variables = build_agent_design_template_variables(getattr(self, "catalog_context", None))
        self.status = {"Prompt Template 변수": "업무 프로필 / 추천 카탈로그 / 추천 근거 / 설계 지침 / 출력 스키마"}
        return Message(text=variables["business_profile_json"])

    def build_catalog_items_json(self) -> Message:
        variables = build_agent_design_template_variables(getattr(self, "catalog_context", None))
        self.status = {"Prompt Template 변수": "업무 프로필 / 추천 카탈로그 / 추천 근거 / 설계 지침 / 출력 스키마"}
        return Message(text=variables["catalog_items_json"])

    def build_recommendation_trace_json(self) -> Message:
        variables = build_agent_design_template_variables(getattr(self, "catalog_context", None))
        self.status = {"Prompt Template 변수": "업무 프로필 / 추천 카탈로그 / 추천 근거 / 설계 지침 / 출력 스키마"}
        return Message(text=variables["recommendation_trace_json"])

    def build_design_instructions(self) -> Message:
        variables = build_agent_design_template_variables(getattr(self, "catalog_context", None))
        self.status = {"Prompt Template 변수": "업무 프로필 / 추천 카탈로그 / 추천 근거 / 설계 지침 / 출력 스키마"}
        return Message(text=variables["design_instructions"])

    def build_design_output_schema(self) -> Message:
        variables = build_agent_design_template_variables(getattr(self, "catalog_context", None))
        self.status = {"Prompt Template 변수": "업무 프로필 / 추천 카탈로그 / 추천 근거 / 설계 지침 / 출력 스키마"}
        return Message(text=variables["design_output_schema"])
