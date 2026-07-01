from __future__ import annotations

"""01 업무 프로세스 구조화 노드.

LLM을 연결하기 전에도 사용자가 적은 업무 설명에서 단계, 데이터, 판단 지점,
반복 작업, 산출물을 대략 추출합니다. 이 결과는 LLM 프롬프트의 컨텍스트이자
LLM 없이 빠르게 확인할 때의 기본 분석 결과로 사용됩니다.
"""

import json
import re
from copy import deepcopy
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, Output
from lfx.schema.data import Data


ACTION_KEYWORDS = {
    "조회": "data_lookup",
    "수집": "data_collection",
    "다운로드": "file_or_data_collection",
    "정리": "data_preparation",
    "가공": "data_preparation",
    "분석": "analysis",
    "비교": "comparison",
    "판단": "decision",
    "검토": "review",
    "승인": "approval",
    "공유": "sharing",
    "보고": "reporting",
    "메일": "communication",
    "알림": "notification",
    "등록": "system_update",
    "업로드": "system_update",
}


def structure_work_process(payload_value: Any) -> dict[str, Any]:
    """업무 설명 payload에 deterministic process_profile을 추가합니다."""

    payload = _payload(payload_value)
    request = _dict(payload.get("business_request"))
    description = str(request.get("work_description") or "").strip()
    goal = str(request.get("business_goal") or "").strip()
    data_systems = str(request.get("data_and_systems") or "").strip()
    constraints = str(request.get("constraints") or "").strip()
    preferred_output = str(request.get("preferred_output") or "").strip()
    additional_instructions = str(request.get("additional_instructions") or "").strip()
    extra_capabilities = str(request.get("extra_capabilities_text") or "").strip()
    combined_context = " ".join(
        [
            description,
            data_systems,
            constraints,
            preferred_output,
            additional_instructions,
            extra_capabilities,
        ]
    )

    steps = _extract_steps(description)
    systems = _extract_systems(combined_context)
    data_objects = _extract_data_objects(combined_context)
    outputs = _extract_outputs(combined_context)
    decisions = _extract_decisions(" ".join([description, constraints, additional_instructions]))
    pain_points = _extract_pain_points(combined_context)
    human_checks = _extract_human_checks(" ".join([description, constraints, additional_instructions]))

    profile = {
        "summary": _summary(description, goal),
        "process_steps": steps,
        "inputs": data_objects,
        "systems": systems,
        "outputs": outputs,
        "decision_points": decisions,
        "pain_points": pain_points,
        "human_checkpoints": human_checks,
        "automation_signals": _automation_signals(description, data_systems, constraints, additional_instructions),
        "missing_information_questions": _missing_questions(request, steps, data_objects, outputs),
    }

    result = deepcopy(payload)
    result["process_profile"] = profile
    result.setdefault("warnings", [])
    return result


def _extract_steps(text: str) -> list[dict[str, Any]]:
    """업무 설명을 문장 단위로 나누고 단계 후보를 만듭니다."""

    chunks = [part.strip(" -\t") for part in re.split(r"[\n\r]+|[.;。]|(?:\s*->\s*)|(?:\s*→\s*)", text or "") if part.strip()]
    if len(chunks) <= 1:
        # 쉼표와 접속어로만 쓴 설명도 단계처럼 보이도록 한 번 더 나눕니다.
        chunks = [part.strip(" -\t") for part in re.split(r",|그리고|그 다음|이후|마지막으로|최종적으로", text or "") if part.strip()]
    if not chunks:
        chunks = ["업무 설명 확인"]

    steps = []
    for idx, chunk in enumerate(chunks[:12], 1):
        step_type = _step_type(chunk)
        steps.append(
            {
                "step_no": idx,
                "step_name": _short_step_name(chunk, step_type, idx),
                "description": chunk[:220],
                "step_type": step_type,
                "likely_actor": "human",
                "automation_candidate": step_type in {"data_lookup", "data_collection", "data_preparation", "analysis", "comparison", "reporting", "notification", "communication"},
            }
        )
    return steps


