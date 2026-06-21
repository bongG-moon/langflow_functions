from __future__ import annotations

"""00 리포트 요청/데이터 불러오기 노드.

이 파일은 Langflow 체험용 첫 번째 노드입니다.
사용자가 입력한 질문, 보고 싶은 방식, CSV/JSON 텍스트, File Read 결과를 하나의
표준 payload로 정리해서 뒤 노드들이 같은 형식으로 처리할 수 있게 합니다.
"""

import csv
import io
import json
from copy import deepcopy
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, MessageTextInput, Output
from lfx.schema.data import Data


def build_demo_report_request(
    question: str,
    view_request: str = "",
    data_text: str = "",
    file_data: Any = None,
) -> dict[str, Any]:
    """질문과 입력 데이터를 HTML 리포트 flow의 표준 요청 payload로 만듭니다.

    `data_text`에 직접 붙여넣은 CSV/JSON이 있으면 그것을 우선 사용하고,
    비어 있으면 `file_data`에 연결된 File Read 결과에서 텍스트를 꺼냅니다.
    이후 CSV/JSON/JSONL 여부를 판단해 rows/columns 형태로 맞춰 둡니다.
    """

    text = _select_input_text(data_text, file_data)
    datasets = _parse_datasets(text)
    selected = _select_dataset(datasets)
    rows = _rows(selected.get("rows"))
    columns = _strings(selected.get("columns")) or _columns_from_rows(rows)
    row_count = _positive_int(selected.get("row_count"), len(rows))

    compact_datasets = []
    for item in datasets:
        # 뒤 노드에는 전체 rows를 여러 번 넘기지 않고, 데이터셋 목록에는 요약만 남깁니다.
        item_rows = _rows(item.get("rows"))
        item_columns = _strings(item.get("columns")) or _columns_from_rows(item_rows)
        compact_datasets.append(
            {
                "dataset_id": str(item.get("dataset_id") or ""),
                "label": str(item.get("label") or item.get("dataset_id") or ""),
                "columns": item_columns,
                "row_count": _positive_int(item.get("row_count"), len(item_rows)),
                "data_ref": _dict(item.get("data_ref")),
            }
        )

    payload = {
        "payload_version": "html-report-demo-v1",
        "flow_type": "html_report_demo",
        "status": "ok",
        "request": {
            "question": str(question or ""),
            "view_request": str(view_request or ""),
            "selected_dataset_id": str(selected.get("dataset_id") or ""),
        },
        "available_datasets": compact_datasets,
        "api_response": {
            "status": "ok",
            "response_type": "demo_data",
            "message": "Demo data loaded for HTML report generation.",
            "data": {
                "columns": columns,
                "rows": rows,
                "row_count": row_count,
                "data_ref": _dict(selected.get("data_ref")),
                "data_is_preview": row_count > len(rows),
            },
        },
        "warnings": [],
        "errors": [],
    }
    if not rows:
        payload["warnings"].append("No rows were loaded from data_text or file_data.")
    return payload


def _select_input_text(data_text: str, file_data: Any) -> str:
    """직접 입력 텍스트와 File Read 결과 중 실제로 사용할 텍스트를 고릅니다."""

    direct = str(data_text or "").strip()
    file_text = _extract_text(file_data).strip()
    return direct or file_text


