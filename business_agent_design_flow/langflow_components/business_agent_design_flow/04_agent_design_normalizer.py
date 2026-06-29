from __future__ import annotations

"""04 AI 에이전트 설계 결과 정리 노드.

LLM이 반환한 JSON을 검증하고 사용자에게 보여줄 최종 `agent_design`으로 정리합니다.
LLM 응답이 없거나 JSON 파싱에 실패해도 기본 설계를 만들어 flow가 멈추지 않게 합니다.
"""

import json
import re
from copy import deepcopy
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, MessageTextInput, Output
from lfx.schema.data import Data


AUTOMATION_LEVELS = {"manual", "assist", "semi_auto", "auto"}
ACTORS = {"human", "llm", "tool", "system", "reviewer"}
TONES = {"info", "success", "warning", "danger", "neutral"}
DIFFICULTIES = {"초급", "중급", "고급"}


def normalize_agent_design(base_payload_value: Any, llm_response_value: Any = "") -> dict[str, Any]:
    """기본 데이터와 LLM 응답을 합쳐 최종 AI 에이전트 설계 데이터를 만듭니다."""

    payload = _payload(base_payload_value)
    llm_text = _text(llm_response_value)
    llm_json = _extract_json_object(llm_text)
    allowed_capabilities = _allowed_capabilities(payload)
    warnings = _list(payload.get("warnings"))

    if llm_json:
        design, normalize_warnings = _normalize_design(llm_json, payload, allowed_capabilities)
        source = "llm"
    else:
        design = _fallback_design(payload)
        normalize_warnings = ["LLM JSON 응답이 없어 기본 설계 결과를 사용했습니다."] if llm_text.strip() else ["LLM 응답 없이 기본 설계 결과를 사용했습니다."]
        source = "deterministic_fallback"

    result = deepcopy(payload)
    result["agent_design"] = design
    result["agent_design_meta"] = {
        "source": source,
        "warnings": normalize_warnings,
        "llm_text_preview": llm_text[:1200],
    }
    result["warnings"] = warnings + normalize_warnings
    return result


def _normalize_design(raw: dict[str, Any], payload: dict[str, Any], allowed_capabilities: set[str]) -> tuple[dict[str, Any], list[str]]:
    """LLM JSON을 출력 노드가 안전하게 렌더링할 수 있는 형태로 정리합니다."""

    warnings = []
    fallback = _fallback_design(payload)
    design = {
        "title": _short(raw.get("title"), fallback.get("title"), 80),
        "executive_summary": _string_list(raw.get("executive_summary"), 5, 220) or fallback.get("executive_summary", []),
        "process_logic": _normalize_process_logic(_dict(raw.get("process_logic")), fallback.get("process_logic", {})),
        "agent_opportunities": _normalize_opportunities(_list(raw.get("agent_opportunities")), fallback.get("agent_opportunities", []), allowed_capabilities, warnings),
        "recommended_flow_architecture": _normalize_architecture(_dict(raw.get("recommended_flow_architecture")), fallback.get("recommended_flow_architecture", {})),
        "required_information": _normalize_required_information(_dict(raw.get("required_information")), fallback.get("required_information", {})),
        "beginner_build_plan": _normalize_build_plan(_list(raw.get("beginner_build_plan")), fallback.get("beginner_build_plan", [])),
        "user_friendly_view": _normalize_user_friendly_view(_dict(raw.get("user_friendly_view")), fallback.get("user_friendly_view", {})),
        "reference_information": _normalize_reference_information(_list(raw.get("reference_information")), fallback.get("reference_information", [])),
        "warnings": _string_list(raw.get("warnings"), 8, 220),
    }
    if not design["agent_opportunities"]:
        design["agent_opportunities"] = fallback.get("agent_opportunities", [])
    if not design["beginner_build_plan"]:
        design["beginner_build_plan"] = fallback.get("beginner_build_plan", [])
    if not design["user_friendly_view"].get("card_sections"):
        design["user_friendly_view"] = fallback.get("user_friendly_view", {})
    return design, warnings


