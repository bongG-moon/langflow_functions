from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, MessageTextInput, Output
from lfx.schema.data import Data


def normalize_agent_design(catalog_context_value: Any, llm_design_response: Any = "") -> dict[str, Any]:
    """Agent/LLM 설계 응답을 검증하고, 없으면 추천 카탈로그 기반의 기본 설계를 만듭니다."""
    payload = _payload(catalog_context_value)
    context = _dict(payload.get("catalog_context"))
    profile = _dict(context.get("business_profile"))
    catalog_items = [_dict(item) for item in _as_list(context.get("ranked_catalog_items"))]

    parsed = _parse_json_like(llm_design_response)
    design = _dict(parsed.get("agent_design")) if isinstance(parsed, dict) else {}
    source = "llm" if design else "fallback"
    if not design:
        design = _fallback_design(profile, catalog_items)

    normalized = _normalize_design(design, profile, catalog_items)
    issues = _validation_issues(normalized, catalog_items)
    validation_report = {
        "validation_flags": {
            "valid": len(issues) == 0,
            "has_as_is_flow": bool(normalized.get("as_is_flow")),
            "has_to_be_flow": bool(normalized.get("to_be_flow")),
            "has_recommended_capabilities": bool(normalized.get("recommended_capabilities")),
            "has_improvement_blueprint": bool(normalized.get("improvement_blueprint")),
        },
        "issues": issues,
        "source": source,
        "normalized_at": _now_iso(),
    }

    trace = _dict(context.get("recommendation_trace"))
    trace = {
        **trace,
        "design_source": source,
        "used_catalog_ids": [item.get("catalog_id") for item in normalized.get("recommended_capabilities", [])],
        "validation_issue_count": len(issues),
    }

    return {
        **payload,
        "agent_design": normalized,
        "recommendation_trace": trace,
        "validation_report": validation_report,
        "agent_design_meta": {
            "source": source,
            "normalized_at": _now_iso(),
        },
    }


def _fallback_design(profile: dict[str, Any], catalog_items: list[dict[str, Any]]) -> dict[str, Any]:
    selected = catalog_items[:5]
    as_is = []
    for index, step in enumerate(_as_list(profile.get("current_flow")), 1):
        step_dict = _dict(step)
        as_is.append(
            {
                "step_id": step_dict.get("step_id") or f"A{index}",
                "title": step_dict.get("title") or f"현재 업무 {index}",
                "description": step_dict.get("description") or "",
                "actor": step_dict.get("actor") or "업무 담당자",
                "systems": step_dict.get("systems") or [],
            }
        )

    to_be = [
        {
            "step_id": "T1",
            "title": "업무 설명 접수 및 구조화",
            "description": "사용자의 자연어 업무 설명을 업무 단계, 데이터, 제약, 원하는 결과로 정리합니다.",
            "agent_role": "AI Agent",
            "systems": ["Langflow"],
        },
        {
            "step_id": "T2",
            "title": "관련 기능/사례 검색",
            "description": "MongoDB 또는 seed 카탈로그에서 업무에 맞는 기능과 개선 사례를 찾습니다.",
            "agent_role": "AI Agent",
            "systems": ["MongoDB", "Langflow"],
        },
        {
            "step_id": "T3",
            "title": "개선안 생성 및 사람 검토",
            "description": "추천 기능을 조합해 개선 Flow를 제안하고, 위험 작업은 사람 확인 뒤 실행하도록 분리합니다.",
            "agent_role": "AI Agent + 사람",
            "systems": ["Langflow"],
        },
    ]

    recommended_capabilities = [
        {
            "catalog_id": item.get("canonical_key"),
            "usage": item.get("summary_ko"),
            "reason": "업무 설명의 키워드와 카탈로그 trigger_signals가 매칭되었습니다.",
            "implementation_hint": ", ".join(item.get("langflow_building_blocks") or []),
            "reference_sources": _reference_sources(
                item.get("source_links"),
                default_title=item.get("title_ko") or item.get("canonical_key"),
                how_used="카탈로그에 등록된 기능 설명과 사용 조건을 개선안 근거로 사용합니다.",
            ),
        }
        for item in selected
    ]

    return {
        "report_title": "업무 AI Agent 개선 설계",
        "summary": profile.get("business_goal") or "업무 설명을 바탕으로 AI Agent 적용 가능 영역을 정리했습니다.",
        "as_is_flow": as_is,
        "to_be_flow": to_be,
        "recommended_capabilities": recommended_capabilities,
        "improvement_blueprint": _fallback_improvement_blueprint(as_is, to_be, recommended_capabilities, profile),
        "implementation_roadmap": [
            {"phase": "1단계", "action": "업무 설명 입력 노드와 구조화 Agent/Prompt Template을 연결합니다.", "owner": "Flow 개발자"},
            {"phase": "2단계", "action": "카탈로그 검색 결과를 Agent 설계 프롬프트에 넣습니다.", "owner": "Flow 개발자"},
            {"phase": "3단계", "action": "검증된 설계 JSON을 HTML 렌더러로 시각화합니다.", "owner": "Flow 개발자"},
        ],
        "risk_controls": [
            {
                "risk": risk,
                "control": "자동 실행하지 않고 사람 검토 단계를 둡니다.",
                "human_review_required": True,
            }
            for risk in (profile.get("risk_signals") or ["중요 작업 자동화"])
        ],
        "alternative_options": [
            {
                "option": "조회/분석만 자동화하고 실행은 사람이 담당",
                "tradeoff": "도입 리스크는 낮지만 자동화 효과는 제한적입니다.",
            },
            {
                "option": "Agent가 도구를 선택해 조회부터 초안 생성까지 수행",
                "tradeoff": "효율은 높지만 도구 권한과 검토 gate 설계가 필요합니다.",
            },
        ],
        "open_questions": profile.get("open_questions") or [],
    }


