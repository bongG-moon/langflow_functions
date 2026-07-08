from __future__ import annotations

"""01 내용 이미지 업로드 노드.

STANDALONE 컴포넌트로 동작하도록 필요한 이미지 변환/배치 로직을
이 파일 안에 모두 포함합니다. 같은 폴더의 다른 .py 파일을 import하지 않습니다.
"""

import base64
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


def attach_content_images(payload_value: Any, content_image_files: Any) -> dict[str, Any]:
    """내용 이미지를 base64 data URI로 바꾸고 페이지 배치를 자동 계산합니다."""

    payload = _ensure_flow_payload(_payload(payload_value))
    request = _dict(payload.get("deck_request"))
    image_assets, image_warnings = _collect_uploaded_page_images(content_image_files)
    placement_text = _clean_preserve(request.get("image_placement_instruction"))
    placements, placement_warnings = _build_image_placements(image_assets, request, placement_text)

    result = deepcopy(payload)
    result["image_assets"] = {"assets": image_assets}
    result["image_placements"] = placements
    result["trace"] = _merge_trace(result.get("trace"), [*image_warnings, *placement_warnings], [])
    result["image_bundle_summary"] = {
        "image_count": len(image_assets),
        "placement_count": len(placements),
        "warnings": [*image_warnings, *placement_warnings],
    }
    return result


def _collect_uploaded_page_images(content_image_files: Any) -> tuple[list[dict[str, Any]], list[str]]:
    """업로드 파일을 내용 이미지 asset 목록으로 변환합니다."""

    raw_images, warnings = _collect_uploaded_images(content_image_files)
    assets: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for index, image in enumerate(raw_images, start=1):
        data_uri = _clean(image.get("data_uri"))
        filename = _clean(image.get("filename"))
        seen_key = "|".join([filename, data_uri])
        if not data_uri or seen_key in seen_keys:
            continue
        seen_keys.add(seen_key)
        image_ref = _safe_ref(filename or f"img{index}")
        image_id = _safe_id(image_ref or f"img{index}") or f"img{index}"
        assets.append(
            {
                "image_id": image_id,
                "image_ref": image_ref or image_id,
                "filename": filename,
                "data_uri": data_uri,
                "mime_type": _clean(image.get("mime_type")) or _mime_from_data_uri(data_uri),
                "width": int(image.get("width") or 0),
                "height": int(image.get("height") or 0),
                "size_bytes": int(image.get("size_bytes") or 0),
                "page_hint": _page_from_filename(filename),
                "source": "content_upload",
                "alt": _alt_from_filename(filename, image_id),
            }
        )
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


