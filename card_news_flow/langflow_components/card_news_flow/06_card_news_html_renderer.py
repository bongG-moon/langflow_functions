from __future__ import annotations

"""06 카드뉴스 HTML 렌더링 노드."""

import html
from copy import deepcopy
from datetime import datetime
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, Output
from lfx.schema.data import Data


ALLOWED_IMAGE_PREFIXES = ("data:image/png;base64,", "data:image/jpeg;base64,", "data:image/webp;base64,")
PLACEHOLDER_MARKERS = ("PUT_BASE64", "PUT_APPROVED_BASE64", "...")
FORBIDDEN_HTML_MARKERS = ("<script", "<iframe", "<object", "<embed", "javascript:", "vbscript:", " onerror=", " onclick=", " onload=")

ROLE_COLORS = {
    "cover": ("#FFF7ED", "#EA002C", "#F47725"),
    "intro": ("#FFF7ED", "#EA002C", "#F47725"),
    "why": ("#FFF3F5", "#EA002C", "#F47725"),
    "case": ("#FFFDF7", "#F47725", "#EA002C"),
    "workflow": ("#FFFDF7", "#F47725", "#EA002C"),
    "tip": ("#FFF0E6", "#F47725", "#EA002C"),
    "checklist": ("#FFF0E6", "#F47725", "#EA002C"),
    "security": ("#FFE8ED", "#EA002C", "#F47725"),
    "caution": ("#FFE8ED", "#EA002C", "#F47725"),
    "quiz": ("#FFFDF7", "#F47725", "#EA002C"),
    "answer": ("#FFFDF7", "#F47725", "#EA002C"),
    "recap": ("#FFF7ED", "#F47725", "#EA002C"),
    "cta": ("#FFF7ED", "#EA002C", "#F47725"),
    "closing": ("#FFF7ED", "#EA002C", "#F47725"),
    "image": ("#FFFDF7", "#EA002C", "#F47725"),
}


def render_card_news_html(plan_payload_value: Any) -> dict[str, Any]:
    """카드뉴스 계획 payload를 독립 실행 가능한 HTML 문서로 렌더링합니다."""

    payload = _payload(plan_payload_value)
    plan = _dict(payload.get("card_news_plan"))
    if not plan:
        return {**payload, "html_result": {"status": "error", "errors": ["card_news_plan is empty"]}}
    assets = _asset_map(_dict(payload.get("character_assets")))
    slides = [slide for slide in _list(plan.get("slides")) if isinstance(slide, dict)]
    style = _dict(plan.get("style"))
    title = _clean(plan.get("title")) or "월간 AI 카드뉴스"
    subtitle = _clean(plan.get("subtitle"))
    document = _document(title, subtitle, slides, plan, style, assets)
    security_report = _security_report(document)
    warnings = _list(_dict(payload.get("trace")).get("warnings"))
    missing_assets = _missing_asset_warnings(slides, assets)
    warnings.extend(missing_assets)
    result = deepcopy(payload)
    result["html_result"] = {
        "status": "ok" if security_report.get("passed") else "security_error",
        "title": title,
        "subtitle": subtitle,
        "html": document if security_report.get("passed") else "",
        "slide_count": len(slides),
        "used_assets": _list(plan.get("used_assets")),
        "theme": style.get("theme", "sk_cute_soft"),
        "filename_hint": _filename_hint(title),
        "rendered_at": datetime.now().isoformat(timespec="seconds"),
        "security_report": security_report,
        "warnings": _dedupe(warnings),
    }
    result["trace"] = {
        **_dict(result.get("trace")),
        "warnings": _dedupe(warnings),
        "errors": _list(_dict(result.get("trace")).get("errors")),
    }
    return result


