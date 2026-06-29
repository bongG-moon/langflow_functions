from __future__ import annotations

"""02 AI 에이전트 기능 카탈로그 노드.

업무를 AI 에이전트로 바꿀 때 참고할 수 있는 기능 목록을 제공합니다.
기존 기능flow의 재사용 가능한 flow와 Langflow에서 자주 쓰는 기능을 함께 담되,
초보 개발자가 이해하기 쉽도록 "언제 쓰는지", "필요 입력", "구현 힌트" 중심으로 적습니다.
"""

import json
import hashlib
from copy import deepcopy
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, MessageTextInput, Output
from lfx.schema.data import Data


def build_agent_capability_catalog(
    payload_value: Any = None,
    simple_catalog_text: str = "",
    custom_catalog_json: str = "",
) -> dict[str, Any]:
    """기본 카탈로그와 선택 입력 카탈로그를 합쳐 payload에 붙입니다."""

    payload = _payload(payload_value)
    catalog = _default_catalog()
    simple = _parse_simple_catalog(simple_catalog_text)
    if simple:
        catalog = _merge_catalog(catalog, simple)
    custom = _parse_json(custom_catalog_json)
    if custom:
        catalog = _merge_catalog(catalog, custom)

    result = deepcopy(payload) if payload else {"flow_type": "business_agent_design", "warnings": []}
    result["agent_capability_catalog"] = catalog
    result["agent_capability_catalog_input"] = {
        "간단 입력 추가 기능 수": len(simple.get("capabilities", [])) if simple else 0,
        "JSON 입력 추가 기능 수": len(custom.get("capabilities", [])) if custom else 0,
        "전체 기능 수": len(catalog.get("capabilities", [])),
    }
    result.setdefault("warnings", [])
    return result


