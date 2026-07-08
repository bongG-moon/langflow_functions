from __future__ import annotations

"""01-1 꾸미기/캐릭터 이미지 업로드 노드.

STANDALONE 컴포넌트로 동작하도록 필요한 캐릭터 asset 생성 로직을
이 파일 안에 모두 포함합니다. 같은 폴더의 다른 .py 파일을 import하지 않습니다.
"""

import base64
import json
import mimetypes
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, FileInput, Output
from lfx.schema.data import Data


ALLOWED_IMAGE_PREFIXES = ("data:image/png;base64,", "data:image/jpeg;base64,", "data:image/webp;base64,")
DEFAULT_MAX_IMAGE_BYTES = 5 * 1024 * 1024
DEFAULT_CHARACTER_MANIFEST_PATHS = (
    "card_news_ver2/assets/generated_characters/generated_character_assets.local.json",
    "card_news_flow/assets/generated_characters/generated_character_assets.local.json",
)


def attach_decorative_assets(payload_value: Any, decorative_image_files: Any) -> dict[str, Any]:
    """꾸미기용 캐릭터/이미지 소스를 캐릭터 manifest 형태로 payload에 붙입니다."""

    payload = _ensure_flow_payload(_payload(payload_value))
    manifest, manifest_warnings = _base_character_manifest(payload)
    uploaded_assets, upload_warnings = _collect_uploaded_decorative_assets(decorative_image_files)

    result_manifest = deepcopy(manifest)
    registered_ids: list[str] = []
    for asset in uploaded_assets:
        result_manifest = _upsert_character_asset(result_manifest, asset)
        _prepend_character_role_defaults(result_manifest, asset)
        registered_ids.append(asset["asset_id"])

    warnings = [*manifest_warnings, *upload_warnings]
    result = deepcopy(payload)
    result["character_assets"] = result_manifest
    result["trace"] = _merge_trace(result.get("trace"), warnings, [])
    result["decorative_asset_summary"] = {
        "default_character_asset_count": len(_list(manifest.get("assets"))),
        "uploaded_decorative_asset_count": len(registered_ids),
        "uploaded_decorative_asset_ids": registered_ids,
        "total_character_asset_count": len(_list(result_manifest.get("assets"))),
        "warnings": warnings,
    }
    return result


def _collect_uploaded_decorative_assets(decorative_image_files: Any) -> tuple[list[dict[str, Any]], list[str]]:
    """업로드 파일을 꾸미기/캐릭터 asset 목록으로 변환합니다."""

    raw_images, warnings = _collect_uploaded_images(decorative_image_files)
    assets: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, image in enumerate(raw_images, start=1):
        asset = _decorative_asset_from_image(image, index)
        asset_id = _clean(asset.get("asset_id"))
        if not asset_id or asset_id in seen_ids:
            continue
        if not _valid_data_uri(_clean(asset.get("data_uri"))):
            warnings.append(f"꾸미기 이미지 #{index}를 base64 asset으로 만들지 못했습니다.")
            continue
        seen_ids.add(asset_id)
        assets.append(asset)
    return assets, warnings


def _collect_uploaded_images(files_value: Any) -> tuple[list[dict[str, Any]], list[str]]:
    """Langflow FileInput 값 하나 또는 여러 개를 이미지 dict 목록으로 바꿉니다."""

    warnings: list[str] = []
    images: list[dict[str, Any]] = []
    for candidate in _candidate_values(files_value):
        image, warning = _image_from_candidate(candidate, DEFAULT_MAX_IMAGE_BYTES)
        if warning:
            warnings.append(warning)
        if image:
            images.append(image)
    return images, warnings


