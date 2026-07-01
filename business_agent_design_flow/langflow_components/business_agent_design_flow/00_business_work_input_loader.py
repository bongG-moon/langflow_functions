from __future__ import annotations

"""00 업무 설명 입력 노드.

사용자가 만지는 입력은 `업무 설명` 하나만 둡니다.
업무를 자연스럽게 서술하면 이 노드가 목적, 데이터/시스템, 제약사항, 원하는 결과물,
추가 구현 지시, 추가 기능 후보를 가볍게 추정해 뒤 노드가 읽기 쉬운 payload로 만듭니다.
"""

from datetime import datetime
import re
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import MessageTextInput, Output
from lfx.schema.data import Data


SECTION_LABELS = {
    "business_goal": [
        "업무 목적",
        "목적",
        "대상",
        "사용자",
        "누가 보는지",
        "왜 하는지",
    ],
    "data_and_systems": [
        "사용 데이터",
        "데이터",
        "시스템",
        "사용 시스템",
        "데이터/시스템",
        "원천",
        "소스",
    ],
    "constraints": [
        "제약",
        "제약사항",
        "보안",
        "승인",
        "주의사항",
        "자동화 금지",
        "사람 확인",
    ],
    "preferred_output": [
        "원하는 결과",
        "원하는 결과물",
        "산출물",
        "출력",
        "결과물",
        "보고 형태",
    ],
    "additional_instructions": [
        "추가 지시",
        "추가 요청",
        "구현 지시",
        "설계 지시",
        "원하는 방식",
        "요구사항",
    ],
    "extra_capabilities_text": [
        "추가 기능",
        "사용 가능한 기능",
        "기존 기능",
        "기존 flow",
        "기존 플로우",
        "기존 컴포넌트",
        "연결 가능한 도구",
        "사내 도구",
    ],
}

NARRATIVE_INFERENCE_RULES = {
    "business_goal": [
        "목적",
        "위해",
        "위한",
        "빠르게",
        "쉽게",
        "안정적으로",
        "일정하게",
        "대상",
    ],
    "data_and_systems": [
        "데이터",
        "엑셀",
        "excel",
        "csv",
        "파일",
        "db",
        "database",
        "oracle",
        "erp",
        "mes",
        "crm",
        "api",
        "시스템",
        "문서",
        "목록",
        "이력",
        "로그",
        "테이블",
    ],
    "constraints": [
        "승인",
        "검토",
        "보안",
        "민감",
        "권한",
        "자동 발송",
        "자동으로 수행하면 안",
        "자동으로 처리하면 안",
        "자동 실행",
        "하지 말",
        "하면 안",
        "금지",
        "사람이 확인",
    ],
    "preferred_output": [
        "리포트",
        "보고서",
        "대시보드",
        "표",
        "목록",
        "요약",
        "초안",
        "알림",
        "체크리스트",
        "로드맵",
        "결과",
        "산출",
        "출력",
    ],
    "additional_instructions": [
        "초보",
        "langflow",
        "플로우",
        "구현",
        "설계",
        "제안",
        "1차",
        "2차",
        "확장",
        "연결",
        "구조",
        "형태",
        "방식",
    ],
    "extra_capabilities_text": [
        "기능",
        "도구",
        "api",
        "mcp",
        "기존",
        "사내",
        "연동",
        "조회 기능",
        "검색 기능",
        "이미 만든",
        "사용 가능한",
        "우리 팀에는",
        "우리팀에는",
    ],
}


