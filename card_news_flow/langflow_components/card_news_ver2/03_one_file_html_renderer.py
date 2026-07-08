from __future__ import annotations

"""03 단일 HTML 렌더링 노드.

검증된 카드뉴스 plan을 받아 모든 페이지가 포함된 HTML 문서 하나를 만듭니다.
외부 이미지/CDN/JS 없이 data URI와 CSS 라디오 전환만 사용합니다.
"""

import html
import re
from copy import deepcopy
from datetime import datetime
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, Output
from lfx.schema.data import Data


ALLOWED_IMAGE_PREFIXES = ("data:image/png;base64,", "data:image/jpeg;base64,", "data:image/webp;base64,")
FORBIDDEN_HTML_MARKERS = ("<script", "<iframe", "<object", "<embed", "javascript:", "vbscript:", " onerror=", " onclick=", " onload=")


def render_one_file_card_news_html(plan_payload_value: Any) -> dict[str, Any]:
    """카드뉴스 전체 plan을 단일 HTML 결과로 렌더링합니다."""

    payload = _payload(plan_payload_value)
    plan = _dict(payload.get("card_news_plan"))
    slides = [slide for slide in _list(plan.get("slides")) if isinstance(slide, dict)]
    if not plan or not slides:
        return {**payload, "html_result": {"status": "error", "errors": ["card_news_plan.slides가 비어 있습니다."]}}

    title = _clean(plan.get("title")) or "카드뉴스"
    html_source = _document(plan, slides)
    security_report = _security_report(html_source)
    result = deepcopy(payload)
    result["html_result"] = {
        "status": "ok" if security_report["passed"] else "security_error",
        "title": title,
        "filename_hint": _filename_hint(plan),
        "html": html_source if security_report["passed"] else "",
        "page_count": len(slides),
        "rendered_at": datetime.now().isoformat(timespec="seconds"),
        "security_report": security_report,
        "warnings": _list(_dict(payload.get("trace")).get("warnings")),
    }
    return result


def _document(plan: dict[str, Any], slides: list[dict[str, Any]]) -> str:
    """HTML 문서 전체 뼈대를 만듭니다."""

    title = _clean(plan.get("title")) or "카드뉴스"
    series_title = _clean(plan.get("series_title")) or "P&T AI INSIGHT"
    issue_label = _clean(plan.get("issue_label"))
    issue_no = _clean(plan.get("issue_no"))
    toolbar_meta = " / ".join(part for part in [issue_label, issue_no] if part)
    rendered_slides = "\n".join(_slide_markup(slide, index, len(slides), plan) for index, slide in enumerate(slides))
    nav = _nav_markup(slides)
    css = _css(len(slides))
    controls = _page_controls(slides)
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none';">
  <title>{html.escape(title)}</title>
  <style>{css}</style>
</head>
<body>
  <main class="deck-shell" aria-label="{html.escape(title)}">
    <header class="deck-toolbar">
      <div class="brand-lockup">
        <span class="brand-mark">{html.escape(series_title)}</span>
        <span class="issue-mark">{html.escape(toolbar_meta)}</span>
      </div>
      <label class="top-button" for="deck-page-1" role="button" tabindex="0" aria-label="첫 페이지로 이동">TOP</label>
    </header>
    <section class="deck-viewport" aria-label="카드뉴스 페이지">
      {controls}
      <div class="slide-stage">
{rendered_slides}
      </div>
      {nav}
    </section>
  </main>