def _default_catalog() -> dict[str, Any]:
    """기본 기능 카탈로그를 반환합니다."""

    return {
        "catalog_version": "business-agent-capability-catalog-v1",
        "catalog_notes": [
            "전체 component/flow 코드를 LLM에 통째로 넣기보다, 사용할 수 있는 기능을 짧은 카탈로그로 알려주는 방식입니다.",
            "초보 Langflow 개발자는 조회, 판단, 생성, 검토, 공유 단계를 나누어 생각하면 flow 설계가 쉬워집니다.",
            "사람 승인이나 고객/외부 발송은 자동 실행보다 검토 후 실행 패턴을 우선 권장합니다.",
        ],
        "reference_information": [
            {
                "title": "프롬프트 템플릿 컴포넌트",
                "description": "Langflow에서 프롬프트 본문에 변수를 넣어 LLM 입력을 표준화할 때 사용합니다.",
                "used_for": "03 노드가 만든 업무_요청_JSON, 작성_규칙, 출력_스키마_JSON 등을 프롬프트 템플릿 변수로 연결합니다.",
                "source_link": "https://docs.langflow.org/components-prompts",
            },
            {
                "title": "커스텀 컴포넌트",
                "description": "Python 코드로 Langflow 안에서 재사용 가능한 입력/출력 컴포넌트를 직접 만들 때 사용합니다.",
                "used_for": "00~05 노드처럼 업무 입력, 구조화, 검증, Markdown 출력 로직을 고정된 컴포넌트로 제공합니다.",
                "source_link": "https://docs.langflow.org/components-custom-components",
            },
            {
                "title": "Langflow 에이전트",
                "description": "LLM이 사용자 요청을 해석하고 필요한 도구를 선택해 작업하도록 구성할 때 사용합니다.",
                "used_for": "업무가 단순 요약을 넘어 조회, 판단, 초안 생성, 후속 조치 추천을 포함할 때 2차 확장 후보로 제안합니다.",
                "source_link": "https://docs.langflow.org/agents",
            },
            {
                "title": "에이전트 도구",
                "description": "AI 에이전트가 호출할 수 있는 도구를 연결해 검색, 조회, 계산, 외부 작업을 수행하게 할 때 사용합니다.",
                "used_for": "업무에 여러 조회 도구나 사내 시스템 도구가 필요한 경우 설계 후보로 사용합니다.",
                "source_link": "https://docs.langflow.org/agents-tools",
            },
            {
                "title": "MCP 도구",
                "description": "MCP 서버가 제공하는 외부 도구를 Langflow에서 사용할 수 있게 연결할 때 참고합니다.",
                "used_for": "사내 시스템, 브라우저, 파일, 협업툴 같은 외부 도구 연동 아이디어를 설명할 때 사용합니다.",
                "source_link": "https://docs.langflow.org/mcp-tools",
            },
            {
                "title": "Flow 실행 API",
                "description": "완성된 Langflow flow를 플레이그라운드 밖의 웹앱, 서버, 스케줄러에서 호출할 때 사용합니다.",
                "used_for": "업무 AI 에이전트 설계가 나중에 서비스나 자동 실행 구조로 확장될 때 참고합니다.",
                "source_link": "https://docs.langflow.org/api-flows-run",
            },
            {
                "title": "플레이그라운드 검증",
                "description": "Langflow 화면에서 입력과 출력을 바로 확인하면서 flow 연결 상태를 점검할 때 사용합니다.",
                "used_for": "초보자가 00~05 노드 연결 후 결과 Markdown을 즉시 확인하는 검증 방법으로 제안합니다.",
                "source_link": "https://docs.langflow.org/concepts-playground",
            },
        ],
        "capabilities": [
            {
                "capability_id": "prompt_template_structuring",
                "display_name": "프롬프트 템플릿으로 자연어 구조화",
                "category": "llm_planning",
                "beginner_use_case": "업무 설명을 단계, 판단 기준, 자동화 후보 JSON으로 변환합니다.",
                "when_to_use": "사람마다 업무 설명 방식이 다르고 LLM이 먼저 의도를 정리해야 할 때",
                "needed_inputs": ["업무 설명", "업무 목적", "데이터/시스템 설명", "출력 스키마"],
                "typical_outputs": ["구조화 JSON", "업무 단계", "AI 에이전트 설계 초안"],
                "difficulty": "초급",
                "implementation_hint": "03 프롬프트 변수 준비 노드의 출력을 Langflow 기본 프롬프트 템플릿 변수에 연결합니다.",
                "source_reference": "https://docs.langflow.org/components-prompts",
            },
            {
                "capability_id": "custom_component",
                "display_name": "커스텀 컴포넌트",
                "category": "langflow_core",
                "beginner_use_case": "반복되는 변환, 검증, 출력 포맷팅을 Python 컴포넌트로 고정합니다.",
                "when_to_use": "LLM이 매번 하면 흔들리는 규칙이나 포맷을 안정적으로 처리해야 할 때",
                "needed_inputs": ["데이터 또는 메시지 입력", "간단한 설정값"],
                "typical_outputs": ["데이터", "메시지", "정규화 결과"],
                "difficulty": "초급-중급",
                "implementation_hint": "입력/출력 포트 이름을 한글로 명확하게 만들고, 내부 payload key는 영어로 고정합니다.",
                "source_reference": "https://docs.langflow.org/components-custom-components",
            },
            {
                "capability_id": "agent_with_tools",
                "display_name": "에이전트와 도구",
                "category": "agent_runtime",
                "beginner_use_case": "LLM이 필요한 도구를 선택해 조회, 계산, 검색, 요약을 수행하게 합니다.",
                "when_to_use": "업무가 단순 요약이 아니라 여러 도구 호출과 판단을 포함할 때",
                "needed_inputs": ["사용자 요청", "사용 가능한 tool 목록", "도구 사용 규칙"],
                "typical_outputs": ["도구 호출 결과", "최종 답변", "작업 로그"],
                "difficulty": "중급",
                "implementation_hint": "처음에는 tool 수를 2~4개로 제한하고, 읽기 전용 tool부터 연결합니다.",
                "source_reference": "https://docs.langflow.org/agents",
            },
            {
                "capability_id": "mcp_tools",
                "display_name": "MCP 도구",
                "category": "integration",
                "beginner_use_case": "외부 시스템이 제공하는 도구를 Langflow AI 에이전트가 사용할 수 있게 연결합니다.",
                "when_to_use": "사내 시스템, 브라우저, 파일, DB, 협업툴 같은 외부 도구를 표준 tool처럼 쓰고 싶을 때",
                "needed_inputs": ["MCP 서버 설정", "허용된 도구 목록", "권한/보안 정책"],
                "typical_outputs": ["도구 구조 정보", "도구 실행 결과"],
                "difficulty": "중급-고급",
                "implementation_hint": "서버형 Langflow에서는 MCP 서버가 Langflow 서버 환경에서 실행 가능해야 합니다. 초보자용 flow에서는 아이디어 단계로만 제안하세요.",
                "source_reference": "https://docs.langflow.org/mcp-tools",
            },
            {
                "capability_id": "flow_api",
                "display_name": "Flow API 실행",
                "category": "deployment",
                "beginner_use_case": "완성된 flow를 웹앱, 스케줄러, 다른 시스템에서 호출합니다.",
                "when_to_use": "Langflow 플레이그라운드 밖에서 업무 자동화를 호출해야 할 때",
                "needed_inputs": ["flow id", "input payload", "API key 또는 인증 정보"],
                "typical_outputs": ["JSON 응답", "사용자 표시 메시지"],
                "difficulty": "중급",
                "implementation_hint": "flow 마지막에 API용 JSON 응답 어댑터를 두면 웹/서버 연동이 쉬워집니다.",
                "source_reference": "https://docs.langflow.org/api-flows-run",
            },
            {
                "capability_id": "playground_validation",
                "display_name": "플레이그라운드 검증",
                "category": "validation",
                "beginner_use_case": "초보자가 flow를 단계별로 연결한 뒤 입력/출력 결과를 즉시 확인합니다.",
                "when_to_use": "처음 flow를 만들거나 프롬프트/컴포넌트 연결이 맞는지 확인할 때",
                "needed_inputs": ["테스트 질문", "샘플 데이터", "채팅 출력 또는 메시지 출력"],
                "typical_outputs": ["사용자 표시 결과", "LLM 응답", "디버깅 힌트"],
                "difficulty": "초급",
                "implementation_hint": "마지막 노드는 우선 Markdown 메시지로 출력하고, 안정화 후 API 응답을 추가합니다.",
                "source_reference": "https://docs.langflow.org/concepts-playground",
            },
            {
                "capability_id": "reusable_data_flow",
                "display_name": "기능flow - 재사용 데이터 조회 Flow",
                "category": "local_feature_flow",
                "beginner_use_case": "업무 질문에 필요한 데이터를 DB/API/파일 등에서 조회하고 표준 datasets 형태로 넘깁니다.",
                "when_to_use": "업무가 데이터 조회, 조건 해석, 여러 소스 결과 병합을 포함할 때",
                "needed_inputs": ["조회 질문", "데이터 소스 설정", "필요시 조회 조건"],
                "typical_outputs": ["조회 데이터 JSON", "표준 데이터셋 목록", "조회 결과 요약"],
                "difficulty": "중급",
                "implementation_hint": "업무 AI 에이전트 설계 결과에서 데이터 조회가 필요하면 이 flow를 후보로 제안합니다.",
                "source_reference": "local:reusable_data_flow",
            },
            {
                "capability_id": "html_report_flow",
                "display_name": "기능flow - HTML 리포트 생성 Flow",
                "category": "local_feature_flow",
                "beginner_use_case": "데이터와 보고 싶은 방식을 받아 분석 리포트 HTML 또는 공유 링크를 만듭니다.",
                "when_to_use": "업무 결과를 사람이 보기 좋은 리포트, 대시보드, 표/차트로 전달해야 할 때",
                "needed_inputs": ["질문", "보고 싶은 방식", "datasets", "데이터 의미 설명"],
                "typical_outputs": ["HTML 원문", "다운로드 링크", "리포트 요약"],
                "difficulty": "중급",
                "implementation_hint": "조회 결과를 사람에게 설명해야 하는 업무라면 마지막 출력 단계 후보로 제안합니다.",
                "source_reference": "local:html_report_flow",
            },
            {
                "capability_id": "human_review_gate",
                "display_name": "사람 검토/승인 Gate",
                "category": "governance",
                "beginner_use_case": "AI 에이전트가 추천/초안만 만들고, 실제 발송/등록/승인은 사람이 결정하게 합니다.",
                "when_to_use": "고객 발송, 비용/계약/승인, 민감 정보 처리처럼 책임 소재가 중요한 업무",
                "needed_inputs": ["승인 기준", "검토자", "승인 전 표시할 요약"],
                "typical_outputs": ["승인 대기 메시지", "반려 사유", "승인 후 실행 데이터"],
                "difficulty": "초급-중급",
                "implementation_hint": "처음 버전에서는 실제 실행 대신 Markdown 체크리스트를 출력하는 방식으로 시작합니다.",
                "source_reference": "local:recommended_pattern",
            },
        ],
        "agent_design_patterns": [
            {
                "pattern_id": "observe_analyze_report",
                "display_name": "조회-분석-리포트",
                "best_for": "반복 데이터 조회 후 요약 리포트를 공유하는 업무",
                "recommended_capabilities": ["reusable_data_flow", "prompt_template_structuring", "html_report_flow"],
            },
            {
                "pattern_id": "triage_recommend_review",
                "display_name": "분류-추천-사람 검토",
                "best_for": "이슈/요청/메일을 분류하고 다음 조치를 추천하는 업무",
                "recommended_capabilities": ["prompt_template_structuring", "agent_with_tools", "human_review_gate"],
            },
            {
                "pattern_id": "tool_agent_with_audit",
                "display_name": "도구 호출 AI 에이전트 + 로그",
                "best_for": "여러 시스템을 조회하거나 업데이트해야 하는 업무",
                "recommended_capabilities": ["agent_with_tools", "mcp_tools", "flow_api", "human_review_gate"],
            },
        ],
    }