def _fallback_design(payload: dict[str, Any]) -> dict[str, Any]:
    """LLM 없이도 볼 수 있는 기본 AI 에이전트 설계를 만듭니다."""

    request = _dict(payload.get("business_request"))
    profile = _dict(payload.get("process_profile"))
    catalog = _dict(payload.get("agent_capability_catalog"))
    steps = _list(profile.get("process_steps"))
    signals = _dict(profile.get("automation_signals"))
    systems = _list(profile.get("systems"))
    outputs = _list(profile.get("outputs"))
    missing = _list(profile.get("missing_information_questions"))

    title = _title_from_request(request)
    process_steps = []
    for item in steps[:9]:
        if not isinstance(item, dict):
            continue
        step_type = str(item.get("step_type") or "")
        process_steps.append(
            {
                "step_no": item.get("step_no"),
                "step_name": item.get("step_name") or "업무 단계",
                "actor": "human",
                "input": "업무 설명 또는 관련 데이터",
                "action": item.get("description") or item.get("step_name") or "업무 수행",
                "output": _output_for_step(step_type, outputs),
                "decision": _decision_for_step(step_type, profile),
                "automation_level": _automation_level_for_step(step_type, signals),
            }
        )

    opportunities = _fallback_opportunities(signals, systems, outputs, catalog)
    architecture_nodes = _fallback_nodes(opportunities)
    friendly_table = [
        {
            "step": str(step.get("step_no")),
            "human_work": step.get("action", ""),
            "agent_support": _agent_support_for_level(step.get("automation_level")),
            "output": step.get("output", ""),
        }
        for step in process_steps[:8]
    ]

    return {
        "title": title,
        "executive_summary": [
            profile.get("summary") or "입력된 업무 설명을 기준으로 업무 프로세스와 AI 에이전트화 후보를 정리했습니다.",
            "반복 조회, 데이터 정리, 조건 판단, 보고/공유 단계는 AI 에이전트가 보조하기 좋은 영역입니다.",
            "승인, 고객 발송, 민감 정보 처리처럼 책임이 필요한 단계는 사람 검토를 남기는 구조가 안전합니다.",
        ],
        "process_logic": {
            "trigger": "사용자가 업무를 시작하거나 정해진 주기에 따라 시작",
            "main_inputs": _list(profile.get("inputs")) or ["업무 설명", "관련 데이터"],
            "main_outputs": outputs or ["업무 처리 결과"],
            "steps": process_steps,
            "decision_points": _list(profile.get("decision_points")),
            "human_checkpoints": _list(profile.get("human_checkpoints")),
        },
        "agent_opportunities": opportunities,
        "recommended_flow_architecture": {
            "flow_summary": "자연어 업무 설명을 구조화하고, 필요한 데이터/도구/리포트 단계를 추천하는 AI 에이전트 설계 flow",
            "nodes": architecture_nodes,
            "reuse_existing_flows": _reuse_existing_flows(opportunities),
        },
        "required_information": {
            "must_have": [
                "업무 시작 조건",
                "사용 데이터와 시스템",
                "판단 기준 또는 예외 조건",
                "최종 산출물과 수신자",
            ],
            "nice_to_have": [
                "샘플 데이터",
                "현재 사용 중인 양식",
                "실패/누락이 자주 발생하는 사례",
                "보안 또는 승인 기준",
            ],
            "missing_information": [str(item) for item in missing],
        },
        "beginner_build_plan": [
            {"step_no": 1, "task": "업무 설명 입력 노드를 만들고 샘플 업무를 넣습니다.", "result": "업무 요청 payload 생성", "check_method": "01 노드에서 단계가 추출되는지 확인"},
            {"step_no": 2, "task": "업무 프로세스 구조화 노드를 연결합니다.", "result": "단계/입력/출력/판단 지점 초안 생성", "check_method": "process_steps 개수 확인"},
            {"step_no": 3, "task": "AI 에이전트 기능 카탈로그를 연결합니다.", "result": "사용 가능한 Langflow 기능 후보 추가", "check_method": "기능 목록이 보이는지 확인"},
            {"step_no": 4, "task": "프롬프트 템플릿과 LLM을 연결해 설계를 보완합니다.", "result": "LLM 기반 AI 에이전트 설계 JSON 생성", "check_method": "04 노드가 생성 방식=llm으로 표시되는지 확인"},
            {"step_no": 5, "task": "Markdown 출력 노드로 사용자에게 보기 좋은 결과를 출력합니다.", "result": "플레이그라운드에서 읽을 수 있는 업무 AI 에이전트 설계서", "check_method": "프로세스 표와 구현 로드맵 확인"},
        ],
        "user_friendly_view": {
            "card_sections": [
                {"title": "업무 구조화", "body": "자연어 업무 설명을 단계와 판단 기준으로 정리합니다.", "tone": "info"},
                {"title": "AI 에이전트화 후보", "body": "반복 조회, 정리, 조건 판단, 보고 단계를 우선 후보로 봅니다.", "tone": "success"},
                {"title": "주의 구간", "body": "승인/보안/외부 발송은 사람 검토 단계를 남깁니다.", "tone": "warning"},
            ],
            "process_table": friendly_table,
            "roadmap": [
                {"phase": "1단계", "goal": "업무를 구조화", "deliverable": "업무 단계/입출력/판단 지점"},
                {"phase": "2단계", "goal": "AI 에이전트 보조 영역 선정", "deliverable": "개선 아이디어와 필요한 기능"},
                {"phase": "3단계", "goal": "Langflow 구현", "deliverable": "노드 연결 순서와 검증 방법"},
            ],
        },
        "reference_information": _reference_information_from_catalog(catalog),
        "warnings": [],
    }