def _build_image_placements(
    assets: list[dict[str, Any]],
    request: dict[str, Any],
    placement_text: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    """자연어 지시, 파일명, 페이지 image_ref 순서로 내용 이미지 배치를 정합니다."""

    warnings: list[str] = []
    placements = _placements_from_numbers(assets, placement_text)

    for asset in assets:
        if _has_image_placement(placements, asset["image_id"]):
            continue
        page_hint = _positive_int(asset.get("page_hint"), 0)
        if page_hint:
            placements = _upsert_placement(placements, _placement(asset["image_id"], page_hint, asset.get("alt")))

    image_ref_map = _image_ref_map(assets)
    for page in _list(request.get("pages")):
        if not isinstance(page, dict):
            continue
        page_no = _positive_int(page.get("page"), 0)
        for ref in _strings(page.get("image_refs")):
            image_id = image_ref_map.get(_safe_ref(ref))
            if page_no and image_id and not _has_image_placement(placements, image_id):
                placements = _upsert_placement(placements, _placement(image_id, page_no, ref))

    placements = _auto_place_remaining_images(placements, assets, request)
    valid_ids = {asset["image_id"] for asset in assets}
    placements = [item for item in placements if item.get("image_id") in valid_ids and _positive_int(item.get("page"), 0)]
    if assets and not placements:
        warnings.append("이미지가 업로드되었지만 배치할 페이지를 찾지 못했습니다.")
    return placements, warnings


def _placements_from_numbers(assets: list[dict[str, Any]], text: str) -> list[dict[str, Any]]:
    """'이미지 4개를 각각 1, 3, 4, 5페이지' 같은 자연어 지시를 처리합니다."""

    if not assets or not text:
        return []
    numbers = [int(item) for item in re.findall(r"\d{1,2}", text)]
    if len(numbers) < len(assets):
        return []
    page_numbers = numbers[-len(assets) :]
    return [_placement(asset["image_id"], page_numbers[index], asset.get("alt")) for index, asset in enumerate(assets)]


def _auto_place_remaining_images(
    placements: list[dict[str, Any]],
    assets: list[dict[str, Any]],
    request: dict[str, Any],
) -> list[dict[str, Any]]:
    """아직 배치되지 않은 이미지는 중간 페이지부터 순서대로 넣습니다."""

    total = max(_positive_int(request.get("requested_page_count"), 0), 3)
    candidate_pages = list(range(2, total)) or [1]
    used_pages = {_positive_int(item.get("page"), 0) for item in placements}
    page_cursor = 0
    result = list(placements)
    for asset in assets:
        if _has_image_placement(result, asset["image_id"]):
            continue
        while page_cursor < len(candidate_pages) and candidate_pages[page_cursor] in used_pages:
            page_cursor += 1
        page = candidate_pages[page_cursor] if page_cursor < len(candidate_pages) else min(total, len(result) + 1)
        used_pages.add(page)
        result = _upsert_placement(result, _placement(asset["image_id"], page, asset.get("alt")))
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


def _placement(image_id: str, page: int, alt: Any) -> dict[str, Any]:
    return {
        "image_id": image_id,
        "page": page,
        "mode": "",
        "fit": "contain",
        "alt": _clean(alt),
    }


def _image_ref_map(assets: list[dict[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for asset in assets:
        image_id = asset["image_id"]
        refs = [asset.get("image_id"), asset.get("image_ref"), asset.get("filename"), Path(_clean(asset.get("filename"))).stem]
        for ref in refs:
            safe = _safe_ref(ref)
            if safe:
                result[safe] = image_id
    return result


def _upsert_placement(items: list[dict[str, Any]], placement: dict[str, Any]) -> list[dict[str, Any]]:
    image_id = _clean(placement.get("image_id"))
    result = [item for item in items if _clean(item.get("image_id")) != image_id]
    result.append(placement)
    return result


def _has_image_placement(items: list[dict[str, Any]], image_id: str) -> bool:
    return any(_clean(item.get("image_id")) == image_id for item in items)


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


def _page_from_filename(filename: Any) -> int:
    name = _clean(filename).replace("\\", "/").split("/")[-1].lower()
    patterns = [
        r"(?:page|p|slide|card|screen|페이지|화면|카드)[-_ ]?(\d{1,2})",
        r"(\d{1,2})[-_ ]?(?:page|p|slide|card|screen|페이지|화면|카드)",
        r"^(\d{1,2})[-_ ]",
    ]
    for pattern in patterns:
        match = re.search(pattern, name)
        if match:
            return _positive_int(match.group(1), 0)
    return 0


def _alt_from_filename(filename: str, image_id: str) -> str:
    stem = Path(filename).stem if filename else image_id
    return stem.replace("_", " ").replace("-", " ").strip() or "카드뉴스 이미지"


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


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        return default
    return max(0, parsed)


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _clean_preserve(value: Any) -> str:
    text = str(value or "").strip()
    return re.sub(r"\n{3,}", "\n\n", text)


class ContentImageUploadBuilder(Component):
    """내용 이미지 파일을 업로드받아 페이지별 이미지 payload를 만드는 Langflow 노드입니다."""

    display_name = "01 내용 이미지 업로드/자동 배치"
    description = "내용에 들어갈 이미지 파일만 업로드하면 base64로 변환하고, 페이지 지시에 맞춰 자동 배치합니다."
    icon = "Images"
    name = "ContentImageUploadBuilder"

    inputs = [
        DataInput(name="payload", display_name="카드뉴스 요청 payload", required=True),
        FileInput(
            name="content_image_files",
            display_name="내용 이미지 파일 업로드",
            info="PNG/JPEG/WebP 파일을 업로드하세요. 여러 파일이 들어오면 파일명, LLM 이미지 배치 지시, image_ref를 기준으로 자동 배치합니다.",
            file_types=["png", "jpg", "jpeg", "webp"],
            # 여러 이미지를 한 번에 업로드할 수 있도록 Langflow 입력을 리스트 모드로 둡니다.
            list=True,
            value=[],
            required=False,
        ),
    ]
    outputs = [Output(name="payload_out", display_name="내용 이미지 포함 payload", method="build_payload", types=["Data"])]

    def build_payload(self) -> Data:
        result = attach_content_images(
            getattr(self, "payload", None),
            getattr(self, "content_image_files", None),
        )
        summary = result.get("image_bundle_summary", {})
        self.status = {
            "내용 이미지 수": summary.get("image_count", 0),
            "이미지 배치 수": summary.get("placement_count", 0),
            "경고 수": len(summary.get("warnings", [])),
        }
        return Data(data=result)