def _merge_catalog(base: dict[str, Any], custom: dict[str, Any]) -> dict[str, Any]:
    """사용자가 추가한 catalog를 기본 catalog 뒤에 붙입니다."""

    result = deepcopy(base)
    for key in ("catalog_notes", "capabilities", "agent_design_patterns"):
        extra = custom.get(key)
        if isinstance(extra, list):
            result.setdefault(key, [])
            result[key].extend(deepcopy(extra))
    return result


def _parse_simple_catalog(text: str) -> dict[str, Any]:
    """초보자용 줄 단위 입력을 기능 카탈로그 dict로 바꿉니다.

    입력 형식:
    기능명 | 설명 | 사용 상황 | 필요 입력 | 산출물 | 난이도 | 구현 힌트 | 참고 링크
    """

    raw = str(text or "").strip()
    if not raw:
        return {}

    capabilities = []
    for line in raw.splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        parts = [part.strip() for part in value.split("|")]
        while len(parts) < 8:
            parts.append("")

        display_name = parts[0] or "사용자 추가 기능"
        description = parts[1] or f"{display_name} 기능을 업무 AI 에이전트 설계 후보로 추가합니다."
        when_to_use = parts[2] or "업무 설명에 이 기능과 관련된 데이터 조회, 판단, 생성, 공유 단계가 있을 때"
        needed_inputs = _split_items(parts[3]) or ["사용자 요청", "필요 데이터"]
        typical_outputs = _split_items(parts[4]) or ["처리 결과"]
        difficulty = _difficulty(parts[5])
        implementation_hint = parts[6] or "처음에는 읽기 전용 또는 초안 생성 용도로 연결하고, 실제 실행은 사람 검토 뒤 진행합니다."
        source_reference = parts[7] or "user_input:simple_catalog"

        capabilities.append(
            {
                "capability_id": _simple_capability_id(display_name, when_to_use),
                "display_name": display_name,
                "category": "user_added",
                "beginner_use_case": description,
                "when_to_use": when_to_use,
                "needed_inputs": needed_inputs,
                "typical_outputs": typical_outputs,
                "difficulty": difficulty,
                "implementation_hint": implementation_hint,
                "source_reference": source_reference,
            }
        )

    if not capabilities:
        return {}
    return {
        "catalog_notes": ["사용자가 02 노드의 간단 입력칸에 적은 기능을 카탈로그에 추가했습니다."],
        "capabilities": capabilities,
    }


