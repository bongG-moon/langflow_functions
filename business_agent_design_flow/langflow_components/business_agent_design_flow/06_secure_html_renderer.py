from __future__ import annotations

import html
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, Output
from lfx.schema.data import Data


def render_secure_html(agent_design_value: Any) -> dict[str, Any]:
    """검증된 설계 JSON을 정적 HTML로 렌더링합니다. LLM이 생성한 HTML은 사용하지 않습니다."""
    payload = _payload(agent_design_value)
    design = _dict(payload.get("agent_design"))
    validation = _dict(payload.get("validation_report"))
    flags = _dict(validation.get("validation_flags"))

    title = design.get("report_title") or "업무 AI Agent 개선 설계"
    body = _render_invalid_body(validation) if flags.get("valid") is False else _render_report_body(design, payload)
    document = _document(title=title, summary=design.get("summary") or "", body=body)
    security_report = {
        "passed": _security_passed(document),
        "renderer": "deterministic_secure_renderer",
        "policy": "no_script_no_iframe_inline_css_only",
        "size_bytes": len(document.encode("utf-8")),
        "rendered_at": _now_iso(),
    }

    return {
        **payload,
        "html_result": {
            "title": title,
            "html": document,
            "security_report": security_report,
        },
    }


def _render_report_body(design: dict[str, Any], payload: dict[str, Any]) -> str:
    trace = _dict(payload.get("recommendation_trace"))
    return (
        "<section class='grid two'>"
        f"<div class='section'>{_section_header('현재 업무 Flow', '사용자가 실제로 수행하는 흐름입니다.')}"
        f"<div class='flow'>{_render_steps(design.get('as_is_flow'), '현재')}</div></div>"
        f"<div class='section'>{_section_header('AI Agent 적용 후 Flow', '자동화, 보조, 사람 검토 단계를 구분한 개선 흐름입니다.')}"
        f"<div class='flow'>{_render_steps(design.get('to_be_flow'), '개선')}</div></div>"
        "</section>"
        f"<section class='section'>{_section_header('추천 기능 매핑', '카탈로그에서 선택된 기능과 적용 이유입니다.')}"
        f"<div class='cards'>{_render_capabilities(design.get('recommended_capabilities'))}</div></section>"
        "<section class='grid two'>"
        f"<div class='section'>{_section_header('구현 순서', '초보 Langflow 개발자가 따라갈 수 있는 작업 순서입니다.')}"
        f"{_render_roadmap(design.get('implementation_roadmap'))}</div>"
        f"<div class='section'>{_section_header('리스크 통제', '자동화 전에 확인해야 할 사람 검토 지점입니다.')}"
        f"{_render_risks(design.get('risk_controls'))}</div>"
        "</section>"
        "<section class='grid two'>"
        f"<div class='section'>{_section_header('대안 옵션', '상황에 따라 선택할 수 있는 구현 방식입니다.')}"
        f"{_render_alternatives(design.get('alternative_options'))}</div>"
        f"<div class='section'>{_section_header('추천 근거 Trace', '어떤 카탈로그 항목을 근거로 삼았는지 확인합니다.')}"
        f"{_render_trace(trace)}</div>"
        "</section>"
    )


def _render_invalid_body(validation: dict[str, Any]) -> str:
    issues = validation.get("issues") or ["필수 설계 정보가 부족합니다."]
    return (
        "<section class='section danger'>"
        f"{_section_header('검증 실패', '설계 JSON에 보완이 필요한 항목이 있습니다.')}"
        f"{_render_plain_list(issues)}"
        "</section>"
    )