def _normalize_design(
    design: dict[str, Any],
    profile: dict[str, Any],
    catalog_items: list[dict[str, Any]],
) -> dict[str, Any]:
    known_items = {str(item.get("canonical_key")): item for item in catalog_items if item.get("canonical_key")}
    as_is_flow = _normalize_steps(design.get("as_is_flow") or profile.get("current_flow"), "A", "현재 업무")
    to_be_flow = _normalize_steps(design.get("to_be_flow"), "T", "개선 업무")
    recommended = []
    for item in _as_list(design.get("recommended_capabilities")):
        cap = _dict(item)
        catalog_id = str(cap.get("catalog_id") or cap.get("canonical_key") or "").strip()
        source = known_items.get(catalog_id, {})
        if not catalog_id or (known_items and catalog_id not in known_items):
            continue
        source_title = source.get("title_ko") or catalog_id
        recommended.append(
            {
                "catalog_id": catalog_id,
                "capability_title": str(cap.get("capability_title") or cap.get("title") or source_title).strip(),
                "usage": str(cap.get("usage") or source.get("summary_ko") or "").strip(),
                "reason": str(cap.get("reason") or "업무 프로필과 카탈로그 매칭 결과로 추천되었습니다.").strip(),
                "implementation_hint": str(cap.get("implementation_hint") or ", ".join(source.get("langflow_building_blocks") or [])).strip(),
                "risk_level": source.get("risk_level", "medium"),
                "human_review_required": bool(source.get("human_review_required")),
                "source_links": _string_list(source.get("source_links"), 8),
                "reference_sources": _reference_sources(
                    cap.get("reference_sources") or cap.get("source_links") or source.get("source_links"),
                    default_title=source_title,
                    how_used="추천 기능의 공식 문서 또는 사내 사례 설명을 구현 참고 자료로 사용합니다.",
                ),
            }
        )

    if not recommended and catalog_items:
        recommended = _fallback_design(profile, catalog_items)["recommended_capabilities"]
        for cap in recommended:
            source = known_items.get(cap.get("catalog_id"), {})
            cap["capability_title"] = source.get("title_ko") or cap.get("catalog_id")
            cap["risk_level"] = source.get("risk_level", "medium")
            cap["human_review_required"] = bool(source.get("human_review_required"))
            cap["source_links"] = _string_list(source.get("source_links"), 8)
            cap["reference_sources"] = _reference_sources(
                cap.get("reference_sources") or source.get("source_links"),
                default_title=source.get("title_ko") or cap.get("catalog_id"),
                how_used="추천 기능의 공식 문서 또는 사내 사례 설명을 구현 참고 자료로 사용합니다.",
            )

    improvement_blueprint = _normalize_improvement_blueprint(
        design.get("improvement_blueprint"),
        as_is_flow=as_is_flow,
        to_be_flow=to_be_flow,
        recommended_capabilities=recommended,
        known_items=known_items,
        profile=profile,
    )

    return {
        "report_title": str(design.get("report_title") or "업무 AI Agent 개선 설계").strip(),
        "summary": str(design.get("summary") or profile.get("business_goal") or "").strip(),
        "as_is_flow": as_is_flow,
        "to_be_flow": to_be_flow,
        "recommended_capabilities": recommended,
        "improvement_blueprint": improvement_blueprint,
        "implementation_roadmap": _normalize_roadmap(design.get("implementation_roadmap")),
        "risk_controls": _normalize_risks(design.get("risk_controls"), profile.get("risk_signals")),
        "alternative_options": _normalize_name_role_items(design.get("alternative_options"), "option", "tradeoff"),
        "open_questions": _string_list(design.get("open_questions")),
    }


