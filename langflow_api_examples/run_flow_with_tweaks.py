from __future__ import annotations

"""Langflow Flow API 호출 + tweaks 예시.

여러 Text Input 또는 Custom Component 입력값을 API 실행 시점에 전달할 때 사용합니다.
이 파일 상단의 TWEAKS 변수만 실제 Flow에 맞게 수정하면 바로 실행할 수 있습니다.
"""

import argparse
import json
import os
import sys
import uuid
from typing import Any

import requests


# ---------------------------------------------------------------------------
# 사용자가 수정하는 영역
# ---------------------------------------------------------------------------
# 1. 기본 Langflow 접속 정보입니다.
#    환경변수를 쓰면 코드 수정 없이 실행할 수 있고, 필요하면 아래 기본값을 직접 바꿔도 됩니다.
BASE_URL = os.getenv("LANGFLOW_BASE_URL", "http://localhost:7860")
FLOW_ID = os.getenv("LANGFLOW_FLOW_ID", "c5e93580-2705-438c-a0ef-0454ee42533c")
API_KEY = os.getenv("LANGFLOW_API_KEY", "")

# 2. Chat Input에도 함께 전달할 값이 있으면 여기에 적습니다.
#    대부분의 tweaks 기반 Flow에서는 빈 문자열로 두면 됩니다.
INPUT_VALUE = "인풋 값 테스트입니다."

# 3. Langflow 컴포넌트 입력값을 직접 지정하는 영역입니다.
#    왼쪽 key는 Langflow 컴포넌트 ID이고, 안쪽 key는 해당 컴포넌트의 input name입니다.
#    예: "BusinessWorkInputLoader-abc12"와 "work_description"을 실제 Flow 값으로 바꿔주세요.
TWEAKS: dict[str, Any] = {
    "TextInput-OXTwZ": {
        "input_value": """매일 아침 생산 데이터를 확인하고 위험 설비를 정리합니다.
        대상 데이터는 생산 실적, 설비 알람, 품질 불량 데이터입니다.
        위험 설비를 우선순위로 정리하고, 팀장 승인 후 후속 조치를 등록합니다."""
    },
    "TextInput-IsGI5": {
        "input_value": (
            "input값 테스트입니다. "
        )
    }
}


def run_flow_with_tweaks(
    *,
    base_url: str,
    flow_id: str,
    api_key: str,
    tweaks: dict[str, Any],
    input_value: str = "",
    input_type: str = "chat",
    output_type: str = "chat",
    session_id: str | None = None,
) -> dict[str, Any]:
    """tweaks를 포함해 Langflow Run API를 호출합니다."""

    url = f"{base_url.rstrip('/')}/api/v1/run/{flow_id}"
    payload = {
        "output_type": output_type,
        "input_type": input_type,
        "input_value": input_value,
        "session_id": session_id or str(uuid.uuid4()),
        "tweaks": tweaks,
    }
    headers = {"x-api-key": api_key}

    response = requests.post(url, json=payload, headers=headers, timeout=120)
    response.raise_for_status()
    return response.json()


def extract_output_message(result: dict[str, Any]) -> str:
    """Langflow 응답 JSON에서 Chat Output의 최종 메시지만 추출합니다."""

    for flow_output in result.get("outputs", []):
        for component_output in flow_output.get("outputs", []):
            for message in component_output.get("messages", []):
                text = message.get("message")
                if text:
                    return str(text)

            artifact_message = component_output.get("artifacts", {}).get("message")
            if artifact_message:
                return str(artifact_message)

            output_message = component_output.get("outputs", {}).get("message", {})
            if isinstance(output_message, dict) and output_message.get("message"):
                return str(output_message["message"])

            result_message = component_output.get("results", {}).get("message", {})
            if isinstance(result_message, dict):
                if result_message.get("text"):
                    return str(result_message["text"])
                data_text = result_message.get("data", {}).get("text")
                if data_text:
                    return str(data_text)

    raise ValueError("Langflow 응답에서 출력 메시지를 찾지 못했습니다.")


def main() -> int:
    """CLI 인자를 읽어 tweaks 기반으로 Flow를 실행합니다."""

    parser = argparse.ArgumentParser(description="Call a Langflow flow with tweaks.")
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--flow-id", default=FLOW_ID)
    parser.add_argument("--api-key", default=API_KEY)
    parser.add_argument("--input", default=INPUT_VALUE, help="Chat Input에 전달할 기본 값")
    parser.add_argument("--session-id", default="", help="비워두면 UUID를 자동 생성합니다.")
    parser.add_argument("--raw-json", action="store_true", help="최종 메시지만이 아니라 원본 JSON 전체를 출력합니다.")
    args = parser.parse_args()

    if not args.flow_id:
        print("LANGFLOW_FLOW_ID 또는 --flow-id 값을 넣어주세요.", file=sys.stderr)
        return 2
    if not args.api_key:
        print("LANGFLOW_API_KEY 또는 --api-key 값을 넣어주세요.", file=sys.stderr)
        return 2
    if not TWEAKS:
        print("파일 상단의 TWEAKS 변수에 컴포넌트 입력값을 넣어주세요.", file=sys.stderr)
        return 2

    try:
        result = run_flow_with_tweaks(
            base_url=args.base_url,
            flow_id=args.flow_id,
            api_key=args.api_key,
            input_value=args.input,
            tweaks=TWEAKS,
            session_id=args.session_id or None,
        )
    except (ValueError, requests.exceptions.RequestException) as exc:
        print(f"Error making API request: {exc}", file=sys.stderr)
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
