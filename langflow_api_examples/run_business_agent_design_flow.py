from __future__ import annotations

"""업무 AI 에이전트 설계 Flow 호출 예시.

업무 설명 하나를 API로 전달하는 가장 단순한 예시입니다.
Chat Input으로 전달하거나, 00 업무 설명 입력 컴포넌트를 tweaks로 직접 설정할 수 있습니다.
"""

import argparse
import json
import os
import sys
import uuid
from typing import Any

import requests


def build_payload(work_description: str, component_id: str = "", session_id: str | None = None) -> dict[str, Any]:
    """업무 설명을 Langflow Run API payload로 변환합니다."""

    payload: dict[str, Any] = {
        "output_type": "chat",
        "input_type": "chat",
        "input_value": work_description if not component_id else "",
        "session_id": session_id or str(uuid.uuid4()),
    }
    if component_id:
        payload["tweaks"] = {
            component_id: {
                "work_description": work_description,
            }
        }
    return payload


def run_business_flow(
    *,
    base_url: str,
    flow_id: str,
    api_key: str,
    work_description: str,
    component_id: str = "",
    session_id: str | None = None,
) -> dict[str, Any]:
    """업무 AI 에이전트 설계 Flow를 실행합니다."""

    url = f"{base_url.rstrip('/')}/api/v1/run/{flow_id}"
    payload = build_payload(work_description, component_id, session_id)
    headers = {"x-api-key": api_key}

    response = requests.post(url, json=payload, headers=headers, timeout=180)
    response.raise_for_status()
    return response.json()


def main() -> int:
    """CLI 인자를 읽어 업무 설계 Flow를 실행합니다."""

    parser = argparse.ArgumentParser(description="Call business_agent_design_flow through Langflow API.")
    parser.add_argument("--base-url", default=os.getenv("LANGFLOW_BASE_URL", "http://localhost:7860"))
    parser.add_argument("--flow-id", default=os.getenv("LANGFLOW_FLOW_ID", ""))
    parser.add_argument("--api-key", default=os.getenv("LANGFLOW_API_KEY", ""))
    parser.add_argument("--work-description", required=True, help="사용자가 자연어로 적은 업무 설명")
    parser.add_argument(
        "--component-id",
        default="",
        help="Chat Input 대신 00 업무 설명 입력 컴포넌트를 tweaks로 직접 설정할 때 사용합니다.",
    )
    parser.add_argument("--session-id", default="", help="비워두면 UUID를 자동 생성합니다.")
    args = parser.parse_args()

    if not args.flow_id:
        print("LANGFLOW_FLOW_ID 또는 --flow-id 값을 넣어주세요.", file=sys.stderr)
        return 2
    if not args.api_key:
        print("LANGFLOW_API_KEY 또는 --api-key 값을 넣어주세요.", file=sys.stderr)
        return 2

    try:
        result = run_business_flow(
            base_url=args.base_url,
            flow_id=args.flow_id,
            api_key=args.api_key,
            work_description=args.work_description,
            component_id=args.component_id,
            session_id=args.session_id or None,
        )
    except requests.exceptions.RequestException as exc:
        print(f"Error making API request: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Error parsing response: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
