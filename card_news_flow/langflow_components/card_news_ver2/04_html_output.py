from __future__ import annotations

"""04 HTML 출력 노드.

생성된 HTML 결과를 사용자가 확인하기 쉬운 요약 메시지와
코드 블록 형태의 HTML 원문으로 나눠 출력합니다.
"""

import json
from copy import deepcopy
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, MessageTextInput, Output
from lfx.schema.message import Message


def build_summary_message(html_payload_value: Any) -> str:
    """카드뉴스 생성 결과 요약을 한국어 메시지로 만듭니다."""

    payload = _payload(html_payload_value)
    plan = _dict(payload.get("card_news_plan"))
    result = _dict(payload.get("html_result"))
    trace = _dict(payload.get("trace"))
    status = _clean(result.get("status")) or "unknown"
    title = _clean(result.get("title")) or _clean(plan.get("title")) or "카드뉴스"
    lines = [
        "카드뉴스 ver2 HTML 생성 결과",
        "",
        f"- 상태: {status}",
        f"- 제목: {title}",
        f"- 페이지 수: {result.get('page_count') or plan.get('page_count')}",
        f"- 파일명 힌트: {_clean(result.get('filename_hint'))}.html",
        f"- HTML 크기: {len(_clean(result.get('html')).encode('utf-8')):,} bytes",
    ]
    used_assets = _list(plan.get("used_character_assets"))
    if used_assets:
        lines.append(f"- 사용 캐릭터: {', '.join(str(item) for item in used_assets)}")
    warnings = _list(result.get("warnings")) or _list(trace.get("warnings"))
    if warnings:
        lines.append("")
        lines.append("경고")
        lines.extend(f"- {warning}" for warning in warnings[:6])
    security = _dict(result.get("security_report"))
    if security:
        lines.append("")
        lines.append(f"보안 검사: {'통과' if security.get('passed') else '실패'}")
        violations = _list(security.get("violations"))
        if violations:
            lines.append(f"- 위반 항목: {', '.join(str(item) for item in violations)}")
    return "\n".join(lines)


def build_html_source_message(html_payload_value: Any, output_mode: Any = "code_block") -> str:
    """HTML 원문을 code block 또는 raw 형태로 출력합니다."""

    payload = _payload(html_payload_value)
    result = _dict(payload.get("html_result"))
    html_source = _clean(result.get("html"))
    mode = _clean(output_mode).lower()
    if mode in {"raw", "plain"}:
        return html_source
    if not html_source:
        return "```html\n\n```"
    escaped = html_source.replace("```", "`\u200b``")
    return f"```html\n{escaped}\n```"


def _payload(value: Any) -> dict[str, Any]:
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
    return deepcopy(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return deepcopy(value) if isinstance(value, list) else []


def _clean(value: Any) -> str:
    return str(value or "").strip()


class CardNewsHtmlOutput(Component):
    """생성 결과를 Chat Output에 연결하기 위한 Langflow 노드입니다."""

    display_name = "04 HTML 결과 출력"
    description = "카드뉴스 생성 요약과 단일 HTML 원문을 출력합니다. HTML 원문은 기본적으로 코드 블록으로 감싸 안전하게 보여줍니다."
    icon = "Code2"
    name = "CardNewsHtmlOutput"

    inputs = [
        DataInput(name="html_result", display_name="단일 HTML 결과", required=True),
        MessageTextInput(
            name="output_mode",
            display_name="HTML 출력 방식",
            value="code_block",
            info="code_block이면 Chat Output에서 HTML이 바로 렌더링되지 않도록 감쌉니다. raw는 파일 저장/Report API 연결용입니다.",
            required=False,
            advanced=True,
        ),
    ]
    outputs = [
        Output(name="summary_message", display_name="생성 요약", method="build_summary"),
        Output(name="html_message", display_name="HTML 원문", method="build_html"),
    ]

    def build_summary(self) -> Message:
        text = build_summary_message(getattr(self, "html_result", None))
        self.status = {"요약 글자 수": len(text)}
        return Message(text=text)

    def build_html(self) -> Message:
        text = build_html_source_message(getattr(self, "html_result", None), getattr(self, "output_mode", "code_block"))
        self.status = {"HTML 출력 글자 수": len(text)}
        return Message(text=text)