</body>
</html>"""


def _slide_markup(slide: dict[str, Any], index: int, total: int, plan: dict[str, Any]) -> str:
    """역할별로 다른 페이지 템플릿을 렌더링합니다."""

    role = _clean(slide.get("role")) or "case"
    if role == "cover":
        return _cover_markup(slide, index, total, plan)
    if role == "closing":
        return _closing_markup(slide, index, total, plan)
    return _content_markup(slide, index, total)


def _cover_markup(slide: dict[str, Any], index: int, total: int, plan: dict[str, Any]) -> str:
    """첫 페이지 전용 표지 레이아웃입니다."""

    slide_id = _slide_id(slide, index)
    image = _dict(slide.get("image"))
    character = _dict(slide.get("character"))
    issue_label = " / ".join(part for part in [_clean(plan.get("issue_label")), _clean(plan.get("issue_no"))] if part)
    image_markup = _image_panel(image, "cover-visual") if image else ""
    character_markup = _character_markup(character)
    media_class = "has-media" if image_markup or character_markup else "no-media"
    next_page = min(index + 2, total)
    return f"""
        <section id="{html.escape(slide_id)}" class="news-slide role-cover layout-cover" data-page="{index + 1}">
          <article class="slide-card cover-card {media_class}">
            <div class="cover-copy">
              <span class="kicker">{html.escape(_clean(slide.get("badge")) or issue_label or "AI NEWS")}</span>
              <h2>{html.escape(_clean(slide.get("title")))}</h2>
              <p>{html.escape(_clean(slide.get("subtitle")))}</p>
              <div class="issue-strip">
                <span>{html.escape(_clean(plan.get("series_title")) or "P&T AI INSIGHT")}</span>
                <strong>{html.escape(issue_label or "카드뉴스")}</strong>
              </div>
              <label class="action-button primary" for="deck-page-{next_page}" role="button" tabindex="0">시작하기</label>
            </div>
            <div class="cover-art">
              {image_markup}
              {character_markup}
            </div>
          </article>
        </section>"""


def _content_markup(slide: dict[str, Any], index: int, total: int) -> str:
    """중간 페이지 레이아웃입니다."""

    slide_id = _slide_id(slide, index)
    layout = _clean(slide.get("layout")) or "text_focus"
    image = _dict(slide.get("image"))
    character = _dict(slide.get("character"))
    title_text = _clean(slide.get("title"))
    subtitle_text = _clean(slide.get("subtitle"))
    body_text = _clean(slide.get("body"))
    bullet_items = _strings(slide.get("bullets"))
    link_items = _slide_links(slide)
    # 다섯 가지 요소(제목/소제목/본문/이미지/하이퍼링크)는 모두 선택값이라, 있는 블록만 렌더링합니다.
    title_markup = f"<h2>{html.escape(title_text)}</h2>" if title_text else ""
    subtitle_markup = _subtitle_block(subtitle_text)
    detail_markup = _paragraphs(body_text) + _bullets(bullet_items) + _links_markup(link_items)
    image_markup = _image_panel(image, "content-visual") if image else ""
    character_markup = _character_markup(character)
    title_block_markup = (
        f"""
              <section class="title-panel">
                {title_markup}
                {subtitle_markup}
              </section>"""
        if title_markup or subtitle_markup
        else ""
    )
    media_markup = (
        f"""
              <aside class="media-panel">
                {image_markup}
                {character_markup}
              </aside>"""
        if image_markup or character_markup
        else ""
    )
    detail_block_markup = (
        f"""
              <section class="detail-panel">
                {detail_markup}
              </section>"""
        if detail_markup
        else ""
    )
    content_classes = _content_profile_classes(slide, bool(image_markup), bool(character_markup))
    prev_page = max(1, index)
    next_page = min(total, index + 2)
    hitarea = (
        f'<label class="slide-hitarea" for="deck-page-{next_page}" role="button" aria-label="다음 페이지로 이동"><span>다음 페이지</span></label>'
        if index < total - 1
        else ""
    )
    return f"""
        <section id="{html.escape(slide_id)}" class="news-slide role-{html.escape(_safe_class(slide.get("role")))} layout-{html.escape(_safe_class(layout))}" data-page="{index + 1}">
          <article class="slide-card content-card {content_classes}">
            {hitarea}
            <div class="slide-topline">
              <span>{html.escape(_clean(slide.get("badge")) or "핵심")}</span>
              <strong>{html.escape(_clean(slide.get("page_label")))}</strong>
            </div>
            <div class="content-grid">
              {title_block_markup}
              {media_markup}
              {detail_block_markup}
            </div>
            <nav class="slide-actions" aria-label="페이지 이동">
              <label class="action-button secondary" for="deck-page-{prev_page}" role="button" tabindex="0">이전</label>
              <label class="action-button primary" for="deck-page-{next_page}" role="button" tabindex="0">다음</label>
            </nav>
          </article>
        </section>"""


def _closing_markup(slide: dict[str, Any], index: int, total: int, plan: dict[str, Any]) -> str:
    """마지막 페이지 전용 CTA 레이아웃입니다."""

    slide_id = _slide_id(slide, index)
    image = _dict(slide.get("image"))
    character = _dict(slide.get("character"))
    cta = _dict(slide.get("cta"))
    cta_label = _clean(cta.get("label")) or "처음으로"
    cta_url = _clean(cta.get("url"))
    subtitle_markup = _subtitle_block(_clean(slide.get("subtitle")))
    has_external_cta = _safe_url(cta_url)
    cta_href = cta_url if has_external_cta else "#slide-1"
    cta_attrs = ' target="_blank" rel="noopener noreferrer"' if has_external_cta else ""
    primary_cta = (
        f'<a class="action-button primary" href="{html.escape(cta_href, quote=True)}"{cta_attrs}>{html.escape(cta_label)}</a>'
        if has_external_cta
        else f'<label class="action-button primary" for="deck-page-1" role="button" tabindex="0">{html.escape(cta_label)}</label>'
    )
    image_markup = _image_panel(image, "closing-visual") if image else ""
    character_markup = _character_markup(character)
    media_class = "has-media" if image_markup or character_markup else "no-media"
    if has_external_cta:
        actions_markup = f"""
                {primary_cta}
                <label class="action-button secondary" for="deck-page-1" role="button" tabindex="0">처음으로</label>"""
    else:
        # 외부 CTA가 없을 때는 같은 의미의 "처음으로" 버튼이 중복되지 않게 하나만 둡니다.
        actions_markup = f"""
                {primary_cta}"""
    return f"""
        <section id="{html.escape(slide_id)}" class="news-slide role-closing layout-closing" data-page="{index + 1}">
          <article class="slide-card closing-card {media_class}">
            <div class="closing-copy">
              <span class="kicker">{html.escape(_clean(slide.get("badge")) or "마무리")}</span>
              <h2>{html.escape(_clean(slide.get("title")))}</h2>
              {subtitle_markup}
              {_paragraphs(_clean(slide.get("body")))}
              {_bullets(_strings(slide.get("bullets")))}
              {_links_markup(_slide_links(slide))}
              <div class="closing-actions">
                {actions_markup}
              </div>
            </div>
            <div class="closing-art">
              {image_markup}
              {character_markup}
            </div>
          </article>
        </section>"""


def _image_panel(image: dict[str, Any], class_name: str) -> str:
    """페이지 이미지 data URI를 안전하게 렌더링합니다."""

    data_uri = _clean(image.get("data_uri"))
    if not _valid_data_uri(data_uri):
        return ""
    fit = _safe_class(image.get("fit") or "contain")
    alt = _clean(image.get("alt")) or "카드뉴스 이미지"
    return f'<figure class="image-panel {html.escape(class_name)} image-fit-{html.escape(fit)}"><img src="{html.escape(data_uri, quote=True)}" alt="{html.escape(alt, quote=True)}"></figure>'


def _character_markup(character: dict[str, Any]) -> str:
    """선택된 캐릭터 asset을 위치/크기 class와 함께 렌더링합니다."""

    data_uri = _clean(character.get("data_uri"))
    if not _valid_data_uri(data_uri):
        return ""
    placement = _safe_class(character.get("placement") or "bottom_right")
    size = _safe_class(character.get("size") or "small")
    alt = _clean(character.get("alt")) or "카드뉴스 캐릭터"
    return f'<figure class="character character-{placement} character-{size}"><img src="{html.escape(data_uri, quote=True)}" alt="{html.escape(alt, quote=True)}"></figure>'


def _paragraphs(text: str) -> str:
    paragraphs = [part.strip() for part in text.splitlines() if part.strip()]
    if not paragraphs:
        return ""
    return '<div class="body-copy">' + "".join(f"<p>{_linkify_text(part)}</p>" for part in paragraphs[:5]) + "</div>"


def _subtitle_block(text: str) -> str:
    """소제목은 본문과 분리해 회사 오렌지 계열 색상으로 렌더링합니다."""

    paragraphs = [part.strip() for part in text.splitlines() if part.strip()]
    if not paragraphs:
        return ""
    return '<div class="subtitle-copy">' + "".join(f"<p>{_linkify_text(part)}</p>" for part in paragraphs[:3]) + "</div>"


def _bullets(items: list[str]) -> str:
    if not items:
        return ""
    rendered = "".join(f"<li><span>{_linkify_text(item)}</span></li>" for item in items[:5])
    return f'<ul class="bullet-list">{rendered}</ul>'


def _links_markup(items: list[dict[str, str]]) -> str:
    """표시 문구와 실제 URL을 분리한 하이퍼링크 목록을 렌더링합니다."""

    if not items:
        return ""
    anchors = []
    for item in items[:3]:
        label = _clean(item.get("label")) or _clean(item.get("url"))
        url = _clean(item.get("url"))
        if not label or not _safe_url(url):
            continue
        anchors.append(
            f'<a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(label)}</a>'
        )
    return f'<div class="link-list">{"".join(anchors)}</div>' if anchors else ""


def _linkify_text(text: str) -> str:
    """본문 안에 직접 적힌 http/https URL도 클릭 가능한 링크로 바꿉니다."""

    source = _clean(text)
    if not source:
        return ""
    result: list[str] = []
    cursor = 0
    for match in re.finditer(r"https?://[^\s<>'\"]+", source, flags=re.IGNORECASE):
        raw_url = match.group(0)
        url = _trim_url(raw_url)
        if not _safe_url(url):
            continue
        result.append(html.escape(source[cursor : match.start()]))
        result.append(
            f'<a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(url)}</a>'
        )
        result.append(html.escape(raw_url[len(url) :]))
        cursor = match.end()
    result.append(html.escape(source[cursor:]))
    return "".join(result)


def _normalize_links(value: Any) -> list[dict[str, str]]:
    """슬라이드 payload의 링크 값을 [{label, url}]로 통일합니다."""

    if value in (None, ""):
        return []
    if isinstance(value, dict):
        if any(key in value for key in ("url", "href", "link")):
            raw_items = [value]
        else:
            raw_items = [{"label": label, "url": url} for label, url in value.items()]
    elif isinstance(value, list):
        raw_items = value
    else:
        raw_items = [part for part in str(value).splitlines() if part.strip()]

    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw_items:
        link = _coerce_link(item)
        if not link or link["url"] in seen:
            continue
        seen.add(link["url"])
        result.append(link)
    return result[:3]


def _coerce_link(item: Any) -> dict[str, str]:
    """dict, markdown link, '표시문구 | URL' 값을 안전한 링크 dict로 바꿉니다."""

    if isinstance(item, dict):
        url = _clean(item.get("url") or item.get("href") or item.get("link"))
        label = _clean(item.get("label") or item.get("text") or item.get("title") or item.get("name")) or url
        return {"label": label, "url": url} if _safe_url(url) else {}

    text = _clean(item)
    if not text:
        return {}
    markdown = re.match(r"^\[([^\]]+)\]\((https?://[^)\s]+)\)$", text, flags=re.IGNORECASE)
    if markdown:
        url = _trim_url(markdown.group(2))
        return {"label": markdown.group(1).strip(), "url": url} if _safe_url(url) else {}

    url_match = re.search(r"https?://[^\s,;|)>\]]+", text, flags=re.IGNORECASE)
    if not url_match:
        return {}
    url = _trim_url(url_match.group(0))
    label = (text[: url_match.start()] + text[url_match.end() :]).strip(" \t-–—:：|,;()[]")
    return {"label": label or url, "url": url} if _safe_url(url) else {}


def _content_profile_classes(slide: dict[str, Any], has_image: bool, has_character: bool) -> str:
    """텍스트 길이와 이미지 유무에 따라 CSS가 배치를 조절할 수 있는 class를 만듭니다."""

    title = _clean(slide.get("title"))
    subtitle = _clean(slide.get("subtitle"))
    body = _clean(slide.get("body"))
    bullets = _strings(slide.get("bullets"))
    links = _slide_links(slide)
    body_paragraphs = [part.strip() for part in body.splitlines() if part.strip()]
    text_weight = len(title) * 2 + len(subtitle) + len(body) + sum(len(item) for item in bullets) + sum(len(item.get("label", "")) for item in links)
    has_media = has_image or has_character
    classes = ["has-media" if has_media else "no-media"]
    classes.append("has-image" if has_image else "no-image")
    classes.append("has-character" if has_character else "no-character")
    if has_character and not has_image:
        classes.append("character-only")
    if has_image and has_character:
        classes.append("image-with-character")
    classes.append("has-title-block" if title or subtitle else "no-title-block")
    classes.append("has-detail-block" if body or bullets or links else "no-detail-block")
    if subtitle:
        classes.append("has-subtitle")
    if len(title) >= 34:
        classes.append("title-very-long")
    elif len(title) >= 22:
        classes.append("title-long")
    else:
        classes.append("title-short")
    # 본문이 길거나 문단이 많으면 이미지/캐릭터보다 텍스트 가독성을 우선하도록 별도 밀도 class를 붙입니다.
    if text_weight >= 420 or len(body) >= 300 or len(body_paragraphs) >= 3:
        classes.extend(["density-high", "density-very-high"])
    elif text_weight >= 260 or len(bullets) >= 4:
        classes.append("density-high")
    elif text_weight <= 120 and len(bullets) <= 2:
        classes.append("density-low")
    else:
        classes.append("density-medium")
    if len(body) >= 220:
        classes.append("body-long")
    if len(body_paragraphs) >= 3:
        classes.append("body-multi-paragraph")
    if bullets:
        classes.append("has-bullets")
    if links:
        classes.append("has-links")
    return " ".join(classes)


def _nav_markup(slides: list[dict[str, Any]]) -> str:
    items = []
    for index, slide in enumerate(slides, start=1):
        label = _clean(slide.get("title")) or f"{index}페이지"
        items.append(f'<label for="deck-page-{index}" role="button" tabindex="0" title="{html.escape(label, quote=True)}"><span>{index}</span></label>')
    return f'<nav class="deck-nav" aria-label="페이지 바로가기">{"".join(items)}</nav>'


def _page_controls(slides: list[dict[str, Any]]) -> str:
    """JS 없이 페이지 버튼이 동작하도록 숨김 라디오 입력을 만듭니다."""

    controls = []
    for index, _slide in enumerate(slides, start=1):
        checked = " checked" if index == 1 else ""
        controls.append(f'<input class="deck-page-control" type="radio" name="deck-page" id="deck-page-{index}"{checked}>')
    return "\n      ".join(controls)


def _control_css(slide_count: int) -> str:
    """라디오 입력 상태와 실제 슬라이드 표시 상태를 연결하는 CSS를 만듭니다."""

    lines = [
        ".deck-page-control { position:absolute; width:1px; height:1px; opacity:0; pointer-events:none; }",
        ".deck-page-control:checked ~ .slide-stage .news-slide { opacity:0; pointer-events:none; transform:translateY(18px) scale(.985); z-index:0; }",
    ]
    for index in range(1, max(1, slide_count) + 1):
        lines.append(
            f"#deck-page-{index}:checked ~ .slide-stage .news-slide:nth-child({index}) "
            "{ opacity:1; pointer-events:auto; transform:none; z-index:3; }"
        )
        lines.append(
            f"#deck-page-{index}:checked ~ .deck-nav label:nth-child({index}) "
            "{ background:var(--sk-red); color:#fff; border-color:var(--sk-red); }"
        )
    return "\n".join(lines)


def _css(slide_count: int) -> str:
    """HTML 한 파일 안에 포함할 정적 CSS입니다."""

    css = """