def _simple_capability_id(display_name: str, when_to_use: str) -> str:
    """간단 입력 기능명으로 안정적인 기능 ID를 만듭니다."""

    digest = hashlib.sha1(f"{display_name}|{when_to_use}".encode("utf-8")).hexdigest()[:10]
    return f"user_added_{digest}"


def _split_items(text: str) -> list[str]:
    """쉼표, 세미콜론, 슬래시로 구분된 값을 list로 바꿉니다."""

    value = str(text or "").strip()
    if not value:
        return []
    for sep in ("，", "、", ";", "/", "·"):
        value = value.replace(sep, ",")
    return [item.strip() for item in value.split(",") if item.strip()]


def _difficulty(text: str) -> str:
    """난이도 입력을 표준 값으로 맞춥니다."""

    value = str(text or "").strip()
    if value in {"초급", "중급", "고급", "초급-중급", "중급-고급"}:
        return value
    return "중급"


def _parse_json(text: str) -> dict[str, Any]:
    """선택 입력 JSON을 파싱합니다."""

    raw = str(text or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


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


class AgentCapabilityCatalog(Component):
    """Langflow 화면에 표시되는 02 커스텀 컴포넌트 클래스."""

    display_name = "02 AI 에이전트 기능 카탈로그"
    description = "업무를 AI 에이전트로 설계할 때 참고할 Langflow 기능과 기존 기능flow 목록을 제공합니다."
    icon = "Library"
    inputs = [
        DataInput(name="payload", display_name="업무 구조화 결과", required=False),
        MessageTextInput(
            name="simple_catalog_text",
            display_name="추가 기능 간단 입력",
            required=False,
            info="한 줄에 기능 하나씩 입력합니다. 형식: 기능명 | 설명 | 사용 상황 | 필요 입력 | 산출물 | 난이도 | 구현 힌트 | 참고 링크",
        ),
        MessageTextInput(
            name="custom_catalog_json",
            display_name="추가 기능 카탈로그 JSON (고급)",
            required=False,
            advanced=True,
        ),
    ]
    outputs = [Output(name="catalog_payload", display_name="기능 카탈로그 결과", method="build_payload")]

    def build_payload(self) -> Data:
        """기능 카탈로그가 포함된 payload를 생성합니다."""

        result = build_agent_capability_catalog(
            payload_value=getattr(self, "payload", None),
            simple_catalog_text=getattr(self, "simple_catalog_text", ""),
            custom_catalog_json=getattr(self, "custom_catalog_json", ""),
        )
        catalog = result.get("agent_capability_catalog", {})
        input_summary = result.get("agent_capability_catalog_input", {})
        self.status = {
            "기능 수": len(catalog.get("capabilities", [])),
            "간단 입력 추가 기능 수": input_summary.get("간단 입력 추가 기능 수", 0),
            "설계 패턴 수": len(catalog.get("agent_design_patterns", [])),
        }
        return Data(data=result)