def _document(title: str, subtitle: str, slides: list[dict[str, Any]], plan: dict[str, Any], style: dict[str, Any], assets: dict[str, dict[str, Any]]) -> str:
    aspect_ratio = _clean(plan.get("aspect_ratio")) or "16:9"
    ratio_css = {"16:9": "16 / 9", "1:1": "1 / 1", "4:5": "4 / 5", "9:16": "9 / 16"}.get(aspect_ratio, "16 / 9")
    nav = _navigation(slides)
    rendered_slides = [_slide_markup(slide, index, len(slides), assets) for index, slide in enumerate(slides)]
    css = _css(style, ratio_css)
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
  <main class="cardnews-shell" aria-label="{html.escape(title)}">
    <header class="deck-header">
      <div>
        <p class="brand-chip">SK hynix AI News</p>
        <h1>{html.escape(title)}</h1>
        {_optional_tag("p", subtitle, "deck-subtitle")}
      </div>
      <a class="home-link" href="#slide-1" aria-label="첫 카드로 이동">TOP</a>
    </header>
    {nav}
    <div class="slide-stage" aria-live="polite">
      {''.join(rendered_slides)}
    </div>
  </main>
</body>
</html>"""


def _slide_markup(slide: dict[str, Any], index: int, total: int, assets: dict[str, dict[str, Any]]) -> str:
    slide_id = _clean(slide.get("slide_id")) or f"slide-{index + 1}"
    role = _clean(slide.get("role")) or "case"
    layout = _clean(slide.get("layout")) or "sticker_grid"
    image_override = _dict(slide.get("image_override"))
    if image_override:
        return _image_slide_markup(slide_id, role, layout, image_override, _clean(slide.get("click_target")), index, total)
    bg, accent, secondary = ROLE_COLORS.get(role, ROLE_COLORS["case"])
    headline = _clean(slide.get("headline")) or f"카드 {index + 1}"
    body = _clean(slide.get("body"))
    bullets = _strings(slide.get("bullets"))
    badge = _clean(slide.get("badge")) or _role_label(role)
    animation = _clean(slide.get("animation")) or "fade_up"
    character_markup = _character_markup(_dict(slide.get("character")), assets)
    bullet_markup = _bullets_markup(bullets, layout)
    buttons = _buttons_markup(_list(slide.get("buttons")))
    publication_markup = _publication_markup(_dict(slide.get("publication_info"))) if index == 0 or role == "cover" else ""
    click_target = _clean(slide.get("click_target"))
    click_markup = _click_target_markup(click_target, headline) if click_target else ""
    page = f"{index + 1:02d} / {total:02d}"
    return f"""
<section id="{html.escape(slide_id)}" class="news-slide role-{html.escape(role)} layout-{html.escape(layout)} anim-{html.escape(animation)}" data-page="{index + 1}" style="--slide-bg:{bg};--slide-accent:{accent};--slide-secondary:{secondary};">
  <article class="slide-card sns-card">
    {click_markup}
    <div class="slide-copy">
      <div class="slide-kicker"><span>{html.escape(badge)}</span><b>{page}</b></div>
      {publication_markup}
      <h2>{html.escape(headline)}</h2>
      {_optional_tag("p", body, "slide-body")}
      {bullet_markup}
    </div>
    {character_markup}
    <div class="slide-actions">{buttons}</div>
  </article>
</section>
"""


def _image_slide_markup(slide_id: str, role: str, layout: str, image_override: dict[str, Any], click_target: str, index: int, total: int) -> str:
    bg, accent, secondary = ROLE_COLORS.get("image", ROLE_COLORS["case"])
    image_bg = _safe_color(image_override.get("background_color"), bg)
    fit = _safe_image_fit(image_override.get("fit"))
    data_uri = _clean(image_override.get("data_uri"))
    alt = _clean(image_override.get("alt")) or "사용자가 지정한 카드뉴스 이미지"
    click_markup = _click_target_markup(click_target, alt) if click_target else ""
    if _valid_data_uri(data_uri):
        image_markup = f'<img class="page-override-image" src="{html.escape(data_uri, quote=True)}" alt="{html.escape(alt, quote=True)}">'
    else:
        image_markup = '<div class="image-fallback" role="status">이미지 데이터 확인 필요</div>'
    return f"""