def _image_from_candidate(candidate: Any, max_bytes: int) -> tuple[dict[str, Any], str]:
    """파일 객체, 경로, bytes, data URI 중 하나를 이미지 dict로 바꿉니다."""

    if candidate in (None, ""):
        return {}, ""
    if isinstance(candidate, dict):
        data_uri = _clean(candidate.get("data_uri") or candidate.get("src"))
        if _valid_data_uri(data_uri):
            try:
                _, encoded = data_uri.split(",", 1)
                raw = base64.b64decode(encoded, validate=True)
            except Exception:
                return {}, "data URI base64를 디코딩하지 못했습니다."
            filename = _clean(candidate.get("filename") or candidate.get("name"))
            image, warning = _image_from_bytes(raw, filename, max_bytes)
            if image:
                image["data_uri"] = data_uri
                image["source"] = "data_uri"
            return image, warning

    raw, filename, read_warning = _read_image_bytes(candidate)
    if read_warning:
        return {}, read_warning
    if raw is not None:
        return _image_from_bytes(raw, filename, max_bytes)

    text = _clean(candidate)
    if not text:
        return {}, ""
    if _valid_data_uri(text):
        try:
            _, encoded = text.split(",", 1)
            raw = base64.b64decode(encoded, validate=True)
        except Exception:
            return {}, "data URI base64를 디코딩하지 못했습니다."
        image, warning = _image_from_bytes(raw, "", max_bytes)
        if image:
            image["data_uri"] = text
            image["source"] = "data_uri"
        return image, warning

    path = Path(text)
    if path.is_file():
        return _image_from_path(path, max_bytes)
    return {}, ""


def _read_image_bytes(candidate: Any) -> tuple[bytes | None, str, str]:
    """Langflow FileInput이 넘기는 다양한 객체 형태에서 bytes와 파일명을 꺼냅니다."""

    if isinstance(candidate, bytes):
        return candidate, "", ""
    if isinstance(candidate, bytearray):
        return bytes(candidate), "", ""
    if isinstance(candidate, Path):
        try:
            return candidate.read_bytes(), candidate.name, ""
        except Exception as exc:
            return None, "", f"이미지 파일을 읽지 못했습니다: {exc}"
    if isinstance(candidate, dict):
        filename = _clean(candidate.get("filename") or candidate.get("name") or candidate.get("path") or candidate.get("file_path"))
        for key in ("bytes", "content", "data"):
            raw = candidate.get(key)
            if isinstance(raw, str):
                raw = raw.encode("utf-8")
            if isinstance(raw, (bytes, bytearray)):
                return bytes(raw), Path(filename).name if filename else "", ""
        for key in ("path", "file_path", "filepath"):
            path_text = _clean(candidate.get(key))
            if path_text and Path(path_text).is_file():
                try:
                    return Path(path_text).read_bytes(), Path(path_text).name, ""
                except Exception as exc:
                    return None, "", f"이미지 파일을 읽지 못했습니다: {exc}"
        return None, filename, ""
    read = getattr(candidate, "read", None)
    if callable(read):
        try:
            raw = read()
        except Exception as exc:
            return None, "", f"업로드 이미지 파일을 읽지 못했습니다: {exc}"
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        if not isinstance(raw, (bytes, bytearray)):
            return None, "", "업로드 파일이 bytes를 반환하지 않았습니다."
        filename = _clean(getattr(candidate, "name", "")) or _clean(getattr(candidate, "filename", ""))
        return bytes(raw), Path(filename).name if filename else "", ""
    return None, "", ""


def _image_from_path(path: Path, max_bytes: int) -> tuple[dict[str, Any], str]:
    try:
        raw = path.read_bytes()
    except Exception as exc:
        return {}, f"이미지 파일을 읽지 못했습니다: {exc}"
    return _image_from_bytes(raw, path.name, max_bytes)


def _image_from_bytes(raw: bytes, filename: str, max_bytes: int) -> tuple[dict[str, Any], str]:
    if len(raw) > max_bytes:
        return {}, f"이미지가 너무 큽니다. 최대 {max_bytes} bytes, 현재 {len(raw)} bytes"
    mime_type = _mime_from_bytes(raw) or mimetypes.guess_type(filename)[0] or ""
    if mime_type not in {"image/png", "image/jpeg", "image/webp"}:
        return {}, "PNG/JPEG/WebP 이미지만 사용할 수 있습니다."
    width, height = _image_size(raw, mime_type)
    return {
        "filename": filename,
        "mime_type": mime_type,
        "data_uri": f"data:{mime_type};base64,{base64.b64encode(raw).decode('ascii')}",
        "width": width,
        "height": height,
        "size_bytes": len(raw),
    }, ""


