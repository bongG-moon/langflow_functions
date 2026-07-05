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


def extract_output_message(result: dict[str, Any]) -> str:
    """Langflow 응답 JSON에서 사용자가 실제로 보고 싶은 최종 메시지만 추출합니다.

    Langflow Run API 응답은 실행 기록, 컴포넌트 정보, 로그, 메시지 객체를 모두 담고 있어서
    그대로 출력하면 매우 복잡합니다. 일반적으로 사람이 확인해야 하는 값은 Chat Output의
    message 텍스트이므로, 자주 등장하는 위치를 순서대로 확인합니다.
    """

    for flow_output in result.get("outputs", []):
        for component_output in flow_output.get("outputs", []):
            # 가장 읽기 쉬운 위치입니다. Chat Output이 만든 메시지 목록입니다.
            for message in component_output.get("messages", []):
                text = message.get("message")
                if text:
                    return str(text)

            # 일부 Langflow 응답은 artifacts.message에 같은 값을 담습니다.
            artifact_message = component_output.get("artifacts", {}).get("message")
            if artifact_message:
                return str(artifact_message)

            # outputs.message.message 형태로 들어오는 경우도 있습니다.
            output_message = component_output.get("outputs", {}).get("message", {})
            if isinstance(output_message, dict) and output_message.get("message"):
                return str(output_message["message"])

            # results.message.text 또는 results.message.data.text도 확인합니다.
            result_message = component_output.get("results", {}).get("message", {})
            if isinstance(result_message, dict):
                if result_message.get("text"):
                    return str(result_message["text"])
                data_text = result_message.get("data", {}).get("text")
                if data_text:
                    return str(data_text)

    raise ValueError("Langflow 응답에서 출력 메시지를 찾지 못했습니다.")


def main() -> int:
    """CLI 인자를 읽어 Flow를 실행합니다."""

    parser = argparse.ArgumentParser(description="Call a Langflow flow with one chat input.")
    parser.add_argument("--base-url", default=os.getenv("LANGFLOW_BASE_URL", "http://localhost:7860"))
    parser.add_argument("--flow-id", default=os.getenv("LANGFLOW_FLOW_ID", ""))
    parser.add_argument("--api-key", default=os.getenv("LANGFLOW_API_KEY", ""))
    parser.add_argument("--input", default="hello world!", help="Chat Input으로 전달할 값")
    parser.add_argument("--session-id", default="", help="비워두면 UUID를 자동 생성합니다.")
    parser.add_argument("--raw-json", action="store_true", help="최종 메시지만이 아니라 원본 JSON 전체를 출력합니다.")
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

    if args.raw_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        try:
            print(extract_output_message(result))
        except ValueError as exc:
            print(f"Error extracting output message: {exc}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
