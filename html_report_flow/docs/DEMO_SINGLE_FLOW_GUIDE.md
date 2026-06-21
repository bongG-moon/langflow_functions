# Demo Single HTML Report Flow Guide

별도 dataset flow가 없는 상태에서 `html_report_flow`를 체험하기 위한 단일 flow 구성입니다.

## 입력

사용자는 `00 리포트 요청/데이터 불러오기`에 아래 값을 넣습니다.

- `질문`: 무엇을 보고 싶은지
- `보고 싶은 방식`: KPI, 도넛, 추이, 상세 표 등 원하는 표현
- `데이터 직접 입력`: CSV/JSON 직접 붙여넣기
- 또는 `파일 데이터`: Langflow `Read File.Structured Content` 연결

## 기본 노드 흐름

```text
00 리포트 요청/데이터 불러오기
-> 01 데이터 구조 분석
-> 02 리포트 요소 카탈로그
-> 03 기본 리포트 계획
-> 03a LLM 계획 프롬프트
-> LLM
-> 03b LLM 계획 검증
-> 04 HTML 렌더링
```

최종 출력은 목적에 따라 둘 중 하나를 연결합니다.

```text
04 HTML 렌더링 -> 05-1 HTML 원문 출력 -> Chat Output
04 HTML 렌더링 -> 05-2 공유 링크 출력 -> Chat Output
```

## Minimal No-Server Experience

Report API 없이 Playground에서 전체 HTML 코드를 보려면:

```text
04 HTML 렌더링.HTML 생성 결과
-> 05-1 HTML 원문 출력.HTML 생성 결과
-> 05-1 HTML 원문 출력.HTML 원문
-> Chat Output.input
```

`05-1.HTML 원문`은 HTML이 실행되지 않도록 코드블록으로 감싸서 출력합니다.

## Full Link Experience

다운로드 링크까지 받으려면 각 PC에서 로컬 Report API 서버를 실행하고 `05-2 공유 링크 출력`을 연결합니다. MongoDB는 필요 없고, 생성 파일은 `report_api/storage/reports`에 저장됩니다.

```text
04 HTML 렌더링.HTML 생성 결과
-> 05-2 공유 링크 출력.HTML 생성 결과
-> 05-2 공유 링크 출력.링크 메시지
-> Chat Output.input
```

`05-2` 입력 예시:

| 화면 입력명 | 값 |
| --- | --- |
| `Report API 주소` | `http://127.0.0.1:8010` |
| `링크 유효시간` | `24` |

서버 실행 상세 절차는 아래 문서에 있습니다.

```text
docs/LOCAL_REPORT_API_GUIDE.md
```

## File Read Mode

```text
Read File.Structured Content
-> 00 리포트 요청/데이터 불러오기.파일 데이터
```

`00`에서는 `데이터 직접 입력`만 비워두면 됩니다. CSV/JSON/JSONL 형식은 자동으로 판별합니다.

`invalid handles`가 나오면 기존 edge를 삭제하고 0번 컴포넌트를 refresh/reload한 뒤 다시 연결하세요.

## Text Input Mode

CSV 전체를 `00.데이터 직접 입력`에 `Ctrl+A`, `Ctrl+C`, `Ctrl+V`로 넣어도 됩니다.

| 화면 입력명 | 값 |
| --- | --- |
| `데이터 직접 입력` | CSV 전체 내용 |

## 샘플 조합

| CSV | Catalog | 확인하기 좋은 시각화 |
| --- | --- | --- |
| `sample_wip.csv` | `catalog_operations_compact.json` | KPI, 추이 선 그래프, 묶음 막대 |
| `sample_sales_channel_mix.csv` | `catalog_composition_dashboard.json` | 도넛, 묶음 막대, 히트맵 |
| `sample_quality_diagnostics.csv` | `catalog_quality_diagnostics.json` | 분포 히스토그램, 산점도, 예외 표 |
| `sample_inventory_flow.csv` | `catalog_composition_dashboard.json` | 도넛, 누적 구성 막대, 묶음 막대 |
| `sample_energy_usage.csv` | `catalog_quality_diagnostics.json` | 추이 선 그래프, 산점도 |
| `sample_customer_funnel.csv` | `catalog_executive_summary.json` | 누적 구성 막대, 도넛, 요약 |

## 지원 데이터 형태

CSV:

```csv
DATE,OPER_SHORT_DESC,PRODUCT,WIP,PRODUCTION
2026-06-16,DA,A,120,80
2026-06-17,WB,B,90,100
```

JSON rows:

```json
[
  {"DATE": "2026-06-16", "OPER_SHORT_DESC": "DA", "PRODUCT": "A", "WIP": 120, "PRODUCTION": 80},
  {"DATE": "2026-06-17", "OPER_SHORT_DESC": "WB", "PRODUCT": "B", "WIP": 90, "PRODUCTION": 100}
]
```

JSON multiple datasets:

```json
{
  "datasets": [
    {
      "dataset_id": "wip_demo",
      "label": "WIP Demo Data",
      "rows": [
        {"DATE": "2026-06-16", "OPER_SHORT_DESC": "DA", "PRODUCT": "A", "WIP": 120}
      ]
    }
  ]
}
```

현재 demo flow는 여러 dataset이 들어오면 첫 번째 dataset을 분석 대상으로 사용하고, 전체 dataset 목록은 payload의 `available_datasets` 요약으로 유지합니다.