def _fallback_opportunities(signals: dict[str, Any], systems: list[Any], outputs: list[Any], catalog: dict[str, Any]) -> list[dict[str, Any]]:
    """자동화 신호를 기반으로 기본 개선 아이디어를 만듭니다."""

    result = []
    if signals.get("has_data_work"):
        result.append(
            {
                "area": "데이터 조회/수집 자동화",
                "current_pain": "데이터를 수동으로 찾거나 여러 시스템에서 가져오는 부담이 있습니다.",
                "agent_idea": "사용자 요청을 조회 조건으로 바꾸고 reusable_data_flow로 데이터 조회를 수행합니다.",
                "expected_impact": "반복 조회 시간 감소와 조회 조건 누락 방지",
                "suggested_capabilities": ["reusable_data_flow", "prompt_template_structuring"],
                "difficulty": "중급",
                "guardrail": "권한이 필요한 데이터는 읽기 전용부터 시작하고 조회 로그를 남깁니다.",
            }
        )
    if signals.get("has_decision_rule"):
        result.append(
            {
                "area": "조건 판단/예외 분류",
                "current_pain": "정상/위험/예외 여부를 사람이 매번 확인해야 합니다.",
                "agent_idea": "판단 기준을 프롬프트와 규칙으로 분리하고 AI 에이전트가 위험 후보를 먼저 표시합니다.",
                "expected_impact": "이상 상황 탐지 속도 개선",
                "suggested_capabilities": ["prompt_template_structuring", "custom_component"],
                "difficulty": "초급",
                "guardrail": "최종 판단이 중요한 경우 사람 검토 단계를 유지합니다.",
            }
        )
    if signals.get("has_external_output") or outputs:
        result.append(
            {
                "area": "보고/공유 자동화",
                "current_pain": "결과 정리와 공유 문구 작성에 시간이 듭니다.",
                "agent_idea": "결과를 Markdown 또는 html_report_flow 리포트로 만들어 공유 가능한 형태로 정리합니다.",
                "expected_impact": "보고서 작성 시간 감소와 결과 형식 표준화",
                "suggested_capabilities": ["html_report_flow", "playground_validation"],
                "difficulty": "중급",
                "guardrail": "외부 발송 전에는 초안만 만들고 사람이 확인하도록 설계합니다.",
            }
        )
    if signals.get("has_human_approval"):
        result.append(
            {
                "area": "검토/승인 Gate",
                "current_pain": "검토 기준과 승인 전 확인 항목이 흩어져 있을 수 있습니다.",
                "agent_idea": "AI 에이전트가 승인 전 요약과 체크리스트를 만들고 최종 실행은 사람이 선택합니다.",
                "expected_impact": "승인 품질과 추적성 개선",
                "suggested_capabilities": ["human_review_gate"],
                "difficulty": "초급",
                "guardrail": "승인/반려 기록과 실행 payload를 분리합니다.",
            }
        )
    if not result:
        result.append(
            {
                "area": "업무 구조화와 표준 출력",
                "current_pain": "업무 설명이 사람마다 달라 구현 범위를 잡기 어렵습니다.",
                "agent_idea": "LLM이 업무를 단계/입출력/판단 기준으로 구조화하고 구현 후보를 제안합니다.",
                "expected_impact": "초기 설계 시간 단축",
                "suggested_capabilities": ["prompt_template_structuring", "custom_component"],
                "difficulty": "초급",
                "guardrail": "부족한 정보는 missing_information으로 되묻습니다.",
            }
        )
    return result[:5]


