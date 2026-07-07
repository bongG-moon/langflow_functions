from __future__ import annotations

"""11 페이지 이미지 대체 업로드 노드.

Langflow 서버에 업로드된 이미지 또는 data URI를 card_news_request.page_image_overrides에 추가합니다.
지정된 페이지는 LLM 생성 문구 없이 이미지 전용 slide로 렌더링됩니다.
"""

import base64
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, MessageTextInput, Output
from lfx.schema.data import Data


ALLOWED_IMAGE_PREFIXES = ("data:image/png;base64,", "data:image/jpeg;base64,", "data:image/webp;base64,")
DEFAULT_MAX_IMAGE_BYTES = 4 * 1024 * 1024


def add_page_image_override(
    payload_value: Any,
    uploaded_image: Any = None,
    image_path: Any = "",
    direct_data_uri: Any = "",
    page: Any = "3",
    slide_id: Any = "",
    alt: Any = "",
    fit: Any = "contain",
    background_color: Any = "#FFFDF7",
    max_image_bytes: Any = DEFAULT_MAX_IMAGE_BYTES,
) -> dict[str, Any]:
    """업로드 이미지를 특정 페이지 대체 이미지로 request payload에 추가합니다."""

    payload = _payload(payload_value)
    max_bytes = _parse_size(max_image_bytes, DEFAULT_MAX_IMAGE_BYTES)
    image, image_warnings = _extract_image(uploaded_image, image_path, direct_data_uri, max_bytes)
    warnings = list(image_warnings)
    errors: list[str] = []
    page_number = _positive_int(page, 0)
    target_slide_id = _clean(slide_id)
    if not page_number and not target_slide_id:
        errors.append("page 또는 slide_id 중 하나는 필요합니다.")
    if not image:
        errors.append("업로드 이미지 또는 data URI를 찾지 못했습니다.")

    override = {
        "page": page_number,
        "slide_id": target_slide_id,
        "data_uri": image.get("data_uri", ""),
        "alt": _clean(alt) or "사용자가 업로드한 카드뉴스 페이지 이미지",
        "fit": _safe_token(fit, {"contain", "cover", "fill"}, "contain"),
        "background_color": _safe_color(background_color, "#FFFDF7"),
        "source": "langflow_upload",
        "mime_type": image.get("mime_type", ""),
        "size_bytes": image.get("size_bytes", 0),
        "width": image.get("width", 0),
        "height": image.get("height", 0),
    }

    result = deepcopy(payload)
    request = _dict(result.get("card_news_request"))
    overrides = [item for item in _list(request.get("page_image_overrides")) if isinstance(item, dict)]
    overrides = _replace_override(overrides, override)
    request["page_image_overrides"] = overrides
    result["card_news_request"] = request
    result["page_image_override_upload"] = {
        "status": "ok" if image and not errors else "error",
        "page": page_number,
        "slide_id": target_slide_id,
        "size_bytes": image.get("size_bytes", 0),
        "warnings": warnings,
        "errors": errors,
    }
    result["trace"] = _merge_trace(result.get("trace"), warnings, errors)
    return result


def _replace_override(items: list[dict[str, Any]], override: dict[str, Any]) -> list[dict[str, Any]]:
    page = _positive_int(override.get("page"), 0)
    slide_id = _clean(override.get("slide_id"))
    result = []
    for item in items:
        same_page = page and _positive_int(item.get("page"), 0) == page
        same_slide = slide_id and _clean(item.get("slide_id")) == slide_id
        if same_page or same_slide:
            continue
        result.append(item)
    result.append(override)
    return result


def _extract_image(uploaded_image: Any, image_path: Any, direct_data_uri: Any, max_bytes: int) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    candidates = [_clean(direct_data_uri), _clean(image_path)]
    candidates.extend(_candidate_values(uploaded_image))
    for candidate in candidates:
        image, warning = _image_from_candidate(candidate, max_bytes)
        if warning:
            warnings.append(warning)
        if image:
            return image, warnings
    return {}, warnings