def _base_character_manifest(payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """기존 manifest가 없으면 기본 생성 캐릭터 manifest 후보를 읽습니다."""

    existing = _dict(payload.get("character_assets"))
    if _list(existing.get("assets")):
        existing.setdefault("slide_role_defaults", {})
        return existing, []

    warnings: list[str] = []
    manifest: dict[str, Any] = {}
    for path in _manifest_path_candidates():
        if not path.is_file():
            continue
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
            break
        except Exception as exc:
            warnings.append(f"기본 캐릭터 manifest를 읽지 못했습니다: {exc}")
    if not manifest:
        warnings.append("기본 캐릭터 manifest 파일을 찾지 못했습니다.")

    manifest = _dict(manifest)
    manifest.setdefault("asset_family", "card_news_ver2_character_assets")
    manifest.setdefault("slide_role_defaults", {})
    manifest.setdefault("assets", [])
    manifest["assets"] = [
        deepcopy(asset)
        for asset in _list(manifest.get("assets"))
        if isinstance(asset, dict) and _clean(asset.get("asset_id")) and _valid_data_uri(_clean(asset.get("data_uri")))
    ]
    return manifest, warnings


def _manifest_path_candidates() -> list[Path]:
    paths: list[Path] = []
    cwd = Path.cwd()
    for text in DEFAULT_CHARACTER_MANIFEST_PATHS:
        paths.append(cwd / text)
    file_path = globals().get("__file__")
    if file_path:
        current = Path(file_path).resolve()
        for parent in current.parents:
            for text in DEFAULT_CHARACTER_MANIFEST_PATHS:
                paths.append(parent / text)
    for parent in cwd.parents:
        for text in DEFAULT_CHARACTER_MANIFEST_PATHS:
            paths.append(parent / text)

    result: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path)
        if key not in seen:
            seen.add(key)
            result.append(path)
    return result


def _decorative_asset_from_image(image: dict[str, Any], index: int) -> dict[str, Any]:
    """업로드 이미지를 02 planner가 고를 수 있는 캐릭터 asset 스키마로 변환합니다."""

    filename = _clean(image.get("filename"))
    asset_id = _safe_id(filename or f"decorative_asset_{index}") or f"decorative_asset_{index}"
    metadata = _infer_decorative_metadata(asset_id, filename)
    return {
        "asset_id": asset_id,
        "character_key": "uploaded_decorative",
        "display_name": _display_name_from_asset_id(asset_id),
        "pose": asset_id,
        "ai_context": metadata["ai_context"],
        "recommended_slide_roles": metadata["recommended_slide_roles"],
        "recommended_layouts": metadata["recommended_layouts"],
        "placement_hints": metadata["placement_hints"],
        "animation_hints": metadata["animation_hints"],
        "mime_type": _clean(image.get("mime_type")) or _mime_from_data_uri(_clean(image.get("data_uri"))),
        "data_uri": _clean(image.get("data_uri")),
        "alt": _display_name_from_asset_id(asset_id),
        "width": int(image.get("width") or 0),
        "height": int(image.get("height") or 0),
        "source": "decorative_upload",
        "filename": filename,
    }


