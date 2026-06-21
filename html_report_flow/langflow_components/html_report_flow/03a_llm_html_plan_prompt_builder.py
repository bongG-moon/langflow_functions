from __future__ import annotations

"""03a LLM 계획 프롬프트 노드.

이 파일은 LLM에게 보낼 프롬프트를 만듭니다.
중요한 점은 LLM이 HTML 전체 코드를 직접 만들지 않고, 렌더러가 안전하게 처리할 수 있는
`report_plan` JSON만 보완하게 한다는 것입니다.
"""

import json
from copy import deepcopy
from typing import Any

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, MessageTextInput, Output
from lfx.schema.data import Data
from lfx.schema.message import Message


def build_llm_html_plan_prompt_payload(
    payload_value: Any,
    data_profile_value: Any = None,
    component_catalog_value: Any = None,
    design_instruction: str = "",
) -> dict[str, Any]:
    """LLM이 report_plan JSON을 보완하도록 지시하는 프롬프트 payload를 만듭니다."""

    if isinstance(data_profile_value, str) and component_catalog_value is None and not design_instruction:
        # 과거 연결 방식과 호환하기 위한 처리입니다.
        # 두 번째 인자로 문자열만 들어오면 추가 디자인 지시로 간주합니다.
        design_instruction = data_profile_value
        data_profile_value = None
    payload = _payload(payload_value)
    request = _dict(payload.get("request"))
    llm_context = _dict(payload.get("llm_context"))
    profile = _payload(data_profile_value) or _dict(payload.get("data_profile")) or _dict(llm_context.get("data_profile"))
    catalog = _payload(component_catalog_value) or _dict(payload.get("html_component_catalog")) or _dict(llm_context.get("html_component_catalog"))
    base_plan = _dict(payload.get("report_plan"))
    data = _dict(_dict(payload.get("api_response")).get("data"))
    rows = _rows(data.get("rows"))

    # 아래 prompt는 LLM에게 전달되는 실제 지시문입니다.
    # JSON만 반환하도록 강하게 제한해서 03b 검증 노드가 안정적으로 읽을 수 있게 합니다.
    prompt = "\n".join(
        [
            "You are the LLM planning node for a Langflow HTML data report flow.",
            "Your job is to complete a report plan JSON, not to write raw HTML.",
            "Use the provided base plan, allowed component catalog, user intent, and data profile.",
            "The renderer will convert your JSON into a static standalone HTML file.",
            "",
            "Hard rules:",
            "- Return one strict JSON object only. Do not wrap it in markdown.",
            "- Do not output HTML, CSS, JavaScript, SVG, script tags, markdown, or prose outside JSON.",
            "- Use only block_id values from the allowed components.",
            "- Use only real column names from the data profile or preview rows.",
            "- Prefer a composed report: KPI cards plus chart/table/narrative blocks when the data supports them.",
            "- Create a rich report spec: audience, goal, narrative, visual style, block order, block width, emphasis, density, font scale, annotations, and table/chart policies.",
            "- Keep text concise enough to fit inside cards and headings.",
            "- If there are many rows or many columns, use compact density and put detailed tables later.",
            "- Use full width for wide tables and trend charts; use half/two_third/third widths for complementary comparisons.",
            "- Keep side-by-side blocks visually balanced: pair half+half or third+two_third blocks with similar density, similar title length, and similar content depth.",
            "- Do not place a long table next to a compact chart; put wide/long tables on a full-width row below charts.",
            "- Keep chart blocks in the same row comparable in height by using concise titles/descriptions, limiting categories, and avoiding long annotations.",
            "- Prefer one strong chart per analytical question rather than many tiny charts with inconsistent spacing.",
            "- Use narrative fields for concise findings, caveats, and recommendations. Do not make unsupported claims.",
            "- Use annotations for short callouts such as highest value, warning, or follow-up point when visible from the preview/profile.",
            "- Use table_policy and chart_policy to specify exact columns, sorting, limits, row numbers, and value display.",
            "- Never invent data values. Titles, labels, and narrative may be user-friendly, but bindings must reference real columns.",
            "",
            "Allowed block ids and base contracts:",
            json.dumps(_component_contracts(catalog), ensure_ascii=False, indent=2),
            "",
            "Template presets/defaults supplied by component_catalog_json:",
            json.dumps(_catalog_template_guidance(catalog), ensure_ascii=False, indent=2),
            "",
            "Available columns and data profile:",
            json.dumps(_profile_summary(profile), ensure_ascii=False, indent=2),
            "",
            "User request:",
            json.dumps(
                {
                    "question": request.get("question") or profile.get("question") or "",
                    "view_request": request.get("view_request") or "",
                    "selected_dataset_id": request.get("selected_dataset_id") or "",
                },
                ensure_ascii=False,
                indent=2,
            ),
            "",
            "Preview rows for context:",
            json.dumps(rows[:8], ensure_ascii=False, indent=2, default=str),
            "",
            "Deterministic base plan. Improve this plan rather than ignoring it:",
            json.dumps(base_plan, ensure_ascii=False, indent=2, default=str),
            "",
            "Additional design instruction from the user/operator:",
            str(design_instruction or "").strip() or "(none)",
            "",
            "Return JSON schema:",
            json.dumps(_schema_hint(), ensure_ascii=False, indent=2),
            "",
            "Style token guidance:",
            "- visual_style.density: compact for dense operational views; comfortable for executive summaries.",
            "- visual_style.font_scale: normal by default; large for executive/KPI-first reports; small for table-heavy query review.",
            "- audience: operator, analyst, executive, engineer, or general.",
            "- report_goal: monitor, compare, diagnose, explain, audit, or explore.",
            "- block.width: full, two_third, half, or third.",
            "- block.emphasis: high for the 1-2 most important blocks; medium for useful supporting blocks; low for notes.",
            "- block.description and block.insight should be one short sentence each.",
            "- block.annotations should be 0-4 compact callouts; tone can be info, positive, warning, danger, or neutral.",
            "- block.style.accent_color can be a hex color such as #0f766e or #2563eb.",
            "",
            "Chart selection guidance:",
            "- trend_line_chart: use for time/date changes and time-series monitoring. Usually full width.",
            "- comparison_bar_chart: use for one metric by one category, ranking-style comparisons, and ordinary bar chart requests.",
            "- grouped_bar_chart: use when the user asks to compare multiple metrics by the same category, such as WIP and production by process.",
            "- stacked_comparison_bar: use for breakdown/composition inside each category, such as process by status or product mix by date.",
            "- donut_chart: use for share/ratio/composition questions. Limit to 6-8 categories and use detail table for the rest.",
            "- distribution_histogram: use for distribution, spread, skew, deviation, or outlier screening of one numeric column.",
            "- scatter_plot: use for relationship/correlation between two numeric metrics.",
            "- heatmap_matrix: use for two-dimensional cross comparison where color intensity helps scanning.",
            "- detail_data_table and ranking_table support charts but should not dominate the first row unless the user asks for raw query results.",
            "",
            "Layout consistency guidance:",
            "- Start with a full-width header/scope, then a balanced KPI/chart row, then detailed tables.",
            "- In a 12-column grid, use full=12, two_third=8, half=6, third=4. Avoid odd combinations that leave gaps.",
            "- If two chart cards are side by side, choose the same width and density for both.",
            "- If one block has long labels, many legend items, or many table columns, make it full width.",
            "- Use chart_policy.limit to keep legends and labels inside the card; prefer 6-8 categories for donut/stacked/grouped charts.",
        ]
    )
    return {
        "prompt_type": "llm_html_report_plan",
        "prompt": prompt,
        "payload": payload,
        "base_plan": base_plan,
        "schema_hint": _schema_hint(),
    }


