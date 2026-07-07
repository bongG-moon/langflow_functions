from __future__ import annotations

"""08 HTML 코드 출력 노드.

Playground/Chat Output에서 HTML이 실제 화면으로 렌더링되지 않도록
기본 출력은 fenced code block 형태로 감쌉니다.
"""

from copy import deepcopy
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, MessageTextInput, Output
from lfx.schema.message import Message


def get_card_news_html_source(html_result_value: Any, output_mode: Any = "code_block") -> str:
    """HTML 코드를 Chat Output에 안전하게 표시합니다."""

    payload = _payload(html_result_value)
    html_result = _dict(payload.get("html_result"))
    html_source = str(html_result.get("html") or "")
    mode = _clean(output_mode).lower()
    if mode in {"raw", "plain"}:
        return html_source
    if not html_source:
        return "```html\n\n```"
    escaped = html_source.replace("```", "`\u200b``")
    return f"```html\n{escaped}\n```"


def _payload(value: Any) -> dict[str, Any]:
    data = getattr(value, "data", value)
    return deepcopy(data) if isinstance(data, dict) else {}


def _dict(value: Any) -> dict[str, Any]:
    return deepcopy(value) if isinstance(value, dict) else {}


def _clean(value: Any) -> str:
    return str(value or "").strip()


class CardNewsHtmlSourceOutput(Component):
    display_name = "08 HTML 코드 출력"
    description = "생성된 카드뉴스 HTML 전체 코드를 Playground/Chat Output에 코드블록으로 표시합니다."
    icon = "Code"
    inputs = [
        DataInput(name="html_result", display_name="HTML 생성 결과", required=True),
        MessageTextInput(
            name="output_mode",
            display_name="출력 모드",
            value="code_block",
            info="code_block이면 HTML이 렌더링되지 않고 코드로 표시됩니다. raw는 실제 HTML 미리보기용으로만 사용하세요.",
            required=False,
            advanced=True,
        ),
    ]
    outputs = [Output(name="html_message", display_name="HTML 코드", method="build_message")]

    def build_message(self) -> Message:
        html_source = get_card_news_html_source(
            getattr(self, "html_result", None),
            getattr(self, "output_mode", "code_block"),
        )
        self.status = {"HTML 글자 수": len(html_source)}
        return Message(text=html_source)
