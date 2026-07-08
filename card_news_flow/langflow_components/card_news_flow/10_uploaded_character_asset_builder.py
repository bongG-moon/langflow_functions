from __future__ import annotations

"""10 업로드 캐릭터 이미지 자산 등록 노드.

Langflow 서버에 업로드된 이미지 또는 data URI를 character asset manifest로 변환합니다.
로컬 PC 경로를 HTML에 남기지 않고, renderer가 사용할 base64 data URI를 payload에 저장합니다.
"""

import base64
import hashlib
import json
import mimetypes
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, FileInput, MessageTextInput, Output
from lfx.schema.data import Data


ALLOWED_IMAGE_PREFIXES = ("data:image/png;base64,", "data:image/jpeg;base64,", "data:image/webp;base64,")
DEFAULT_MAX_IMAGE_BYTES = 2 * 1024 * 1024


def build_uploaded_character_asset_payload(
    payload_value: Any = None,
    uploaded_image: Any = None,
    image_file: Any = None,
    image_path: Any = "",
    direct_data_uri: Any = "",
    existing_manifest_json: Any = "",
    asset_id: Any = "",
    character_key: Any = "hayangi",
    display_name: Any = "",
    pose: Any = "",
    ai_context: Any = "cover_intro",
    recommended_slide_roles: Any = "cover,intro",
    recommended_layouts: Any = "cover_character,character_speech",
    placement_hints: Any = "bottom_right,center",
    animation_hints: Any = "float_in,fade_up",
    alt: Any = "",
    approval_status: Any = "approved",
    max_image_bytes: Any = DEFAULT_MAX_IMAGE_BYTES,
) -> dict[str, Any]:
    """업로드 이미지 1개를 manifest asset으로 등록합니다."""

    payload = _payload(payload_value)
    max_bytes = _parse_size(max_image_bytes, DEFAULT_MAX_IMAGE_BYTES)
    image, image_warnings = _extract_image(uploaded_image, image_file, image_path, direct_data_uri, max_bytes)
    warnings = list(image_warnings)
    errors: list[str] = []
    if not image:
        errors.append("업로드 이미지 또는 data URI를 찾지 못했습니다.")

    manifest = _resolve_manifest(payload, existing_manifest_json)
    resolved_asset_id = _safe_asset_id(asset_id) or _safe_asset_id(Path(_clean(image.get("filename"))).stem) or f"uploaded_asset_{_short_hash(image.get('data_uri', _now_seed()))}"
    if image:
        asset = {
            "asset_id": resolved_asset_id,
            "character_key": _safe_token(character_key, {"hayangi", "hadaengi", "duo"}, "hayangi"),
            "display_name": _clean(display_name) or resolved_asset_id,
            "pose": _clean(pose) or resolved_asset_id,
            "ai_context": _clean(ai_context) or "cover_intro",
            "mood_tags": [],
            "recommended_slide_roles": _csv(recommended_slide_roles),
            "recommended_layouts": _csv(recommended_layouts),
            "placement_hints": _csv(placement_hints),
            "animation_hints": _csv(animation_hints),
            "mime_type": image.get("mime_type", "image/png"),
            "data_uri": image.get("data_uri", ""),
            "alt": _clean(alt) or _clean(display_name) or resolved_asset_id,
            "width": image.get("width", 0),
            "height": image.get("height", 0),
            "source": "langflow_upload",
        }
        manifest = _upsert_asset(manifest, asset)
        if not _clean(manifest.get("default_asset_id")):
            manifest["default_asset_id"] = resolved_asset_id
        manifest["approval"] = {
            **_dict(manifest.get("approval")),
            "status": _safe_token(approval_status, {"approved", "pending", "placeholder"}, "approved"),
        }
        _extend_role_defaults(manifest, asset)

    result = deepcopy(payload)
    result["character_assets"] = manifest
    result["uploaded_character_asset"] = {
        "status": "ok" if image and not errors else "error",
        "asset_id": resolved_asset_id,
        "mime_type": image.get("mime_type", ""),
        "size_bytes": image.get("size_bytes", 0),
        "warnings": warnings,
        "errors": errors,
    }
    result["trace"] = _merge_trace(result.get("trace"), warnings, errors)
    return result


def _extract_image(uploaded_image: Any, image_file: Any, image_path: Any, direct_data_uri: Any, max_bytes: int) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    candidates = [_clean(direct_data_uri)]
    candidates.extend(_candidate_values(image_file))
    candidates.append(_clean(image_path))
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
        nested = _candidate_values(data)
        if nested:
            return nested
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
            candidates = _candidate_values(nested)
            if candidates:
                return candidates
    return [value]