def _step_type(text: str) -> str:
    """키워드 기반으로 단계 유형을 추정합니다."""

    for keyword, step_type in ACTION_KEYWORDS.items():
        if keyword in text:
            return step_type
    return "work_step"


def _short_step_name(text: str, step_type: str, idx: int) -> str:
    """UI에서 읽기 쉬운 단계명을 만듭니다."""

    labels = {
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
    base = labels.get(step_type) or f"업무 단계 {idx}"
    words = re.sub(r"\s+", " ", text).strip()
    if len(words) <= 22:
        return words
    return base


def _extract_systems(text: str) -> list[str]:
    """업무에 등장하는 시스템/도구 후보를 추출합니다."""

    candidates = {
        "엑셀": ["excel", "엑셀", "xlsx", "csv"],
        "데이터베이스": ["db", "database", "oracle", "postgres", "mysql", "mongodb", "데이터베이스", "쿼리"],
        "API": ["api", "endpoint", "인터페이스"],
        "메일": ["메일", "email", "outlook", "gmail"],
        "메신저": ["teams", "slack", "메신저", "채팅"],
        "사내 시스템": ["사내 시스템", "시스템", "포털", "erp", "mes", "crm"],
        "문서": ["문서", "pdf", "word", "보고서"],
    }
    lower = text.lower()
    result = []
    for label, keys in candidates.items():
        if any(key.lower() in lower for key in keys):
            result.append(label)
    return result


def _extract_data_objects(text: str) -> list[str]:
    """입력 데이터 후보를 추출합니다."""

    candidates = [
        "생산량",
        "WIP",
        "재고",
        "불량",
        "수율",
        "매출",
        "주문",
        "고객",
        "설비",
        "알림",
        "이슈",
        "작업 요청",
        "파일",
        "메일",
        "담당자",
    ]
    result = [item for item in candidates if item.lower() in text.lower()]
    if "데이터" in text and "데이터" not in result:
        result.append("데이터")
    return result


def _extract_outputs(text: str) -> list[str]:
    """업무 산출물 후보를 추출합니다."""

    candidates = {
        "리포트": ["리포트", "보고서", "대시보드"],
        "표": ["표", "테이블", "목록"],
        "알림": ["알림", "통보"],
        "메일 초안": ["메일", "email"],
        "승인 요청": ["승인"],
        "시스템 등록 결과": ["등록", "업로드", "입력"],
        "요약": ["요약", "정리"],
    }
    lower = text.lower()
    result = []
    for label, keys in candidates.items():
        if any(key.lower() in lower for key in keys):
            result.append(label)
    return result or ["업무 처리 결과"]


def _extract_decisions(text: str) -> list[str]:
    """판단/조건 표현을 추출합니다."""

    patterns = [
        r"[^.\n\r]*(?:이상|초과|이하|미만|위험|정상|warning|error|승인|반려|확인)[^.\n\r]*",
        r"[^.\n\r]*(?:이면|라면|경우|조건|기준)[^.\n\r]*",
    ]
    result = []
    for pattern in patterns:
        for match in re.findall(pattern, text or "", flags=re.I):
            value = re.sub(r"\s+", " ", match).strip(" ,")
            if value and value not in result:
                result.append(value[:180])
            if len(result) >= 8:
                return result
    return result


def _extract_pain_points(text: str) -> list[str]:
    """수동/반복/오류 가능성 표현을 pain point로 추정합니다."""

    rules = [
        ("반복", "반복 작업이 많아 자동화 후보입니다."),
        ("매일", "주기적으로 수행되는 업무입니다."),
        ("수동", "수동 처리 구간이 있습니다."),
        ("복사", "복사/붙여넣기 작업이 있습니다."),
        ("누락", "누락 위험이 있습니다."),
        ("오류", "오류 검증이 필요합니다."),
        ("시간", "처리 시간이 오래 걸릴 수 있습니다."),
    ]
    result = [message for keyword, message in rules if keyword in text]
    return result[:8]


def _extract_human_checks(text: str) -> list[str]:
    """사람 검토가 필요한 구간 후보를 추출합니다."""

    rules = [
        ("승인", "승인/반려는 사람 검토 단계로 남기는 것이 안전합니다."),
        ("확인", "최종 확인 구간은 human-in-the-loop로 설계하는 것이 좋습니다."),
        ("보안", "보안 제약이 있는 데이터는 권한/마스킹 검토가 필요합니다."),
        ("민감", "민감 정보는 자동 처리 범위를 제한해야 합니다."),
        ("고객", "고객에게 나가는 메시지는 발송 전 검토 단계를 권장합니다."),
    ]
    result = [message for keyword, message in rules if keyword in text]
    return result[:8]


def _automation_signals(
    description: str,
    data_systems: str,
    constraints: str,
    additional_instructions: str = "",
) -> dict[str, Any]:
    """AI 에이전트화 가능성을 판단하는 간단한 신호를 만듭니다."""

    combined = " ".join([description, data_systems, constraints, additional_instructions]).lower()
    return {
        "has_repeated_work": any(key in combined for key in ["매일", "매주", "반복", "정기", "daily", "weekly"]),
        "has_data_work": any(key in combined for key in ["데이터", "조회", "excel", "엑셀", "db", "api", "csv"]),
        "has_decision_rule": any(key in combined for key in ["기준", "조건", "이상", "초과", "이하", "위험", "정상"]),
        "has_external_output": any(key in combined for key in ["메일", "공유", "보고", "알림", "등록"]),
        "has_human_approval": any(key in combined for key in ["승인", "검토", "확인", "반려"]),
    }


def _missing_questions(request: dict[str, Any], steps: list[dict[str, Any]], inputs: list[str], outputs: list[str]) -> list[str]:
    """AI 에이전트 설계 품질을 높이기 위해 추가로 물어볼 질문을 만듭니다."""

    questions = []
    if not request.get("business_goal"):
        questions.append("이 업무의 최종 사용자와 의사결정 목적은 무엇인가요?")
    if not request.get("data_and_systems") and not inputs:
        questions.append("업무에서 사용하는 데이터와 시스템은 무엇인가요?")
    if not request.get("constraints"):
        questions.append("자동화하면 안 되는 구간이나 반드시 사람이 승인해야 하는 구간이 있나요?")
    if len(steps) <= 2:
        questions.append("업무를 시작부터 종료까지 3~7단계로 조금 더 풀어쓸 수 있나요?")
    if not outputs:
        questions.append("최종 산출물은 리포트, 표, 알림, 메일, 시스템 등록 중 어떤 형태인가요?")
    return questions[:6]


def _summary(description: str, goal: str) -> str:
    """업무 요약 문장을 만듭니다."""

    if goal:
        return f"{goal[:120]}을 위해 수행하는 업무입니다."
    first = re.split(r"[\n\r.]", description or "")[0].strip()
    return first[:160] if first else "업무 설명을 기반으로 프로세스를 구조화합니다."


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


class WorkProcessStructurer(Component):
    """Langflow 화면에 표시되는 01 커스텀 컴포넌트 클래스."""

    display_name = "01 업무 프로세스 구조화"
    description = "업무 설명에서 처리 단계, 입력 데이터, 산출물, 판단 기준, 자동화 후보를 기본 분석합니다."
    icon = "ListTree"
    inputs = [DataInput(name="payload", display_name="업무 요청", required=True)]
    outputs = [Output(name="process_payload", display_name="업무 구조화 결과", method="build_payload")]

    def build_payload(self) -> Data:
        """업무 구조화 결과 payload를 생성합니다."""

        result = structure_work_process(getattr(self, "payload", None))
        profile = result.get("process_profile", {})
        self.status = {
            "추출 단계 수": len(profile.get("process_steps", [])),
            "사용 시스템 후보": profile.get("systems", []),
            "추가 질문 수": len(profile.get("missing_information_questions", [])),
        }
        return Data(data=result)
