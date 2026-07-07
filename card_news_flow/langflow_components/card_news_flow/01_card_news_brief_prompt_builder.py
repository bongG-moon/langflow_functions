from __future__ import annotations

"""01 카드뉴스 브리프 프롬프트 변수 준비 노드."""

import json
from copy import deepcopy
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, Output
from lfx.schema.message import Message


def build_brief_template_variables(card_news_request_value: Any) -> dict[str, str]:
    """Langflow Prompt Template에 연결할 브리프 생성 변수들을 만듭니다."""

    payload = _payload(card_news_request_value)
    request = _dict(payload.get("card_news_request"))
    raw_content = _clean(request.get("raw_content"))
    instructions = "\n".join(
        [
            "- 사용자의 원문에서 월간 카드뉴스의 제목, 목적, 독자, 핵심 메시지, CTA, 제약사항을 추출하세요.",
            "- 회사 사내 카드뉴스이므로 귀엽고 친근하지만 과장되거나 유아적인 표현은 피하세요.",
            "- SK RED #EA002C와 SK Orange #F47725 기반의 귀여운 브랜드 톤을 염두에 두세요.",
            "- 결과물은 기본적으로 16:9 가로형 SNS 카드뉴스 deck이며 아래로 긴 문서가 아니라 한 화면씩 전환되는 구조입니다.",
            "- 카드 수가 지정되어 있으면 그 안에서 메시지 우선순위를 정리하세요.",
            "- template.fixed_structure가 true이면 같은 화면 수에서 역할 순서가 고정된다는 전제를 유지하세요.",
            "- 지시사항에 발간호/호수/발행일이 있으면 publication_info에 보존하세요.",
            "- 지시사항의 총 화면 수는 request_context_json.slide_count를 기준으로 따르세요.",
            "- page_image_overrides가 있는 페이지는 사용자가 만든 이미지 전용 페이지이므로 해당 페이지용 문구를 새로 만들 필요가 없습니다.",
            "- 보안, 개인정보, 기밀, 외부 AI 사용 관련 문장은 constraints와 must_include에 반드시 반영하세요.",
            "- 출력은 JSON object 하나만 반환하고 설명 문장은 붙이지 마세요.",
        ]
    )
    context = {
        "target_audience": request.get("target_audience", "전 직원"),
        "brand_tone": request.get("brand_tone", ""),
        "slide_count": request.get("slide_count", 6),
        "generation_instructions": request.get("generation_instructions", ""),
        "publication_info": _dict(request.get("publication_info")),
        "aspect_ratio": request.get("aspect_ratio", "16:9"),
        "animation_level": request.get("animation_level", "standard"),
        "primary_cta": _dict(request.get("primary_cta")),
        "theme": request.get("theme", "sk_cute_soft"),
        "template": _dict(request.get("template")),
        "page_image_overrides": _list(request.get("page_image_overrides")),
    }
    return {
        "raw_content": raw_content,
        "request_context_json": json.dumps(context, ensure_ascii=False, indent=2),
        "brief_instructions": instructions,
        "brief_output_schema": json.dumps(_brief_schema(), ensure_ascii=False, indent=2),
    }


def _brief_schema() -> dict[str, Any]:
    return {
        "brief": {
            "campaign_title": "카드뉴스 제목",
            "audience": "대상 독자",
            "communication_goal": "커뮤니케이션 목표",
            "tone_keywords": ["귀여운", "명확한", "실용적인"],
            "must_include": ["반드시 포함할 핵심 내용"],
            "content_pillars": [
                {
                    "pillar_id": "P1",
                    "title": "메시지 묶음 제목",
                    "summary": "카드뉴스에서 다룰 내용",
                    "priority": "high",
                }
            ],
            "cta": {"label": "CTA 문구", "url": "https://example.com"},
            "constraints": ["주의할 표현 또는 반드시 지켜야 하는 제약"],
            "template_id": "monthly_ai_news_standard",
            "fixed_structure": True,
            "suggested_slide_roles": ["cover", "why", "case", "tip", "security", "cta"],
        }
    }


def _payload(value: Any) -> dict[str, Any]:
    data = getattr(value, "data", value)
    return deepcopy(data) if isinstance(data, dict) else {}


def _dict(value: Any) -> dict[str, Any]:
    return deepcopy(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return deepcopy(value) if isinstance(value, list) else []


def _clean(value: Any) -> str:
    return str(value or "").strip()


class CardNewsBriefPromptBuilder(Component):
    display_name = "01 카드뉴스 브리프 프롬프트 변수 준비"
    description = "카드뉴스 브리프 생성을 위한 Prompt Template 변수들을 제공합니다."
    icon = "Braces"
    inputs = [DataInput(name="card_news_request", display_name="카드뉴스 요청", required=True)]
    outputs = [
        Output(name="raw_content", display_name="입력 원문", method="build_raw_content", types=["Message"], group_outputs=True),
        Output(name="request_context_json", display_name="요청 설정 JSON", method="build_request_context", types=["Message"], group_outputs=True),
        Output(name="brief_instructions", display_name="브리프 작성 지침", method="build_brief_instructions", types=["Message"], group_outputs=True),
        Output(name="brief_output_schema", display_name="출력 스키마 JSON", method="build_brief_output_schema", types=["Message"], group_outputs=True),
    ]

    def _variables(self) -> dict[str, str]:
        self.status = {"Prompt Template 변수": "입력 원문 / 요청 설정 JSON / 브리프 작성 지침 / 출력 스키마 JSON"}
        return build_brief_template_variables(getattr(self, "card_news_request", None))

    def build_raw_content(self) -> Message:
        return Message(text=self._variables()["raw_content"])

    def build_request_context(self) -> Message:
        return Message(text=self._variables()["request_context_json"])

    def build_brief_instructions(self) -> Message:
        return Message(text=self._variables()["brief_instructions"])

    def build_brief_output_schema(self) -> Message:
        return Message(text=self._variables()["brief_output_schema"])