def _image_from_candidate(candidate: Any, max_bytes: int) -> tuple[dict[str, Any], str]:
    if not candidate:
        return {}, ""
    raw, filename, read_warning = _read_image_bytes(candidate)
    if read_warning:
        return {}, read_warning
    if raw is not None:
        return _image_from_bytes(raw, filename, max_bytes)
    text = _clean(candidate)
    if not text:
        return {}, ""
    if text.startswith(ALLOWED_IMAGE_PREFIXES):
        try:
            prefix, encoded = text.split(",", 1)
            raw = base64.b64decode(encoded, validate=True)
        except Exception:
            return {}, "data URI base64를 디코딩하지 못했습니다."
        image, warning = _image_from_bytes(raw, "", max_bytes)
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
        image, warning = _image_from_bytes(raw, path.name, max_bytes)
        if image and not image.get("mime_type"):
            image["mime_type"] = mimetypes.guess_type(path.name)[0] or "image/png"
        return image, warning
    try:
        raw = base64.b64decode(text, validate=True)
    except Exception:
        return {}, ""
    return _image_from_bytes(raw, "", max_bytes)


def _read_image_bytes(candidate: Any) -> tuple[bytes | None, str, str]:
    if isinstance(candidate, bytes):
        return candidate, "", ""
    if isinstance(candidate, bytearray):
        return bytes(candidate), "", ""
    if isinstance(candidate, Path):
        try:
            return candidate.read_bytes(), candidate.name, ""
        except Exception as exc:
            return None, "", f"이미지 파일을 읽지 못했습니다: {exc}"
    read = getattr(candidate, "read", None)
    if callable(read):
        try:
            raw = read()
        except Exception as exc:
            return None, "", f"업로드 이미지 파일을 읽지 못했습니다: {exc}"
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        if not isinstance(raw, (bytes, bytearray)):
            return None, "", "업로드 이미지 파일이 bytes를 반환하지 않았습니다."
        filename = _clean(getattr(candidate, "name", "")) or _clean(getattr(candidate, "filename", ""))
        return bytes(raw), Path(filename).name if filename else "", ""
    return None, "", ""


def _image_from_bytes(raw: bytes, filename: str, max_bytes: int) -> tuple[dict[str, Any], str]:
    if len(raw) > max_bytes:
        return {}, f"이미지가 너무 큽니다. 최대 {max_bytes} bytes, 현재 {len(raw)} bytes"
    mime_type = _mime_from_bytes(raw)
    if mime_type not in {"image/png", "image/jpeg", "image/webp"}:
        return {}, "PNG/JPEG/WebP 이미지만 업로드할 수 있습니다."
    width, height = _image_size(raw, mime_type)
    data_uri = f"data:{mime_type};base64,{base64.b64encode(raw).decode('ascii')}"
    return {"data_uri": data_uri, "mime_type": mime_type, "filename": filename, "size_bytes": len(raw), "width": width, "height": height}, ""


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


def _resolve_manifest(payload: dict[str, Any], manifest_json: Any) -> dict[str, Any]:
    parsed = _parse_json_object(manifest_json)
    if parsed:
        return _normalize_manifest(parsed)
    for key in ("character_assets", "character_asset_manifest", "asset_manifest"):
        if isinstance(payload.get(key), dict):
            return _normalize_manifest(payload[key])
    return _normalize_manifest({})


def _normalize_manifest(value: dict[str, Any]) -> dict[str, Any]:
    manifest = deepcopy(value) if isinstance(value, dict) else {}
    manifest.setdefault("asset_family", "sk_hynix_hayangi_hadaengi_ai_pose_pack")
    manifest.setdefault("version", "0.2.0")
    manifest.setdefault("usage_scope", "internal_card_news")
    manifest.setdefault("approval", {"status": "approved"})
    manifest.setdefault("slide_role_defaults", {})
    manifest.setdefault("selection_rules", [])
    manifest.setdefault("assets", [])
    return manifest


