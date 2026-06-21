# 02 요소 양식 JSON 예시

아래 JSON 파일 중 하나를 열어 전체 내용을 복사한 뒤 `02 리포트 요소 카탈로그`의 `요소 양식 JSON` 입력칸에 붙여넣으면 됩니다.

| 파일 | 같이 쓰기 좋은 데이터 | 바뀌는 점 |
| --- | --- | --- |
| `catalog_operations_compact.json` | `sample_wip.csv`, `sample_inventory_flow.csv`, `sample_energy_usage.csv` | 운영자용 compact 대시보드, KPI 우선, 조밀한 표, full-width 추이/묶음 막대 |
| `catalog_executive_summary.json` | `sample_sales_channel_mix.csv`, `sample_customer_funnel.csv` | 큰 글자, 적은 블록 수, 상단 인사이트/추천 중심 |
| `catalog_quality_diagnostics.json` | `sample_quality_diagnostics.csv`, `sample_energy_usage.csv` | 분포/산점도/예외 표 강조, warning/danger row highlight |
| `catalog_composition_dashboard.json` | `sample_sales_channel_mix.csv`, `sample_inventory_flow.csv`, `sample_customer_funnel.csv` | 도넛, 누적 막대, 히트맵, 구성비 중심 레이아웃 |

사용 순서:

1. JSON 파일 하나를 엽니다.
2. 전체 JSON 객체를 복사합니다.
3. `02.요소 양식 JSON`에 붙여넣습니다.
4. flow를 실행합니다.

이 JSON은 내장 catalog를 통째로 대체하지 않습니다. 같은 `component_id`의 설명과 기본값을 보강하고, `template_defaults`, `style_presets`, `catalog_notes`를 LLM prompt와 deterministic fallback plan에 전달합니다.
