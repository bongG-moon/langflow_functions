from __future__ import annotations

"""05 카드뉴스 공유 링크 출력 노드.

03 단일 HTML 렌더링 결과를 기존 html_report_flow의 Report API 서버에 저장하고,
브라우저에서 바로 볼 수 있는 링크를 메시지로 출력합니다.
"""

import json
import urllib.error
import urllib.request
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, MessageTextInput, Output
from lfx.schema.message import Message


DEFAULT_REPORT_API_URL = "http://127.0.0.1:8010"
DEFAULT_TIMEOUT_SECONDS = 30


def publish_card_news_html(
    payload_value: Any,
    report_api_url: Any = DEFAULT_REPORT_API_URL,
    ttl_hours: Any = "24",
) -> dict[str, Any]:
    """카드뉴스 HTML 결과를 Report API에 저장하고 공유 링크 정보를 payload에 추가합니다."""

    payload = _payload(payload_value)
    if not payload:
        return {"card_news_publish": {"status": "error", "errors": ["empty payload"]}}

    html_result = _dict(payload.get("html_result"))
    plan = _dict(payload.get("card_news_plan"))
    request = _dict(payload.get("deck_request"))
    html = _clean(html_result.get("html"))
    if not html:
        return {**payload, "card_news_publish": {"status": "error", "errors": ["html is empty"]}}

    post_url = _post_url(report_api_url)
    if not post_url:
        return {**payload, "card_news_publish": {"status": "error", "errors": ["report_api_url is empty"]}}

    title = _clean(html_result.get("title") or plan.get("title") or _dict(request.get("cover")).get("title") or "카드뉴스")
    create_request = {
        # html_report_flow/report_api/server.py의 CreateReportRequest와 같은 형식입니다.
        "html": html,
        "title": title,
        "question": _card_news_question(plan, request),
        "view_request": "card_news_ver2",
        "available_datasets": [],
        "report_plan": _compact_card_news_plan(plan),
        "ttl_hours": _positive_int(ttl_hours, 24),
        "filename_hint": _clean(html_result.get("filename_hint") or title or "card_news"),
    }

    try:
        response = _post_json(post_url, create_request, timeout=DEFAULT_TIMEOUT_SECONDS)
    except Exception as exc:
        # 서버가 꺼져 있어도 flow 전체가 죽지 않도록 오류 payload를 반환합니다.
        return {**payload, "card_news_publish": {"status": "error", "errors": [str(exc)], "post_url": post_url}}

    return _compact_published_payload(payload, response)


def build_card_news_link_message(payload_value: Any) -> str:
    """게시 결과 payload를 사용자가 읽기 쉬운 링크 메시지로 바꿉니다."""

    payload = _payload(payload_value)
    publish = _dict(payload.get("card_news_publish"))
    html_result = _dict(payload.get("html_result"))
    title = _clean(html_result.get("title") or publish.get("title") or "카드뉴스")
    view_url = _clean(html_result.get("view_url") or publish.get("view_url"))
    download_url = _clean(html_result.get("download_url") or publish.get("download_url"))
    expires_at = _clean(html_result.get("expires_at") or publish.get("expires_at"))
    if view_url:
        lines = [f"카드뉴스가 공유 서버에 저장되었습니다: {title}", "", f"- 보기 링크: {view_url}"]
        if download_url:
            lines.append(f"- 다운로드 링크: {download_url}")
        if expires_at:
            lines.append(f"- 만료 시간: {_format_expires_at(expires_at)}")
        return "\n".join(lines)
    if publish.get("status") == "error":
        errors = "; ".join(str(item) for item in _list(publish.get("errors"))) or "알 수 없는 오류"
        return f"HTML은 생성했지만 카드뉴스 공유 링크 생성에 실패했습니다: {errors}"
    return "카드뉴스 공유 링크가 아직 없습니다. 03 단일 HTML 결과와 Report API 주소를 확인하세요."