def _normalize_steps(value: Any, prefix: str, fallback_title: str) -> list[dict[str, Any]]:
    steps = []
    for index, item in enumerate(_as_list(value), 1):
        step = _dict(item)
        steps.append(
            {
                "step_id": str(step.get("step_id") or f"{prefix}{index}"),
                "title": str(step.get("title") or f"{fallback_title} {index}").strip(),
                "description": str(step.get("description") or "").strip(),
                "actor": str(step.get("actor") or step.get("agent_role") or "").strip(),
                "agent_role": str(step.get("agent_role") or step.get("actor") or "").strip(),
                "systems": _string_list(step.get("systems")),
                "maps_from_as_is_step_ids": _string_list(step.get("maps_from_as_is_step_ids")),
                "automation_type": str(step.get("automation_type") or "").strip(),
            }
        )
    return steps


def _fallback_improvement_blueprint(
    as_is_flow: list[dict[str, Any]],
    to_be_flow: list[dict[str, Any]],
    recommended_capabilities: list[dict[str, Any]],
    profile: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = []
    risks = _string_list(profile.get("risk_signals"))
    for index, step in enumerate(as_is_flow[:8], 1):
        capability = recommended_capabilities[(index - 1) % len(recommended_capabilities)] if recommended_capabilities else {}
        nodes = _string_list(capability.get("implementation_hint")) or ["Prompt Template", "Agent", "Custom Component"]
        review_required = bool(capability.get("human_review_required")) or bool(risks)
        rows.append(
            {
                "as_is_step_id": step.get("step_id") or f"A{index}",
                "as_is_step_title": step.get("title") or f"현재 업무 {index}",
                "current_pain_point": "수작업 반복, 판단 근거 누락, 담당자별 처리 방식 차이가 발생할 수 있습니다.",
                "improvement_goal": "반복 입력과 조회를 줄이고, 동일한 기준으로 판단 근거와 후속 조치 초안을 남깁니다.",
                "automation_type": "사람 검토" if review_required else "보조",
                "to_be_step_ids": [item.get("step_id") for item in to_be_flow[:2] if item.get("step_id")],
                "applied_capabilities": [_blueprint_capability(capability)],
                "implementation_detail": {
                    "what_changes": f"`{step.get('title') or '현재 단계'}` 단계의 수동 확인을 기능 기반 조회/정리 흐름으로 바꿉니다.",
                    "how_to_build": [
                        "업무 설명과 필요한 입력값을 Prompt Template 변수로 분리합니다.",
                        "추천 기능을 Agent 또는 Custom Component로 연결합니다.",
                        "기능 실행 결과를 다음 판단 단계에서 사용할 JSON 필드로 정규화합니다.",
                    ],
                    "connection_guide": [
                        f"현재 단계 `{step.get('step_id') or f'A{index}'}`의 입력/출력 값을 개선 단계에 전달합니다.",
                        "도구 호출 결과는 검증 노드에서 누락 여부를 확인한 뒤 HTML 렌더러로 전달합니다.",
                    ],
                    "acceptance_criteria": [
                        "동일한 업무 설명을 넣었을 때 현재 단계와 개선 단계의 매핑이 표시됩니다.",
                        "적용 기능, 입력값, 출력값, 참고 링크가 함께 표시됩니다.",
                    ],
                },
                "human_review": {
                    "required": review_required,
                    "reason": "전송, 등록, 승인, 민감 정보 처리 가능성이 있으면 사람 검토 후 실행합니다." if review_required else "조회/정리 중심 단계라 자동 보조가 가능합니다.",
                },
            }
        )
    return rows


def _normalize_improvement_blueprint(
    value: Any,
    as_is_flow: list[dict[str, Any]],
    to_be_flow: list[dict[str, Any]],
    recommended_capabilities: list[dict[str, Any]],
    known_items: dict[str, dict[str, Any]],
    profile: dict[str, Any],
) -> list[dict[str, Any]]:
    source_rows = _as_list(value)
    if not source_rows:
        return _fallback_improvement_blueprint(as_is_flow, to_be_flow, recommended_capabilities, profile)

    fallback_by_id = {row.get("as_is_step_id"): row for row in _fallback_improvement_blueprint(as_is_flow, to_be_flow, recommended_capabilities, profile)}
    normalized = []
    for index, item in enumerate(source_rows[:12], 1):
        row = _dict(item)
        step_id = str(row.get("as_is_step_id") or f"A{index}").strip()
        fallback = fallback_by_id.get(step_id, {})
        applied = _normalize_applied_capabilities(
            row.get("applied_capabilities"),
            known_items=known_items,
            recommended_capabilities=recommended_capabilities,
        )
        detail = _dict(row.get("implementation_detail"))
        human_review = _dict(row.get("human_review"))
        normalized.append(
            {
                "as_is_step_id": step_id,
                "as_is_step_title": str(row.get("as_is_step_title") or fallback.get("as_is_step_title") or f"현재 업무 {index}").strip(),
                "current_pain_point": str(row.get("current_pain_point") or fallback.get("current_pain_point") or "").strip(),
                "improvement_goal": str(row.get("improvement_goal") or fallback.get("improvement_goal") or "").strip(),
                "automation_type": str(row.get("automation_type") or fallback.get("automation_type") or "보조").strip(),
                "to_be_step_ids": _string_list(row.get("to_be_step_ids")) or _string_list(fallback.get("to_be_step_ids")),
                "applied_capabilities": applied or _as_list(fallback.get("applied_capabilities")),
                "implementation_detail": {
                    "what_changes": str(detail.get("what_changes") or _dict(fallback.get("implementation_detail")).get("what_changes") or "").strip(),
                    "how_to_build": _string_list(detail.get("how_to_build"), 20) or _string_list(_dict(fallback.get("implementation_detail")).get("how_to_build"), 20),
                    "connection_guide": _string_list(detail.get("connection_guide"), 20) or _string_list(_dict(fallback.get("implementation_detail")).get("connection_guide"), 20),
                    "acceptance_criteria": _string_list(detail.get("acceptance_criteria"), 20) or _string_list(_dict(fallback.get("implementation_detail")).get("acceptance_criteria"), 20),
                },
                "human_review": {
                    "required": bool(human_review.get("required", _dict(fallback.get("human_review")).get("required", False))),
                    "reason": str(human_review.get("reason") or _dict(fallback.get("human_review")).get("reason") or "").strip(),
                },
            }
        )
    return normalized


def _normalize_applied_capabilities(
    value: Any,
    known_items: dict[str, dict[str, Any]],
    recommended_capabilities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    fallback_by_id = {cap.get("catalog_id"): cap for cap in recommended_capabilities if cap.get("catalog_id")}
    source_items = _as_list(value) or recommended_capabilities[:1]
    for item in source_items[:6]:
        cap = _dict(item)
        catalog_id = str(cap.get("catalog_id") or cap.get("canonical_key") or "").strip()
        if not catalog_id:
            continue
        catalog = known_items.get(catalog_id, {})
        fallback = fallback_by_id.get(catalog_id, {})
        title = cap.get("capability_title") or cap.get("title") or catalog.get("title_ko") or fallback.get("capability_title") or catalog_id
        source_links = cap.get("source_links") or cap.get("reference_sources") or catalog.get("source_links") or fallback.get("source_links")
        rows.append(
            {
                "catalog_id": catalog_id,
                "capability_title": str(title).strip(),
                "usage": str(cap.get("usage") or fallback.get("usage") or catalog.get("summary_ko") or "").strip(),
                "why_this_capability": str(cap.get("why_this_capability") or cap.get("reason") or fallback.get("reason") or "현재 단계의 반복 작업과 판단 기준을 구조화하기 위해 사용합니다.").strip(),
                "langflow_nodes": _string_list(cap.get("langflow_nodes")) or _string_list(catalog.get("langflow_building_blocks")) or _string_list(fallback.get("implementation_hint")),
                "inputs": _string_list(cap.get("inputs")),
                "outputs": _string_list(cap.get("outputs")),
                "reference_sources": _reference_sources(
                    cap.get("reference_sources") or source_links,
                    default_title=str(title).strip(),
                    how_used="해당 기능의 구현 방식과 사용 조건을 개선 명세에 반영했습니다.",
                ),
            }
        )
    return rows


def _blueprint_capability(capability: dict[str, Any]) -> dict[str, Any]:
    cap = _dict(capability)
    return {
        "catalog_id": cap.get("catalog_id", ""),
        "capability_title": cap.get("capability_title") or cap.get("catalog_id", ""),
        "usage": cap.get("usage", ""),
        "why_this_capability": cap.get("reason", ""),
        "langflow_nodes": _string_list(cap.get("implementation_hint")) or ["Prompt Template", "Agent"],
        "inputs": ["사용자 업무 설명", "업무 단계별 입력 데이터"],
        "outputs": ["정규화된 판단 근거", "개선 후 실행/검토 결과"],
        "reference_sources": cap.get("reference_sources") or _reference_sources(cap.get("source_links"), default_title=cap.get("catalog_id", ""), how_used="카탈로그 참고 링크를 구현 근거로 사용합니다."),
    }


def _reference_sources(value: Any, default_title: str = "참고 자료", how_used: str = "") -> list[dict[str, str]]:
    rows = []
    seen = set()
    for index, item in enumerate(_as_list(value), 1):
        row = _dict(item)
        if row:
            url = str(row.get("url") or row.get("link") or "").strip()
            title = str(row.get("title") or default_title or f"참고 자료 {index}").strip()
            note = str(row.get("how_used") or row.get("note") or how_used or "").strip()
        else:
            text = str(item or "").strip()
            url = text if text.startswith(("http://", "https://")) else ""
            title = default_title or f"참고 자료 {index}"
            note = text if not url else how_used
        key = url or title
        if not key or key in seen:
            continue
        seen.add(key)
        rows.append({"title": title, "url": url, "how_used": note})
    return rows


def _normalize_roadmap(value: Any) -> list[dict[str, str]]:
    rows = []
    for index, item in enumerate(_as_list(value), 1):
        row = _dict(item)
        rows.append(
            {
                "phase": str(row.get("phase") or f"{index}단계"),
                "action": str(row.get("action") or row.get("description") or "").strip(),
                "owner": str(row.get("owner") or "Flow 개발자").strip(),
            }
        )
    return rows


def _normalize_risks(value: Any, fallback_risks: Any) -> list[dict[str, Any]]:
    rows = []
    source = _as_list(value) or [{"risk": risk, "control": "사람 검토 후 실행"} for risk in _string_list(fallback_risks)]
    for item in source:
        row = _dict(item)
        risk = str(row.get("risk") or row.get("title") or "").strip()
        if risk:
            rows.append(
                {
                    "risk": risk,
                    "control": str(row.get("control") or row.get("description") or "사람 검토 후 실행").strip(),
                    "human_review_required": bool(row.get("human_review_required", True)),
                }
            )
    return rows


def _validation_issues(design: dict[str, Any], catalog_items: list[dict[str, Any]]) -> list[str]:
    issues = []
    if not design.get("as_is_flow"):
        issues.append("현재 업무 Flow가 비어 있습니다.")
    if not design.get("to_be_flow"):
        issues.append("개선 후 업무 Flow가 비어 있습니다.")
    if not design.get("recommended_capabilities"):
        issues.append("추천 기능 매핑이 비어 있습니다.")
    if not design.get("improvement_blueprint"):
        issues.append("업무 단계별 개선 명세가 비어 있습니다.")
    known = {item.get("canonical_key") for item in catalog_items}
    unknown = [
        cap.get("catalog_id")
        for cap in design.get("recommended_capabilities", [])
        if known and cap.get("catalog_id") not in known
    ]
    if unknown:
        issues.append(f"카탈로그에 없는 추천 기능이 제외되었습니다: {', '.join(str(item) for item in unknown)}")
    for row in design.get("improvement_blueprint", []):
        blueprint = _dict(row)
        if not blueprint.get("applied_capabilities"):
            issues.append(f"{blueprint.get('as_is_step_id', 'unknown')}: 적용 기능이 비어 있습니다.")
        detail = _dict(blueprint.get("implementation_detail"))
        if not detail.get("how_to_build"):
            issues.append(f"{blueprint.get('as_is_step_id', 'unknown')}: 구현 방법이 비어 있습니다.")
        if not detail.get("acceptance_criteria"):
            issues.append(f"{blueprint.get('as_is_step_id', 'unknown')}: 검증 기준이 비어 있습니다.")
    return issues


def _parse_json_like(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    text = _extract_text(value).strip()
    if not text:
        return None
    if "```" in text:
        for block in re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.I | re.S):
            parsed = _parse_json_like(block)
            if parsed is not None:
                return parsed
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"(\{.*\}|\[.*\])", text, flags=re.S)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            return None
    return None


def _extract_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if hasattr(value, "text"):
        return str(value.text)
    if hasattr(value, "data"):
        return _extract_text(value.data)
    if isinstance(value, dict):
        for key in ("text", "message", "content", "input_value"):
            if key in value:
                return _extract_text(value[key])
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _payload(value: Any) -> dict[str, Any]:
    data = getattr(value, "data", value)
    return deepcopy(data) if isinstance(data, dict) else {}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value in (None, "", {}):
        return []
    return [value]


def _string_list(value: Any, limit: int = 12) -> list[str]:
    result = []
    seen = set()
    for item in _as_list(value):
        text = str(item or "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
        if len(result) >= limit:
            break
    return result


def _normalize_name_role_items(value: Any, name_key: str, role_key: str) -> list[dict[str, str]]:
    result = []
    for item in _as_list(value):
        row = _dict(item)
        name = str(row.get(name_key) or row.get("title") or "").strip()
        role = str(row.get(role_key) or row.get("description") or "").strip()
        if name:
            result.append({name_key: name, role_key: role})
    return result


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class AgentDesignNormalizer(Component):
    display_name = "05 AI Agent 설계 결과 검증"
    description = "Agent/LLM 설계 응답을 검증하고 카탈로그 근거가 있는 AI Agent 설계 JSON으로 정리합니다."
    icon = "ShieldCheck"
    inputs = [
        DataInput(name="catalog_context", display_name="추천 컨텍스트", required=True),
        MessageTextInput(name="llm_design_response", display_name="Agent/LLM 설계 응답", required=False),
    ]
    outputs = [Output(name="agent_design", display_name="AI Agent 설계 결과", method="build_payload")]

    def build_payload(self) -> Data:
        result = normalize_agent_design(
            getattr(self, "catalog_context", None),
            getattr(self, "llm_design_response", ""),
        )
        validation = result.get("validation_report", {}).get("validation_flags", {})
        self.status = {
            "처리 방식": result.get("agent_design_meta", {}).get("source"),
            "검증 상태": "정상" if validation.get("valid") else "확인 필요",
            "추천 기능 수": len(result.get("agent_design", {}).get("recommended_capabilities", [])),
        }
        return Data(data=result)