def _component_contracts(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    """카탈로그를 LLM이 읽기 쉬운 컴포넌트 계약 목록으로 줄입니다."""

    components = _list(catalog.get("components"))
    recommended = {
        str(item.get("component_id")): item
        for item in _list(catalog.get("recommended_components"))
        if isinstance(item, dict)
    }
    result = []
    for item in components:
        if not isinstance(item, dict):
            continue
        component_id = str(item.get("component_id") or "")
        rec = _dict(recommended.get(component_id))
        result.append(
            _compact_dict(
                {
                "component_id": component_id,
                "display_name": item.get("display_name") or component_id,
                "description": item.get("description") or "",
                "layout_role": item.get("layout_role") or "",
                "data_contract": _dict(item.get("data_contract")),
                "recommended": bool(rec),
                "suggested_bindings": _dict(rec.get("suggested_bindings")),
                "reason": rec.get("reason") or "",
                "template_guidance": item.get("template_guidance") or item.get("usage_guidance") or "",
                "style_defaults": _dict(item.get("style_defaults")),
                "default_spec": _dict(item.get("default_spec")),
                "example_spec": _dict(item.get("example_spec")),
                }
            )
        )
    return result


def _catalog_template_guidance(catalog: dict[str, Any]) -> dict[str, Any]:
    """카탈로그 JSON에 포함된 스타일/프리셋/메모 정보를 프롬프트에 넣습니다."""

    return {
        "template_defaults": _dict(catalog.get("template_defaults")),
        "style_presets": catalog.get("style_presets") if isinstance(catalog.get("style_presets"), (dict, list)) else {},
        "report_presets": catalog.get("report_presets") if isinstance(catalog.get("report_presets"), (dict, list)) else {},
        "catalog_notes": _list(catalog.get("catalog_notes")),
    }


def _compact_dict(value: dict[str, Any]) -> dict[str, Any]:
    """빈 값을 제거해 프롬프트에 들어가는 JSON을 짧게 만듭니다."""

    return {key: item for key, item in value.items() if item not in ("", {}, [], None)}


def _profile_summary(profile: dict[str, Any]) -> dict[str, Any]:
    """데이터 프로파일 중 LLM 판단에 필요한 컬럼/의도/경고 요약만 만듭니다."""

    groups = _dict(profile.get("column_groups"))
    shape = _dict(profile.get("shape"))
    return {
        "question": profile.get("question") or "",
        "shape": shape,
        "column_groups": groups,
        "columns": [
            {
                "name": item.get("name"),
                "inferred_type": item.get("inferred_type"),
                "semantic_hint": item.get("semantic_hint", ""),
                "sample_values": item.get("sample_values", [])[:3],
            }
            for item in _list(profile.get("columns"))
            if isinstance(item, dict)
        ],
        "question_hints": _dict(profile.get("question_hints")),
        "report_signals": _dict(profile.get("report_signals")),
        "warnings": _list(profile.get("warnings")),
        "errors": _list(profile.get("errors")),
    }


def _schema_hint() -> dict[str, Any]:
    """LLM이 반환해야 하는 report_plan JSON 구조 예시를 제공합니다.

    실제 검증은 03b에서 다시 수행하므로, 여기서는 LLM이 형식을 이해하도록 돕는
    스키마 힌트 역할을 합니다.
    """

    return {
        "title": "Short report title",
        "subtitle": "Short subtitle or scope statement",
        "audience": "operator | analyst | executive | engineer | general",
        "report_goal": "monitor | compare | diagnose | explain | audit | explore",
        "layout": "dashboard | query_review | diagnosis | executive_summary | detail_review",
        "visual_style": {
            "density": "compact | comfortable",
            "font_scale": "small | normal | large",
            "accent_color": "#0f766e",
            "secondary_color": "#2563eb",
            "max_width": "normal | wide",
        },
        "narrative": {
            "executive_summary": "One concise summary sentence",
            "key_findings": ["short finding grounded in the data/profile"],
            "caveats": ["data limitation or interpretation caveat"],
            "recommendations": ["next action or follow-up check"],
            "data_quality_notes": ["preview/data_ref/row-count note"],
        },
        "reading_order": ["kpi", "trend", "comparison", "detail"],
        "blocks": [
            {
                "block_id": "allowed component id",
                "title": "Block title",
                "section": "Overview | Trend | Comparison | Detail | Quality | Action",
                "description": "One short sentence explaining what this block shows",
                "insight": "One short sentence explaining why it matters",
                "badge": "Optional short label",
                "width": "full | two_third | half | third",
                "emphasis": "high | medium | low",
                "density": "compact | comfortable",
                "font_scale": "small | normal | large",
                "x": "real column name for chart/table when needed",
                "y": "real numeric column name for chart when needed",
                "series": "real dimension column when needed",
                "columns": ["real column names for tables"],
                "metrics": [{"label": "short label", "column": "real numeric column", "aggregation": "sum | avg | min | max | count | nunique"}],
                "sort": {"by": "real column name", "direction": "desc | asc"},
                "limit": 10,
                "chart_policy": {
                    "chart_type": "bar | horizontal_bar | grouped_bar | stacked_bar | line | donut | histogram | scatter | heatmap",
                    "orientation": "horizontal | vertical",
                    "x": "real column",
                    "y": "real numeric column",
                    "series": "real column",
                    "metrics": [{"label": "short label", "column": "real numeric column", "aggregation": "sum | avg | min | max | count | nunique"}],
                    "limit": 10,
                    "bin_count": 8,
                    "show_values": True,
                    "show_legend": True,
                    "show_percent": True,
                    "normalize": False,
                },
                "table_policy": {"columns": ["real column names"], "sort_by": "real column", "sort_direction": "desc", "limit": 50, "show_row_numbers": True},
                "annotations": [{"label": "short label", "value": "short text/value", "tone": "info | positive | warning | danger | neutral"}],
                "highlight_rules": [{"column": "real column", "operator": "eq | ne | gt | gte | lt | lte | contains", "value": "comparison value", "tone": "warning | danger | positive | info"}],
                "footnote": "Optional short note",
                "style": {"accent_color": "#0f766e"},
            }
        ],
        "reasoning_notes": ["brief reason for block and layout choices"],
    }


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


class LlmHtmlPlanPromptBuilder(Component):
    """Langflow 화면에 표시되는 03a 커스텀 컴포넌트 클래스."""

    display_name = "03a LLM 계획 프롬프트"
    description = "기본 계획에 포함된 데이터/요소 요약을 바탕으로 LLM이 리포트 계획을 보완할 프롬프트를 만듭니다."
    icon = "Sparkles"
    inputs = [
        DataInput(name="payload", display_name="기본 계획", required=True),
        MessageTextInput(name="design_instruction", display_name="추가 디자인 지시", required=False, advanced=True),
    ]
    outputs = [
        Output(name="llm_prompt", display_name="LLM 프롬프트", method="build_prompt"),
        Output(name="prompt_payload", display_name="프롬프트 데이터", method="build_payload"),
    ]

    def build_payload(self) -> Data:
        """프롬프트와 base_plan/schema_hint를 포함한 Data 출력을 만듭니다."""

        result = build_llm_html_plan_prompt_payload(
            getattr(self, "payload", None),
            design_instruction=getattr(self, "design_instruction", ""),
        )
        self.status = {
            "prompt_type": result.get("prompt_type"),
            "prompt_chars": len(str(result.get("prompt") or "")),
        }
        return Data(data=result)

    def build_prompt(self) -> Message:
        """LLM 컴포넌트의 입력에 바로 연결할 수 있는 Message 프롬프트를 만듭니다."""

        result = build_llm_html_plan_prompt_payload(
            getattr(self, "payload", None),
            design_instruction=getattr(self, "design_instruction", ""),
        )
        return Message(text=str(result.get("prompt") or ""))
