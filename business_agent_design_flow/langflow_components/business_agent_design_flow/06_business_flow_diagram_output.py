from __future__ import annotations

"""06 업무 Flow 다이어그램 출력 노드.

AI 에이전트 설계 결과 또는 업무 구조화 결과를 Mermaid flowchart Markdown으로 변환합니다.
Chat Output이 Mermaid를 렌더링하는 환경이면 그림처럼 보이고, 그렇지 않은 환경에서는
복사 가능한 Mermaid 코드로 확인할 수 있습니다.
"""

import json
import re
from copy import deepcopy
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, Output
from lfx.schema.message import Message


def build_business_flow_diagram_markdown(payload_value: Any) -> str:
    """payload에서 업무 단계를 찾아 Mermaid 다이어그램 Markdown을 만듭니다."""

    payload = _payload(payload_value)
    title = _diagram_title(payload)
    steps = _process_steps(payload)
    checkpoints = _human_checkpoints(payload)

    lines = [f"# {title}", ""]
    if not steps:
        lines.append("업무 단계를 찾지 못했습니다. `04 AI 에이전트 설계 결과` 또는 `01 업무 프로세스 구조화` 출력을 연결하세요.")
        return "\n".join(lines).strip()

    lines.append("```mermaid")
    lines.extend(_mermaid_lines(steps, checkpoints))
    lines.append("```")
    lines.append("")
    lines.append("Mermaid 렌더링을 지원하는 화면에서는 위 코드가 업무 Flow 다이어그램으로 표시됩니다.")
    lines.append("")
    lines.append("## 단계 요약")
    for step in steps[:14]:
        lines.append(f"- **{step['no']}. {step['name']}**: {step['summary']}")
    return "\n".join(lines).strip()


def _mermaid_lines(steps: list[dict[str, str]], checkpoints: list[str]) -> list[str]:
    """Mermaid flowchart 본문을 생성합니다."""

    lines = ["flowchart TD", '  START([업무 시작])']
    previous = "START"
    for idx, step in enumerate(steps[:14], 1):
        node_id = f"S{idx}"
        label = _node_label(f"{step['no']}. {step['name']}", step.get("summary", ""))
        lines.append(f'  {node_id}["{label}"]')
        lines.append(f"  {previous} --> {node_id}")
        previous = node_id
        if step.get("decision"):
            decision_id = f"D{idx}"
            decision_label = _node_label("판단", step["decision"])
            lines.append(f'  {decision_id}{{"{decision_label}"}}')
            lines.append(f"  {previous} --> {decision_id}")
            previous = decision_id

    for idx, checkpoint in enumerate(checkpoints[:4], 1):
        review_id = f"R{idx}"
        review_label = _node_label("사람 검토", checkpoint)
        lines.append(f'  {review_id}[/"{review_label}"/]')
        lines.append(f"  {previous} --> {review_id}")
        previous = review_id

    lines.append("  END([업무 종료])")
    lines.append(f"  {previous} --> END")
    lines.extend(
        [
            "  classDef human fill:#EEF2FF,stroke:#4F46E5,color:#111827,stroke-width:1px;",
            "  classDef decision fill:#FFF7ED,stroke:#F97316,color:#111827,stroke-width:1px;",
            "  classDef terminal fill:#ECFDF5,stroke:#10B981,color:#111827,stroke-width:1px;",
            "  class START,END terminal;",
        ]
    )
    if checkpoints:
        lines.append("  class " + ",".join(f"R{idx}" for idx in range(1, min(len(checkpoints), 4) + 1)) + " human;")
    decision_ids = [f"D{idx}" for idx, step in enumerate(steps[:14], 1) if step.get("decision")]
    if decision_ids:
        lines.append("  class " + ",".join(decision_ids) + " decision;")
    return lines


def _process_steps(payload: dict[str, Any]) -> list[dict[str, str]]:
    """최종 설계 결과 또는 기본 구조화 결과에서 업무 단계를 가져옵니다."""

    design = _dict(payload.get("agent_design"))
    process = _dict(design.get("process_logic"))
    raw_steps = _list(process.get("steps"))
    if raw_steps:
        return [_normalize_design_step(item, idx) for idx, item in enumerate(raw_steps, 1) if isinstance(item, dict)]

    profile = _dict(payload.get("process_profile"))
    raw_profile_steps = _list(profile.get("process_steps"))
    return [_normalize_profile_step(item, idx) for idx, item in enumerate(raw_profile_steps, 1) if isinstance(item, dict)]


def _normalize_design_step(item: dict[str, Any], idx: int) -> dict[str, str]:
    """LLM 설계 결과의 step을 다이어그램용으로 정리합니다."""

    name = _short(item.get("step_name"), f"단계 {idx}", 42)
    action = _short(item.get("action"), item.get("output") or "", 78)
    actor = _actor_label(item.get("actor"))
    summary = f"{actor} - {action}" if action else actor
    return {
        "no": str(item.get("step_no") or idx),
        "name": name,
        "summary": summary,
        "decision": _short(item.get("decision"), "", 90),
    }