def _infer_decorative_metadata(asset_id: str, filename: str) -> dict[str, Any]:
    """파일명 키워드로 어느 페이지 역할에 어울리는 꾸미기 소스인지 추정합니다."""

    text = " ".join([asset_id, filename]).lower()
    metadata = {
        "ai_context": "general_helper",
        "recommended_slide_roles": ["cover", "why", "case", "tip", "checklist", "closing"],
        "recommended_layouts": ["cover", "text_focus", "image_side", "checklist", "closing"],
        "placement_hints": ["bottom_right", "bottom_left"],
        "animation_hints": ["float_in", "fade_up"],
    }
    if any(token in text for token in ("security", "shield", "privacy", "secret", "safe", "보안", "개인정보", "기밀", "주의")):
        metadata.update(
            {
                "ai_context": "security_notice",
                "recommended_slide_roles": ["security", "caution", "tip"],
                "recommended_layouts": ["notice", "text_focus", "image_side"],
                "placement_hints": ["bottom_left", "bottom_right"],
            }
        )
    elif any(token in text for token in ("tip", "prompt", "guide", "helper", "프롬프트", "팁", "가이드", "도움")):
        metadata.update(
            {
                "ai_context": "ai_helper",
                "recommended_slide_roles": ["tip", "checklist", "case", "workflow"],
                "recommended_layouts": ["checklist", "text_focus", "image_side"],
            }
        )
    elif any(token in text for token in ("cta", "closing", "apply", "point", "마무리", "신청", "문의", "다음")):
        metadata.update(
            {
                "ai_context": "cta_closing",
                "recommended_slide_roles": ["closing", "cta", "recap"],
                "recommended_layouts": ["closing", "text_focus"],
                "placement_hints": ["bottom_right", "center"],
                "animation_hints": ["pulse_soft", "float_in"],
            }
        )
    elif any(token in text for token in ("cover", "intro", "welcome", "hello", "표지", "인사", "소개")):
        metadata.update(
            {
                "ai_context": "cover_intro",
                "recommended_slide_roles": ["cover", "intro", "why", "closing"],
                "recommended_layouts": ["cover", "text_focus", "closing"],
                "placement_hints": ["bottom_right", "center"],
            }
        )
    return metadata


def _prepend_character_role_defaults(manifest: dict[str, Any], asset: dict[str, Any]) -> None:
    """업로드 소스가 관련 role에서 우선 선택되도록 기본값 앞에 넣습니다."""

    defaults = _dict(manifest.get("slide_role_defaults"))
    for role in _strings(asset.get("recommended_slide_roles")):
        existing = [item for item in _strings(defaults.get(role)) if item != asset["asset_id"]]
        defaults[role] = [asset["asset_id"], *existing]
    manifest["slide_role_defaults"] = defaults