<section id="{html.escape(slide_id)}" class="news-slide role-{html.escape(role)} layout-{html.escape(layout)} anim-fade_up" data-page="{index + 1}" style="--slide-bg:{bg};--slide-accent:{accent};--slide-secondary:{secondary};--image-bg:{image_bg};--image-fit:{fit};">
  <article class="slide-card sns-card image-slide-card" aria-label="사용자 지정 이미지 카드 {index + 1} / {total}">
    {click_markup}
    {image_markup}
  </article>
</section>
"""


def _publication_markup(info: dict[str, Any]) -> str:
    """첫 카드에 표시할 발간호/발행 정보를 렌더링합니다."""

    issue_label = _clean(info.get("issue_label"))
    issue_date = _clean(info.get("issue_date"))
    series_name = _clean(info.get("series_name")) or "AI 카드뉴스"
    publisher = _clean(info.get("publisher")) or "SK hynix"
    if not any([issue_label, issue_date, series_name, publisher]):
        return ""
    issue = issue_label or issue_date or "월간호"
    date_markup = f"<small>{html.escape(issue_date)}</small>" if issue_date and issue_date != issue else ""
    return f"""
<div class="publication-card" aria-label="발간 정보">
  <span>{html.escape(series_name)}</span>
  <strong>{html.escape(issue)}</strong>
  {date_markup}
  <em>{html.escape(publisher)}</em>
</div>
"""


def _click_target_markup(target: str, headline: str) -> str:
    """카드 전체 클릭 시 다음 slide로 이동하는 투명 anchor를 만듭니다."""

    safe_target = _safe_anchor(target)
    label = f"다음 카드로 이동: {headline}" if headline else "다음 카드로 이동"
    return f'<a class="slide-hitarea" href="#{html.escape(safe_target)}" aria-label="{html.escape(label, quote=True)}"><span>다음 카드 보기</span></a>'


def _character_markup(character: dict[str, Any], assets: dict[str, dict[str, Any]]) -> str:
    asset_id = _clean(character.get("asset_id"))
    asset = assets.get(asset_id, {})
    data_uri = _clean(asset.get("data_uri"))
    if not _valid_data_uri(data_uri):
        return ""
    alt = _clean(asset.get("alt")) or _clean(asset.get("display_name")) or "card news character"
    placement = _safe_class(_clean(character.get("placement")) or "bottom_right")
    animation = _safe_class(_clean(character.get("animation")) or "float_in")
    return f"""
<figure class="character character-{placement} character-anim-{animation}">
  <img src="{html.escape(data_uri, quote=True)}" alt="{html.escape(alt, quote=True)}">
</figure>
"""


def _bullets_markup(bullets: list[str], layout: str) -> str:
    if not bullets:
        return ""
    item_class = "note-item" if layout in {"checklist_note", "sticker_grid"} else "bubble-item"
    items = "".join(f'<li class="{item_class}"><span>{html.escape(item)}</span></li>' for item in bullets[:5])
    return f'<ul class="slide-bullets">{items}</ul>'


def _buttons_markup(buttons: list[Any]) -> str:
    rendered = []
    for button in buttons:
        if not isinstance(button, dict):
            continue
        label = _clean(button.get("label")) or "이동"
        action = _clean(button.get("action_type"))
        target = _clean(button.get("target"))
        style = _safe_class(_clean(button.get("style")) or "primary")
        href = ""
        attrs = ""
        if action == "anchor" and target:
            href = f"#{_safe_anchor(target)}"
        elif action == "external_link" and _safe_url(target):
            href = target
            attrs = ' target="_blank" rel="noopener noreferrer"'
        if href:
            rendered.append(f'<a class="action-button button-{style}" href="{html.escape(href, quote=True)}"{attrs}>{html.escape(label)}</a>')
    return "".join(rendered)


def _navigation(slides: list[dict[str, Any]]) -> str:
    dots = []
    for index, slide in enumerate(slides):
        slide_id = _clean(slide.get("slide_id")) or f"slide-{index + 1}"
        label = _clean(slide.get("headline")) or f"카드 {index + 1}"
        dots.append(f'<a href="#{html.escape(_safe_anchor(slide_id))}" title="{html.escape(label, quote=True)}"><span>{index + 1}</span></a>')
    return f'<nav class="deck-nav" aria-label="카드뉴스 페이지 이동">{"".join(dots)}</nav>'


def _css(style: dict[str, Any], ratio_css: str) -> str:
    accent = _safe_color(style.get("accent_color"), "#EA002C")
    secondary = _safe_color(style.get("secondary_color"), "#F47725")
    bg = _safe_color(style.get("background_color"), "#FFF7ED")
    surface = _safe_color(style.get("surface_color"), "#FFFDF7")
    return f"""