def _normalize_profile_step(item: dict[str, Any], idx: int) -> dict[str, str]:
    """01 업무 구조화 결과의 step을 다이어그램용으로 정리합니다."""

    name = _short(item.get("step_name"), f"단계 {idx}", 42)
    description = _short(item.get("description"), "", 78)
    return {
        "no": str(item.get("step_no") or idx),
        "name": name,
        "summary": description or _step_type_label(item.get("step_type")),
        "decision": "",
    }


def _human_checkpoints(payload: dict[str, Any]) -> list[str]:
    """사람 검토/승인 단계 후보를 가져옵니다."""

    design = _dict(payload.get("agent_design"))
    process = _dict(design.get("process_logic"))
    checkpoints = _string_list(process.get("human_checkpoints"))
    if checkpoints:
        return checkpoints
    profile = _dict(payload.get("process_profile"))
    return _string_list(profile.get("human_checkpoints"))


def _diagram_title(payload: dict[str, Any]) -> str:
    """다이어그램 제목을 정합니다."""

    design = _dict(payload.get("agent_design"))
    title = str(design.get("title") or "").strip()
    if title:
        return f"{_short(title, '업무 Flow 다이어그램', 60)} - 업무 Flow"
    profile = _dict(payload.get("process_profile"))
    summary = str(profile.get("summary") or "").strip()
    if summary:
        return f"{_short(summary, '업무 Flow 다이어그램', 60)} - 업무 Flow"
    return "업무 Flow 다이어그램"


def _node_label(title: str, body: str = "") -> str:
    """Mermaid 노드 안에 넣을 안전한 라벨을 만듭니다."""

    title_text = _mermaid_text(title, 42)
    body_text = _mermaid_text(body, 70)
    return f"{title_text}<br/>{body_text}" if body_text else title_text


def _mermaid_text(value: Any, limit: int) -> str:
    """Mermaid 문자열에서 문제될 수 있는 문자를 정리합니다."""

    text = _short(value, "", limit)
    text = text.replace('"', "'")
    text = text.replace("[", "(").replace("]", ")")
    text = text.replace("{", "(").replace("}", ")")
    text = text.replace("|", "/")
    return text


def _actor_label(value: Any) -> str:
    """actor 값을 한국어로 바꿉니다."""

    mapping = {
        "human": "사람",
        "llm": "LLM",
        "tool": "도구",
        "system": "시스템",
        "reviewer": "검토자",
    }
    text = str(value or "").strip()
    return mapping.get(text, text or "담당자")


def _step_type_label(value: Any) -> str:
    """01 구조화 결과의 step_type을 한국어로 바꿉니다."""

    mapping = {
        "data_lookup": "데이터 조회",
        "data_collection": "데이터 수집",
        "file_or_data_collection": "파일/데이터 확보",
        "data_preparation": "데이터 정리",
        "analysis": "분석",
        "comparison": "비교",
        "decision": "판단",
        "review": "검토",
        "approval": "승인",
        "sharing": "공유",
        "reporting": "보고",
        "communication": "커뮤니케이션",
        "notification": "알림",
        "system_update": "시스템 입력",
    }
    text = str(value or "").strip()
    return mapping.get(text, text or "업무 단계")


def _short(value: Any, fallback: str, limit: int) -> str:
    """긴 텍스트를 다이어그램에 들어갈 수 있게 줄입니다."""

    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        text = fallback
    return text[:limit]


def _string_list(value: Any) -> list[str]:
    """list 값을 문자열 list로 정리합니다."""

    result = []
    for item in _list(value):
        text = _short(item, "", 100)
        if text:
            result.append(text)
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


class BusinessFlowDiagramOutput(Component):
    """Langflow 화면에 표시되는 06 커스텀 컴포넌트 클래스."""

    display_name = "06 업무 Flow 다이어그램 출력"
    description = "업무 구조화 결과 또는 AI 에이전트 설계 결과를 Mermaid 업무 Flow 다이어그램으로 변환합니다."
    icon = "Workflow"
    inputs = [
        DataInput(name="payload", display_name="AI 에이전트 설계 결과", required=True),
    ]
    outputs = [Output(name="diagram_message", display_name="업무 Flow 다이어그램", method="build_message")]

    def build_message(self) -> Message:
        """Chat Output에 연결할 다이어그램 Markdown 메시지를 만듭니다."""

        markdown = build_business_flow_diagram_markdown(getattr(self, "payload", None))
        self.status = {"출력 형식": "Mermaid Markdown", "글자 수": len(markdown)}
        return Message(text=markdown)
