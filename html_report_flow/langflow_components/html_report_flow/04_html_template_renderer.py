from __future__ import annotations

"""04 HTML 렌더링 노드.

이 파일은 최종 report_plan과 rows 데이터를 받아 독립 실행 가능한 HTML 문자열을 만듭니다.
03/03b까지는 "어떤 블록을 어떤 순서와 스타일로 보여줄지"를 계획하고,
이 파일은 그 계획을 실제 HTML/CSS 조각으로 바꿉니다.
"""

import html
import json
from copy import deepcopy
from datetime import datetime
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, Output
from lfx.schema.data import Data


# 차트에서 반복 사용되는 기본 색상 팔레트입니다.
CHART_COLORS = ["#2563eb", "#0f766e", "#f59e0b", "#dc2626", "#7c3aed", "#0891b2", "#65a30d", "#be185d", "#475569", "#ea580c"]


def render_html_report(payload_value: Any) -> dict[str, Any]:
    """최종 payload를 받아 HTML 원문을 생성하고 `html_report`에 담아 반환합니다."""

    payload = _payload(payload_value)
    plan = _dict(payload.get("report_plan"))
    data = _dict(_dict(payload.get("api_response")).get("data"))
    rows = _rows(data.get("rows"))
    columns = _strings(data.get("columns")) or _columns_from_rows(rows)
    title = str(plan.get("title") or "HTML 데이터 리포트")
    blocks = _list(plan.get("blocks"))
    rendered_blocks = []
    for block in blocks:
        # block_id에 따라 KPI/차트/표/문장 블록 중 하나를 렌더링합니다.
        if not isinstance(block, dict):
            continue
        rendered = _render_block(block, payload, rows, columns)
        if rendered:
            rendered_blocks.append(_wrap_block(block, rendered))
    document = _document(title, str(plan.get("subtitle") or ""), rendered_blocks, plan)
    result = _compact_renderer_payload(payload)
    result["html_report"] = {
        **_dict(payload.get("html_report")),
        "title": title,
        "html": document,
        "row_count": int(data.get("row_count") or len(rows)),
        "blocks": [block.get("block_id") for block in blocks if isinstance(block, dict)],
        "filename_hint": _filename_hint(title),
        "rendered_at": datetime.now().isoformat(timespec="seconds"),
    }
    return result


def _compact_renderer_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """렌더링 이후에도 필요한 payload 정보만 추려 다음 노드로 넘깁니다."""

    result: dict[str, Any] = {
        "payload_version": payload.get("payload_version", "html-report-demo-v1"),
        "flow_type": payload.get("flow_type", "html_report_demo"),
        "status": payload.get("status", "ok"),
        "request": _dict(payload.get("request")),
        "available_datasets": _list(payload.get("available_datasets")),
        "api_response": _dict(payload.get("api_response")),
        "data_summary": _dict(payload.get("data_summary")),
        "report_plan": _dict(payload.get("report_plan")),
        "warnings": _list(payload.get("warnings")),
        "errors": _list(payload.get("errors")),
    }
    for key in ("llm_report_plan",):
        if payload.get(key):
            result[key] = deepcopy(payload[key])
    return result


def _render_block(block: dict[str, Any], payload: dict[str, Any], rows: list[dict[str, Any]], columns: list[str]) -> str:
    """block_id를 보고 알맞은 렌더링 함수로 분기합니다."""

    block_id = str(block.get("block_id") or "")
    markup = ""
    if block_id == "report_header":
        markup = _report_header(block, payload, rows)
    elif block_id == "scope_summary":
        markup = _scope_summary(block, payload, rows, columns)
    elif block_id == "warning_box":
        markup = _warning_box(block, payload)
    elif block_id == "empty_state":
        markup = _empty_state(block)
    elif block_id in {"kpi_card_grid", "metric_delta_card_grid"}:
        markup = _kpi_cards(block, rows)
    elif block_id == "comparison_bar_chart":
        markup = _bar_chart(block, rows)
    elif block_id == "donut_chart":
        markup = _donut_chart(block, rows)
    elif block_id == "grouped_bar_chart":
        markup = _grouped_bar_chart(block, rows)
    elif block_id == "stacked_comparison_bar":
        markup = _stacked_bar_chart(block, rows)
    elif block_id == "trend_line_chart":
        markup = _line_chart(block, rows)
    elif block_id == "distribution_histogram":
        markup = _histogram_chart(block, rows)
    elif block_id == "scatter_plot":
        markup = _scatter_plot(block, rows)
    elif block_id in {"heatmap_matrix", "pivot_matrix_table"}:
        markup = _heatmap_matrix(block, rows)
    elif block_id in {"ranking_table", "detail_data_table", "period_comparison_table", "outlier_exception_table"}:
        markup = _table(block, rows, columns)
    elif block_id == "insight_bullets":
        markup = _insight_bullets(block, payload, rows)
    elif block_id == "recommendation_list":
        markup = _recommendations(block, payload)
    elif block_id == "method_note":
        markup = _method_note(block, payload)
    return _decorate_block_markup(block, markup)