:root {{
  --sk-red:{accent};
  --sk-orange:{secondary};
  --sk-bg:{bg};
  --sk-surface:{surface};
  --sk-ink:#17202A;
  --sk-muted:#64748B;
  --sk-line:#F2D9D0;
  --sk-soft-blue:#EFF6FF;
  --sk-soft-green:#ECFDF5;
  --slide-ratio:{ratio_css};
}}
* {{ box-sizing:border-box; }}
html, body {{ width:100%; height:100%; overflow:hidden; }}
body {{ margin:0; background:#F8FAFC; color:var(--sk-ink); font-family:Arial, "Noto Sans KR", sans-serif; }}
.cardnews-shell {{ width:100%; height:100svh; padding:18px 28px 24px; display:grid; grid-template-rows:auto auto minmax(0, 1fr); gap:12px; background:#F8FAFC; overflow:hidden; }}
.deck-header {{ width:min(100%, 1180px); margin:0 auto; display:flex; align-items:flex-end; justify-content:space-between; gap:16px; }}
.brand-chip {{ display:inline-flex; margin:0 0 6px; padding:6px 11px; border:1px solid #FFD0D9; border-radius:999px; background:#fff; color:var(--sk-red); font-size:12px; font-weight:850; }}
h1 {{ margin:0; font-size:34px; line-height:1.12; }}
.deck-subtitle {{ margin:6px 0 0; color:var(--sk-muted); font-size:14px; line-height:1.45; }}
.home-link {{ flex:0 0 auto; display:inline-flex; min-width:46px; min-height:36px; align-items:center; justify-content:center; padding:8px 12px; border-radius:999px; background:var(--sk-red); color:#fff; text-decoration:none; font-size:12px; font-weight:850; }}
.deck-nav {{ z-index:5; width:min(100%, 1180px); margin:0 auto; padding:8px; display:flex; justify-content:center; gap:8px; overflow:auto; border:1px solid var(--sk-line); border-radius:999px; background:rgba(255, 255, 255, .9); backdrop-filter:blur(8px); }}
.deck-nav a {{ flex:0 0 auto; width:30px; height:30px; display:grid; place-items:center; border-radius:50%; background:#FFF0E6; color:#9A3412; text-decoration:none; font-size:12px; font-weight:850; transition:background .18s ease, color .18s ease, transform .18s ease; }}
.deck-nav a:hover, .deck-nav a:focus {{ outline:2px solid var(--sk-orange); outline-offset:2px; background:var(--sk-orange); color:#fff; transform:translateY(-1px); }}
.slide-stage {{ position:relative; width:min(100%, 1180px); min-height:0; margin:0 auto; overflow:hidden; }}
.news-slide {{ position:absolute; inset:0; display:grid; place-items:center; padding:6px; opacity:0; pointer-events:none; transform:translateX(34px) scale(.985); transition:opacity .42s ease, transform .46s cubic-bezier(.2,.8,.2,1); }}
.news-slide:first-child {{ opacity:1; pointer-events:auto; transform:translateX(0) scale(1); }}
.slide-stage:has(.news-slide:target) .news-slide:first-child {{ opacity:0; pointer-events:none; transform:translateX(-34px) scale(.985); }}
.slide-stage:has(.news-slide:target) .news-slide:first-child:target,
.news-slide:target {{ opacity:1; pointer-events:auto; transform:translateX(0) scale(1); }}
.slide-card {{ position:relative; width:min(100%, 1120px, calc(176svh - 278px)); max-height:100%; aspect-ratio:var(--slide-ratio); overflow:hidden; border:1px solid rgba(234, 0, 44, .14); border-radius:22px; background:var(--slide-bg); box-shadow:0 22px 58px rgba(15, 23, 42, .14); padding:36px 42px; display:grid; grid-template-rows:1fr auto; isolation:isolate; }}
.slide-card::before {{ content:""; position:absolute; inset:18px; border:2px dashed rgba(234, 0, 44, .16); border-radius:16px; pointer-events:none; }}
.slide-card::after {{ content:""; position:absolute; right:34px; bottom:31px; width:38%; height:14px; border-radius:999px; background:rgba(244, 119, 37, .22); box-shadow:0 -24px 0 rgba(234, 0, 44, .08); transform:rotate(-2deg); pointer-events:none; }}
.image-slide-card {{ padding:0; background:var(--image-bg); display:block; }}
.image-slide-card::before, .image-slide-card::after {{ display:none; }}
.page-override-image {{ position:relative; z-index:0; display:block; width:100%; height:100%; object-fit:var(--image-fit); background:var(--image-bg); }}
.image-fallback {{ width:100%; height:100%; display:grid; place-items:center; padding:24px; color:var(--sk-red); background:var(--image-bg); font-size:16px; font-weight:850; text-align:center; }}
.slide-hitarea {{ position:absolute; inset:0; z-index:1; border-radius:22px; text-decoration:none; cursor:pointer; }}
.slide-hitarea span {{ position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; }}
.slide-hitarea:focus {{ outline:4px solid rgba(244, 119, 37, .5); outline-offset:-8px; }}
.slide-card:has(.slide-hitarea):hover {{ box-shadow:0 26px 66px rgba(15, 23, 42, .17); }}
.slide-copy {{ position:relative; z-index:2; max-width:70%; pointer-events:none; }}
.layout-cover_character .slide-copy, .layout-cta_character .slide-copy {{ max-width:68%; }}
.layout-checklist_note .slide-copy, .layout-sticker_grid .slide-copy {{ max-width:82%; }}
.slide-kicker {{ display:flex; align-items:center; gap:9px; flex-wrap:wrap; margin-bottom:12px; }}
.slide-kicker span {{ display:inline-flex; min-height:30px; align-items:center; padding:6px 11px; border-radius:999px; background:#fff; color:var(--slide-accent); font-size:12px; font-weight:850; box-shadow:0 5px 14px rgba(15, 23, 42, .07); }}
.slide-kicker b {{ color:var(--slide-secondary); font-size:12px; }}
.publication-card {{ display:flex; align-items:center; gap:9px; flex-wrap:wrap; margin:0 0 14px; padding:8px 0; border-top:1px solid rgba(234, 0, 44, .16); border-bottom:1px solid rgba(244, 119, 37, .18); }}
.publication-card span {{ color:var(--sk-muted); font-size:12px; font-weight:800; }}
.publication-card strong {{ color:var(--sk-red); font-size:20px; line-height:1.15; }}
.publication-card small {{ color:#9A3412; font-size:12px; font-weight:750; }}
.publication-card em {{ color:var(--sk-muted); font-size:11px; font-style:normal; }}
h2 {{ margin:0; max-width:100%; font-size:42px; line-height:1.1; color:var(--slide-accent); overflow-wrap:anywhere; }}
.slide-body {{ margin:14px 0 0; max-width:36em; color:#334155; font-size:18px; line-height:1.52; overflow-wrap:anywhere; }}
.slide-bullets {{ list-style:none; padding:0; margin:16px 0 0; display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:10px; }}
.slide-bullets li {{ display:flex; align-items:flex-start; gap:9px; min-height:50px; padding:10px 12px; border-radius:16px; background:rgba(255, 255, 255, .84); box-shadow:0 8px 18px rgba(15, 23, 42, .07); color:#1F2937; font-size:14px; line-height:1.45; overflow-wrap:anywhere; }}
.slide-bullets li::before {{ content:""; flex:0 0 auto; width:9px; height:9px; margin-top:6px; border-radius:50%; background:var(--slide-secondary); }}
.character {{ position:absolute; z-index:1; margin:0; pointer-events:none; }}
.character img {{ display:block; width:clamp(150px, 22vw, 268px); height:auto; object-fit:contain; filter:drop-shadow(0 18px 24px rgba(15, 23, 42, .16)); animation:mascotIdle 3.6s ease-in-out infinite; transform-origin:50% 86%; }}
.character-bottom_right {{ right:40px; bottom:58px; }}
.character-bottom_left {{ left:40px; bottom:58px; }}
.character-right {{ right:40px; top:50%; transform:translateY(-50%); }}
.character-left {{ left:40px; top:50%; transform:translateY(-50%); }}
.character-center {{ right:50%; bottom:56px; transform:translateX(50%); }}
.slide-actions {{ position:relative; z-index:3; display:flex; flex-wrap:wrap; gap:10px; align-items:center; justify-content:flex-end; }}
.action-button {{ display:inline-flex; min-height:42px; align-items:center; justify-content:center; padding:10px 15px; border-radius:999px; text-decoration:none; font-size:14px; font-weight:850; line-height:1.2; box-shadow:0 10px 20px rgba(15, 23, 42, .12); }}
.button-primary {{ background:var(--sk-red); color:#fff; }}
.button-secondary {{ background:#fff; color:var(--sk-red); border:1px solid #FFD0D9; }}
.action-button:hover, .action-button:focus {{ outline:3px solid rgba(244, 119, 37, .45); outline-offset:2px; }}
.news-slide:target .slide-copy,
.news-slide:first-child .slide-copy {{ animation:fadeUp .55s ease both; }}
.anim-slide_in .slide-copy {{ animation:copySlideIn .62s ease both; }}
.anim-stagger .slide-bullets li {{ animation:fadeUp .48s ease both; }}
.anim-stagger .slide-bullets li:nth-child(2) {{ animation-delay:.07s; }}
.anim-stagger .slide-bullets li:nth-child(3) {{ animation-delay:.14s; }}
.character-anim-pulse_soft img {{ animation:mascotPulse 2.6s ease-in-out infinite; }}
.character-anim-slide_in img {{ animation:mascotPeek 3.8s ease-in-out infinite; }}
.character-anim-fade_up img, .character-anim-stagger img, .character-anim-float_in img {{ animation:mascotIdle 3.6s ease-in-out infinite; }}
@keyframes fadeUp {{ from {{ opacity:0; transform:translateY(12px); }} to {{ opacity:1; transform:translateY(0); }} }}
@keyframes copySlideIn {{ from {{ opacity:0; transform:translateX(-18px); }} to {{ opacity:1; transform:translateX(0); }} }}
@keyframes mascotIdle {{ 0%,100% {{ transform:translateY(0) rotate(-1deg); }} 50% {{ transform:translateY(-9px) rotate(1deg); }} }}
@keyframes mascotPulse {{ 0%,100% {{ transform:scale(1) rotate(-1deg); }} 50% {{ transform:scale(1.035) rotate(1.5deg); }} }}
@keyframes mascotPeek {{ 0%,100% {{ transform:translateX(0) translateY(0); }} 50% {{ transform:translateX(-7px) translateY(-5px); }} }}
@media (max-width: 900px) {{
  .cardnews-shell {{ padding:14px 12px 18px; gap:9px; }}
  .deck-header {{ align-items:flex-start; }}
  h1 {{ font-size:26px; }}
  .deck-subtitle {{ font-size:13px; }}
  .deck-nav {{ justify-content:flex-start; }}
  .slide-card {{ width:100%; padding:24px 22px; border-radius:18px; }}
  .image-slide-card {{ padding:0; }}
  .slide-copy, .layout-cover_character .slide-copy, .layout-cta_character .slide-copy {{ max-width:100%; }}
  h2 {{ font-size:28px; }}
  .slide-body {{ font-size:15px; }}
  .slide-bullets {{ grid-template-columns:1fr; gap:8px; }}
  .slide-bullets li {{ min-height:42px; font-size:13px; }}
  .character {{ opacity:.22; right:16px; bottom:48px; left:auto; top:auto; transform:none; }}
  .character img {{ width:170px; }}
  .slide-actions {{ justify-content:flex-start; }}
}}
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ animation-duration:.001ms !important; animation-iteration-count:1 !important; transition-duration:.001ms !important; }}
}}
"""


def _asset_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = {}
    for asset in _list(manifest.get("assets")):
        if isinstance(asset, dict) and _clean(asset.get("asset_id")):
            result[_clean(asset.get("asset_id"))] = deepcopy(asset)
    return result


def _missing_asset_warnings(slides: list[dict[str, Any]], assets: dict[str, dict[str, Any]]) -> list[str]:
    warnings = []
    for index, slide in enumerate(slides, start=1):
        image_override = _dict(slide.get("image_override"))
        if image_override and not _valid_data_uri(_clean(image_override.get("data_uri"))):
            warnings.append(f"{index}페이지 이미지 대체 data_uri가 유효하지 않아 fallback 문구를 표시했습니다.")
        asset_id = _clean(_dict(slide.get("character")).get("asset_id"))
        if asset_id and not _valid_data_uri(_clean(assets.get(asset_id, {}).get("data_uri"))):
            warnings.append(f"캐릭터 이미지가 아직 유효한 base64가 아니라 HTML에서 생략했습니다: {asset_id}")
    return warnings


def _security_report(document: str) -> dict[str, Any]:
    lowered = document.lower()
    violations = [marker for marker in FORBIDDEN_HTML_MARKERS if marker in lowered]
    return {
        "passed": not violations,
        "policy": "card_news_static_html_v1",
        "violations": violations,
    }


def _valid_data_uri(value: str) -> bool:
    return bool(value) and value.startswith(ALLOWED_IMAGE_PREFIXES) and not any(marker in value for marker in PLACEHOLDER_MARKERS)


def _optional_tag(tag: str, value: str, class_name: str) -> str:
    return f'<{tag} class="{class_name}">{html.escape(value)}</{tag}>' if value else ""


def _role_label(role: str) -> str:
    labels = {
        "cover": "이번 달 AI 소식",
        "why": "WHY",
        "case": "사례",
        "workflow": "업무 흐름",
        "tip": "TIP",
        "checklist": "CHECK",
        "security": "보안",
        "caution": "주의",
        "quiz": "QUIZ",
        "recap": "요약",
        "cta": "NEXT",
        "closing": "마무리",
    }
    return labels.get(role, role.upper())


def _payload(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return deepcopy(value)
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


def _safe_color(value: Any, default: str) -> str:
    text = _clean(value)
    if len(text) == 7 and text.startswith("#") and all(ch in "0123456789abcdefABCDEF" for ch in text[1:]):
        return text
    return default


def _safe_image_fit(value: Any) -> str:
    text = _clean(value).lower()
    return text if text in {"contain", "cover", "fill"} else "contain"


def _safe_class(value: str) -> str:
    result = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in value.lower())
    return result or "default"


def _safe_anchor(value: str) -> str:
    return _safe_class(value)


def _safe_url(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def _filename_hint(value: Any) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in _clean(value)).strip("_")
    return (safe or "card_news")[:80]


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _dedupe(items: list[Any]) -> list[str]:
    result = []
    for item in items:
        text = _clean(item)
        if text and text not in result:
            result.append(text)
    return result


class CardNewsHtmlRenderer(Component):
    display_name = "06 카드뉴스 HTML 렌더링"
    description = "검증된 카드뉴스 계획을 SK 컬러 기반 독립 실행형 HTML로 렌더링합니다."
    icon = "FileCode2"
    inputs = [DataInput(name="card_news_plan", display_name="카드뉴스 계획", required=True)]
    outputs = [Output(name="html_result", display_name="HTML 생성 결과", method="build_payload", types=["Data"])]

    def build_payload(self) -> Data:
        result = render_card_news_html(getattr(self, "card_news_plan", None))
        html_result = _dict(result.get("html_result"))
        self.status = {
            "제목": html_result.get("title"),
            "카드 수": html_result.get("slide_count"),
            "HTML bytes": len(_clean(html_result.get("html")).encode("utf-8")),
            "보안 통과": _dict(html_result.get("security_report")).get("passed"),
        }
        return Data(data=result)
