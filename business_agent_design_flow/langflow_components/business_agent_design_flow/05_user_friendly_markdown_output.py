from __future__ import annotations

"""05 사용자용 Markdown 출력 노드.

최종 AI 에이전트 설계 payload를 플레이그라운드에서 바로 읽기 좋은 Markdown으로 변환합니다.
초보 Langflow 개발자가 다음 행동을 알 수 있도록 요약, 표, 구현 순서, 추가 질문을 함께 보여줍니다.
"""

import json
from copy import deepcopy
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, Output
from lfx.schema.message import Message


def build_agent_design_markdown(payload_value: Any) -> str:
    """최종 payload를 Markdown 문자열로 변환합니다."""

    payload = _payload(payload_value)
    design = _dict(payload.get("agent_design"))
    meta = _dict(payload.get("agent_design_meta"))
    if not design:
        return "AI 에이전트 설계 결과가 비어 있습니다. 04 AI 에이전트 설계 결과 정리 노드의 출력을 연결하세요."

    lines = []
    title = str(design.get("title") or "업무 AI 에이전트 설계 결과").strip()
    lines.append(f"# {title}")
    if meta.get("source"):
        source_label = "LLM 설계" if meta.get("source") == "llm" else "기본 설계"
        lines.append("")
        lines.append(f"> 생성 방식: {source_label}")

    summary = _list(design.get("executive_summary"))
    if summary:
        lines.append("")
        lines.append("## 한눈에 보는 요약")
        for item in summary[:5]:
            lines.append(f"- {str(item).strip()}")

    friendly = _dict(design.get("user_friendly_view"))
    cards = _list(friendly.get("card_sections"))
    if cards:
        lines.append("")
        lines.append("## 핵심 카드")
        for item in cards[:6]:
            if not isinstance(item, dict):
                continue
            tone = _tone_label(item.get("tone"))
            lines.append(f"- **{str(item.get('title') or '요약').strip()}** `{tone}`: {str(item.get('body') or '').strip()}")

    process = _dict(design.get("process_logic"))
    process_steps = _list(process.get("steps"))
    if process_steps:
        lines.append("")
        lines.append("## 업무 프로세스 로직")
        lines.append("")
        lines.append("| 단계 | 담당 | 입력 | 작업 | 출력 | 자동화 수준 |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for item in process_steps[:12]:
            if not isinstance(item, dict):
                continue
            lines.append(
                "| {step} | {actor} | {input} | {action} | {output} | {level} |".format(
                    step=_cell(f"{item.get('step_no', '')}. {item.get('step_name', '')}"),
                    actor=_cell(_actor_label(item.get("actor"))),
                    input=_cell(item.get("input")),
                    action=_cell(item.get("action")),
                    output=_cell(item.get("output")),
                    level=_cell(_level_label(item.get("automation_level"))),
                )
            )

    table = _list(friendly.get("process_table"))
    if table:
        lines.append("")
        lines.append("## 사람이 하는 일과 AI 에이전트가 도울 일")
        lines.append("")
        lines.append("| 단계 | 현재 사람 업무 | AI 에이전트 지원 | 산출물 |")
        lines.append("| --- | --- | --- | --- |")
        for item in table[:12]:
            if isinstance(item, dict):
                lines.append(
                    "| {step} | {human} | {agent} | {output} |".format(
                        step=_cell(item.get("step")),
                        human=_cell(item.get("human_work")),
                        agent=_cell(item.get("agent_support")),
                        output=_cell(item.get("output")),
                    )
                )

    opportunities = _list(design.get("agent_opportunities"))
    if opportunities:
        lines.append("")
        lines.append("## AI 에이전트화 개선 아이디어")
        for idx, item in enumerate(opportunities[:8], 1):
            if not isinstance(item, dict):
                continue
            caps = ", ".join(str(cap) for cap in _list(item.get("suggested_capabilities"))) or "추가 판단 필요"
            lines.append("")
            lines.append(f"### {idx}. {str(item.get('area') or '개선 영역').strip()}")
            if item.get("current_pain"):
                lines.append(f"- 현재 불편함: {item.get('current_pain')}")
            if item.get("agent_idea"):
                lines.append(f"- AI 에이전트 아이디어: {item.get('agent_idea')}")
            if item.get("expected_impact"):
                lines.append(f"- 기대 효과: {item.get('expected_impact')}")
            lines.append(f"- 추천 기능: `{caps}`")
            if item.get("difficulty"):
                lines.append(f"- 난이도: {item.get('difficulty')}")
            if item.get("guardrail"):
                lines.append(f"- 주의사항: {item.get('guardrail')}")

    architecture = _dict(design.get("recommended_flow_architecture"))
    arch_nodes = _list(architecture.get("nodes"))
    if arch_nodes:
        lines.append("")
        lines.append("## Langflow 구현 흐름")
        if architecture.get("flow_summary"):
            lines.append("")
            lines.append(str(architecture.get("flow_summary")))
        lines.append("")
        lines.append("| 순서 | 노드 | 역할 | 입력 | 출력 | 초보자 팁 |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for item in arch_nodes[:14]:
            if isinstance(item, dict):
                lines.append(
                    "| {order} | {node} | {role} | {inp} | {out} | {tip} |".format(
                        order=_cell(item.get("order")),
                        node=_cell(item.get("node_name")),
                        role=_cell(item.get("role")),
                        inp=_cell(item.get("input")),
                        out=_cell(item.get("output")),
                        tip=_cell(item.get("beginner_tip")),
                    )
                )

    reuse = _list(architecture.get("reuse_existing_flows"))
    if reuse:
        lines.append("")
        lines.append("## 기존 기능flow 재사용 후보")
        for item in reuse[:6]:
            if isinstance(item, dict):
                lines.append(f"- **{item.get('flow_name')}**: {item.get('where_to_use')} - {item.get('why')}")

    build_plan = _list(design.get("beginner_build_plan"))
    if build_plan:
        lines.append("")
        lines.append("## 초보자용 구현 순서")
        for item in build_plan[:12]:
            if isinstance(item, dict):
                lines.append(f"{item.get('step_no')}. {item.get('task')}")
                if item.get("result"):
                    lines.append(f"   - 결과: {item.get('result')}")
                if item.get("check_method"):
                    lines.append(f"   - 확인: {item.get('check_method')}")

    required = _dict(design.get("required_information"))
    missing = _list(required.get("missing_information"))
    must_have = _list(required.get("must_have"))
    nice = _list(required.get("nice_to_have"))
    if must_have or nice or missing:
        lines.append("")
        lines.append("## 추가로 있으면 좋은 정보")
        if must_have:
            lines.append("")
            lines.append("**필수 확인 정보**")
            for item in must_have[:10]:
                lines.append(f"- {item}")
        if nice:
            lines.append("")
            lines.append("**있으면 설계 품질이 좋아지는 정보**")
            for item in nice[:10]:
                lines.append(f"- {item}")
        if missing:
            lines.append("")
            lines.append("**사용자에게 추가로 물어볼 질문**")
            for item in missing[:10]:
                lines.append(f"- {item}")

    references = _reference_information(payload, design)
    if references:
        lines.append("")
        lines.append("## 참조 정보")
        for item in references[:8]:
            title = _clean_text(item.get("title"), "참조 문서")
            description = _clean_text(item.get("description"), "")
            used_for = _clean_text(item.get("used_for"), "")
            source_link = _clean_text(item.get("source_link"), "")
            lines.append(f"- **{title}**")
            if description:
                lines.append(f"  - 설명: {description}")
            if used_for:
                lines.append(f"  - 이 설계에서 참고한 이유: {used_for}")
            if source_link:
                lines.append(f"  - 링크: {source_link}")

    warnings = _list(design.get("warnings")) + _list(meta.get("warnings"))
    if warnings:
        lines.append("")
        lines.append("## 주의사항")
        seen = set()
        for item in warnings:
            text = str(item or "").strip()
            if text and text not in seen:
                seen.add(text)
                lines.append(f"- {text}")

    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(design, ensure_ascii=False, indent=2, default=str))
    lines.append("```")
    return "\n".join(lines).strip()


def _tone_label(value: Any) -> str:
    """tone 값을 한국어 라벨로 바꿉니다."""

    mapping = {
        "info": "정보",
        "success": "추천",
        "warning": "주의",
        "danger": "위험",
        "neutral": "참고",
    }
    return mapping.get(str(value or "").strip(), "정보")


def _actor_label(value: Any) -> str:
    """actor 값을 한국어 라벨로 바꿉니다."""

    mapping = {
        "human": "사람",
        "llm": "LLM",
        "tool": "도구",
        "system": "시스템",
        "reviewer": "검토자",
    }
    return mapping.get(str(value or "").strip(), str(value or "").strip())


def _level_label(value: Any) -> str:
    """automation level 값을 한국어 라벨로 바꿉니다."""

    mapping = {
        "manual": "수동",
        "assist": "보조",
        "semi_auto": "반자동",
        "auto": "자동",
    }
    return mapping.get(str(value or "").strip(), str(value or "").strip())


def _cell(value: Any) -> str:
    """Markdown 표 셀이 깨지지 않게 정리합니다."""

    text = str(value or "").replace("\n", " ").replace("|", "/").strip()
    return text[:180] if text else "-"


def _clean_text(value: Any, fallback: str = "") -> str:
    """Markdown 본문에 넣을 짧은 문자열을 정리합니다."""

    return str(value or fallback or "").replace("\n", " ").strip()


def _reference_information(payload: dict[str, Any], design: dict[str, Any]) -> list[dict[str, Any]]:
    """최종 설계 또는 카탈로그에서 참조 정보를 가져옵니다."""

    references = _list(design.get("reference_information"))
    if references:
        return [item for item in references if isinstance(item, dict)]

    catalog = _dict(payload.get("agent_capability_catalog"))
    references = _list(catalog.get("reference_information"))
    if references:
        return [item for item in references if isinstance(item, dict)]

    result = []
    seen = set()
    for item in _list(catalog.get("capabilities")):
        if not isinstance(item, dict):
            continue
        link = str(item.get("source_reference") or "").strip()
        if not link.startswith("http") or link in seen:
            continue
        seen.add(link)
        result.append(
            {
                "title": item.get("display_name") or "Langflow 참고 문서",
                "description": item.get("beginner_use_case") or "해당 기능을 설계할 때 참고한 공식 문서입니다.",
                "used_for": item.get("implementation_hint") or "업무 AI 에이전트 설계의 기능 후보를 정할 때 참고합니다.",
                "source_link": link,
            }
        )
    return result


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


class UserFriendlyMarkdownOutput(Component):
    """Langflow 화면에 표시되는 05 커스텀 컴포넌트 클래스."""

    display_name = "05 사용자용 설계서 출력"
    description = "AI 에이전트 설계 결과를 플레이그라운드에서 보기 좋은 Markdown 설계서로 출력합니다."
    icon = "FileText"
    inputs = [DataInput(name="payload", display_name="AI 에이전트 설계 결과", required=True)]
    outputs = [Output(name="markdown_message", display_name="사용자용 설계서", method="build_message")]

    def build_message(self) -> Message:
        """사용자에게 보여줄 Markdown Message를 생성합니다."""

        text = build_agent_design_markdown(getattr(self, "payload", None))
        self.status = {"Markdown 글자 수": len(text)}
        return Message(text=text)