def build_business_work_request(work_description: str) -> dict[str, Any]:
    """사용자가 한 칸에 적은 자연어 업무 설명을 표준 request dict로 만듭니다."""

    raw_description = str(work_description or "").strip()
    if not raw_description:
        raw_description = "업무 설명이 입력되지 않았습니다."

    extracted = _split_embedded_sections(raw_description)
    extracted = _infer_missing_sections(raw_description, extracted)
    description = extracted.get("work_description") or raw_description

    return {
        "flow_type": "business_agent_design",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "business_request": {
            "work_description": description,
            "raw_work_description": raw_description,
            "business_goal": extracted.get("business_goal", ""),
            "data_and_systems": extracted.get("data_and_systems", ""),
            "constraints": extracted.get("constraints", ""),
            "preferred_output": extracted.get("preferred_output", ""),
            "additional_instructions": extracted.get("additional_instructions", ""),
            "extra_capabilities_text": extracted.get("extra_capabilities_text", ""),
            "input_mode": "single_natural_language",
            "field_extraction_mode": "label_or_narrative_inference",
        },
        "warnings": [],
    }


def _split_embedded_sections(text: str) -> dict[str, str]:
    """업무 설명 안에 섞여 있는 간단한 라벨형 정보를 분리합니다.

    예를 들어 `목적: ...`, `데이터: ...`, `제약: ...`처럼 적힌 줄은 별도 필드로
    담고, 라벨이 없는 줄은 실제 업무 설명 본문으로 유지합니다.
    """

    result = {
        "work_description": "",
        "business_goal": "",
        "data_and_systems": "",
        "constraints": "",
        "preferred_output": "",
        "additional_instructions": "",
        "extra_capabilities_text": "",
    }
    body_lines: list[str] = []
    current_key = "work_description"

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        key, content = _section_from_line(line)
        if key:
            current_key = key
            if content:
                _append_section(result, current_key, content)
            continue

        if _looks_like_heading(line):
            maybe_key = _section_key(line)
            if maybe_key:
                current_key = maybe_key
                continue

        if current_key == "work_description":
            body_lines.append(line)
        else:
            _append_section(result, current_key, line)

    result["work_description"] = "\n".join(body_lines).strip()
    if not result["work_description"]:
        result["work_description"] = text.strip()
    return result


def _infer_missing_sections(text: str, extracted: dict[str, str]) -> dict[str, str]:
    """라벨이 없는 서술형 문장에서 비어 있는 항목을 추정합니다.

    이 단계는 LLM 판단을 대체하는 정답 분류기가 아니라, 뒤 노드가 참고할 수 있는
    힌트를 만드는 가벼운 전처리입니다. 원문은 `raw_work_description`과
    `work_description`에 그대로 남아 LLM이 다시 해석할 수 있습니다.
    """

    result = dict(extracted)
    sentences = _sentence_units(text)
    for key in (
        "business_goal",
        "data_and_systems",
        "constraints",
        "preferred_output",
        "additional_instructions",
        "extra_capabilities_text",
    ):
        if result.get(key):
            continue
        inferred = _matching_sentences(sentences, key)
        if inferred:
            result[key] = "\n".join(inferred[:4])
    return result


def _sentence_units(text: str) -> list[str]:
    """업무 설명을 너무 잘게 쪼개지 않으면서 문장 후보로 나눕니다."""

    units: list[str] = []
    for line in str(text or "").splitlines():
        line = line.strip(" -\t")
        if not line:
            continue
        parts = re.split(r"(?<=[.!?。])\s+|(?<=다\.)\s+|(?<=요\.)\s+", line)
        for part in parts:
            cleaned = re.sub(r"\s+", " ", part).strip(" -\t")
            if cleaned:
                units.append(cleaned)
    return units


def _matching_sentences(sentences: list[str], key: str) -> list[str]:
    """항목별 키워드와 문장 점수를 이용해 관련 문장을 고릅니다."""

    rules = NARRATIVE_INFERENCE_RULES.get(key, [])
    threshold = _score_threshold(key)
    matches: list[tuple[int, str]] = []
    for sentence in sentences:
        score = _sentence_score(sentence, rules, key)
        if score >= threshold:
            matches.append((score, sentence))
    matches.sort(key=lambda item: (-item[0], sentences.index(item[1])))
    return _dedupe([sentence for _, sentence in matches])


