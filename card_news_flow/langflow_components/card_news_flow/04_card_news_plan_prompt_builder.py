from __future__ import annotations

"""04 카드뉴스 생성 프롬프트 변수 준비 노드."""

import json
from copy import deepcopy
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, Output
from lfx.schema.message import Message


def build_plan_template_variables(character_payload_value: Any) -> dict[str, str]:
    """카드뉴스 계획 생성을 위한 Prompt Template 변수들을 만듭니다."""

    payload = _payload(character_payload_value)
    request = _dict(payload.get("card_news_request"))
    brief = _dict(payload.get("brief"))
    asset_context = _dict(payload.get("character_asset_context"))
    compact_assets = {
        "asset_family": asset_context.get("asset_family", ""),
        "default_asset_id": asset_context.get("default_asset_id", ""),
        "pose_groups": _list(asset_context.get("pose_groups")),
        "slide_role_defaults": _dict(asset_context.get("slide_role_defaults")),
        "available_character_assets": _list(asset_context.get("available_character_assets")),
    }
    instructions = "\n".join(
        [
            "- 카드뉴스 전체 HTML을 만들지 말고 JSON 계획만 작성하세요.",
            "- theme은 기본적으로 sk_cute_soft를 사용하고 SK RED #EA002C, SK Orange #F47725 색감을 반영하세요.",
            "- 기본 화면 비율은 16:9 가로형 SNS 카드뉴스 deck입니다. 세로형/긴 문서형으로 설계하지 마세요.",
            "- request_json.slide_count와 같은 개수의 slide를 생성하세요.",
            "- request_json.template.fixed_structure가 true이면 brief_json.suggested_slide_roles 순서를 그대로 사용하세요. 역할/레이아웃 순서를 새로 설계하지 말고 각 슬롯의 내용만 작성하세요.",
            "- request_json.publication_info 또는 brief_json.publication_info의 발간호 정보를 card_news_plan.publication_info와 첫 cover slide에 반영하세요.",
            "- 첫 slide는 반드시 role=cover로 두고 제목, 발간호/호수, 발행 정보를 보여주는 표지로 구성하세요.",
            "- 화면은 아래로 내려가는 스크롤 문서가 아니라 한 장씩 전환되는 carousel/deck 구조입니다. 각 slide는 한 화면 안에서 독립적으로 읽히도록 작성하세요.",
            "- request_json.page_image_overrides에 지정된 page 또는 slide_id는 사용자가 만든 이미지를 그대로 보여주는 페이지입니다. 해당 slide는 role=image, layout=image_full로 두고 headline/body/bullets/buttons/character를 비워두세요.",
            "- 캐릭터 이미지는 새로 만들지 말고 available_character_assets 중 asset_id만 선택하세요.",
            "- 각 slide는 한눈에 읽히도록 headline은 짧게, body는 2-4줄 분량으로 작성하세요.",
            "- 일반 slide role은 cover, why, case, workflow, tip, checklist, security, caution, quiz, recap, cta, closing 중에서 고르세요. 이미지 대체 slide에만 image를 사용하세요.",
            "- 보안/개인정보/기밀/외부 AI 관련 내용은 security 또는 caution slide로 분리하세요.",
            "- 버튼은 anchor 또는 external_link만 사용하세요. 내부 이동 target은 slide id여야 합니다.",
            "- 애니메이션은 none, fade_up, slide_in, float_in, pulse_soft, stagger 중 하나만 사용하세요.",
            "- 캐릭터가 있는 slide는 character.animation에 float_in, pulse_soft, slide_in 중 하나를 우선 사용해 가만히 있어도 살짝 움직이는 느낌을 유지하세요.",
            "- 출력은 JSON object 하나만 반환하고 Markdown 설명은 붙이지 마세요.",
        ]
    )
    return {
        "brief_json": json.dumps(brief, ensure_ascii=False, indent=2),
        "request_json": json.dumps(request, ensure_ascii=False, indent=2),
        "character_assets_json": json.dumps(compact_assets, ensure_ascii=False, indent=2),
        "card_news_instructions": instructions,
        "card_news_output_schema": json.dumps(_plan_schema(), ensure_ascii=False, indent=2),
    }


