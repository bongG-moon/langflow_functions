from __future__ import annotations

"""00 업무 설명 입력 노드.

이 노드는 사용자가 자연어로 적은 업무 설명을 뒤 노드들이 공통으로 읽을 수 있는
`business_request` payload로 정리합니다. 초보 Langflow 개발자가 사용할 것을 전제로
필수 입력은 `업무 설명` 하나만 두고, 나머지는 선택 입력으로 둡니다.
"""

from datetime import datetime
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import MessageTextInput, Output
from lfx.schema.data import Data


def build_business_work_request(
    work_description: str,
    business_goal: str = "",
    data_and_systems: str = "",
    constraints: str = "",
    preferred_output: str = "",
) -> dict[str, Any]:
    """사용자 입력을 표준 request dict로 만듭니다."""

    description = str(work_description or "").strip()
    if not description:
        description = "업무 설명이 입력되지 않았습니다."

    return {
        "flow_type": "business_agent_design",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "business_request": {
            "work_description": description,
            "business_goal": str(business_goal or "").strip(),
            "data_and_systems": str(data_and_systems or "").strip(),
            "constraints": str(constraints or "").strip(),
            "preferred_output": str(preferred_output or "").strip(),
        },
        "warnings": [],
    }


class BusinessWorkInputLoader(Component):
    """Langflow 화면에 표시되는 00 커스텀 컴포넌트 클래스."""

    display_name = "00 업무 설명 입력"
    description = "사람이 자연어로 적은 업무 설명과 선택 정보를 다음 노드가 읽을 수 있는 업무 요청 데이터로 정리합니다."
    icon = "ClipboardEdit"
    inputs = [
        MessageTextInput(
            name="work_description",
            display_name="업무 설명",
            required=True,
            info="현재 사람이 수행하는 업무를 자연어로 적습니다.",
        ),
        MessageTextInput(
            name="business_goal",
            display_name="업무 목적/대상",
            required=False,
            info="이 업무를 왜 하는지, 결과를 누가 보는지 적습니다.",
        ),
        MessageTextInput(
            name="data_and_systems",
            display_name="사용 데이터/시스템",
            required=False,
            info="Excel, DB, API, 메일, 사내 시스템, 파일 등 사용하는 데이터와 시스템을 적습니다.",
        ),
        MessageTextInput(
            name="constraints",
            display_name="제약사항",
            required=False,
            info="승인 필요, 보안, 사람이 꼭 확인해야 하는 구간, 자동화 금지 영역 등을 적습니다.",
        ),
        MessageTextInput(
            name="preferred_output",
            display_name="원하는 결과물",
            required=False,
            info="표, 리포트, 알림, 메일 초안, 대시보드, 처리 로그 등 원하는 산출물을 적습니다.",
        ),
    ]
    outputs = [Output(name="business_request", display_name="업무 요청", method="build_payload")]

    def build_payload(self) -> Data:
        """업무 요청 payload를 생성합니다."""

        result = build_business_work_request(
            work_description=getattr(self, "work_description", ""),
            business_goal=getattr(self, "business_goal", ""),
            data_and_systems=getattr(self, "data_and_systems", ""),
            constraints=getattr(self, "constraints", ""),
            preferred_output=getattr(self, "preferred_output", ""),
        )
        self.status = {
            "업무 목적 입력 여부": bool(result["business_request"].get("business_goal")),
            "데이터/시스템 입력 여부": bool(result["business_request"].get("data_and_systems")),
            "업무 설명 글자 수": len(result["business_request"].get("work_description", "")),
        }
        return Data(data=result)