def _upsert_asset(manifest: dict[str, Any], asset: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(manifest)
    assets = [item for item in result.get("assets", []) if isinstance(item, dict) and _clean(item.get("asset_id")) != asset["asset_id"]]
    assets.append(asset)
    result["assets"] = assets
    return result


def _extend_role_defaults(manifest: dict[str, Any], asset: dict[str, Any]) -> None:
    defaults = _dict(manifest.get("slide_role_defaults"))
    for role in asset.get("recommended_slide_roles", []):
        items = [item for item in defaults.get(role, []) if item != asset["asset_id"]]
        defaults[role] = [asset["asset_id"], *items]
    manifest["slide_role_defaults"] = defaults


def _payload(value: Any) -> dict[str, Any]:
    data = getattr(value, "data", value)
    return deepcopy(data) if isinstance(data, dict) else {}


def _parse_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return deepcopy(value)
    text = _clean(value)
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:
        return {}
    return deepcopy(parsed) if isinstance(parsed, dict) else {}


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


def _csv(value: Any) -> list[str]:
    result = []
    for item in re.split(r"[\n,]+", _clean(value)):
        text = item.strip()
        if text and text not in result:
            result.append(text)
    return result


def _safe_asset_id(value: Any) -> str:
    text = _clean(value).lower()
    text = re.sub(r"[^a-z0-9_]+", "_", text).strip("_")
    return text[:80]


def _safe_token(value: Any, allowed: set[str], default: str) -> str:
    text = _clean(value).lower()
    return text if text in allowed else default


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


def _short_hash(value: Any) -> str:
    return hashlib.sha1(_clean(value).encode("utf-8")).hexdigest()[:10]


def _now_seed() -> str:
    return hashlib.sha1(b"empty").hexdigest()


def _clean(value: Any) -> str:
    return str(value or "").strip()


class UploadedCharacterAssetBuilder(Component):
    display_name = "10 업로드 캐릭터 이미지 자산 등록"
    description = "Langflow 업로드 이미지/File 출력을 base64 character asset manifest로 변환합니다."
    icon = "ImagePlus"
    inputs = [
        DataInput(
            name="payload",
            display_name="기존 payload",
            input_types=["Data", "JSON", "StructuredContent", "Structured Content"],
            required=False,
        ),
        DataInput(
            name="uploaded_image",
            display_name="Base64 Message/File 출력",
            input_types=["Data", "Message", "File", "Text", "JSON", "StructuredContent", "Structured Content"],
            required=False,
        ),
        FileInput(
            name="image_file",
            display_name="업로드 이미지 파일",
            info="Read File을 거치지 말고 PNG/JPEG/WebP 파일을 여기 직접 업로드하세요.",
            file_types=["png", "jpg", "jpeg", "webp"],
            required=False,
        ),
        MessageTextInput(name="image_path", display_name="서버 이미지 경로", value="", required=False, advanced=True),
        MessageTextInput(name="direct_data_uri", display_name="이미지 data URI", value="", required=False, advanced=True),
        MessageTextInput(name="existing_manifest_json", display_name="기존 manifest JSON", value="", required=False, advanced=True),
        MessageTextInput(name="asset_id", display_name="asset_id", value="hayangi_ai_hello", required=True),
        MessageTextInput(name="character_key", display_name="캐릭터 키", value="hayangi", required=False),
        MessageTextInput(name="display_name", display_name="표시 이름", value="", required=False),
        MessageTextInput(name="pose", display_name="포즈", value="", required=False, advanced=True),
        MessageTextInput(name="ai_context", display_name="AI 맥락", value="cover_intro", required=False, advanced=True),
        MessageTextInput(name="recommended_slide_roles", display_name="권장 slide 역할", value="cover,intro", required=False, advanced=True),
        MessageTextInput(name="recommended_layouts", display_name="권장 layout", value="cover_character,character_speech", required=False, advanced=True),
        MessageTextInput(name="placement_hints", display_name="배치 후보", value="bottom_right,center", required=False, advanced=True),
        MessageTextInput(name="animation_hints", display_name="애니메이션 후보", value="float_in,fade_up", required=False, advanced=True),
        MessageTextInput(name="alt", display_name="대체 텍스트", value="", required=False, advanced=True),
        MessageTextInput(name="approval_status", display_name="승인 상태", value="approved", required=False, advanced=True),
        MessageTextInput(name="max_image_bytes", display_name="이미지 최대 크기", value=str(DEFAULT_MAX_IMAGE_BYTES), required=False, advanced=True),
    ]
    outputs = [Output(name="payload_out", display_name="자산 등록 payload", method="build_payload", types=["Data"])]

    def build_payload(self) -> Data:
        result = build_uploaded_character_asset_payload(
            getattr(self, "payload", None),
            getattr(self, "uploaded_image", None),
            getattr(self, "image_file", None),
            getattr(self, "image_path", ""),
            getattr(self, "direct_data_uri", ""),
            getattr(self, "existing_manifest_json", ""),
            getattr(self, "asset_id", ""),
            getattr(self, "character_key", "hayangi"),
            getattr(self, "display_name", ""),
            getattr(self, "pose", ""),
            getattr(self, "ai_context", "cover_intro"),
            getattr(self, "recommended_slide_roles", "cover,intro"),
            getattr(self, "recommended_layouts", "cover_character,character_speech"),
            getattr(self, "placement_hints", "bottom_right,center"),
            getattr(self, "animation_hints", "float_in,fade_up"),
            getattr(self, "alt", ""),
            getattr(self, "approval_status", "approved"),
            getattr(self, "max_image_bytes", str(DEFAULT_MAX_IMAGE_BYTES)),
        )
        upload = _dict(result.get("uploaded_character_asset"))
        self.status = {
            "status": upload.get("status"),
            "asset_id": upload.get("asset_id"),
            "size_bytes": upload.get("size_bytes"),
            "warnings": len(_list(upload.get("warnings"))),
            "errors": len(_list(upload.get("errors"))),
        }
        return Data(data=result)