def _upsert_character_asset(manifest: dict[str, Any], asset: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(manifest)
    assets = [item for item in _list(result.get("assets")) if _clean(_dict(item).get("asset_id")) != asset["asset_id"]]
    assets.append(asset)
    result["assets"] = assets
    return result


def _candidate_values(value: Any) -> list[Any]:
    """Langflow FileInput/Data/list/dict 입력을 후보 파일 값 목록으로 펼칩니다."""

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
        if any(key in value for key in ("bytes", "content", "data", "data_uri", "src")):
            return [value]
        if any(key in value for key in ("path", "file_path", "filepath")) and any(key in value for key in ("filename", "name")):
            return [value]
        result: list[Any] = []
        for key in ("files", "file", "images", "image", "path", "file_path", "filepath", "data_uri", "value", "content", "data"):
            if key in value:
                result.extend(_candidate_values(value[key]))
        return result or [value]
    for attr in ("files", "file", "path", "file_path", "filepath", "location", "content", "text", "value"):
        nested = getattr(value, attr, None)
        if nested is not None and nested is not value:
            candidates = _candidate_values(nested)
            if candidates:
                return candidates
    return [value]


def _ensure_flow_payload(value: dict[str, Any]) -> dict[str, Any]:
    """00을 건너뛰고 00-2의 deck_request가 바로 들어와도 flow payload로 감쌉니다."""

    payload = deepcopy(value) if isinstance(value, dict) else {}
    if isinstance(payload.get("deck_request"), dict):
        payload.setdefault("payload_version", "card-news-ver2")
        payload.setdefault("flow_type", "card_news_ver2")
        payload.setdefault("image_assets", {"assets": []})
        payload.setdefault("image_placements", [])
        payload.setdefault("character_assets", {})
        payload.setdefault("card_news_plan", {})
        payload.setdefault("html_result", {})
        payload.setdefault("trace", {"warnings": [], "errors": []})
        return payload
    if _looks_like_deck_request(payload):
        return {
            "payload_version": "card-news-ver2",
            "flow_type": "card_news_ver2",
            "request_id": "card_news_v2_from_structured_input",
            "deck_request": payload,
            "image_assets": {"assets": []},
            "image_placements": [],
            "character_assets": {},
            "card_news_plan": {},
            "html_result": {},
            "trace": {"warnings": [], "errors": []},
        }
    return payload


def _looks_like_deck_request(value: dict[str, Any]) -> bool:
    if not isinstance(value, dict):
        return False
    request_keys = {
        "series_title",
        "issue_label",
        "issue_no",
        "cover",
        "pages",
        "closing",
        "requested_page_count",
        "image_placement_instruction",
    }
    return bool(request_keys.intersection(value.keys()))


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


def _display_name_from_asset_id(asset_id: str) -> str:
    return (asset_id or "uploaded_decorative").replace("_", " ").strip()


def _safe_ref(value: Any) -> str:
    text = _clean(value).lower().replace("\\", "/").split("/")[-1]
    text = re.sub(r"\.[a-z0-9]{2,5}$", "", text)
    return re.sub(r"[^a-z0-9가-힣 _-]+", "", text).replace(" ", "_").strip("_-")


def _safe_id(value: Any) -> str:
    text = _safe_ref(value)
    text = re.sub(r"[^a-z0-9_]+", "_", text).strip("_")
    return text[:80]


def _valid_data_uri(value: str) -> bool:
    return bool(value) and value.startswith(ALLOWED_IMAGE_PREFIXES) and "PUT_BASE64" not in value


def _mime_from_data_uri(value: str) -> str:
    match = re.match(r"^data:([^;]+);base64,", value)
    return match.group(1) if match else ""


def _merge_trace(trace_value: Any, warnings: list[str], errors: list[str]) -> dict[str, Any]:
    trace = _dict(trace_value)
    trace["warnings"] = _dedupe([*_list(trace.get("warnings")), *warnings])
    trace["errors"] = _dedupe([*_list(trace.get("errors")), *errors])
    return trace


def _payload(value: Any) -> dict[str, Any]:
    data = getattr(value, "data", value)
    value = data if data is not None else value
    return deepcopy(value) if isinstance(value, dict) else {}


def _dict(value: Any) -> dict[str, Any]:
    return deepcopy(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return deepcopy(value) if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    raw_items = value if isinstance(value, list) else ([value] if value not in (None, "") else [])
    return _dedupe(_clean(item) for item in raw_items)


def _dedupe(items: Any) -> list[str]:
    result: list[str] = []
    for item in items:
        text = _clean(item)
        if text and text not in result:
            result.append(text)
    return result


def _clean(value: Any) -> str:
    return str(value or "").strip()


class DecorativeAssetUploadBuilder(Component):
    """꾸미기용 이미지/캐릭터 파일을 업로드받아 캐릭터 asset manifest를 만드는 Langflow 노드입니다."""

    display_name = "01-1 꾸미기/캐릭터 이미지 업로드"
    description = "꾸미기용 캐릭터나 이미지 소스를 업로드하면 base64로 변환하고, 파일명 키워드로 어울리는 페이지 역할을 자동 추정합니다."
    icon = "Sparkles"
    name = "DecorativeAssetUploadBuilder"

    inputs = [
        DataInput(name="payload", display_name="내용 이미지 포함 payload", required=True),
        FileInput(
            name="decorative_image_files",
            display_name="꾸미기/캐릭터 이미지 파일 업로드",
            info="PNG/JPEG/WebP 파일을 업로드하세요. 파일명에 cover, tip, security, closing 같은 키워드가 있으면 역할을 자동 추정합니다.",
            file_types=["png", "jpg", "jpeg", "webp"],
            # 여러 꾸미기/캐릭터 이미지를 한 번에 업로드할 수 있도록 리스트 모드로 둡니다.
            list=True,
            value=[],
            required=False,
        ),
    ]
    outputs = [Output(name="payload_out", display_name="꾸미기 asset 포함 payload", method="build_payload", types=["Data"])]

    def build_payload(self) -> Data:
        result = attach_decorative_assets(
            getattr(self, "payload", None),
            getattr(self, "decorative_image_files", None),
        )
        summary = result.get("decorative_asset_summary", {})
        self.status = {
            "기본 캐릭터 수": summary.get("default_character_asset_count", 0),
            "업로드 꾸미기 수": summary.get("uploaded_decorative_asset_count", 0),
            "전체 캐릭터 asset 수": summary.get("total_character_asset_count", 0),
            "경고 수": len(summary.get("warnings", [])),
        }
        return Data(data=result)