def _score_threshold(key: str) -> int:
    """항목별 오탐을 줄이기 위한 최소 점수입니다."""

    return {
        "business_goal": 2,
        "data_and_systems": 2,
        "constraints": 3,
        "preferred_output": 3,
        "additional_instructions": 3,
        "extra_capabilities_text": 4,
    }.get(key, 1)


def _sentence_score(sentence: str, rules: list[str], key: str) -> int:
    """문장이 특정 항목에 얼마나 가까운지 간단히 점수화합니다."""

    lower = sentence.lower()
    score = sum(1 for rule in rules if rule.lower() in lower)
    if key == "extra_capabilities_text" and any(marker in lower for marker in ["기능", "api", "도구", "기존", "사내"]):
        score += 2
    if key == "constraints" and any(marker in lower for marker in ["안", "말", "승인", "검토", "확인"]):
        score += 1
    if key == "preferred_output" and any(marker in lower for marker in ["만들", "보여", "출력", "작성", "보고 싶"]):
        score += 1
    if key == "business_goal" and any(marker in lower for marker in ["위해", "위한", "목적"]):
        score += 2
    return score


def _dedupe(values: list[str]) -> list[str]:
    """순서를 유지하며 중복 문장을 제거합니다."""

    seen = set()
    result = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _section_from_line(line: str) -> tuple[str, str]:
    """`라벨: 내용` 형태의 줄이면 payload key와 내용을 반환합니다."""

    for separator in (":", "：", "-", " - "):
        if separator not in line:
            continue
        label, content = line.split(separator, 1)
        key = _section_key(label)
        if key:
            return key, content.strip()
    return "", ""


def _section_key(label: str) -> str:
    """사용자가 쓴 한글 라벨을 내부 payload key로 매핑합니다."""

    normalized = str(label or "").strip().lower().replace("#", "").replace("*", "")
    normalized = normalized.replace(" ", "")
    for key, labels in SECTION_LABELS.items():
        for candidate in labels:
            if candidate.replace(" ", "").lower() in normalized:
                return key
    return ""


def _looks_like_heading(line: str) -> bool:
    """마크다운 제목이나 짧은 라벨 줄인지 판단합니다."""

    cleaned = line.strip("#-[]() ")
    return len(cleaned) <= 24


def _append_section(result: dict[str, str], key: str, value: str) -> None:
    """같은 섹션이 여러 줄이면 줄바꿈으로 이어 붙입니다."""

    value = str(value or "").strip()
    if not value:
        return
    result[key] = f"{result[key]}\n{value}".strip() if result.get(key) else value


class BusinessWorkInputLoader(Component):
    """Langflow 화면에 표시되는 00 커스텀 컴포넌트 클래스."""

    display_name = "00 업무 설명 입력"
    description = "업무 진행 방식을 한 칸에 자연어로 입력하면 뒤 노드가 읽을 수 있는 업무 요청 데이터로 정리합니다."
    icon = "ClipboardEdit"
    inputs = [
        MessageTextInput(
            name="work_description",
            display_name="업무 설명",
            required=True,
            info="업무 진행 방식, 목적, 데이터, 제약, 원하는 결과, 추가 기능 설명을 모두 이 칸에 자연어로 적습니다.",
        ),
    ]
    outputs = [Output(name="business_request", display_name="업무 요청", method="build_payload")]

    def build_payload(self) -> Data:
        """업무 요청 payload를 생성합니다."""

        result = build_business_work_request(work_description=getattr(self, "work_description", ""))
        request = result["business_request"]
        extracted_fields = [
            key
            for key in (
                "business_goal",
                "data_and_systems",
                "constraints",
                "preferred_output",
                "additional_instructions",
                "extra_capabilities_text",
            )
            if request.get(key)
        ]
        self.status = {
            "입력 방식": "업무 설명 1개 입력",
            "업무 설명 글자 수": len(request.get("raw_work_description", "")),
            "자동 분리된 항목": extracted_fields,
        }
        return Data(data=result)