def _report_header(block: dict[str, Any], payload: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    """리포트 최상단 제목/부제목/row 수 메타 정보를 그립니다."""

    plan = _dict(payload.get("report_plan"))
    request = _dict(payload.get("request"))
    data = _dict(_dict(payload.get("api_response")).get("data"))
    title = html.escape(str(plan.get("title") or block.get("title") or "HTML 데이터 리포트"))
    subtitle = html.escape(str(plan.get("subtitle") or request.get("view_request") or request.get("question") or ""))
    row_count = int(data.get("row_count") or len(rows))
    audience = str(plan.get("audience") or "").strip()
    goal = str(plan.get("report_goal") or "").strip()
    badge = str(block.get("badge") or audience or "HTML REPORT").strip()
    meta = [f"{row_count:,} rows"]
    if audience:
        meta.append(f"Audience: {audience}")
    if goal:
        meta.append(f"Goal: {goal}")
    return f"""
<section class="hero">
  <div>
    <p class="eyebrow">{html.escape(badge)}</p>
    <h1>{title}</h1>
    <p class="subtitle">{subtitle}</p>
  </div>
  <div class="hero-meta">
    {''.join(f'<span>{html.escape(item)}</span>' for item in meta)}
  </div>
</section>
"""


def _scope_summary(block: dict[str, Any], payload: dict[str, Any], rows: list[dict[str, Any]], columns: list[str]) -> str:
    """데이터셋명, row 수, preview 여부, 컬럼 수를 카드 형태로 요약합니다."""

    request = _dict(payload.get("request"))
    data = _dict(_dict(payload.get("api_response")).get("data"))
    datasets = _list(payload.get("available_datasets"))
    selected = str(request.get("selected_dataset_id") or "")
    dataset_label = selected
    for item in datasets:
        if isinstance(item, dict) and str(item.get("dataset_id")) == selected:
            dataset_label = str(item.get("label") or selected)
            break
    items = [
        ("Dataset", dataset_label or "demo_dataset"),
        ("Rows", f"{int(data.get('row_count') or len(rows)):,}"),
        ("Preview", "Yes" if data.get("data_is_preview") else "No"),
        ("Columns", f"{len(columns):,}"),
    ]
    cards = "".join(f"<div><b>{html.escape(label)}</b><span>{html.escape(value)}</span></div>" for label, value in items)
    return f"""
<section class="panel">
  <h2>{html.escape(str(block.get("title") or "데이터 범위"))}</h2>
  <div class="scope-grid">{cards}</div>
</section>
"""


def _warning_box(block: dict[str, Any], payload: dict[str, Any]) -> str:
    """경고/오류/preview 제한 같은 사용자가 알아야 할 주의사항을 표시합니다."""

    warnings = [str(item) for item in _list(payload.get("warnings"))]
    errors = [str(item) for item in _list(payload.get("errors"))]
    data = _dict(_dict(payload.get("api_response")).get("data"))
    if data.get("data_is_preview"):
        warnings.append("전체 row 중 일부 preview만 HTML에 표시될 수 있습니다.")
    if not warnings and not errors:
        return ""
    lines = "".join(f"<li>{html.escape(item)}</li>" for item in [*errors, *warnings])
    return f"""
<section class="notice">
  <h2>{html.escape(str(block.get("title") or "확인 필요 사항"))}</h2>
  <ul>{lines}</ul>
</section>
"""


def _empty_state(block: dict[str, Any]) -> str:
    """row가 없을 때 보여줄 빈 상태 안내 블록을 만듭니다."""

    return f"""
<section class="panel empty">
  <h2>{html.escape(str(block.get("title") or "조회 결과 없음"))}</h2>
  <p>조건에 맞는 데이터가 없습니다. 입력 데이터 또는 조회 조건을 확인하세요.</p>
</section>
"""


def _kpi_cards(block: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    """metric 설정을 집계해서 KPI 카드 묶음으로 표시합니다."""

    metrics = [item for item in _list(block.get("metrics")) if isinstance(item, dict)]
    if not metrics:
        return ""
    cards = []
    for metric in metrics[:4]:
        column = str(metric.get("column") or "")
        aggregation = str(metric.get("aggregation") or "sum")
        label = str(metric.get("label") or column)
        value = _aggregate(rows, column, aggregation)
        cards.append(
            f"""
<div class="kpi-card">
  <span>{html.escape(label)}</span>
  <strong>{html.escape(_format_number(value))}</strong>
  <small>{html.escape(aggregation)}</small>
</div>
"""
        )
    return f"""
<section class="panel">
  <h2>{html.escape(str(block.get("title") or "주요 지표"))}</h2>
  <div class="kpi-grid">{''.join(cards)}</div>
</section>
"""


def _bar_chart(block: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    """범주별 숫자 합계를 수평 막대 그래프로 그립니다."""

    policy = _dict(block.get("chart_policy"))
    x = str(block.get("x") or policy.get("x") or "")
    y = str(block.get("y") or policy.get("y") or "")
    limit = _positive_int(block.get("limit") or policy.get("limit"), 10)
    grouped = _group_sum(rows, x, y)[:limit]
    if not grouped:
        return ""
    max_value = max(value for _, value in grouped) or 1
    bars = []
    for label, value in grouped:
        width = max(2, round(value / max_value * 100))
        bars.append(
            f"""
<div class="bar-row">
  <span class="bar-label">{html.escape(str(label))}</span>
  <div class="bar-track"><div class="bar-fill" style="width:{width}%"></div></div>
  <span class="bar-value">{html.escape(_format_number(value))}</span>
</div>
"""
        )
    return f"""
<section class="panel">
  <h2>{html.escape(str(block.get("title") or "그룹별 비교"))}</h2>
  <div class="bar-chart chart-zone">{''.join(bars)}</div>
</section>
"""


def _donut_chart(block: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    """범주별 구성비를 CSS conic-gradient 기반 도넛 차트로 그립니다."""

    policy = _dict(block.get("chart_policy"))
    x = str(block.get("x") or policy.get("x") or "")
    y = str(block.get("y") or policy.get("y") or "")
    limit = _positive_int(block.get("limit") or policy.get("limit"), 8)
    if not x:
        return ""
    grouped = (_group_sum(rows, x, y) if y else _group_count(rows, x))[:limit]
    total = sum(value for _, value in grouped)
    if not grouped or total <= 0:
        return ""

    start = 0.0
    segments = []
    legend = []
    for index, (label, value) in enumerate(grouped):
        color = _chart_color(index)
        degrees = 360 * value / total
        end = start + degrees
        segments.append(f"{color} {start:.2f}deg {end:.2f}deg")
        percent = value / total * 100
        legend.append(
            f"""
<div class="legend-item">
  <span class="legend-swatch" style="background:{color}"></span>
  <span class="legend-label">{html.escape(str(label))}</span>
  <b>{html.escape(_format_number(value))}</b>
  <small>{percent:.1f}%</small>
</div>
"""
        )
        start = end
    gradient = ", ".join(segments)
    return f"""
<section class="panel">
  <h2>{html.escape(str(block.get("title") or "구성비"))}</h2>
  <div class="donut-layout chart-zone">
    <div class="donut-visual" style="background:conic-gradient({gradient});">
      <div class="donut-hole"><strong>100%</strong><span>{html.escape(_format_number(total))}</span></div>
    </div>
    <div class="chart-legend">{''.join(legend)}</div>
  </div>
</section>
"""


def _grouped_bar_chart(block: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    """하나의 범주 안에서 여러 metric을 나란히 비교하는 묶음 막대 그래프를 만듭니다."""

    policy = _dict(block.get("chart_policy"))
    x = str(block.get("x") or policy.get("x") or "")
    metrics = [item for item in _list(block.get("metrics") or policy.get("metrics")) if isinstance(item, dict)]
    y = str(block.get("y") or policy.get("y") or "")
    if not metrics and y:
        metrics = [{"label": y, "column": y, "aggregation": "sum"}]
    metrics = metrics[:4]
    limit = _positive_int(block.get("limit") or policy.get("limit"), 8)
    if not x or not metrics:
        return ""

    labels = _top_group_labels(rows, x, [str(metric.get("column") or "") for metric in metrics], limit)
    values_by_label: dict[str, list[tuple[str, float]]] = {}
    max_value = 0.0
    for label in labels:
        label_rows = [row for row in rows if str(row.get(x) or "(blank)") == label]
        metric_values = []
        for metric in metrics:
            column = str(metric.get("column") or "")
            aggregation = str(metric.get("aggregation") or "sum")
            value = _aggregate(label_rows, column, aggregation)
            number = _number(value) or 0
            max_value = max(max_value, number)
            metric_values.append((str(metric.get("label") or column), number))
        values_by_label[label] = metric_values
    if not values_by_label:
        return ""

    rows_markup = []
    for label in labels:
        metric_bars = []
        for index, (metric_label, value) in enumerate(values_by_label.get(label, [])):
            width = max(2, round(value / max(max_value, 1) * 100))
            color = _chart_color(index)
            metric_bars.append(
                f"""
<div class="grouped-metric-row">
  <span>{html.escape(metric_label)}</span>
  <div class="bar-track"><div class="bar-fill solid" style="width:{width}%;background:{color};"></div></div>
  <b>{html.escape(_format_number(value))}</b>
</div>
"""
            )
        rows_markup.append(
            f"""
<div class="grouped-category">
  <div class="grouped-label">{html.escape(label)}</div>
  <div class="grouped-bars">{''.join(metric_bars)}</div>
</div>
"""
        )
    return f"""
<section class="panel">
  <h2>{html.escape(str(block.get("title") or "복수 지표 비교"))}</h2>
  <div class="grouped-chart chart-zone">{''.join(rows_markup)}</div>
</section>
"""


def _stacked_bar_chart(block: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    """큰 범주별 내부 구성을 누적 막대로 표시합니다."""

    policy = _dict(block.get("chart_policy"))
    x = str(block.get("x") or policy.get("x") or "")
    series = str(block.get("series") or policy.get("series") or "")
    y = str(block.get("y") or policy.get("y") or "")
    limit = _positive_int(block.get("limit") or policy.get("limit"), 8)
    if not x or not series:
        return ""

    matrix: dict[str, dict[str, float]] = {}
    series_totals: dict[str, float] = {}
    for row in rows:
        x_label = str(row.get(x) or "(blank)")
        series_label = str(row.get(series) or "(blank)")
        value = _row_metric(row, y)
        matrix.setdefault(x_label, {})
        matrix[x_label][series_label] = matrix[x_label].get(series_label, 0) + value
        series_totals[series_label] = series_totals.get(series_label, 0) + value
    if not matrix:
        return ""

    x_labels = sorted(matrix, key=lambda label: sum(matrix[label].values()), reverse=True)[:limit]
    series_labels = sorted(series_totals, key=series_totals.get, reverse=True)[:8]
    legend = "".join(
        f'<span class="stacked-legend-item"><i style="background:{_chart_color(index)}"></i>{html.escape(label)}</span>'
        for index, label in enumerate(series_labels)
    )
    stacked_rows = []
    for label in x_labels:
        total = sum(matrix[label].values())
        if total <= 0:
            continue
        segments = []
        for index, series_label in enumerate(series_labels):
            value = matrix[label].get(series_label, 0)
            if value <= 0:
                continue
            width = max(1, value / total * 100)
            segments.append(
                f'<div class="stacked-segment" style="width:{width:.2f}%;background:{_chart_color(index)}" title="{html.escape(series_label)} {html.escape(_format_number(value))}"></div>'
            )
        stacked_rows.append(
            f"""
<div class="stacked-row">
  <span class="stacked-label">{html.escape(label)}</span>
  <div class="stacked-track">{''.join(segments)}</div>
  <span class="stacked-total">{html.escape(_format_number(total))}</span>
</div>
"""
        )
    return f"""
<section class="panel">
  <h2>{html.escape(str(block.get("title") or "구성 비교"))}</h2>
  <div class="stacked-chart chart-zone">
    <div class="stacked-legend">{legend}</div>
    {''.join(stacked_rows)}
  </div>
</section>
"""


def _line_chart(block: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    """시간/순서 축에 따른 숫자 변화를 SVG 선 그래프로 그립니다."""

    policy = _dict(block.get("chart_policy"))
    x = str(block.get("x") or policy.get("x") or "")
    y = str(block.get("y") or policy.get("y") or "")
    points = sorted(_group_sum(rows, x, y), key=lambda item: str(item[0]))
    if len(points) < 2:
        return ""
    width = 720
    height = 240
    pad = 32
    values = [value for _, value in points]
    min_value = min(values)
    max_value = max(values)
    span = max(max_value - min_value, 1)
    coords = []
    for index, (_, value) in enumerate(points):
        px = pad + (width - pad * 2) * index / max(len(points) - 1, 1)
        py = height - pad - (height - pad * 2) * (value - min_value) / span
        coords.append((px, py))
    polyline = " ".join(f"{xv:.1f},{yv:.1f}" for xv, yv in coords)
    circles = "".join(f'<circle cx="{xv:.1f}" cy="{yv:.1f}" r="3"></circle>' for xv, yv in coords)
    first_label = html.escape(str(points[0][0]))
    last_label = html.escape(str(points[-1][0]))
    return f"""
<section class="panel">
  <h2>{html.escape(str(block.get("title") or "시간에 따른 변화"))}</h2>
  <div class="chart-zone">
    <svg class="line-chart" viewBox="0 0 {width} {height}" role="img">
      <line x1="{pad}" y1="{height-pad}" x2="{width-pad}" y2="{height-pad}" class="axis"></line>
      <polyline points="{polyline}" class="trend-line"></polyline>
      {circles}
    </svg>
  </div>
  <div class="chart-caption"><span>{first_label}</span><span>{last_label}</span></div>
</section>
"""


def _histogram_chart(block: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    """숫자 컬럼의 분포를 구간별 막대 수로 보여주는 히스토그램을 만듭니다."""

    policy = _dict(block.get("chart_policy"))
    column = str(block.get("x") or policy.get("x") or policy.get("column") or "")
    values = sorted(value for value in (_number(row.get(column)) for row in rows) if value is not None)
    if len(values) < 2:
        return ""
    bin_count = min(max(_positive_int(policy.get("bin_count"), 8), 3), 20)
    min_value = min(values)
    max_value = max(values)
    if min_value == max_value:
        bins = [len(values)]
        labels = [str(_format_number(min_value))]
    else:
        width = (max_value - min_value) / bin_count
        bins = [0 for _ in range(bin_count)]
        for value in values:
            index = min(int((value - min_value) / width), bin_count - 1)
            bins[index] += 1
        labels = [_format_number(min_value), _format_number(max_value)]
    max_count = max(bins) or 1
    bars = "".join(
        f'<div class="histogram-bar" style="height:{max(4, count / max_count * 100):.2f}%"><span>{count}</span></div>'
        for count in bins
    )
    label_markup = "".join(f"<span>{html.escape(label)}</span>" for label in labels)
    return f"""
<section class="panel">
  <h2>{html.escape(str(block.get("title") or "분포"))}</h2>
  <div class="histogram-chart chart-zone">
    <div class="histogram-bars">{bars}</div>
    <div class="histogram-labels">{label_markup}</div>
  </div>
</section>
"""


def _scatter_plot(block: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    """두 숫자 컬럼의 관계를 SVG 산점도로 표시합니다."""

    policy = _dict(block.get("chart_policy"))
    x = str(block.get("x") or policy.get("x") or "")
    y = str(block.get("y") or policy.get("y") or "")
    limit = _positive_int(block.get("limit") or policy.get("limit"), 120)
    points = [(_number(row.get(x)), _number(row.get(y))) for row in rows]
    points = [(xv, yv) for xv, yv in points if xv is not None and yv is not None][:limit]
    if len(points) < 2:
        return ""
    width = 720
    height = 260
    pad = 34
    x_values = [item[0] for item in points]
    y_values = [item[1] for item in points]
    x_min, x_max = min(x_values), max(x_values)
    y_min, y_max = min(y_values), max(y_values)
    x_span = max(x_max - x_min, 1)
    y_span = max(y_max - y_min, 1)
    circles = []
    for xv, yv in points:
        px = pad + (width - pad * 2) * (xv - x_min) / x_span
        py = height - pad - (height - pad * 2) * (yv - y_min) / y_span
        circles.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4"></circle>')
    return f"""
<section class="panel">
  <h2>{html.escape(str(block.get("title") or "상관/산포"))}</h2>
  <div class="chart-zone">
    <svg class="scatter-chart" viewBox="0 0 {width} {height}" role="img">
      <line x1="{pad}" y1="{height-pad}" x2="{width-pad}" y2="{height-pad}" class="axis"></line>
      <line x1="{pad}" y1="{pad}" x2="{pad}" y2="{height-pad}" class="axis"></line>
      {''.join(circles)}
    </svg>
  </div>
  <div class="chart-caption"><span>{html.escape(x)}</span><span>{html.escape(y)}</span></div>
</section>
"""


def _heatmap_matrix(block: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    """두 범주 축의 교차값을 색상 강도로 보여주는 히트맵 표를 만듭니다."""

    policy = _dict(block.get("chart_policy"))
    x = str(block.get("x") or policy.get("x") or "")
    series = str(block.get("series") or policy.get("series") or "")
    y = str(block.get("y") or policy.get("y") or "")
    limit = _positive_int(block.get("limit") or policy.get("limit"), 8)
    if not x or not series:
        return ""
    matrix: dict[str, dict[str, float]] = {}
    row_totals: dict[str, float] = {}
    col_totals: dict[str, float] = {}
    for row in rows:
        row_label = str(row.get(x) or "(blank)")
        col_label = str(row.get(series) or "(blank)")
        value = _row_metric(row, y)
        matrix.setdefault(row_label, {})
        matrix[row_label][col_label] = matrix[row_label].get(col_label, 0) + value
        row_totals[row_label] = row_totals.get(row_label, 0) + value
        col_totals[col_label] = col_totals.get(col_label, 0) + value
    if not matrix:
        return ""
    row_labels = sorted(row_totals, key=row_totals.get, reverse=True)[:limit]
    col_labels = sorted(col_totals, key=col_totals.get, reverse=True)[:limit]
    max_value = max((matrix.get(row_label, {}).get(col_label, 0) for row_label in row_labels for col_label in col_labels), default=0) or 1
    header = "".join(f"<th>{html.escape(label)}</th>" for label in col_labels)
    body = []
    for row_label in row_labels:
        cells = []
        for col_label in col_labels:
            value = matrix.get(row_label, {}).get(col_label, 0)
            alpha = 0.12 + (value / max_value) * 0.68 if value else 0.04
            cells.append(f'<td style="background:rgba(37,99,235,{alpha:.2f})">{html.escape(_format_number(value))}</td>')
        body.append(f"<tr><th>{html.escape(row_label)}</th>{''.join(cells)}</tr>")
    return f"""
<section class="panel">
  <h2>{html.escape(str(block.get("title") or "교차 히트맵"))}</h2>
  <div class="heatmap-wrap chart-zone">
    <table class="heatmap-table">
      <thead><tr><th></th>{header}</tr></thead>
      <tbody>{''.join(body)}</tbody>
    </table>
  </div>
</section>
"""


def _table(block: dict[str, Any], rows: list[dict[str, Any]], fallback_columns: list[str]) -> str:
    """상세표/랭킹표/예외표 등 표 형태 블록을 렌더링합니다."""

    policy = _dict(block.get("table_policy"))
    columns = _strings(block.get("columns")) or _strings(policy.get("columns")) or fallback_columns[:12]
    sort = _dict(block.get("sort"))
    if not sort and policy.get("sort_by"):
        sort = {"by": policy.get("sort_by"), "direction": policy.get("sort_direction") or "desc"}
    limit = _positive_int(block.get("limit") or policy.get("limit"), 50)
    show_row_numbers = bool(block.get("show_row_numbers") or policy.get("show_row_numbers"))
    highlight_rules = _list(block.get("highlight_rules"))
    table_rows = deepcopy(rows)
    sort_by = str(sort.get("by") or "")
    if sort_by:
        # 숫자 컬럼 정렬을 우선 지원합니다. 숫자로 해석되지 않으면 0으로 처리됩니다.
        reverse = str(sort.get("direction") or "desc").lower() != "asc"
        table_rows = sorted(table_rows, key=lambda row: _number(row.get(sort_by)) or 0, reverse=reverse)
    table_rows = table_rows[:limit]
    if not columns or not table_rows:
        return ""
    header = ("<th>#</th>" if show_row_numbers else "") + "".join(f"<th>{html.escape(column)}</th>" for column in columns)
    body = []
    for index, row in enumerate(table_rows, start=1):
        row_class = _row_class(row, highlight_rules)
        row_number = f"<td>{index}</td>" if show_row_numbers else ""
        cells = "".join(f"<td>{html.escape(_cell(row.get(column)))}</td>" for column in columns)
        body.append(f'<tr class="{row_class}">{row_number}{cells}</tr>')
    return f"""
<section class="panel">
  <h2>{html.escape(str(block.get("title") or "상세 데이터"))}</h2>
  <div class="table-wrap">
    <table>
      <thead><tr>{header}</tr></thead>
      <tbody>{''.join(body)}</tbody>
    </table>
  </div>
</section>
"""


def _insight_bullets(block: dict[str, Any], payload: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    """LLM 또는 기본 로직이 만든 핵심 해석 문장을 bullet 목록으로 표시합니다."""

    data = _dict(_dict(payload.get("api_response")).get("data"))
    plan = _dict(payload.get("report_plan"))
    narrative = _dict(plan.get("narrative"))
    profile = _dict(payload.get("data_profile"))
    groups = _dict(profile.get("column_groups"))
    lines = _strings(block.get("lines")) or _strings(narrative.get("key_findings"))
    if not lines:
        lines = [
            f"총 {int(data.get('row_count') or len(rows)):,}건의 데이터를 기준으로 구성했습니다.",
            f"숫자 지표 {len(_strings(groups.get('numeric_columns')))}개와 비교 기준 {len(_strings(groups.get('dimension_columns')))}개를 감지했습니다.",
        ]
        if _strings(groups.get("time_columns")):
            lines.append("시간 컬럼이 있어 추이형 블록을 함께 구성할 수 있습니다.")
    summary = str(narrative.get("executive_summary") or "").strip()
    summary_markup = f'<p class="block-lead">{html.escape(summary)}</p>' if summary else ""
    return f"""
<section class="panel">
  <h2>{html.escape(str(block.get("title") or "핵심 해석"))}</h2>
  {summary_markup}
  <ul class="insight-list">{''.join(f'<li>{html.escape(line)}</li>' for line in lines)}</ul>
</section>
"""


def _recommendations(block: dict[str, Any], payload: dict[str, Any]) -> str:
    """다음 확인 사항이나 권장 조치를 bullet 목록으로 표시합니다."""

    plan = _dict(payload.get("report_plan"))
    narrative = _dict(plan.get("narrative"))
    lines = _strings(block.get("items")) or _strings(narrative.get("recommendations"))
    if not lines:
        lines = ["상세 row가 필요한 경우 원본 데이터 또는 data_ref 기반 전체 조회를 확인하세요.", "공유 전 민감정보 컬럼이 포함되어 있지 않은지 점검하세요."]
    return f"""
<section class="panel">
  <h2>{html.escape(str(block.get("title") or "다음 확인 사항"))}</h2>
  <ul class="insight-list">{''.join(f'<li>{html.escape(line)}</li>' for line in lines)}</ul>
</section>
"""


def _method_note(block: dict[str, Any], payload: dict[str, Any]) -> str:
    """리포트 생성 기준과 caveat를 하단 안내문으로 표시합니다."""

    plan = _dict(payload.get("report_plan"))
    narrative = _dict(plan.get("narrative"))
    source = str(plan.get("plan_source") or "deterministic")
    caveats = _strings(narrative.get("caveats")) + _strings(narrative.get("data_quality_notes"))
    caveat_markup = "".join(f"<li>{html.escape(item)}</li>" for item in caveats)
    return f"""
<section class="method-note">
  <h2>{html.escape(str(block.get("title") or "생성 기준"))}</h2>
  <p>이 HTML은 허용된 block registry와 renderer로 생성되었습니다. Plan source: {html.escape(source)}. LLM raw HTML은 삽입하지 않습니다.</p>
  {f'<ul class="insight-list">{caveat_markup}</ul>' if caveat_markup else ''}
</section>
"""


def _decorate_block_markup(block: dict[str, Any], markup: str) -> str:
    """렌더링된 블록 HTML에 설명문, insight, annotation, footnote를 추가합니다."""

    if not markup:
        return ""
    description = str(block.get("description") or "").strip()
    insight = str(block.get("insight") or "").strip()
    lead_parts = [text for text in (description, insight) if text]
    if lead_parts and "</h2>" in markup:
        lead = "".join(f'<p class="block-lead">{html.escape(text)}</p>' for text in lead_parts)
        markup = markup.replace("</h2>", f"</h2>{lead}", 1)

    annotations = _annotation_markup(_list(block.get("annotations")))
    footnote = str(block.get("footnote") or "").strip()
    footer = annotations
    if footnote:
        footer += f'<p class="block-footnote">{html.escape(footnote)}</p>'
    if footer and "</section>" in markup:
        markup = markup.replace("</section>", f"{footer}</section>", 1)
    return markup


def _annotation_markup(annotations: list[Any]) -> str:
    """annotation 설정을 작은 chip UI HTML로 바꿉니다."""

    chips = []
    for item in annotations:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        value = str(item.get("value") or "").strip()
        tone = _safe_token(item.get("tone"), {"info", "positive", "warning", "danger", "neutral"}, "info")
        if not label and not value:
            continue
        text = f"{label}: {value}" if label and value else label or value
        chips.append(f'<span class="annotation-chip tone-{tone}">{html.escape(text)}</span>')
    return f'<div class="annotation-list">{"".join(chips)}</div>' if chips else ""


def _row_class(row: dict[str, Any], rules: list[Any]) -> str:
    """highlight_rules에 맞는 row라면 강조 CSS class를 반환합니다."""

    for rule in rules:
        if isinstance(rule, dict) and _rule_matches(row, rule):
            tone = _safe_token(rule.get("tone"), {"info", "positive", "warning", "danger", "neutral"}, "warning")
            return f"row-{tone}"
    return ""


def _rule_matches(row: dict[str, Any], rule: dict[str, Any]) -> bool:
    """하나의 row가 강조 규칙과 일치하는지 비교합니다."""

    column = str(rule.get("column") or "")
    operator = str(rule.get("operator") or "eq").lower()
    actual = row.get(column)
    expected = rule.get("value")
    actual_number = _number(actual)
    expected_number = _number(expected)
    if operator in {"gt", "gte", "lt", "lte"} and actual_number is not None and expected_number is not None:
        if operator == "gt":
            return actual_number > expected_number
        if operator == "gte":
            return actual_number >= expected_number
        if operator == "lt":
            return actual_number < expected_number
        if operator == "lte":
            return actual_number <= expected_number
    actual_text = str(actual or "")
    expected_text = str(expected or "")
    if operator == "contains":
        return expected_text.lower() in actual_text.lower()
    if operator == "ne":
        return actual_text != expected_text
    return actual_text == expected_text


def _wrap_block(block: dict[str, Any], markup: str) -> str:
    """각 블록을 12컬럼 grid에서 배치할 수 있는 wrapper div로 감쌉니다."""

    width = _safe_token(block.get("width"), {"full", "two_third", "half", "third"}, "full")
    density = _safe_token(block.get("density"), {"compact", "comfortable"}, "comfortable")
    font_scale = _safe_token(block.get("font_scale"), {"small", "normal", "large"}, "normal")
    emphasis = _safe_token(block.get("emphasis"), {"low", "medium", "high", "critical"}, "medium")
    style = _dict(block.get("style"))
    accent = _safe_color(style.get("accent_color") or block.get("accent_color"))
    style_attr = f' style="--block-accent:{accent};"' if accent else ""
    classes = " ".join(
        [
            "report-block",
            f"block-{width}",
            f"density-{density}",
            f"font-{font_scale}",
            f"emphasis-{emphasis}",
        ]
    )
    return f'<div class="{classes}"{style_attr}>{markup}</div>'


def _document(title: str, subtitle: str, body: list[str], plan: dict[str, Any]) -> str:
    """완성된 블록 HTML 목록을 하나의 독립 실행 HTML 문서로 감쌉니다.

    외부 CSS/JS 파일 없이 Playground나 다운로드 파일만으로 바로 열리게 하려고
    필요한 CSS를 `<style>` 태그 안에 함께 넣습니다.
    """

    visual_style = _dict(plan.get("visual_style"))
    main_style = _visual_style_attr(visual_style)
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{ color-scheme: light; --ink:#17202a; --muted:#5f6b7a; --line:#d8dee8; --surface:#f5f7fb; --accent:#0f766e; --accent-2:#2563eb; --warn:#9f580a; --report-width:1180px; --panel-pad:18px; --grid-gap:18px; --h1-size:32px; --h2-size:19px; --body-size:14px; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:Segoe UI, Arial, sans-serif; font-size:var(--body-size); color:var(--ink); background:#ffffff; line-height:1.5; }}
    main {{ max-width:var(--report-width); margin:0 auto; padding:28px 22px 44px; }}
    .report-grid {{ display:grid; grid-template-columns:repeat(12, minmax(0, 1fr)); gap:var(--grid-gap); align-items:stretch; grid-auto-flow:row dense; }}
    .report-block {{ min-width:0; display:flex; flex-direction:column; font-size:var(--body-size); --block-accent:var(--accent); }}
    .block-full {{ grid-column:span 12; }}
    .block-two_third {{ grid-column:span 8; }}
    .block-half {{ grid-column:span 6; }}
    .block-third {{ grid-column:span 4; }}
    .report-block > .hero, .report-block > .panel, .report-block > .notice, .report-block > .method-note {{ margin-top:0; height:100%; flex:1; }}
    .hero {{ display:flex; justify-content:space-between; gap:20px; align-items:flex-end; padding:26px 0 20px; border-bottom:2px solid var(--ink); }}
    .eyebrow {{ margin:0 0 8px; font-size:12px; font-weight:700; color:var(--accent); letter-spacing:0; }}
    h1 {{ margin:0; font-size:var(--h1-size); line-height:1.2; }}
    h2 {{ margin:0 0 14px; font-size:var(--h2-size); }}
    .subtitle {{ margin:10px 0 0; color:var(--muted); max-width:760px; }}
    .hero-meta {{ display:flex; flex-direction:column; gap:6px; font-size:13px; color:var(--muted); text-align:right; }}
    .panel, .notice, .method-note {{ margin-top:22px; padding:var(--panel-pad); border:1px solid var(--line); border-radius:8px; background:#fff; display:flex; flex-direction:column; }}
    .notice {{ background:#fff8ed; border-color:#f0c98b; color:#4c3104; }}
    .method-note {{ background:var(--surface); color:var(--muted); }}
    .block-lead {{ margin:0 0 12px; color:var(--muted); max-width:72ch; }}
    .block-footnote {{ margin:12px 0 0; font-size:12px; color:var(--muted); }}
    .annotation-list {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:12px; }}
    .annotation-chip {{ display:inline-flex; align-items:center; min-height:26px; padding:4px 9px; border-radius:999px; font-size:12px; font-weight:650; background:#edf2f7; color:#334155; }}
    .tone-info {{ background:#e0f2fe; color:#075985; }}
    .tone-positive {{ background:#dcfce7; color:#166534; }}
    .tone-warning {{ background:#fef3c7; color:#92400e; }}
    .tone-danger {{ background:#fee2e2; color:#991b1b; }}
    .tone-neutral {{ background:#edf2f7; color:#334155; }}
    .density-compact {{ --panel-pad:14px; }}
    .density-compact table {{ font-size:12px; }}
    .density-compact th, .density-compact td {{ padding:7px 8px; }}
    .font-small {{ --h1-size:28px; --h2-size:17px; --body-size:13px; }}
    .font-large {{ --h1-size:38px; --h2-size:22px; --body-size:15px; }}
    .emphasis-high > .panel, .emphasis-high > .notice {{ box-shadow:0 8px 24px rgba(15, 23, 42, .08); }}
    .emphasis-critical > .panel, .emphasis-critical > .notice {{ border-color:#e5a3a3; background:#fff7f7; box-shadow:0 8px 24px rgba(15, 23, 42, .08); }}
    .emphasis-high h2, .emphasis-critical h2 {{ color:var(--block-accent); }}
    .chart-zone {{ flex:1; min-height:220px; }}
    .block-third .chart-zone, .block-half .chart-zone {{ min-height:240px; }}
    .scope-grid, .kpi-grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(170px, 1fr)); gap:12px; }}
    .scope-grid div, .kpi-card {{ border:1px solid var(--line); border-radius:8px; padding:14px; background:var(--surface); }}
    .scope-grid b, .kpi-card span {{ display:block; font-size:12px; color:var(--muted); margin-bottom:8px; }}
    .scope-grid span, .kpi-card strong {{ display:block; font-size:22px; font-weight:750; overflow-wrap:anywhere; }}
    .kpi-card small {{ display:block; margin-top:6px; color:var(--muted); }}
    .bar-chart {{ display:grid; gap:10px; align-content:center; }}
    .bar-row {{ display:grid; grid-template-columns:minmax(110px, 180px) 1fr minmax(70px, auto); gap:10px; align-items:center; }}
    .bar-label, .bar-value {{ font-size:13px; color:var(--muted); overflow-wrap:anywhere; }}
    .bar-track {{ height:14px; background:#e7edf5; border-radius:999px; overflow:hidden; }}
    .bar-fill {{ height:100%; background:linear-gradient(90deg, var(--accent), var(--accent-2)); }}
    .bar-fill.solid {{ background:var(--accent); }}
    .donut-layout {{ display:grid; grid-template-columns:minmax(160px, 220px) 1fr; gap:18px; align-items:center; }}
    .donut-visual {{ width:min(220px, 100%); aspect-ratio:1; border-radius:50%; position:relative; margin:auto; box-shadow:inset 0 0 0 1px var(--line); }}
    .donut-hole {{ position:absolute; inset:24%; border-radius:50%; background:#fff; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; border:1px solid var(--line); }}
    .donut-hole strong {{ font-size:24px; }}
    .donut-hole span {{ color:var(--muted); font-size:12px; }}
    .chart-legend {{ display:grid; gap:8px; align-content:center; }}
    .legend-item {{ display:grid; grid-template-columns:12px minmax(0, 1fr) auto auto; gap:8px; align-items:center; font-size:12px; color:var(--muted); }}
    .legend-swatch {{ width:10px; height:10px; border-radius:999px; }}
    .legend-label {{ color:var(--ink); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
    .grouped-chart {{ display:grid; gap:14px; }}
    .grouped-category {{ display:grid; grid-template-columns:minmax(100px, 160px) 1fr; gap:12px; align-items:start; }}
    .grouped-label {{ font-size:13px; font-weight:650; color:var(--ink); overflow-wrap:anywhere; }}
    .grouped-bars {{ display:grid; gap:6px; }}
    .grouped-metric-row {{ display:grid; grid-template-columns:minmax(80px, 130px) 1fr minmax(64px, auto); gap:8px; align-items:center; font-size:12px; color:var(--muted); }}
    .grouped-metric-row b {{ color:var(--ink); text-align:right; }}
    .stacked-chart {{ display:grid; gap:10px; align-content:center; }}
    .stacked-legend {{ display:flex; flex-wrap:wrap; gap:8px 12px; margin-bottom:4px; }}
    .stacked-legend-item {{ display:inline-flex; gap:6px; align-items:center; font-size:12px; color:var(--muted); }}
    .stacked-legend-item i {{ width:10px; height:10px; border-radius:2px; display:inline-block; }}
    .stacked-row {{ display:grid; grid-template-columns:minmax(100px, 170px) 1fr minmax(64px, auto); gap:10px; align-items:center; }}
    .stacked-label, .stacked-total {{ font-size:13px; color:var(--muted); overflow-wrap:anywhere; }}
    .stacked-track {{ display:flex; height:18px; overflow:hidden; border-radius:999px; background:#e7edf5; }}
    .stacked-segment {{ height:100%; min-width:1px; }}
    .histogram-chart {{ display:grid; grid-template-rows:1fr auto; gap:8px; }}
    .histogram-bars {{ display:flex; gap:7px; align-items:end; min-height:210px; padding:12px; border:1px solid var(--line); border-radius:8px; background:var(--surface); }}
    .histogram-bar {{ flex:1; min-width:10px; border-radius:6px 6px 0 0; background:linear-gradient(180deg, var(--accent-2), var(--accent)); position:relative; }}
    .histogram-bar span {{ position:absolute; left:50%; bottom:100%; transform:translateX(-50%); margin-bottom:3px; font-size:11px; color:var(--muted); }}
    .histogram-labels {{ display:flex; justify-content:space-between; font-size:12px; color:var(--muted); }}
    .line-chart, .scatter-chart {{ width:100%; height:auto; max-height:300px; background:var(--surface); border:1px solid var(--line); border-radius:8px; }}
    .line-chart .axis {{ stroke:#94a3b8; stroke-width:1; }}
    .line-chart .trend-line {{ fill:none; stroke:var(--accent-2); stroke-width:3; }}
    .line-chart circle {{ fill:#ffffff; stroke:var(--accent-2); stroke-width:2; }}
    .scatter-chart .axis {{ stroke:#94a3b8; stroke-width:1; }}
    .scatter-chart circle {{ fill:var(--accent-2); opacity:.72; }}
    .chart-caption {{ display:flex; justify-content:space-between; color:var(--muted); font-size:13px; margin-top:6px; }}
    .heatmap-wrap {{ overflow:auto; }}
    .heatmap-table {{ min-width:max-content; }}
    .heatmap-table th, .heatmap-table td {{ text-align:center; white-space:nowrap; }}
    .heatmap-table tbody th {{ background:#f1f5f9; position:sticky; left:0; z-index:1; text-align:left; }}
    .table-wrap {{ overflow:auto; border:1px solid var(--line); border-radius:8px; }}
    table {{ border-collapse:collapse; min-width:100%; font-size:13px; }}
    th, td {{ padding:9px 10px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
    th {{ position:sticky; top:0; background:#eef3f8; font-weight:700; }}
    tr.row-info td {{ background:#f0f9ff; }}
    tr.row-positive td {{ background:#f0fdf4; }}
    tr.row-warning td {{ background:#fffbeb; }}
    tr.row-danger td {{ background:#fef2f2; }}
    tr.row-neutral td {{ background:#f8fafc; }}
    .insight-list {{ margin:0; padding-left:20px; }}
    @media (max-width: 900px) {{ .block-half, .block-third, .block-two_third {{ grid-column:span 12; }} }}
    @media (max-width: 720px) {{ main {{ padding:22px 16px 34px; }} .hero {{ display:block; }} .hero-meta {{ text-align:left; margin-top:16px; }} .bar-row, .grouped-category, .grouped-metric-row, .stacked-row, .donut-layout {{ grid-template-columns:1fr; }} .chart-zone {{ min-height:180px; }} }}
  </style>
</head>
<body>
  <main{main_style}>
    <div class="report-grid">
      {''.join(body)}
    </div>
  </main>
</body>
</html>"""


def _visual_style_attr(visual_style: dict[str, Any]) -> str:
    """visual_style 설정을 CSS 변수 style 속성으로 변환합니다."""

    declarations = []
    accent = _safe_color(visual_style.get("accent_color"))
    secondary = _safe_color(visual_style.get("secondary_color"))
    if accent:
        declarations.append(f"--accent:{accent}")
    if secondary:
        declarations.append(f"--accent-2:{secondary}")
    if str(visual_style.get("max_width") or "").lower() == "wide":
        declarations.append("--report-width:1380px")
    density = str(visual_style.get("density") or "").lower()
    if density == "compact":
        declarations.extend(["--panel-pad:14px", "--grid-gap:14px"])
    elif density == "comfortable":
        declarations.extend(["--panel-pad:20px", "--grid-gap:20px"])
    font_scale = str(visual_style.get("font_scale") or "").lower()
    if font_scale == "small":
        declarations.extend(["--h1-size:28px", "--h2-size:17px", "--body-size:13px"])
    elif font_scale == "large":
        declarations.extend(["--h1-size:38px", "--h2-size:22px", "--body-size:15px"])
    return f' style="{";".join(declarations)}"' if declarations else ""


def _safe_token(value: Any, allowed: set[str], fallback: str) -> str:
    """허용된 문자열 토큰만 통과시키고 나머지는 fallback으로 바꿉니다."""

    text = str(value or "").strip().lower().replace("-", "_")
    return text if text in allowed else fallback


def _safe_color(value: Any) -> str:
    """`#RRGGBB` 형식의 색상만 CSS에 넣도록 검증합니다."""

    text = str(value or "").strip()
    if len(text) == 7 and text.startswith("#") and all(ch in "0123456789abcdefABCDEF" for ch in text[1:]):
        return text
    return ""


def _aggregate(rows: list[dict[str, Any]], column: str, aggregation: str) -> Any:
    """KPI 카드와 차트에서 사용할 기본 집계값을 계산합니다."""

    values = [_number(row.get(column)) for row in rows]
    numbers = [value for value in values if value is not None]
    if aggregation == "count":
        return len(rows)
    if aggregation == "nunique":
        return len({str(row.get(column)) for row in rows if row.get(column) not in (None, "")})
    if not numbers:
        return 0
    if aggregation in {"avg", "average", "mean"}:
        return sum(numbers) / len(numbers)
    if aggregation == "min":
        return min(numbers)
    if aggregation == "max":
        return max(numbers)
    return sum(numbers)


def _group_sum(rows: list[dict[str, Any]], dimension: str, metric: str) -> list[tuple[str, float]]:
    """범주별 metric 합계를 계산하고 큰 값 순서로 정렬합니다."""

    grouped: dict[str, float] = {}
    for row in rows:
        label = str(row.get(dimension) or "(blank)")
        value = _number(row.get(metric)) or 0
        grouped[label] = grouped.get(label, 0) + value
    return sorted(grouped.items(), key=lambda item: item[1], reverse=True)


def _group_count(rows: list[dict[str, Any]], dimension: str) -> list[tuple[str, float]]:
    """범주별 row 개수를 계산하고 큰 값 순서로 정렬합니다."""

    grouped: dict[str, float] = {}
    for row in rows:
        label = str(row.get(dimension) or "(blank)")
        grouped[label] = grouped.get(label, 0) + 1
    return sorted(grouped.items(), key=lambda item: item[1], reverse=True)


def _top_group_labels(rows: list[dict[str, Any]], dimension: str, metrics: list[str], limit: int) -> list[str]:
    """여러 metric 합계 기준으로 상위 범주 label을 고릅니다."""

    totals: dict[str, float] = {}
    for row in rows:
        label = str(row.get(dimension) or "(blank)")
        value = sum((_number(row.get(metric)) or 0) for metric in metrics if metric)
        totals[label] = totals.get(label, 0) + value
    return [label for label, _ in sorted(totals.items(), key=lambda item: item[1], reverse=True)[:limit]]


def _row_metric(row: dict[str, Any], metric: str) -> float:
    """row 하나에서 metric 값을 숫자로 꺼냅니다. metric이 없으면 count용 1을 반환합니다."""

    if metric:
        return _number(row.get(metric)) or 0
    return 1.0


def _chart_color(index: int) -> str:
    """팔레트에서 index에 맞는 차트 색상을 순환 선택합니다."""

    return CHART_COLORS[index % len(CHART_COLORS)]


def _number(value: Any) -> float | None:
    """문자열/숫자 값을 float로 변환하고, 실패하면 None을 반환합니다."""

    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and value == value:
        return float(value)
    text = str(value or "").strip().replace(",", "").replace("%", "")
    try:
        return float(text) if text else None
    except Exception:
        return None


def _format_number(value: Any) -> str:
    """숫자를 리포트에 보기 좋은 문자열로 포맷합니다."""

    number = _number(value)
    if number is None:
        return str(value)
    if abs(number) >= 1000:
        return f"{number:,.0f}" if number.is_integer() else f"{number:,.2f}"
    return f"{number:.0f}" if number.is_integer() else f"{number:.2f}"


def _cell(value: Any) -> str:
    """테이블 셀에 넣을 값을 문자열로 변환합니다."""

    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return _format_number(value) if _number(value) is not None else str(value)


def _filename_hint(title: str) -> str:
    """리포트 제목을 다운로드 파일명 힌트로 쓸 수 있게 정리합니다."""

    safe = "".join(ch if ch.isalnum() else "_" for ch in title.lower()).strip("_")
    return (safe or "html_report")[:80]


def _payload(value: Any) -> dict[str, Any]:
    """Langflow Data/Message/dict/JSON 문자열을 일반 dict로 맞춥니다."""

    if isinstance(value, dict):
        return deepcopy(value)
    data = getattr(value, "data", None)
    if isinstance(data, dict):
        return deepcopy(data)
    text = getattr(value, "text", None) or getattr(value, "content", None)
    if isinstance(text, str) and text.strip():
        try:
            parsed = json.loads(text)
        except Exception:
            return {"text": text}
        return deepcopy(parsed) if isinstance(parsed, dict) else {"text": text}
    return {}


def _dict(value: Any) -> dict[str, Any]:
    """dict면 복사본을, 아니면 빈 dict를 반환합니다."""

    return deepcopy(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    """list면 복사본을, 아니면 빈 list를 반환합니다."""

    return deepcopy(value) if isinstance(value, list) else []


def _rows(value: Any) -> list[dict[str, Any]]:
    """dict row 목록만 안전하게 복사해서 반환합니다."""

    return [deepcopy(row) for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    """문자열 목록을 정리하고 중복을 제거합니다."""

    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        text = str(item or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def _columns_from_rows(rows: list[dict[str, Any]]) -> list[str]:
    """rows에서 컬럼명을 처음 등장한 순서대로 수집합니다."""

    columns: list[str] = []
    for row in rows:
        for key in row:
            text = str(key)
            if text not in columns:
                columns.append(text)
    return columns


def _positive_int(value: Any, default: int) -> int:
    """값을 양의 정수로 바꾸고 실패하면 default를 사용합니다."""

    try:
        parsed = int(value)
    except Exception:
        parsed = default
    return max(1, parsed)


class HtmlTemplateRenderer(Component):
    """Langflow 화면에 표시되는 04번 커스텀 컴포넌트 클래스."""

    display_name = "04 HTML 렌더링"
    description = "최종 리포트 계획과 데이터를 이용해 독립 실행 가능한 HTML 원문을 생성합니다."
    icon = "FileCode2"
    inputs = [DataInput(name="payload", display_name="최종 계획", required=True)]
    outputs = [Output(name="payload_out", display_name="HTML 생성 결과", method="build_payload")]

    def build_payload(self) -> Data:
        """최종 계획 payload를 받아 HTML 생성 결과 payload를 출력합니다."""

        result = render_html_report(getattr(self, "payload", None))
        html_report = result.get("html_report", {})
        self.status = {
            "title": html_report.get("title"),
            "blocks": html_report.get("blocks", []),
            "html_bytes": len(str(html_report.get("html") or "").encode("utf-8")),
        }
        return Data(data=result)