def _candidate_values(value: Any) -> list[Any]:
    if value is None:
        return []
    data = getattr(value, "data", None)
    if data is not None and data is not value:
        return _candidate_values(data)
    if isinstance(value, list):
        result: list[Any] = []
        for item in value:
            result.extend(_candidate_values(item))
        return result
    if isinstance(value, dict):
        result = []
        for key in ("data_uri", "base64", "b64", "file_base64", "path", "file_path", "filepath", "file", "files", "file_paths", "location", "content", "file_content", "value"):
            if key in value:
                result.append(value[key])
        return result
    for attr in ("path", "file_path", "filepath", "file", "files", "file_paths", "location", "content", "text", "value"):
        nested = getattr(value, attr, None)
        if nested is not None and nested is not value:
            return _candidate_values(nested)
    return [value]


def _image_from_candidate(candidate: Any, max_bytes: int) -> tuple[dict[str, Any], str]:
    if not candidate:
        return {}, ""
    if isinstance(candidate, bytes):
        return _image_from_bytes(candidate, max_bytes)
    text = _clean(candidate)
    if not text:
        return {}, ""
    if text.startswith(ALLOWED_IMAGE_PREFIXES):
        try:
            prefix, encoded = text.split(",", 1)
            raw = base64.b64decode(encoded, validate=True)
        except Exception:
            return {}, "data URI base64를 디코딩하지 못했습니다."
        image, warning = _image_from_bytes(raw, max_bytes)
        if image:
            image["data_uri"] = text
        return image, warning
    try:
        path = Path(text)
        is_file = path.is_file()
    except Exception:
        is_file = False
    if is_file:
        try:
            raw = path.read_bytes()
        except Exception as exc:
            return {}, f"이미지 파일을 읽지 못했습니다: {exc}"
        return _image_from_bytes(raw, max_bytes)
    try:
        raw = base64.b64decode(text, validate=True)
    except Exception:
        return {}, ""
    return _image_from_bytes(raw, max_bytes)


def _image_from_bytes(raw: bytes, max_bytes: int) -> tuple[dict[str, Any], str]:
    if len(raw) > max_bytes:
        return {}, f"이미지가 너무 큽니다. 최대 {max_bytes} bytes, 현재 {len(raw)} bytes"
    mime_type = _mime_from_bytes(raw)
    if mime_type not in {"image/png", "image/jpeg", "image/webp"}:
        return {}, "PNG/JPEG/WebP 이미지만 업로드할 수 있습니다."
    width, height = _image_size(raw, mime_type)
    data_uri = f"data:{mime_type};base64,{base64.b64encode(raw).decode('ascii')}"
    return {"data_uri": data_uri, "mime_type": mime_type, "size_bytes": len(raw), "width": width, "height": height}, ""


def _mime_from_bytes(raw: bytes) -> str:
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if raw.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "image/webp"
    return ""


def _image_size(raw: bytes, mime_type: str) -> tuple[int, int]:
    if mime_type == "image/png" and len(raw) >= 24:
        return int.from_bytes(raw[16:20], "big"), int.from_bytes(raw[20:24], "big")
    if mime_type == "image/jpeg":
        index = 2
        while index + 9 < len(raw):
            if raw[index] != 0xFF:
                index += 1
                continue
            marker = raw[index + 1]
            length = int.from_bytes(raw[index + 2 : index + 4], "big")
            if marker in {0xC0, 0xC2} and index + 8 < len(raw):
                return int.from_bytes(raw[index + 7 : index + 9], "big"), int.from_bytes(raw[index + 5 : index + 7], "big")
            index += max(2, length + 2)
    return 0, 0


def _payload(value: Any) -> dict[str, Any]:
    data = getattr(value, "data", value)
    return deepcopy(data) if isinstance(data, dict) else {}