def _document(title: str, summary: str, body: str) -> str:
    safe_title = _safe(title)
    safe_summary = _safe(summary)
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; font-src 'self' data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none';">
  <title>{safe_title}</title>
  <style>
    :root {{
      --primary:#5267f5;
      --primary-2:#6f3fd8;
      --ink:#171c2a;
      --muted:#667085;
      --line:#d9deea;
      --soft:#f6f8fc;
      --card:#ffffff;
      --danger:#b42318;
      --shadow:0 18px 46px rgba(26, 37, 74, .10);
    }}
    * {{ box-sizing:border-box; }}
    body {{
      margin:0;
      background:#eef2f8;
      color:var(--ink);
      font-family:Arial, 'Malgun Gothic', sans-serif;
      line-height:1.55;
    }}
    .page {{ max-width:1280px; margin:0 auto; padding:32px; }}
    .hero {{
      background:linear-gradient(135deg, var(--primary), var(--primary-2));
      color:#fff;
      border-radius:18px;
      padding:34px 38px;
      box-shadow:var(--shadow);
    }}
    .eyebrow {{ font-size:13px; font-weight:800; letter-spacing:.08em; opacity:.82; text-transform:uppercase; }}
    h1 {{ margin:8px 0 10px; font-size:34px; line-height:1.2; letter-spacing:0; }}
    h2 {{ margin:0; font-size:22px; line-height:1.25; letter-spacing:0; }}
    h3 {{ margin:0 0 8px; font-size:16px; line-height:1.35; letter-spacing:0; }}
    p {{ margin:0; }}
    .grid {{ display:grid; gap:18px; margin-top:22px; }}
    .two {{ grid-template-columns:1fr 1fr; }}
    .section {{
      background:var(--card);
      border:1px solid var(--line);
      border-radius:14px;
      padding:24px;
      box-shadow:0 10px 26px rgba(20, 32, 60, .06);
    }}
    .section-title {{ display:flex; gap:12px; align-items:flex-start; margin-bottom:18px; }}
    .section-title:before {{
      content:"";
      width:5px;
      height:30px;
      border-radius:999px;
      background:var(--primary);
      flex:none;
      margin-top:2px;
    }}
    .hint {{ color:var(--muted); margin-top:8px; font-size:14px; }}
    .flow {{ display:grid; gap:12px; }}
    .flow-step {{
      border:1px solid var(--line);
      border-left:5px solid var(--primary);
      border-radius:12px;
      padding:15px 16px;
      background:#fff;
    }}
    .badges {{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:8px; }}
    .badge {{
      display:inline-flex;
      padding:3px 9px;
      border-radius:999px;
      background:#edf0ff;
      color:#3346c4;
      font-size:12px;
      font-weight:700;
    }}
    .badge.subtle {{ background:#f1f4f9; color:#536074; }}
    .cards {{ display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:12px; }}
    .cap-card {{
      border:1px solid var(--line);
      border-radius:12px;
      padding:15px;
      background:var(--soft);
      min-height:142px;
    }}
    .muted {{ color:var(--muted); }}
    .links {{ margin-top:10px; display:flex; gap:8px; flex-wrap:wrap; }}
    .links a {{ color:#3346c4; font-weight:700; text-decoration:none; font-size:13px; }}
    .list {{ margin:0; padding-left:20px; }}
    .list li + li {{ margin-top:9px; }}
    .list span {{ display:block; color:var(--muted); margin-top:2px; }}
    .danger {{ border-color:#fecdca; }}
    .danger .section-title:before {{ background:var(--danger); }}
    .footer {{ margin-top:18px; color:var(--muted); font-size:12px; }}
    @media (max-width: 900px) {{
      .page {{ padding:18px; }}
      .two, .cards {{ grid-template-columns:1fr; }}
      h1 {{ font-size:27px; }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <div class="eyebrow">Business Agent Design</div>
      <h1>{safe_title}</h1>
      <p>{safe_summary}</p>
    </section>
    {body}
    <p class="footer">Generated at {_safe(_now_iso())}. 이 HTML은 검증된 deterministic renderer에서 생성되었습니다.</p>
  </main>
</body>
</html>"""


def _section_header(title: str, hint: str) -> str:
    return (
        "<div class='section-title'>"
        f"<div><h2>{_safe(title)}</h2><p class='hint'>{_safe(hint)}</p></div>"
        "</div>"
    )


def _render_steps(steps: Any, fallback_label: str) -> str:
    rows = []
    for index, item in enumerate(_as_list(steps)[:12], 1):
        step = _dict(item)
        role = step.get("agent_role") or step.get("actor") or ""
        systems = ", ".join(_string_list(step.get("systems"), 5))
        badges = f"<span class='badge'>{index}</span>"
        if role:
            badges += f"<span class='badge subtle'>{_safe(role)}</span>"
        if systems:
            badges += f"<span class='badge subtle'>{_safe(systems)}</span>"
        rows.append(
            "<article class='flow-step'>"
            f"<div class='badges'>{badges}</div>"
            f"<h3>{_safe(step.get('title') or fallback_label)}</h3>"
            f"<p class='muted'>{_safe(step.get('description') or '')}</p>"
            "</article>"
        )
    return "".join(rows) or "<p class='muted'>표시할 단계가 없습니다.</p>"


def _render_capabilities(items: Any) -> str:
    rows = []
    for item in _as_list(items)[:9]:
        cap = _dict(item)
        links = [
            link
            for link in _string_list(cap.get("source_links"), 4)
            if link.startswith(("http://", "https://", "local:", "internal:"))
        ]
        link_html = ""
        if links:
            link_html = "<div class='links'>" + "".join(_link_html(link, index) for index, link in enumerate(links, 1)) + "</div>"
        review = "사람 검토 필요" if cap.get("human_review_required") else "자동화 가능"
        rows.append(
            "<article class='cap-card'>"
            f"<div class='badges'><span class='badge'>{_safe(cap.get('catalog_id'))}</span><span class='badge subtle'>{_safe(review)}</span></div>"
            f"<h3>{_safe(cap.get('usage') or '추천 기능')}</h3>"
            f"<p class='muted'>{_safe(cap.get('reason') or '')}</p>"
            f"{link_html}"
            "</article>"
        )
    return "".join(rows) or "<p class='muted'>추천 기능이 없습니다.</p>"


def _link_html(link: str, index: int) -> str:
    safe_link = _safe(link)
    if link.startswith(("http://", "https://")):
        return f"<a href='{safe_link}' target='_blank' rel='noreferrer noopener'>참고 링크 {index}</a>"
    return f"<span class='muted'>{safe_link}</span>"


def _render_roadmap(items: Any) -> str:
    rows = []
    for item in _as_list(items)[:12]:
        row = _dict(item)
        rows.append(
            "<li>"
            f"<strong>{_safe(row.get('phase') or '단계')}</strong>"
            f"<span>{_safe(row.get('action') or '')}</span>"
            f"<span>{_safe(row.get('owner') or '')}</span>"
            "</li>"
        )
    return "<ol class='list'>" + "".join(rows) + "</ol>" if rows else "<p class='muted'>구현 순서가 없습니다.</p>"


def _render_risks(items: Any) -> str:
    rows = []
    for item in _as_list(items)[:12]:
        row = _dict(item)
        review = "사람 검토 필요" if row.get("human_review_required") else "자동 통제 가능"
        rows.append(
            "<li>"
            f"<strong>{_safe(row.get('risk') or '위험')}</strong>"
            f"<span>{_safe(row.get('control') or '')}</span>"
            f"<span>{_safe(review)}</span>"
            "</li>"
        )
    return "<ol class='list'>" + "".join(rows) + "</ol>" if rows else "<p class='muted'>리스크 항목이 없습니다.</p>"


def _render_alternatives(items: Any) -> str:
    rows = []
    for item in _as_list(items)[:8]:
        row = _dict(item)
        rows.append(
            "<li>"
            f"<strong>{_safe(row.get('option') or '대안')}</strong>"
            f"<span>{_safe(row.get('tradeoff') or '')}</span>"
            "</li>"
        )
    return "<ol class='list'>" + "".join(rows) + "</ol>" if rows else "<p class='muted'>대안 옵션이 없습니다.</p>"


def _render_trace(trace: dict[str, Any]) -> str:
    selected = trace.get("selected_item_keys") or trace.get("used_catalog_ids") or []
    lines = [
        f"Trace ID: {trace.get('trace_id', '-')}",
        f"검색 소스: {trace.get('retrieval_source', '-')}",
        "선택 항목: " + ", ".join(str(item) for item in selected),
    ]
    return _render_plain_list(lines)


def _render_plain_list(items: Any) -> str:
    rows = [f"<li>{_safe(item)}</li>" for item in _as_list(items)]
    return "<ul class='list'>" + "".join(rows) + "</ul>" if rows else "<p class='muted'>표시할 항목이 없습니다.</p>"


def _security_passed(document: str) -> bool:
    lowered = document.lower()
    blocked = ["<script", "</script", "<iframe", "<object", "<embed", "javascript:"]
    return not any(token in lowered for token in blocked)


def _payload(value: Any) -> dict[str, Any]:
    data = getattr(value, "data", value)
    return deepcopy(data) if isinstance(data, dict) else {}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value in (None, "", {}):
        return []
    return [value]


def _string_list(value: Any, limit: int = 12) -> list[str]:
    result = []
    seen = set()
    for item in _as_list(value):
        text = str(item or "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
        if len(result) >= limit:
            break
    return result


def _safe(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class SecureHtmlRenderer(Component):
    display_name = "06 HTML 업무 Flow 렌더링"
    description = "AI Agent 설계 JSON을 안전한 정적 HTML 리포트로 렌더링합니다."
    icon = "FileCode"
    inputs = [DataInput(name="agent_design", display_name="AI Agent 설계 결과", required=True)]
    outputs = [Output(name="html_result", display_name="HTML 생성 결과", method="build_payload")]

    def build_payload(self) -> Data:
        result = render_secure_html(getattr(self, "agent_design", None))
        security = result.get("html_result", {}).get("security_report", {})
        self.status = {
            "HTML 제목": result.get("html_result", {}).get("title"),
            "보안 검사": "통과" if security.get("passed") else "확인 필요",
            "HTML 크기(bytes)": security.get("size_bytes"),
        }
        return Data(data=result)
