from __future__ import annotations

"""Langflow Flow API 호출 + tweaks 예시.

여러 Text Input 또는 Custom Component 입력값을 API 실행 시점에 전달할 때 사용합니다.
"""

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

import requests


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


def load_tweaks(path: str) -> dict[str, Any]:
    """JSON 파일에서 tweaks 값을 읽습니다."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if "tweaks" in payload and isinstance(payload["tweaks"], dict):
        return payload["tweaks"]
    if isinstance(payload, dict):
        return payload
    raise ValueError("tweaks JSON은 object 형태여야 합니다.")


def main() -> int:
    """CLI 인자를 읽어 tweaks 기반으로 Flow를 실행합니다."""

    parser = argparse.ArgumentParser(description="Call a Langflow flow with tweaks.")
    parser.add_argument("--base-url", default=os.getenv("LANGFLOW_BASE_URL", "http://localhost:7860"))
    parser.add_argument("--flow-id", default=os.getenv("LANGFLOW_FLOW_ID", ""))
    parser.add_argument("--api-key", default=os.getenv("LANGFLOW_API_KEY", ""))
    parser.add_argument("--input", default="", help="Chat Input에 전달할 기본 값")
    parser.add_argument("--tweaks-file", required=True, help="tweaks JSON 파일 경로")
    parser.add_argument("--session-id", default="", help="비워두면 UUID를 자동 생성합니다.")
    args = parser.parse_args()

    if not args.flow_id:
        print("LANGFLOW_FLOW_ID 또는 --flow-id 값을 넣어주세요.", file=sys.stderr)
        return 2
    if not args.api_key:
        print("LANGFLOW_API_KEY 또는 --api-key 값을 넣어주세요.", file=sys.stderr)
        return 2

    try:
        tweaks = load_tweaks(args.tweaks_file)
        result = run_flow_with_tweaks(
            base_url=args.base_url,
            flow_id=args.flow_id,
            api_key=args.api_key,
            input_value=args.input,
            tweaks=tweaks,
            session_id=args.session_id or None,
        )
    except (OSError, ValueError, requests.exceptions.RequestException) as exc:
        print(f"Error making API request: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
