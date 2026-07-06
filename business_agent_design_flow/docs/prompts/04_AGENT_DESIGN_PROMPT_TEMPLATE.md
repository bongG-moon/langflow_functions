# 04 AI Agent 설계 Prompt Template

Langflow 기본 `Prompt Template` 컴포넌트에 아래 코드블록 내용을 그대로 붙여넣습니다.

## 연결 변수

| Prompt Template 변수 | 연결할 값 |
| --- | --- |
| `business_profile_json` | `04 AI Agent 설계 프롬프트 변수 준비`의 `업무 프로필 JSON` |
| `catalog_items_json` | `04 AI Agent 설계 프롬프트 변수 준비`의 `추천 카탈로그 JSON` |
| `recommendation_trace_json` | `04 AI Agent 설계 프롬프트 변수 준비`의 `추천 근거 JSON` |
| `design_instructions` | `04 AI Agent 설계 프롬프트 변수 준비`의 `설계 지침` |
| `design_output_schema` | `04 AI Agent 설계 프롬프트 변수 준비`의 `출력 스키마 JSON` |

## 프롬프트

```text
당신은 초보 Langflow 개발자가 실제로 구현할 수 있는 AI Agent 업무 개선안을 설계하는 컨설턴트입니다.
아래 업무 프로필과 추천 카탈로그를 참고해 현재 업무 Flow와 AI Agent 적용 후 Flow를 설계하세요.

[업무 프로필 JSON]
{business_profile_json}

[사용 가능한 기능/사례 카탈로그 JSON]
{catalog_items_json}

[추천 근거 Trace]
{recommendation_trace_json}

[설계 원칙]
{design_instructions}

[반환 JSON 스키마]
{design_output_schema}
```

## 결과에 반드시 포함되어야 하는 핵심 구조

- `as_is_flow`: 현재 업무 흐름
- `to_be_flow`: AI Agent 적용 후 업무 흐름
- `recommended_capabilities`: 추천 기능과 추천 이유
- `improvement_blueprint`: 현재 업무 단계별 개선 명세
- `improvement_blueprint.applied_capabilities.reference_sources`: 적용 기능별 참고 정보와 링크

`improvement_blueprint`는 HTML의 `업무 단계별 개선 명세` 섹션으로 렌더링됩니다.