def _compact_published_payload(payload: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    """게시 후에는 링크 확인에 필요한 정보만 남겨 payload를 가볍게 만듭니다."""

    html_result = _dict(payload.get("html_result"))
    plan = _dict(payload.get("card_news_plan"))
    publish = {
        "status": "published",
        "errors": [],
        "report_id": response.get("report_id", ""),
        "title": response.get("title", ""),
        "view_url": response.get("view_url", ""),
        "download_url": response.get("download_url", ""),
        "expires_at": response.get("expires_at", ""),
        "ttl_hours": response.get("ttl_hours", ""),
    }
    return {
        "payload_version": payload.get("payload_version", "card-news-ver2"),
        "flow_type": payload.get("flow_type", "card_news_ver2"),
        "deck_request": _compact_request(_dict(payload.get("deck_request"))),
        "card_news_plan": _compact_card_news_plan(plan),
        "html_result": {
            "status": html_result.get("status", "ok"),
            "title": html_result.get("title") or publish.get("title"),
            "filename_hint": html_result.get("filename_hint", ""),
            "page_count": html_result.get("page_count") or plan.get("page_count"),
            "view_url": publish["view_url"],
            "download_url": publish["download_url"],
            "expires_at": publish["expires_at"],
        },
        "card_news_publish": publish,
        "trace": _dict(payload.get("trace")),
    }


def _compact_card_news_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """메타데이터에는 base64 data URI를 제외한 카드뉴스 계획만 저장합니다."""

    slides = []
    for slide in _list(plan.get("slides")):
        if not isinstance(slide, dict):
            continue
        image = _dict(slide.get("image"))
        character = _dict(slide.get("character"))
        slides.append(
            {
                "page": slide.get("page"),
                "role": slide.get("role", ""),
                "layout": slide.get("layout", ""),
                "title": slide.get("title", ""),
                "image_id": image.get("image_id", ""),
                "character_asset_id": character.get("asset_id", ""),
            }
        )
    return {
        "plan_version": plan.get("plan_version", "card-news-ver2-plan"),
        "title": plan.get("title", ""),
        "series_title": plan.get("series_title", ""),
        "issue_label": plan.get("issue_label", ""),
        "issue_no": plan.get("issue_no", ""),
        "publisher": plan.get("publisher", ""),
        "page_count": plan.get("page_count", len(slides)),
        "aspect_ratio": plan.get("aspect_ratio", "16:9"),
        "slides": slides,
        "used_character_assets": _list(plan.get("used_character_assets")),
        "navigation": _dict(plan.get("navigation")),
    }


def _compact_request(request: dict[str, Any]) -> dict[str, Any]:
    """링크 결과에 남길 최소 요청 정보만 정리합니다."""

    return {
        "series_title": request.get("series_title", ""),
        "issue_label": request.get("issue_label", ""),
        "issue_no": request.get("issue_no", ""),
        "publisher": request.get("publisher", ""),
        "requested_page_count": request.get("requested_page_count", 0),
        "cover": _dict(request.get("cover")),
        "closing": _dict(request.get("closing")),
    }


def _card_news_question(plan: dict[str, Any], request: dict[str, Any]) -> str:
    """Report API 메타데이터의 question 필드에 들어갈 카드뉴스 설명을 만듭니다."""

    title = _clean(plan.get("title") or _dict(request.get("cover")).get("title") or "카드뉴스")
    issue = " / ".join(part for part in [_clean(request.get("issue_label")), _clean(request.get("issue_no"))] if part)
    return f"{title} 카드뉴스" + (f" ({issue})" if issue else "")


def _post_url(report_api_url: Any) -> str:
    base_url = _clean(report_api_url)
    if not base_url:
        return ""
    post_url = base_url.rstrip("/")
    if not post_url.endswith("/reports"):
        post_url = post_url + "/reports"
    return post_url


def _post_json(url: str, body: dict[str, Any], timeout: int) -> dict[str, Any]:
    """표준 라이브러리만 사용해 JSON POST 요청을 보냅니다."""

    data = json.dumps(body, ensure_ascii=False, default=str).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Report API HTTP {exc.code}: {detail}") from exc
    parsed = json.loads(raw or "{}")
    if not isinstance(parsed, dict):
        raise RuntimeError("Report API did not return a JSON object")
    return parsed


def _payload(value: Any) -> dict[str, Any]:
    """Langflow Data/Message/dict/JSON 문자열을 일반 dict로 맞춥니다."""

    if isinstance(value, dict):
        return deepcopy(value)
    data = getattr(value, "data", None)
    if isinstance(data, dict):
        return deepcopy(data)
    text = getattr(value, "text", None) or getattr(value, "content", None)
    if isinstance(text, str):
        try:
            parsed = json.loads(text)
        except Exception:
            return {"text": text}
        return deepcopy(parsed) if isinstance(parsed, dict) else {"text": text}
    return {}


def _dict(value: Any) -> dict[str, Any]:
    return deepcopy(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return deepcopy(value) if isinstance(value, list) else []


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _format_expires_at(value: Any) -> str:
    """서버가 준 UTC 만료 시간을 한국 시간 문자열로 바꿉니다."""

    text = _clean(value)
    if not text:
        return ""
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return text
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    kst = parsed.astimezone(timezone(timedelta(hours=9)))
    return kst.strftime("%Y-%m-%d %H:%M KST")


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = default
    return max(1, parsed)


class CardNewsApiPublisher(Component):
    """카드뉴스 HTML을 Report API 서버에 게시하는 Langflow 노드입니다."""

    display_name = "05 카드뉴스 공유 링크 출력"
    description = "생성된 카드뉴스 HTML을 기존 Report API 서버에 저장하고 브라우저 보기 링크를 출력합니다."
    icon = "ExternalLink"
    name = "CardNewsApiPublisher"

    inputs = [
        DataInput(name="payload", display_name="단일 HTML 결과", required=True),
        MessageTextInput(name="report_api_url", display_name="Report API 주소", value=DEFAULT_REPORT_API_URL, required=False),
        MessageTextInput(name="ttl_hours", display_name="링크 유효시간", value="24", required=False),
    ]
    outputs = [Output(name="link_message", display_name="보기 링크 메시지", method="build_message")]

    def _published_payload(self) -> dict[str, Any]:
        """같은 노드 실행 중 API POST가 중복 호출되지 않도록 결과를 캐시합니다."""

        cached = getattr(self, "_cached_publish_result", None)
        if isinstance(cached, dict):
            return cached
        result = publish_card_news_html(
            getattr(self, "payload", None),
            getattr(self, "report_api_url", DEFAULT_REPORT_API_URL),
            getattr(self, "ttl_hours", "24"),
        )
        self._cached_publish_result = result
        return result

    def build_message(self) -> Message:
        result = self._published_payload()
        publish = _dict(result.get("card_news_publish")) if isinstance(result, dict) else {}
        self.status = {
            "status": publish.get("status"),
            "view_url": publish.get("view_url", ""),
            "download_url": publish.get("download_url", ""),
            "expires_at": publish.get("expires_at", ""),
            "errors": len(publish.get("errors", [])) if isinstance(publish.get("errors"), list) else 0,
        }
        return Message(text=build_card_news_link_message(result))