def _extract_text(value: Any) -> str:
    """Langflow의 다양한 데이터 객체에서 가능한 텍스트 내용을 꺼냅니다.

    File Read 컴포넌트는 Langflow 버전/파일 유형에 따라 Data, Message, DataFrame 등
    서로 다른 모양으로 값을 넘길 수 있습니다. 그래서 흔히 쓰이는 속성과 key를
    차례로 확인하면서 CSV/JSON으로 변환 가능한 값을 찾습니다.
    """

    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if hasattr(value, "to_csv"):
        try:
            # pandas DataFrame처럼 `to_csv`가 있으면 CSV 문자열로 바꿉니다.
            return value.to_csv(index=False)
        except Exception:
            pass
    if hasattr(value, "to_dict"):
        try:
            # pandas DataFrame처럼 `to_dict`가 있으면 row dict 목록으로 바꿉니다.
            rows = value.to_dict(orient="records")
            if isinstance(rows, list):
                return json.dumps(rows, ensure_ascii=False, default=str)
        except Exception:
            pass
    data = getattr(value, "data", None)
    if isinstance(data, dict):
        for key in ("text", "content", "data", "raw", "file_content", "file_contents"):
            if isinstance(data.get(key), str):
                return data[key]
        for key in ("dataframe", "structured_content", "structuredContent"):
            if data.get(key) is not None:
                extracted = _extract_text(data.get(key))
                if extracted:
                    return extracted
        if isinstance(data.get("rows"), list):
            return json.dumps(data, ensure_ascii=False, default=str)
        if isinstance(data.get("records"), list):
            return json.dumps(data["records"], ensure_ascii=False, default=str)
        if isinstance(data.get("columns"), list) and isinstance(data.get("data"), list):
            return json.dumps(data, ensure_ascii=False, default=str)
    if isinstance(data, list):
        return json.dumps(data, ensure_ascii=False, default=str)
    for attr in ("text", "content"):
        text = getattr(value, attr, None)
        if isinstance(text, str):
            return text
    for attr in ("dataframe", "structured_content", "structuredContent", "value"):
        nested = getattr(value, attr, None)
        if nested is not None and nested is not value:
            extracted = _extract_text(nested)
            if extracted:
                return extracted
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, default=str)
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def _parse_datasets(text: str) -> list[dict[str, Any]]:
    """입력 문자열을 데이터셋 목록으로 파싱합니다.

    우선 JSON을 시도하고, 실패하면 JSONL, 마지막으로 CSV로 해석합니다.
    아무 입력도 없으면 빈 demo 데이터셋을 만들어 flow가 끊기지 않게 합니다.
    """

    raw = str(text or "").strip()
    if not raw:
        return [_dataset("demo_dataset", "입력 데이터", [], [])]
    parsed = _try_json(raw)
    if parsed is not None:
        return _datasets_from_json(parsed)
    parsed_rows = _try_jsonl(raw)
    if parsed_rows is not None:
        return [_dataset("demo_dataset", "입력 데이터", _columns_from_rows(parsed_rows), parsed_rows)]
    rows = _parse_csv(raw)
    return [_dataset("demo_dataset", "입력 데이터", _columns_from_rows(rows), rows)]


def _datasets_from_json(value: Any) -> list[dict[str, Any]]:
    """JSON 값에서 rows/columns/data_ref 구조를 찾아 데이터셋 목록으로 바꿉니다."""

    if isinstance(value, list):
        if all(isinstance(item, dict) for item in value):
            return [_dataset("demo_dataset", "입력 데이터", _columns_from_rows(value), value)]
        return [_dataset("demo_dataset", "입력 데이터", ["value"], [{"value": item} for item in value])]
    if not isinstance(value, dict):
        return [_dataset("demo_dataset", "입력 데이터", ["value"], [{"value": value}])]

    if isinstance(value.get("datasets"), list):
        datasets = []
        for index, item in enumerate(value["datasets"], start=1):
            if not isinstance(item, dict):
                continue
            rows = _rows(item.get("rows") or _dict(item.get("data")).get("rows"))
            columns = _strings(item.get("columns")) or _strings(_dict(item.get("data")).get("columns")) or _columns_from_rows(rows)
            datasets.append(
                _dataset(
                    str(item.get("dataset_id") or item.get("id") or f"dataset_{index}"),
                    str(item.get("label") or item.get("name") or item.get("dataset_id") or f"Dataset {index}"),
                    columns,
                    rows,
                    data_ref=_dict(item.get("data_ref")),
                    row_count=_positive_int(item.get("row_count"), len(rows)),
                )
            )
        return datasets or [_dataset("demo_dataset", "입력 데이터", [], [])]

    data = _dict(value.get("data"))
    rows = _rows(value.get("rows") or data.get("rows"))
    columns = _strings(value.get("columns")) or _strings(data.get("columns")) or _columns_from_rows(rows)
    return [
        _dataset(
            str(value.get("dataset_id") or value.get("id") or "demo_dataset"),
            str(value.get("label") or value.get("name") or "입력 데이터"),
            columns,
            rows,
            data_ref=_dict(value.get("data_ref") or data.get("data_ref")),
            row_count=_positive_int(value.get("row_count") or data.get("row_count"), len(rows)),
        )
    ]


def _try_json(text: str) -> Any | None:
    """문자열 전체를 JSON으로 읽어 봅니다. 실패하면 None을 반환합니다."""

    try:
        return json.loads(text)
    except Exception:
        return None


def _try_jsonl(text: str) -> list[dict[str, Any]] | None:
    """한 줄에 JSON 객체 하나씩 있는 JSONL 형식을 읽어 봅니다."""

    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except Exception:
            return None
        if not isinstance(parsed, dict):
            return None
        rows.append(parsed)
    return rows if rows else None