def _merge_trace(trace_value: Any, warnings: list[str], errors: list[str]) -> dict[str, Any]:
    trace = _dict(trace_value)
    trace["warnings"] = _dedupe([*_list(trace.get("warnings")), *warnings])
    trace["errors"] = _dedupe([*_list(trace.get("errors")), *errors])
    return trace


def _parse_size(value: Any, default: int) -> int:
    text = _clean(value).lower().replace(" ", "")
    match = re.match(r"^(\d+)(kb|mb)?$", text)
    if not match:
        return default
    number = int(match.group(1))
    unit = match.group(2)
    if unit == "kb":
        return number * 1024
    if unit == "mb":
        return number * 1024 * 1024
    return number


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        return default
    return max(0, parsed)


def _safe_token(value: Any, allowed: set[str], default: str) -> str:
    text = _clean(value).lower()
    return text if text in allowed else default


def _safe_color(value: Any, default: str) -> str:
    text = _clean(value)
    if len(text) == 7 and text.startswith("#") and all(ch in "0123456789abcdefABCDEF" for ch in text[1:]):
        return text
    return default


def _dict(value: Any) -> dict[str, Any]:
    return deepcopy(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return deepcopy(value) if isinstance(value, list) else []


def _dedupe(items: list[Any]) -> list[str]:
    result = []
    for item in items:
        text = _clean(item)
        if text and text not in result:
            result.append(text)
    return result


def _clean(value: Any) -> str:
    return str(value or "").strip()


class PageImageOverrideBuilder(Component):
    display_name = "11 페이지 이미지 대체 업로드"
    description = "Langflow 업로드 이미지/File 출력을 특정 카드뉴스 페이지의 이미지 전용 화면으로 등록합니다."
    icon = "ImageUp"
    inputs = [
        DataInput(
            name="payload",
            display_name="카드뉴스 요청 payload",
            input_types=["Data", "JSON", "StructuredContent", "Structured Content"],
            required=True,
        ),
        DataInput(
            name="uploaded_image",
            display_name="업로드 이미지/File 출력",
            input_types=["Data", "Message", "File", "Text", "JSON", "StructuredContent", "Structured Content"],
            required=False,
        ),
        MessageTextInput(name="image_path", display_name="서버 이미지 경로", value="", required=False, advanced=True),
        MessageTextInput(name="direct_data_uri", display_name="이미지 data URI", value="", required=False, advanced=True),
        MessageTextInput(name="page", display_name="대체할 페이지 번호", value="3", required=False),
        MessageTextInput(name="slide_id", display_name="대체할 slide_id", value="", required=False, advanced=True),
        MessageTextInput(name="alt", display_name="대체 텍스트", value="", required=False),
        MessageTextInput(name="fit", display_name="이미지 맞춤", value="contain", required=False),
        MessageTextInput(name="background_color", display_name="배경색", value="#FFFDF7", required=False, advanced=True),
        MessageTextInput(name="max_image_bytes", display_name="이미지 최대 크기", value=str(DEFAULT_MAX_IMAGE_BYTES), required=False, advanced=True),
    ]
    outputs = [Output(name="payload_out", display_name="이미지 대체 payload", method="build_payload", types=["Data"])]

    def build_payload(self) -> Data:
        result = add_page_image_override(
            getattr(self, "payload", None),
            getattr(self, "uploaded_image", None),
            getattr(self, "image_path", ""),
            getattr(self, "direct_data_uri", ""),
            getattr(self, "page", "3"),
            getattr(self, "slide_id", ""),
            getattr(self, "alt", ""),
            getattr(self, "fit", "contain"),
            getattr(self, "background_color", "#FFFDF7"),
            getattr(self, "max_image_bytes", str(DEFAULT_MAX_IMAGE_BYTES)),
        )
        upload = _dict(result.get("page_image_override_upload"))
        self.status = {
            "status": upload.get("status"),
            "page": upload.get("page"),
            "slide_id": upload.get("slide_id"),
            "size_bytes": upload.get("size_bytes"),
            "errors": len(_list(upload.get("errors"))),
        }
        return Data(data=result)