def _fallback_nodes(opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """초보자용 권장 노드 구조를 만듭니다."""

    nodes = [
        {"order": 1, "node_name": "Chat/Input 또는 00 업무 설명 입력", "role": "업무 설명 수집", "input": "자연어 업무 설명", "output": "업무 요청", "beginner_tip": "필수 입력은 업무 설명 하나로 시작하세요."},
        {"order": 2, "node_name": "업무 프로세스 구조화", "role": "단계와 판단 기준 추출", "input": "업무 요청", "output": "업무 구조화 결과", "beginner_tip": "먼저 LLM 없이 단계가 잘 나오는지 확인하세요."},
        {"order": 3, "node_name": "AI 에이전트 기능 카탈로그", "role": "쓸 수 있는 기능 후보 제공", "input": "업무 구조화 결과", "output": "기능 카탈로그 결과", "beginner_tip": "처음에는 기본 카탈로그를 그대로 쓰세요."},
        {"order": 4, "node_name": "프롬프트 템플릿 + LLM", "role": "AI 에이전트 설계 보완", "input": "프롬프트 변수", "output": "LLM 설계 JSON", "beginner_tip": "LLM에게 JSON만 반환하도록 지시하세요."},
        {"order": 5, "node_name": "AI 에이전트 설계 결과 정리", "role": "LLM JSON 검증과 기본 설계 보완", "input": "기본 데이터 + LLM 설계 응답", "output": "최종 AI 에이전트 설계", "beginner_tip": "LLM이 실패해도 결과가 나오게 만드는 안전장치입니다."},
        {"order": 6, "node_name": "Markdown 출력", "role": "사용자용 결과 표시", "input": "최종 AI 에이전트 설계", "output": "읽기 좋은 설계서", "beginner_tip": "처음엔 API보다 플레이그라운드 출력으로 확인하세요."},
    ]
    if any("reusable_data_flow" in _list(item.get("suggested_capabilities")) for item in opportunities):
        nodes.append({"order": 7, "node_name": "reusable_data_flow 연결", "role": "실제 데이터 조회 확장", "input": "조회 조건", "output": "datasets", "beginner_tip": "2차 버전에서 연결하세요."})
    if any("html_report_flow" in _list(item.get("suggested_capabilities")) for item in opportunities):
        nodes.append({"order": 8, "node_name": "html_report_flow 연결", "role": "결과 리포트 생성", "input": "datasets + 보고 싶은 방식", "output": "HTML 리포트", "beginner_tip": "사람에게 보여줄 산출물이 필요할 때 연결하세요."})
    return nodes


def _reuse_existing_flows(opportunities: list[dict[str, Any]]) -> list[dict[str, str]]:
    """기존 기능flow 재사용 후보를 만듭니다."""

    caps = set()
    for item in opportunities:
        caps.update(_list(item.get("suggested_capabilities")))
    result = []
    if "reusable_data_flow" in caps:
        result.append({"flow_name": "reusable_data_flow", "where_to_use": "데이터 조회/수집 단계", "why": "여러 데이터 소스를 표준 datasets 형태로 넘기기 위해 사용"})
    if "html_report_flow" in caps:
        result.append({"flow_name": "html_report_flow", "where_to_use": "결과 보고/공유 단계", "why": "조회/분석 결과를 사람이 보기 좋은 HTML 리포트로 만들기 위해 사용"})
    return result


def _normalize_process_logic(raw: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    """process_logic 필드를 정리합니다."""

    steps = []
    for idx, item in enumerate(_list(raw.get("steps")), 1):
        if not isinstance(item, dict):
            continue
        steps.append(
            {
                "step_no": _int(item.get("step_no"), idx),
                "step_name": _short(item.get("step_name"), f"단계 {idx}", 60),
                "actor": _choice(item.get("actor"), ACTORS, "human"),
                "input": _short(item.get("input"), "", 160),
                "action": _short(item.get("action"), "", 220),
                "output": _short(item.get("output"), "", 160),
                "decision": _short(item.get("decision"), "", 160),
                "automation_level": _choice(item.get("automation_level"), AUTOMATION_LEVELS, "assist"),
            }
        )
    if not steps:
        steps = _list(fallback.get("steps"))
    return {
        "trigger": _short(raw.get("trigger"), fallback.get("trigger"), 160),
        "main_inputs": _string_list(raw.get("main_inputs"), 10, 80) or _list(fallback.get("main_inputs")),
        "main_outputs": _string_list(raw.get("main_outputs"), 10, 80) or _list(fallback.get("main_outputs")),
        "steps": steps[:12],
        "decision_points": _string_list(raw.get("decision_points"), 10, 160) or _list(fallback.get("decision_points")),
        "human_checkpoints": _string_list(raw.get("human_checkpoints"), 10, 160) or _list(fallback.get("human_checkpoints")),
    }


def _normalize_opportunities(values: list[Any], fallback: list[Any], allowed: set[str], warnings: list[str]) -> list[dict[str, Any]]:
    """AI 에이전트 개선 아이디어 목록을 정리합니다."""

    result = []
    for item in values:
        if not isinstance(item, dict):
            continue
        caps = []
        for cap in _list(item.get("suggested_capabilities")):
            text = str(cap or "").strip()
            if text in allowed and text not in caps:
                caps.append(text)
            elif text:
                warnings.append(f"알 수 없는 capability_id를 제외했습니다: {text}")
        result.append(
            {
                "area": _short(item.get("area"), "개선 영역", 70),
                "current_pain": _short(item.get("current_pain"), "", 180),
                "agent_idea": _short(item.get("agent_idea"), "", 240),
                "expected_impact": _short(item.get("expected_impact"), "", 180),
                "suggested_capabilities": caps,
                "difficulty": _choice(item.get("difficulty"), DIFFICULTIES, "중급"),
                "guardrail": _short(item.get("guardrail"), "", 180),
            }
        )
    return result[:8] or deepcopy(fallback)


def _normalize_architecture(raw: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    """권장 flow 구조를 정리합니다."""

    nodes = []
    for idx, item in enumerate(_list(raw.get("nodes")), 1):
        if not isinstance(item, dict):
            continue
        nodes.append(
            {
                "order": _int(item.get("order"), idx),
                "node_name": _short(item.get("node_name"), f"노드 {idx}", 80),
                "role": _short(item.get("role"), "", 160),
                "input": _short(item.get("input"), "", 160),
                "output": _short(item.get("output"), "", 160),
                "beginner_tip": _short(item.get("beginner_tip"), "", 180),
            }
        )
    reuse = []
    for item in _list(raw.get("reuse_existing_flows")):
        if isinstance(item, dict):
            reuse.append(
                {
                    "flow_name": _short(item.get("flow_name"), "", 80),
                    "where_to_use": _short(item.get("where_to_use"), "", 140),
                    "why": _short(item.get("why"), "", 180),
                }
            )
    return {
        "flow_summary": _short(raw.get("flow_summary"), fallback.get("flow_summary"), 220),
        "nodes": nodes[:12] or _list(fallback.get("nodes")),
        "reuse_existing_flows": reuse[:6] or _list(fallback.get("reuse_existing_flows")),
    }


def _normalize_required_information(raw: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    """추가 필요 정보 목록을 정리합니다."""

    return {
        "must_have": _string_list(raw.get("must_have"), 10, 120) or _list(fallback.get("must_have")),
        "nice_to_have": _string_list(raw.get("nice_to_have"), 10, 120) or _list(fallback.get("nice_to_have")),
        "missing_information": _string_list(raw.get("missing_information"), 10, 160) or _list(fallback.get("missing_information")),
    }


def _normalize_build_plan(values: list[Any], fallback: list[Any]) -> list[dict[str, Any]]:
    """초보자용 구현 순서를 정리합니다."""

    result = []
    for idx, item in enumerate(values, 1):
        if not isinstance(item, dict):
            continue
        result.append(
            {
                "step_no": _int(item.get("step_no"), idx),
                "task": _short(item.get("task"), "", 180),
                "result": _short(item.get("result"), "", 160),
                "check_method": _short(item.get("check_method"), "", 160),
            }
        )
    return result[:12] or deepcopy(fallback)


def _normalize_user_friendly_view(raw: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    """사용자에게 보기 좋은 표시 구조를 정리합니다."""

    cards = []
    for item in _list(raw.get("card_sections")):
        if isinstance(item, dict):
            cards.append(
                {
                    "title": _short(item.get("title"), "요약", 60),
                    "body": _short(item.get("body"), "", 180),
                    "tone": _choice(item.get("tone"), TONES, "info"),
                }
            )
    table = []
    for item in _list(raw.get("process_table")):
        if isinstance(item, dict):
            table.append(
                {
                    "step": _short(item.get("step"), "", 30),
                    "human_work": _short(item.get("human_work"), "", 160),
                    "agent_support": _short(item.get("agent_support"), "", 160),
                    "output": _short(item.get("output"), "", 120),
                }
            )
    roadmap = []
    for item in _list(raw.get("roadmap")):
        if isinstance(item, dict):
            roadmap.append(
                {
                    "phase": _short(item.get("phase"), "", 40),
                    "goal": _short(item.get("goal"), "", 120),
                    "deliverable": _short(item.get("deliverable"), "", 120),
                }
            )
    return {
        "card_sections": cards[:6] or _list(fallback.get("card_sections")),
        "process_table": table[:12] or _list(fallback.get("process_table")),
        "roadmap": roadmap[:8] or _list(fallback.get("roadmap")),
    }


def _normalize_reference_information(values: list[Any], fallback: list[Any]) -> list[dict[str, str]]:
    """참조 정보를 한글 설명과 링크 중심으로 정리합니다."""

    result = []
    for item in values:
        if not isinstance(item, dict):
            continue
        title = _short(item.get("title"), "", 80)
        description = _short(item.get("description"), "", 220)
        used_for = _short(item.get("used_for"), "", 220)
        source_link = _short(item.get("source_link") or item.get("link") or item.get("url"), "", 260)
        if title and source_link:
            result.append(
                {
                    "title": title,
                    "description": description,
                    "used_for": used_for,
                    "source_link": source_link,
                }
            )
    return result[:8] or deepcopy(fallback)


def _reference_information_from_catalog(catalog: dict[str, Any]) -> list[dict[str, str]]:
    """카탈로그의 공식 문서 참조 정보를 출력용으로 추립니다."""

    references = _normalize_reference_information(_list(catalog.get("reference_information")), [])
    if references:
        return references[:8]

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
                "title": _short(item.get("display_name"), "Langflow 참고 문서", 80),
                "description": _short(item.get("beginner_use_case"), "해당 기능을 설계할 때 참고한 공식 문서입니다.", 220),
                "used_for": _short(item.get("implementation_hint"), "업무 AI 에이전트 설계의 기능 후보를 정할 때 참고합니다.", 220),
                "source_link": link,
            }
        )
    return result[:8]


def _allowed_capabilities(payload: dict[str, Any]) -> set[str]:
    """카탈로그의 capability_id set을 만듭니다."""

    catalog = _dict(payload.get("agent_capability_catalog"))
    return {str(item.get("capability_id")) for item in _list(catalog.get("capabilities")) if isinstance(item, dict) and item.get("capability_id")}


def _extract_json_object(text: str) -> dict[str, Any]:
    """LLM 응답 텍스트에서 JSON object를 추출합니다."""

    raw = str(text or "").strip()
    if not raw:
        return {}
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, flags=re.S | re.I)
    candidates = [fenced.group(1)] if fenced else []
    candidates.append(raw)
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        candidates.append(raw[start : end + 1])
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except Exception:
            continue
        if isinstance(parsed, dict):
            return parsed
    return {}


def _title_from_request(request: dict[str, Any]) -> str:
    """업무 설명에서 제목을 만듭니다."""

    goal = str(request.get("business_goal") or "").strip()
    description = str(request.get("work_description") or "").strip()
    if goal:
        return f"{goal[:40]} AI 에이전트 설계"
    first = re.split(r"[\n\r.]", description)[0].strip()
    return f"{first[:40]} AI 에이전트 설계" if first else "업무 AI 에이전트 설계"


def _output_for_step(step_type: str, outputs: list[Any]) -> str:
    """단계 유형에 맞는 기본 산출물을 정합니다."""

    mapping = {
        "data_lookup": "조회 데이터",
        "data_collection": "수집 데이터",
        "data_preparation": "정리된 데이터",
        "analysis": "분석 결과",
        "comparison": "비교 결과",
        "decision": "판단 결과",
        "review": "검토 결과",
        "approval": "승인/반려 결과",
        "reporting": "리포트",
        "communication": "공유 메시지",
        "notification": "알림",
        "system_update": "시스템 반영 결과",
    }
    return mapping.get(step_type) or (str(outputs[0]) if outputs else "단계 결과")


def _decision_for_step(step_type: str, profile: dict[str, Any]) -> str:
    """단계 유형에 맞는 기본 판단 기준을 정합니다."""

    decisions = _list(profile.get("decision_points"))
    if step_type in {"decision", "review", "approval"} and decisions:
        return str(decisions[0])
    if step_type == "analysis":
        return "이상/변동/우선순위 여부 확인"
    if step_type == "reporting":
        return "수신자가 이해할 수 있는 결과인지 확인"
    return ""


def _automation_level_for_step(step_type: str, signals: dict[str, Any]) -> str:
    """단계별 자동화 수준을 추정합니다."""

    if step_type in {"approval", "review"}:
        return "assist"
    if step_type in {"data_lookup", "data_collection", "data_preparation", "analysis", "comparison", "reporting", "notification"}:
        return "semi_auto" if signals.get("has_human_approval") else "auto"
    if step_type in {"communication", "system_update"}:
        return "assist"
    return "manual"


def _agent_support_for_level(level: Any) -> str:
    """자동화 수준을 사용자용 설명으로 바꿉니다."""

    value = str(level or "")
    if value == "auto":
        return "AI 에이전트가 자동 처리 가능"
    if value == "semi_auto":
        return "AI 에이전트가 처리하고 사람이 확인"
    if value == "assist":
        return "AI 에이전트가 초안/추천 제공"
    return "사람이 직접 수행"


def _text(value: Any) -> str:
    """Langflow Message/Data/dict 등에서 텍스트를 꺼냅니다."""

    if value is None:
        return ""
    if isinstance(value, str):
        return value
    data = getattr(value, "data", None)
    if isinstance(data, dict):
        for key in ("text", "content", "response", "message"):
            if isinstance(data.get(key), str):
                return data[key]
    for attr in ("text", "content"):
        text = getattr(value, attr, None)
        if isinstance(text, str):
            return text
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


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


def _string_list(value: Any, limit: int, item_limit: int) -> list[str]:
    """문자열 또는 문자열 목록을 정리합니다."""

    values = _list(value)
    if isinstance(value, str):
        values = [value]
    result = []
    for item in values:
        if isinstance(item, dict):
            text = str(item.get("text") or item.get("body") or item.get("title") or "").strip()
        else:
            text = str(item or "").strip()
        if text and text not in result:
            result.append(text[:item_limit])
        if len(result) >= limit:
            break
    return result


def _short(value: Any, fallback: Any, limit: int) -> str:
    """짧은 문자열을 반환합니다."""

    text = str(value or fallback or "").strip()
    return text[:limit]


def _choice(value: Any, allowed: set[str], fallback: str) -> str:
    """허용된 값만 통과시킵니다."""

    text = str(value or "").strip()
    return text if text in allowed else fallback


def _int(value: Any, default: int) -> int:
    """정수 변환 유틸입니다."""

    try:
        return int(value)
    except Exception:
        return default


class AgentDesignNormalizer(Component):
    """Langflow 화면에 표시되는 04 커스텀 컴포넌트 클래스."""

    display_name = "04 AI 에이전트 설계 결과 정리"
    description = "LLM의 업무 AI 에이전트 설계 JSON을 검증하고 사용자용 출력 데이터로 정리합니다."
    icon = "ShieldCheck"
    inputs = [
        DataInput(name="base_payload", display_name="기능 카탈로그 결과", required=True),
        MessageTextInput(name="llm_response", display_name="LLM 설계 응답", required=False),
    ]
    outputs = [Output(name="agent_design_payload", display_name="AI 에이전트 설계 결과", method="build_payload")]

    def build_payload(self) -> Data:
        """최종 AI 에이전트 설계 payload를 생성합니다."""

        result = normalize_agent_design(
            base_payload_value=getattr(self, "base_payload", None),
            llm_response_value=getattr(self, "llm_response", ""),
        )
        meta = result.get("agent_design_meta", {})
        design = result.get("agent_design", {})
        source_label = "LLM 설계" if meta.get("source") == "llm" else "기본 설계"
        self.status = {
            "생성 방식": source_label,
            "설계 제목": design.get("title"),
            "개선 아이디어 수": len(design.get("agent_opportunities", [])),
        }
        return Data(data=result)
