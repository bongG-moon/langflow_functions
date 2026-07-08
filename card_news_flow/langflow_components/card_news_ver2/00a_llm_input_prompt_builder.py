from __future__ import annotations

"""00-1 LLM 입력 정리 프롬프트 노드.

사용자가 대충 적은 카드뉴스 요청을 LLM이 카드뉴스 ver2 표준 JSON으로
정리하도록 프롬프트를 만들어 줍니다.
"""

from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import MessageTextInput, MultilineInput, Output
from lfx.schema.message import Message


def build_llm_input_prompt(
    rough_card_news_input: Any,
    default_series_title: Any = "P&T AI INSIGHT",
) -> str:
    """LLM이 표준 카드뉴스 JSON만 출력하도록 프롬프트를 만듭니다."""

    user_input = _clean_preserve(rough_card_news_input)
    series_title = _clean(default_series_title) or "P&T AI INSIGHT"
    return f"""너는 카드뉴스 입력 정리 도우미입니다.
아래 사용자의 자연어/메모/마크다운 입력을 카드뉴스 ver2의 표준 JSON으로 정리하세요.

중요 규칙:
- 출력은 JSON object 하나만 작성하세요. 설명, 인사말, markdown code fence는 쓰지 마세요.
- 사용자가 쓴 문장을 최대한 보존하세요. 과장하거나 없는 사실을 만들지 마세요.
- 첫 페이지는 cover_title/cover_subtitle로 정리하고, 중간 페이지는 pages 배열에 넣으세요.
- 중간 페이지는 기본적으로 제목(title), 소제목(subtitle), 본문(body), 이미지(image_ref), 하이퍼링크(links) 5개 요소로 정리하세요.
- 5개 요소는 모두 선택값입니다. 사용자가 쓰지 않은 항목은 빈 문자열 또는 빈 배열로 두고 억지로 만들지 마세요.
- 목록형 핵심 문장이 따로 있으면 bullets에 넣어도 됩니다. 단, 일반 본문 문장은 body에 넣으세요.
- 페이지 안의 "링크", "하이퍼링크", "참고 URL"은 links 배열에 넣으세요.
- 사용자가 적은 하이퍼링크 줄은 절대 삭제하지 말고, 본문(body)에 넣지 말고, 반드시 links 배열에 넣으세요.
- 하이퍼링크는 화면에 보일 글자(label)와 실제 이동할 주소(url)를 분리하세요. 예: "AI 포털 | https://example.com" -> {{"label":"AI 포털","url":"https://example.com"}}
- links.url은 http 또는 https로 시작하는 값만 넣으세요. URL이 없으면 links는 빈 배열로 두세요.
- 마지막 페이지는 closing 객체로 정리하세요.
- 페이지 번호가 명시되어 있으면 그대로 사용하세요.
- 사용자가 전체 페이지 수를 명시한 경우에만 page_count를 숫자로 추가하세요.
- 전체 페이지 수가 없으면 page_count를 만들지 마세요. 뒤 노드가 페이지 번호를 보고 자동 계산합니다.
- 이미지 배치 지시가 있으면 image_placement_instruction에 그대로 보존하세요.
- 페이지 안의 "이미지: prompt_tip" 같은 값은 image_ref에 넣으세요.
- 사용자가 "본문", "내용", "body"라고 쓴 값은 body에 넣으세요. content 대신 body를 우선 사용하세요.
- 사용자가 "소제목", "부제", "요약", "subtitle"이라고 쓴 값은 subtitle에 넣으세요.
- CTA URL이 없으면 빈 문자열로 두세요.
- 모르는 값은 빈 문자열 또는 빈 배열로 두세요.

반드시 아래 스키마를 따르세요.

{{
  "series_title": "{series_title}",
  "issue_label": "",
  "issue_no": "",
  "cover_title": "",
  "cover_subtitle": "",
  "pages": [
    {{
      "page": 2,
      "title": "",
      "subtitle": "",
      "image_ref": "",
      "body": "",
      "bullets": [],
      "links": [
        {{
          "label": "",
          "url": ""
        }}
      ],
      "role": ""
    }}
  ],
  "closing": {{
    "title": "",
    "content": "",
    "cta": {{
      "label": "",
      "url": ""
    }}
  }},
  "image_placement_instruction": ""
}}

role은 확실할 때만 아래 중 하나로 넣으세요.
- why, case, tip, checklist, security, workflow, metric, recap

사용자 입력:
{user_input}
"""


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _clean_preserve(value: Any) -> str:
    return str(value or "").strip()


class LlmInputPromptBuilder(Component):
    """LLM에 보낼 입력 정리 프롬프트를 만드는 Langflow 노드입니다."""

    display_name = "00-1 LLM 입력 정리 프롬프트"
    description = "대충 적은 카드뉴스 요청을 카드뉴스 ver2 표준 JSON으로 정리하도록 LLM 프롬프트를 생성합니다."
    icon = "MessagesSquare"
    name = "LlmInputPromptBuilder"

    inputs = [
        MultilineInput(
            name="rough_card_news_input",
            display_name="대충 적은 카드뉴스 요청",
            info="사용자가 편하게 쓴 카드뉴스 내용, 페이지 구성, 이미지 배치 지시를 그대로 넣으세요.",
            required=True,
        ),
        MessageTextInput(name="default_series_title", display_name="기본 소식지명", value="P&T AI INSIGHT", required=False),
    ]
    outputs = [Output(name="prompt", display_name="LLM 정리 프롬프트", method="build_prompt")]

    def build_prompt(self) -> Message:
        prompt = build_llm_input_prompt(
            getattr(self, "rough_card_news_input", ""),
            getattr(self, "default_series_title", "P&T AI INSIGHT"),
        )
        self.status = {"프롬프트 글자 수": len(prompt)}
        return Message(text=prompt)