def _parse_csv(text: str) -> list[dict[str, Any]]:
    """CSV 문자열을 dict row 목록으로 변환합니다."""

    sample = text[:2048]
    try:
        # 구분자가 쉼표인지 탭인지 등을 csv.Sniffer가 샘플을 보고 추정합니다.
        dialect = csv.Sniffer().sniff(sample)
    except Exception:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    return [_clean_row(row) for row in reader if isinstance(row, dict)]


def _clean_row(row: dict[str, Any]) -> dict[str, Any]:
    """CSV row에서 빈 컬럼명은 제거하고 값은 숫자면 숫자로 변환합니다."""

    return {str(key or "").strip(): _coerce(value) for key, value in row.items() if str(key or "").strip()}


def _coerce(value: Any) -> Any:
    """문자열 값을 가능한 경우 int/float 숫자로 바꿉니다."""

    text = str(value or "").strip()
    if text == "":
        return ""
    normalized = text.replace(",", "")
    try:
        number = float(normalized)
    except Exception:
        return text
    return int(number) if number.is_integer() else number


def _dataset(
    dataset_id: str,
    label: str,
    columns: list[str],
    rows: list[dict[str, Any]],
    data_ref: dict[str, Any] | None = None,
    row_count: int | None = None,
) -> dict[str, Any]:
    """뒤 노드들이 기대하는 데이터셋 딕셔너리 형식을 만듭니다."""

    return {
        "dataset_id": str(dataset_id or "demo_dataset"),
        "label": str(label or dataset_id or "Demo Dataset"),
        "columns": columns,
        "rows": rows,
        "row_count": len(rows) if row_count is None else int(row_count),
        "data_ref": data_ref or {},
    }


def _select_dataset(datasets: list[dict[str, Any]]) -> dict[str, Any]:
    """현재 체험 flow에서는 첫 번째 데이터셋을 분석 대상으로 선택합니다."""

    return deepcopy(datasets[0]) if datasets else _dataset("demo_dataset", "Demo Dataset", [], [])


def _rows(value: Any) -> list[dict[str, Any]]:
    """값이 dict 목록이면 안전하게 복사해서 반환하고, 아니면 빈 목록을 반환합니다."""

    return [deepcopy(row) for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _columns_from_rows(rows: list[dict[str, Any]]) -> list[str]:
    """rows에 실제로 등장한 컬럼명을 처음 나온 순서대로 모읍니다."""

    columns: list[str] = []
    for row in rows:
        for key in row:
            text = str(key)
            if text not in columns:
                columns.append(text)
    return columns


def _strings(value: Any) -> list[str]:
    """문자열 목록만 깨끗하게 정리하고 중복을 제거합니다."""

    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        text = str(item or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def _dict(value: Any) -> dict[str, Any]:
    """값이 dict면 복사본을, 아니면 빈 dict를 반환합니다."""

    return deepcopy(value) if isinstance(value, dict) else {}


def _positive_int(value: Any, default: int) -> int:
    """정수로 변환하되 음수는 0으로 보정합니다."""

    try:
        parsed = int(value)
    except Exception:
        parsed = default
    return max(0, parsed)


class DemoReportRequestLoader(Component):
    """Langflow 화면에 표시되는 00번 커스텀 컴포넌트 클래스."""

    display_name = "00 리포트 요청/데이터 불러오기"
    description = "질문, 표시 요청, 직접 입력 데이터 또는 File Read 결과를 HTML 리포트용 요청으로 정리합니다."
    icon = "FileInput"
    inputs = [
        MessageTextInput(name="question", display_name="질문", required=True),
        MessageTextInput(name="view_request", display_name="보고 싶은 방식", required=False),
        MessageTextInput(name="data_text", display_name="데이터 직접 입력", required=False),
        DataInput(
            name="file_data",
            display_name="파일 데이터",
            input_types=[
                "Data",
                "DataFrame",
                "Message",
                "Text",
                "File",
                "JSON",
                "StructuredContent",
                "Structured Content",
            ],
            required=False,
        ),
    ]
    outputs = [Output(name="payload", display_name="요청 데이터", method="build_payload")]

    def build_payload(self) -> Data:
        """Langflow가 이 노드를 실행할 때 호출하는 출력 생성 함수입니다."""

        result = build_demo_report_request(
            getattr(self, "question", ""),
            getattr(self, "view_request", ""),
            getattr(self, "data_text", ""),
            getattr(self, "file_data", None),
        )
        self.status = {
            "datasets": len(result.get("available_datasets", [])),
            "selected": (result.get("request") or {}).get("selected_dataset_id"),
            "rows": ((result.get("api_response") or {}).get("data") or {}).get("row_count", 0),
        }
        return Data(data=result)