def _plan_schema() -> dict[str, Any]:
    return {
        "card_news_plan": {
            "title": "카드뉴스 제목",
            "subtitle": "짧은 부제목",
            "template_id": "monthly_ai_news_standard",
            "fixed_structure": True,
            "aspect_ratio": "16:9",
            "publication_info": {
                "series_name": "AI 카드뉴스",
                "issue_label": "2026년 7월호",
                "issue_date": "2026년 7월",
                "publisher": "SK hynix",
            },
            "style": {
                "theme": "sk_cute_soft",
                "brand": "sk_hynix",
                "accent_color": "#EA002C",
                "secondary_color": "#F47725",
                "background_color": "#FFF7ED",
                "surface_color": "#FFFDF7",
                "density": "comfortable",
            },
            "slides": [
                {
                    "slide_id": "slide-1",
                    "role": "cover",
                    "layout": "cover_character",
                    "headline": "짧은 제목",
                    "body": "본문",
                    "bullets": ["선택 bullet"],
                    "character": {
                        "asset_id": "duo_ai_welcome",
                        "character_key": "duo",
                        "placement": "bottom_right",
                        "animation": "float_in",
                    },
                    "animation": "fade_up",
                    "image_override": {
                        "data_uri": "",
                        "alt": "",
                        "fit": "contain",
                        "background_color": "#FFFDF7",
                    },
                    "buttons": [{"label": "다음", "action_type": "anchor", "target": "slide-2", "style": "primary"}],
                }
            ],
            "navigation": {"mode": "screen_transition", "show_progress": True, "show_home_button": True},
        }
    }


def _payload(value: Any) -> dict[str, Any]:
    data = getattr(value, "data", value)
    return deepcopy(data) if isinstance(data, dict) else {}


def _dict(value: Any) -> dict[str, Any]:
    return deepcopy(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return deepcopy(value) if isinstance(value, list) else []


class CardNewsPlanPromptBuilder(Component):
    display_name = "04 카드뉴스 생성 프롬프트 변수 준비"
    description = "카드뉴스 계획 생성을 위한 Prompt Template 변수들을 제공합니다."
    icon = "PanelsTopLeft"
    inputs = [DataInput(name="character_payload", display_name="캐릭터 자산 포함 브리프", required=True)]
    outputs = [
        Output(name="brief_json", display_name="브리프 JSON", method="build_brief_json", types=["Message"], group_outputs=True),
        Output(name="request_json", display_name="요청 JSON", method="build_request_json", types=["Message"], group_outputs=True),
        Output(name="character_assets_json", display_name="캐릭터 자산 요약 JSON", method="build_character_assets_json", types=["Message"], group_outputs=True),
        Output(name="card_news_instructions", display_name="카드뉴스 작성 지침", method="build_instructions", types=["Message"], group_outputs=True),
        Output(name="card_news_output_schema", display_name="출력 스키마 JSON", method="build_schema", types=["Message"], group_outputs=True),
    ]

    def _variables(self) -> dict[str, str]:
        self.status = {"Prompt Template 변수": "브리프 / 요청 / 캐릭터 자산 / 작성 지침 / 출력 스키마"}
        return build_plan_template_variables(getattr(self, "character_payload", None))

    def build_brief_json(self) -> Message:
        return Message(text=self._variables()["brief_json"])

    def build_request_json(self) -> Message:
        return Message(text=self._variables()["request_json"])

    def build_character_assets_json(self) -> Message:
        return Message(text=self._variables()["character_assets_json"])

    def build_instructions(self) -> Message:
        return Message(text=self._variables()["card_news_instructions"])

    def build_schema(self) -> Message:
        return Message(text=self._variables()["card_news_output_schema"])
