from __future__ import annotations

"""Langflow Flow 기본 API 호출 예시.

Flow가 Chat Input을 통해 하나의 사용자 메시지를 받는 경우에 사용합니다.
"""

import argparse
import json
import os
import sys
import uuid
from typing import Any

import requests


def run_flow(
    *,
    base_url: str,
    flow_id: str,
    api_key: str,
    input_value: str,
    input_type: str = "chat",
    output_type: str = "chat",
    session_id: str | None = None,
) -> dict[str, Any]:
    """Langflow Run API를 호출하고 JSON 응답을 반환합니다."""

    url = f"{base_url.rstrip('/')}/api/v1/run/{flow_id}"
    payload = {
        "output_type": output_type,
        "input_type": input_type,
        "input_value": input_value,
        "session_id": session_id or str(uuid.uuid4()),
    }
    headers = {"x-api-key": api_key}

    response = requests.post(url, json=payload, headers=headers, timeout=120)
    response.raise_for_status()
    return response.json()


def main() -> int:
    """CLI 인자를 읽어 Flow를 실행합니다."""

    parser = argparse.ArgumentParser(description="Call a Langflow flow with one chat input.")
    parser.add_argument("--base-url", default=os.getenv("LANGFLOW_BASE_URL", "http://localhost:7860"))
    parser.add_argument("--flow-id", default=os.getenv("LANGFLOW_FLOW_ID", ""))
    parser.add_argument("--api-key", default=os.getenv("LANGFLOW_API_KEY", ""))
    parser.add_argument("--input", default="hello world!", help="Chat Input으로 전달할 값")
    parser.add_argument("--session-id", default="", help="비워두면 UUID를 자동 생성합니다.")
    args = parser.parse_args()

    if not args.flow_id:
        print("LANGFLOW_FLOW_ID 또는 --flow-id 값을 넣어주세요.", file=sys.stderr)
        return 2
    if not args.api_key:
        print("LANGFLOW_API_KEY 또는 --api-key 값을 넣어주세요.", file=sys.stderr)
        return 2

    try:
        result = run_flow(
            base_url=args.base_url,
            flow_id=args.flow_id,
            api_key=args.api_key,
            input_value=args.input,
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