:root {
  --sk-red:#EA002C;
  --sk-orange:#F47725;
  --sk-red-bright:#D7282F;
  --sk-orange-deep:#D9631C;
  --body-ink:#334155;
  --mint:#0F9F8F;
  --blue:#2563EB;
  --ink:#17202A;
  --muted:#64748B;
  --paper:#FBFBFD;
  --soft:#FFF4EA;
  --line:rgba(23,32,42,.14);
}
* { box-sizing:border-box; }
html, body { margin:0; min-height:100%; }
body {
  overflow:auto;
  color:var(--ink);
  font-family:"Pretendard","Apple SD Gothic Neo","Noto Sans KR",system-ui,-apple-system,sans-serif;
  background:#F5F5F7;
}
.deck-shell { min-height:100svh; display:grid; grid-template-rows:auto minmax(0, 1fr); gap:12px; padding:16px 18px 12px; }
.deck-toolbar { min-height:44px; display:flex; justify-content:space-between; align-items:center; gap:14px; }
.brand-lockup { min-width:0; display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
.brand-mark { padding:8px 12px; border-radius:999px; background:var(--ink); color:#fff; font-size:13px; font-weight:900; }
.issue-mark { color:#475569; font-size:13px; font-weight:800; }
.top-button { min-width:48px; min-height:36px; display:grid; place-items:center; border-radius:999px; background:#fff; color:var(--sk-red); border:1px solid rgba(234,0,44,.22); text-decoration:none; font-size:12px; font-weight:900; cursor:pointer; user-select:none; }
.deck-viewport { min-height:0; width:100%; display:grid; grid-template-rows:minmax(0, 1fr) auto; gap:10px; place-items:center; align-content:center; }
.slide-stage { position:relative; width:min(1180px, 96vw, calc(177svh - 263px)); aspect-ratio:16 / 9; min-width:0; min-height:0; }
.news-slide { position:absolute; inset:0; opacity:0; pointer-events:none; transform:translateY(18px) scale(.985); transition:opacity .28s ease, transform .28s ease; z-index:0; }
.news-slide:first-child { opacity:1; pointer-events:auto; transform:none; z-index:1; }
.news-slide:target { opacity:1; pointer-events:auto; transform:none; z-index:3; }
__CONTROL_CSS__
.slide-card {
  position:relative;
  width:100%;
  height:100%;
  overflow:hidden;
  border:1px solid rgba(23,32,42,.12);
  border-radius:28px;
  background:var(--paper);
  box-shadow:0 22px 50px rgba(15,23,42,.10);
}
.slide-card::before {
  content:none;
}
.kicker { display:inline-flex; width:max-content; max-width:100%; align-items:center; min-height:34px; padding:7px 12px; border-radius:999px; background:#FFE1D2; color:#9A3412; font-size:13px; font-weight:900; }
.cover-card, .closing-card { display:grid; grid-template-columns:minmax(0, .96fr) minmax(280px, .74fr); gap:22px; padding:42px 54px 46px; }
.cover-copy, .closing-copy { position:relative; z-index:2; display:grid; align-content:start; justify-items:start; gap:14px; min-width:0; padding-top:34px; }
.cover-copy h2 { margin:0; color:var(--sk-red-bright); font-size:clamp(34px, 4.8vw, 58px); line-height:1.08; letter-spacing:0; word-break:keep-all; overflow-wrap:anywhere; }
.closing-copy h2 { margin:0; color:var(--sk-red-bright); font-size:clamp(26px, 3.25vw, 42px); line-height:1.12; letter-spacing:0; word-break:keep-all; overflow-wrap:anywhere; }
.cover-copy p, .closing-copy p, .body-copy p { margin:0; color:var(--body-ink); font-size:clamp(15px, 1.45vw, 20px); line-height:1.62; font-weight:720; word-break:keep-all; overflow-wrap:anywhere; }
.subtitle-copy { display:grid; gap:6px; max-width:min(900px, 100%); }
.subtitle-copy p { margin:0; color:var(--sk-orange); font-size:clamp(15px, 1.35vw, 19px); line-height:1.45; font-weight:780; word-break:keep-all; overflow-wrap:anywhere; }
.cover-card.no-media .cover-art { display:none; }
.closing-card { grid-template-columns:minmax(0, .98fr) minmax(220px, .52fr); padding:38px 54px 42px; }
.closing-copy { align-content:center; gap:12px; padding-top:0; }
.closing-copy .body-copy { max-width:min(820px, 100%); gap:7px; }
.closing-copy .body-copy p { font-size:clamp(13px, 1.16vw, 16px); line-height:1.52; }
.closing-card.no-media { grid-template-columns:minmax(0, 1fr); place-items:stretch; padding:38px clamp(48px, 6vw, 76px) 42px; }
.closing-card.no-media .closing-copy { width:min(880px, 100%); justify-items:start; align-content:center; text-align:left; padding-top:0; }
.closing-card.no-media .closing-copy h2 { max-width:760px; font-size:clamp(26px, 3.25vw, 42px); word-break:keep-all; }
.closing-card.no-media .closing-actions { justify-content:flex-start; }
.closing-card.no-media .closing-art { display:none; }
.issue-strip { display:flex; align-items:center; gap:10px; flex-wrap:wrap; padding:12px 0; border-top:1px solid var(--line); border-bottom:1px solid var(--line); }
.issue-strip span { color:var(--muted); font-size:13px; font-weight:850; }
.issue-strip strong { color:var(--sk-red); font-size:18px; }
.cover-art, .closing-art, .media-panel { position:relative; z-index:2; min-width:0; min-height:0; display:grid; place-items:center; }
.slide-topline { position:relative; z-index:4; display:flex; justify-content:space-between; align-items:center; gap:12px; min-height:36px; padding:24px 30px 0; }
.slide-topline span { padding:7px 11px; border-radius:999px; background:#FFF0E6; color:var(--sk-red); font-size:12px; font-weight:900; }
.slide-topline strong { color:#64748B; font-size:12px; font-weight:900; }
.content-card { display:grid; grid-template-rows:auto minmax(0, 1fr) auto; gap:10px; padding:0; }
.content-grid { position:relative; z-index:2; min-height:0; display:grid; grid-template-columns:1fr; grid-template-rows:minmax(88px, .30fr) minmax(232px, 1fr) minmax(92px, .34fr); gap:14px; padding:0 clamp(46px, 5.5vw, 74px); align-items:stretch; }
.content-card.density-low.has-media .content-grid { grid-template-rows:minmax(96px, .32fr) minmax(246px, 1fr) minmax(86px, .30fr); }
.content-card.density-high.has-media .content-grid { grid-template-rows:minmax(76px, .24fr) minmax(158px, .58fr) minmax(188px, .86fr); }
.content-card.density-very-high.has-media .content-grid { grid-template-rows:minmax(66px, .20fr) minmax(112px, .36fr) minmax(246px, 1fr); gap:9px; }
.content-card.no-media .content-grid { grid-template-rows:minmax(118px, .40fr) minmax(0, 1fr); }
.content-card.no-title-block.has-media.has-detail-block .content-grid { grid-template-rows:minmax(286px, 1fr) minmax(120px, .40fr); }
.content-card.has-title-block.has-media.no-detail-block .content-grid { grid-template-rows:minmax(112px, .34fr) minmax(306px, 1fr); }
.content-card.has-title-block.no-media.has-detail-block .content-grid { grid-template-rows:minmax(128px, .36fr) minmax(0, 1fr); }
.content-card.no-title-block.has-media.no-detail-block .content-grid { grid-template-rows:minmax(0, 1fr); align-items:center; }
.content-card.no-title-block.no-media.has-detail-block .content-grid { grid-template-rows:minmax(0, 1fr); align-items:center; }
.content-card.no-media .media-panel { display:none; }
.content-card.no-media .detail-panel { min-height:220px; }
.content-card.no-title-block.no-media.has-detail-block .detail-panel { min-height:0; align-content:center; }
.content-card.no-detail-block .media-panel { align-self:center; }
.content-card.no-media .slide-actions { justify-content:center; }
.title-panel, .detail-panel { min-width:0; display:grid; align-content:center; justify-items:center; text-align:center; background:transparent; border:0; border-radius:0; box-shadow:none; overflow:visible; }
.title-panel { gap:8px; padding:0 clamp(22px, 3vw, 34px); }
.title-panel h2 { max-width:min(980px, 100%); margin:0; color:var(--sk-red-bright); font-size:clamp(28px, 3.35vw, 44px); font-weight:850; line-height:1.08; letter-spacing:0; word-break:keep-all; overflow-wrap:anywhere; }
.content-card.title-long .title-panel h2 { font-size:clamp(25px, 2.85vw, 36px); line-height:1.12; }
.content-card.title-very-long .title-panel h2 { font-size:clamp(22px, 2.45vw, 31px); line-height:1.16; }
.role-tip .title-panel h2, .role-checklist .title-panel h2, .role-workflow .title-panel h2, .role-security .title-panel h2, .role-metric .title-panel h2, .role-why .title-panel h2 { color:var(--sk-red-bright); }
.body-copy { display:grid; gap:8px; }
.title-panel .body-copy { max-width:min(850px, 100%); gap:4px; }
.title-panel .subtitle-copy { justify-items:center; margin:0 auto; }
.title-panel .subtitle-copy p { text-align:center; }
.title-panel .body-copy p { color:var(--sk-orange); text-align:center; font-size:clamp(14px, 1.24vw, 18px); line-height:1.42; font-weight:650; }
.detail-panel { justify-items:center; align-content:start; padding:4px clamp(20px, 3vw, 32px) 0; }
.content-card.density-very-high .detail-panel { padding-top:2px; }
.role-security .detail-panel, .role-tip .detail-panel, .role-checklist .detail-panel { background:transparent; border:0; }
.detail-panel .body-copy { width:min(920px, 100%); margin:0 auto; }
.detail-panel .body-copy p { margin:0; color:var(--body-ink); text-align:center; font-size:clamp(15px, 1.35vw, 19px); line-height:1.48; font-weight:680; word-break:keep-all; overflow-wrap:anywhere; }
.content-card.density-high .detail-panel .body-copy { gap:6px; }
.content-card.density-high .detail-panel .body-copy p { font-size:clamp(12px, 1.02vw, 15px); line-height:1.40; }
.content-card.density-very-high .detail-panel .body-copy { width:min(980px, 100%); grid-template-columns:repeat(2, minmax(0, 1fr)); column-gap:24px; row-gap:7px; align-items:start; }
.content-card.density-very-high .detail-panel .body-copy p { text-align:left; font-size:clamp(11px, .88vw, 13px); line-height:1.34; font-weight:650; }
.bullet-list { list-style:none; width:min(920px, 100%); margin:0 auto; padding:0; display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:18px; }
.detail-panel .body-copy + .bullet-list { margin-top:16px; }
.content-card.density-high .bullet-list, .content-card.no-media .bullet-list { grid-template-columns:repeat(2, minmax(0, 1fr)); }
.bullet-list li { min-height:auto; display:flex; align-items:center; justify-content:center; gap:8px; padding:0; border-radius:0; background:transparent; box-shadow:none; color:var(--body-ink); font-size:clamp(13px, 1.14vw, 16px); line-height:1.35; font-weight:720; overflow-wrap:anywhere; }
.content-card.density-very-high .bullet-list { gap:10px 18px; margin-top:10px; }
.content-card.density-very-high .bullet-list li { justify-content:flex-start; text-align:left; font-size:clamp(11px, .90vw, 13px); line-height:1.28; font-weight:680; }
.bullet-list li::before { content:""; flex:0 0 auto; width:7px; height:7px; border-radius:50%; background:var(--sk-orange); }
.role-security .bullet-list li::before { background:var(--sk-red); }
.role-tip .bullet-list li::before, .role-checklist .bullet-list li::before, .role-workflow .bullet-list li::before { background:var(--sk-orange); }
.body-copy a, .subtitle-copy a, .bullet-list a { color:var(--sk-red-bright); text-decoration:underline; text-underline-offset:3px; font-weight:850; }
.link-list { width:min(920px, 100%); margin:14px auto 0; display:flex; justify-content:center; align-items:center; gap:10px; flex-wrap:wrap; }
.link-list a { display:inline-flex; min-height:34px; align-items:center; justify-content:center; padding:8px 14px; border-radius:999px; border:1px solid rgba(234,0,44,.22); background:#fff; color:var(--sk-red); text-decoration:none; font-size:clamp(12px, .98vw, 14px); line-height:1.2; font-weight:900; box-shadow:0 10px 22px rgba(15,23,42,.08); }
.link-list a::after { content:"↗"; margin-left:6px; font-size:.9em; }
.content-card.density-high .link-list { margin-top:10px; gap:8px; }
.content-card.density-high .link-list a { min-height:30px; padding:6px 11px; font-size:clamp(11px, .88vw, 13px); }
.image-panel { position:relative; margin:0; width:100%; height:100%; min-height:200px; display:grid; place-items:center; border-radius:20px; background:#fff; border:1px solid rgba(15,23,42,.10); box-shadow:0 18px 34px rgba(15,23,42,.12); overflow:hidden; }
.image-panel img { position:absolute; inset:0; width:100%; height:100%; max-height:100%; display:block; object-fit:contain; }
.image-fit-cover img { object-fit:cover; }
.image-fit-fill img { object-fit:fill; }
.cover-visual, .closing-visual { position:absolute; inset:38px 18px 54px 18px; opacity:.92; transform:rotate(-1deg); }
.content-visual { max-height:100%; }
.content-card .media-panel { width:min(74%, 760px); justify-self:center; overflow:visible; isolation:auto; }
.content-card .media-panel .image-panel { min-height:0; background:transparent; border:0; box-shadow:none; }
.content-card.density-high .media-panel { width:min(58%, 620px); }
.content-card.density-very-high .media-panel { width:min(46%, 500px); }
.layout_image_focus .content-grid { grid-template-rows:minmax(82px, .30fr) minmax(230px, 1.08fr) minmax(104px, .42fr); }
.layout_image_focus .media-panel { width:min(82%, 860px); }
.layout_image_focus.density-high .media-panel { width:min(62%, 640px); }
.layout_image_focus.density-very-high .media-panel { width:min(48%, 520px); }
.character { position:absolute; z-index:3; margin:0; pointer-events:none; }
.character img { display:block; width:210px; max-width:32vw; height:auto; object-fit:contain; filter:drop-shadow(0 20px 22px rgba(15,23,42,.18)); animation:mascotIdle 3.8s ease-in-out infinite; }
.character-large img { width:300px; max-width:36vw; }
.character-bottom_right { right:-10px; bottom:-20px; }
.character-bottom_left { left:-12px; bottom:-20px; }
.character-center { left:50%; bottom:4px; transform:translateX(-50%); }
.media-panel .character { z-index:2; }
.media-panel .character img { width:clamp(190px, 18vw, 285px); max-width:min(100%, 36vw); opacity:1; }
.media-panel .character-small img { width:clamp(180px, 17vw, 260px); }
.media-panel .character-large img { width:clamp(220px, 21vw, 330px); max-width:min(100%, 40vw); }
.media-panel .character-bottom_left { left:clamp(6px, 1.7vw, 18px); bottom:clamp(6px, 1.6vw, 16px); }
.media-panel .character-bottom_right { right:clamp(6px, 1.7vw, 18px); bottom:clamp(6px, 1.6vw, 16px); }
.media-panel .character-center { bottom:clamp(6px, 1.4vw, 14px); }
.media-panel .character-right_side { right:clamp(-210px, -13vw, -118px); bottom:clamp(22px, 5vw, 76px); }
.media-panel .character-right_side img { width:clamp(176px, 16vw, 255px); max-width:min(100%, 34vw); }
.content-card .media-panel .character { display:block; opacity:1; }
.content-card.character-only .media-panel { width:min(52%, 560px); overflow:visible; isolation:auto; }
.content-card.character-only .media-panel .character { position:static; transform:none; }
.slide-actions, .closing-actions { position:relative; z-index:5; display:flex; justify-content:flex-end; align-items:center; gap:10px; flex-wrap:wrap; padding:0 34px 28px; }
.closing-actions { padding:0; justify-content:flex-start; }
.action-button { display:inline-flex; min-height:42px; align-items:center; justify-content:center; padding:10px 16px; border-radius:999px; text-decoration:none; font-size:14px; font-weight:900; line-height:1.2; box-shadow:0 10px 18px rgba(15,23,42,.13); cursor:pointer; user-select:none; }
.action-button.primary { background:var(--sk-red); color:#fff; }
.action-button.secondary { background:#fff; color:var(--sk-red); border:1px solid #FFD0D9; }
.slide-hitarea { position:absolute; inset:0; z-index:1; text-decoration:none; }
.slide-hitarea span { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; }
.deck-nav { min-height:30px; display:flex; justify-content:center; align-items:center; gap:8px; flex-wrap:wrap; }
.deck-nav label { width:28px; height:28px; display:grid; place-items:center; border-radius:50%; background:#fff; border:1px solid rgba(234,0,44,.20); color:var(--sk-red); text-decoration:none; font-size:12px; font-weight:900; cursor:pointer; user-select:none; }
.deck-nav label:hover, .deck-nav label:focus, .action-button:hover, .action-button:focus, .top-button:hover, .top-button:focus { outline:3px solid rgba(244,119,37,.35); outline-offset:2px; }
@keyframes mascotIdle { 0%,100% { transform:translateY(0) rotate(-1deg); } 50% { transform:translateY(-9px) rotate(1deg); } }
@media (max-width: 860px) {
  body { overflow:auto; }
  .deck-shell { min-height:auto; padding:10px; }
  .slide-stage { width:100%; height:auto; aspect-ratio:auto; display:grid; gap:14px; }
  .news-slide, .news-slide:first-child, .news-slide:target { position:relative; opacity:1; pointer-events:auto; transform:none; }
  .slide-card { min-height:620px; }
  .slide-card::before { inset:18px; }
  .cover-card, .closing-card { grid-template-columns:1fr; padding:72px 42px 54px; }
  .cover-copy, .closing-copy { padding-top:0; }
  .cover-copy h2, .closing-copy h2 { font-size:34px; }
  .content-grid, .layout_image_focus .content-grid, .layout_text_focus .content-grid, .layout_checklist .content-grid, .layout_notice .content-grid, .layout_metric .content-grid { grid-template-columns:1fr; grid-template-rows:auto minmax(210px, auto) auto; padding:0 20px; }
  .slide-topline { padding:26px 20px 0; }
  .title-panel { padding:18px 16px; }
  .title-panel h2 { font-size:26px; }
  .detail-panel { padding:18px 16px; }
  .content-card.density-very-high .detail-panel .body-copy { grid-template-columns:1fr; }
  .bullet-list, .content-card.density-high .bullet-list, .content-card.no-media .bullet-list { grid-template-columns:1fr; }
  .link-list { justify-content:flex-start; }
  .content-card .media-panel { width:100%; min-height:210px; }
  .image-panel { min-height:210px; }
  .cover-visual, .closing-visual { position:relative; inset:auto; min-height:230px; }
  .character, .media-panel .character-bottom_left, .media-panel .character-bottom_right { right:8px; left:auto; bottom:-16px; opacity:.38; }
  .media-panel .character-right_side { right:8px; left:auto; bottom:-16px; opacity:.72; }
  .character img, .character-large img, .media-panel .character-small img { width:clamp(150px, 34vw, 220px); max-width:70vw; }
  .media-panel .character { opacity:1; }
  .content-card.character-only .media-panel .character { position:static; opacity:1; transform:none; }
  .content-card.character-only .media-panel .character img,
  .content-card.character-only .media-panel .character-small img,
  .content-card.character-only .media-panel .character-large img { width:clamp(150px, 34vw, 220px); max-width:70vw; opacity:1; }
  .slide-actions { justify-content:flex-start; padding:0 20px 24px; }
  .deck-nav { display:none; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration:.001ms !important; animation-iteration-count:1 !important; transition-duration:.001ms !important; }
}
"""
    return css.replace("__CONTROL_CSS__", _control_css(slide_count))


def _security_report(document: str) -> dict[str, Any]:
    lowered = document.lower()
    violations = [marker for marker in FORBIDDEN_HTML_MARKERS if marker in lowered]
    return {"passed": not violations, "policy": "card_news_ver2_static_html", "violations": violations}


def _valid_data_uri(value: str) -> bool:
    return bool(value) and value.startswith(ALLOWED_IMAGE_PREFIXES) and "PUT_BASE64" not in value


def _safe_url(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def _slide_links(slide: dict[str, Any]) -> list[dict[str, str]]:
    """슬라이드 안의 여러 링크 키 이름을 모두 links 배열로 통일합니다."""

    return _normalize_links(
        slide.get("links")
        or slide.get("hyperlinks")
        or slide.get("hyperlink")
        or slide.get("link")
        or slide.get("reference_link")
        or slide.get("reference_url")
        or slide.get("url")
    )


def _trim_url(value: str) -> str:
    return _clean(value).rstrip(".,;:!?)］】")


def _slide_id(slide: dict[str, Any], index: int) -> str:
    return _safe_anchor(_clean(slide.get("slide_id")) or f"slide-{index + 1}")


def _safe_anchor(value: str) -> str:
    return _safe_class(value or "slide")


def _safe_class(value: Any) -> str:
    text = _clean(value).lower().replace("-", "_")
    return re.sub(r"[^a-z0-9_]+", "_", text).strip("_") or "default"


def _filename_hint(plan: dict[str, Any]) -> str:
    parts = [_clean(plan.get("series_title")), _clean(plan.get("issue_label")), _clean(plan.get("issue_no")), _clean(plan.get("title"))]
    text = "_".join(part for part in parts if part)
    safe = re.sub(r"[^A-Za-z0-9가-힣_]+", "_", text).strip("_")
    return (safe or "card_news_ver2")[:90]


def _payload(value: Any) -> dict[str, Any]:
    data = getattr(value, "data", value)
    return deepcopy(data) if isinstance(data, dict) else {}


def _dict(value: Any) -> dict[str, Any]:
    return deepcopy(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return deepcopy(value) if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    raw_items = value if isinstance(value, list) else ([value] if value not in (None, "") else [])
    result = []
    for item in raw_items:
        text = _clean(item)
        if text and text not in result:
            result.append(text)
    return result


def _clean(value: Any) -> str:
    return str(value or "").strip()


class OneFileHtmlRenderer(Component):
    """카드뉴스 plan을 단일 HTML로 바꾸는 Langflow 노드입니다."""

    display_name = "03 단일 HTML 렌더링"
    description = "전체 카드뉴스 페이지, 업로드 이미지, 캐릭터를 하나의 독립 실행 HTML 파일로 렌더링합니다."
    icon = "FileCode2"
    name = "OneFileHtmlRenderer"

    inputs = [DataInput(name="card_news_plan", display_name="카드뉴스 전체 계획", required=True)]
    outputs = [Output(name="html_result", display_name="단일 HTML 결과", method="build_payload", types=["Data"])]

    def build_payload(self) -> Data:
        result = render_one_file_card_news_html(getattr(self, "card_news_plan", None))
        html_result = _dict(result.get("html_result"))
        self.status = {
            "상태": html_result.get("status"),
            "제목": html_result.get("title"),
            "페이지 수": html_result.get("page_count"),
            "HTML bytes": len(_clean(html_result.get("html")).encode("utf-8")),
            "보안 통과": _dict(html_result.get("security_report")).get("passed"),
        }
        return Data(data=result)
