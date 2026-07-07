from __future__ import annotations

"""07 사용자 요약 출력 노드."""

from copy import deepcopy
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, Output
from lfx.schema.message import Message


def build_card_news_summary(html_result_value: Any) -> str:
    """HTML 생성 결과를 Chat Output용 짧은 요약 메시지로 바꿉니다."""

    payload = _payload(html_result_value)
    html_result = _dict(payload.get("html_result"))
    plan = _dict(payload.get("card_news_plan"))
    slides = _list(plan.get("slides"))
    used_assets = _list(plan.get("used_assets"))
    warnings = _list(html_result.get("warnings")) or _list(_dict(payload.get("trace")).get("warnings"))
    title = _clean(html_result.get("title")) or _clean(plan.get("title")) or "카드뉴스"
    status = _clean(html_result.get("status")) or "ok"
    lines = [
        f"카드뉴스 초안이 생성되었습니다: {title}",
        "",
        f"- 카드 수: {len(slides) or html_result.get('slide_count', 0)}장",
        f"- 테마: {_clean(html_result.get('theme')) or _clean(_dict(plan.get('style')).get('theme')) or 'sk_cute_soft'}",
        f"- 캐릭터 자산: {len(used_assets)}개 사용",
        "- 포함 기능: 이전/다음 이동, 페이지 점 이동, CTA 버튼, CSS 애니메이션",
    ]
    if status != "ok":
        lines.append(f"- 상태: {status}")
    if warnings:
        lines.extend(["", "확인 필요:"])
        lines.extend(f"- {warning}" for warning in warnings[:5])
    lines.extend(["", "HTML 코드 출력 또는 공유 링크 발행 노드를 연결해 결과를 확인하세요."])
    return "\n".join(lines)


def _payload(value: Any) -> dict[str, Any]:
    data = getattr(value, "data", value)
    return deepcopy(data) if isinstance(data, dict) else {}


def _dict(value: Any) -> dict[str, Any]:
    return deepcopy(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return deepcopy(value) if isinstance(value, list) else []


def _clean(value: Any) -> str:
    return str(value or "").strip()


class CardNewsUserSummaryOutput(Component):
    display_name = "07 사용자 요약 출력"
    description = "생성된 카드뉴스 결과를 사용자가 읽기 쉬운 짧은 메시지로 출력합니다."
    icon = "MessageSquareText"
    inputs = [DataInput(name="html_result", display_name="HTML 생성 결과", required=True)]
    outputs = [Output(name="summary_message", display_name="요약 메시지", method="build_message")]

    def build_message(self) -> Message:
        message = build_card_news_summary(getattr(self, "html_result", None))
        self.status = {"요약 글자 수": len(message)}
        return Message(text=message)
