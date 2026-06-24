# HTML 리포트 상세 지시문 반영 테스트

이 문서는 LLM이 `보고 싶은 방식`의 구체적인 지시를 실제 HTML 리포트 구조에 반영하는지 확인하기 위한 테스트 세트입니다.

테스트 데이터:

```text
C:\Users\qkekt\Desktop\기능flow\html_report_flow\sample_payloads\sample_instruction_stress.csv
```

`00 리포트 요청/데이터 불러오기`에 CSV 전체를 붙여넣거나 `Read File.Structured Content -> 00.파일 데이터`로 연결합니다.

## 고정 입력

아래 `질문`은 모든 테스트에서 동일하게 사용합니다.

```text
라인/공정별 WIP, 생산량, 불량, 수율, 지연 상태를 종합해서 병목과 위험 공정을 확인하고 싶어
```

아래 테스트에서는 `보고 싶은 방식`만 바꿔가며 실행합니다.

## 확인 방법

각 케이스 실행 후 `03b LLM 계획 검증.최종 계획`과 최종 HTML을 같이 봅니다.

확인할 항목:

- `request_interpretation.layout_intent`가 지시한 상단/중단/하단 구조를 이해했는지
- `request_interpretation.style_intent`가 색상, 밀도, 독자 유형을 반영하는지
- `blocks[].block_id`가 요청한 차트 유형에 맞게 달라지는지
- `blocks[].width`가 full, two_third, half, third로 적절히 바뀌는지
- `chart_policy`, `table_policy`, `annotations`, `highlight_rules`에 필터/정렬/강조 지시가 들어갔는지
- HTML에서 실제 배치, 카드 높이, 간격, 표 위치가 지시와 비슷하게 보이는지

## 케이스 1. 운영 대시보드형 상세 지시

보고 싶은 방식:

```text
현장 운영자가 아침 회의에서 바로 볼 수 있는 한 화면짜리 compact 대시보드로 만들어줘.
상단 첫 줄에는 KPI 카드 5개를 한 줄로 배치해줘. KPI는 총 WIP_QTY, 총 OUTPUT_QTY, 총 DEFECT_QTY, 평균 YIELD_RATE, ALERT_LEVEL이 HIGH인 건수로 구성해줘.
KPI 카드 중 HIGH 건수와 DEFECT_QTY는 빨간색/주황색 계열로 강조하고, 나머지는 초록 계열로 차분하게 보여줘.
두 번째 줄은 좌측 2/3 너비에 DATE별 OUTPUT_QTY 추이 선 그래프를 크게 배치하고, 우측 1/3 너비에는 ALERT_LEVEL별 WIP_QTY 비중 도넛 차트를 배치해줘.
세 번째 줄은 PROCESS별 WIP_QTY와 BACKLOG_QTY를 묶음 막대그래프로 보여주고, 같은 줄 오른쪽에는 PROCESS별 평균 YIELD_RATE를 비교 막대그래프로 보여줘.
마지막에는 ALERT_LEVEL이 HIGH 또는 WARN인 행만 표로 보여줘. 표 컬럼은 DATE, LINE, PROCESS, STATUS, WIP_QTY, BACKLOG_QTY, DEFECT_QTY, YIELD_RATE만 사용하고, BACKLOG_QTY 내림차순으로 정렬해줘.
설명 문장은 짧게 하고, 각 차트에는 가장 위험한 공정 1개만 annotation으로 표시해줘.
```

기대되는 변화:

- `kpi_card_grid`가 상단 high emphasis로 배치
- `trend_line_chart`가 two_third 또는 full에 가까운 큰 블록으로 배치
- `donut_chart`가 ALERT_LEVEL 비중용으로 선택
- `grouped_bar_chart`가 WIP_QTY/BACKLOG_QTY 비교용으로 선택
- 위험 행 표가 마지막 full width로 배치
- style accent가 초록 중심이되 위험 값은 warning/danger로 강조

## 케이스 2. 임원 보고용 요약형 상세 지시

보고 싶은 방식:

```text
임원이 1분 안에 볼 수 있는 요약 보고서처럼 만들어줘.
전체 화면은 여유 있게 comfortable density로 구성하고, 글자는 normal보다 조금 크게 보여줘.
상단에는 제목과 함께 "현재 병목은 WB 공정과 PACK 공정 중심인지 확인"이라는 관점이 드러나게 해줘.
KPI는 3개만 크게 보여줘. 총 BACKLOG_QTY, 평균 YIELD_RATE, HIGH/WARN 비율만 보여줘.
차트는 너무 많이 넣지 말고 2개만 사용해줘. 첫 번째는 PROCESS별 BACKLOG_QTY 순위 막대그래프를 full width로 크게 보여주고, 두 번째는 ALERT_LEVEL별 WIP_QTY 구성비를 도넛 차트로 보여줘.
표는 원본 전체를 보여주지 말고, 마지막에 "우선 확인 대상"이라는 제목으로 BACKLOG_QTY가 높은 상위 5개만 보여줘.
색상은 남색/회색 기반으로 차분하게 하고, HIGH만 빨간색 포인트로 강조해줘.
마지막 narrative에는 핵심 발견 3개와 다음 조치 2개를 짧은 문장으로 넣어줘.
```

기대되는 변화:

- block 수가 줄고, 요약/의사결정 중심 narrative가 늘어남
- KPI가 3개만 선택되는지 확인
- chart block이 2개 정도로 제한되는지 확인
- `ranking_table` 또는 제한된 `detail_data_table`이 상위 5개만 보여주도록 구성
- density/font_scale이 임원용으로 조정

## 케이스 3. 품질 엔지니어 진단형 상세 지시

보고 싶은 방식:

```text
품질 엔지니어가 원인 후보를 찾는 진단 리포트로 구성해줘.
상단에는 평균 YIELD_RATE, 총 DEFECT_QTY, DEFECT_QTY가 가장 높은 PROCESS, CYCLE_TIME_HR 평균을 KPI로 보여줘.
첫 번째 분석 영역에는 YIELD_RATE 분포를 히스토그램으로 full width에 가깝게 보여줘. 수율이 낮은 구간이 눈에 띄도록 warning 색상을 써줘.
두 번째 분석 영역에는 DEFECT_QTY와 CYCLE_TIME_HR의 관계를 산점도로 보여줘. 점 색상은 ALERT_LEVEL 기준으로 다르게 하고, HIGH 행은 annotation으로 표시해줘.
세 번째 분석 영역에는 PROCESS와 PRODUCT_FAMILY를 교차한 heatmap 형태로 평균 DEFECT_QTY를 보여줘.
하단 표는 ALERT_LEVEL이 HIGH이거나 YIELD_RATE가 95 이하인 행만 보여주고, DEFECT_QTY 내림차순으로 정렬해줘.
전체 톤은 분석가용으로 차분하지만, 위험 구간은 빨간색/주황색으로 명확하게 보이게 해줘.
```

기대되는 변화:

- `distribution_histogram`, `scatter_plot`, `heatmap_matrix`가 선택되는지 확인
- chart_policy에 x/y/series가 실제 컬럼으로 들어가는지 확인
- HIGH 또는 낮은 YIELD_RATE 조건이 annotation/highlight/table_policy에 반영되는지 확인
- 품질 진단형 제목, caveat, reasoning_notes가 생성되는지 확인

## 케이스 4. 생산 흐름 모니터링형 상세 지시

보고 싶은 방식:

```text
생산 흐름을 시간 순서로 보는 모니터링 화면으로 만들어줘.
상단에는 데이터 범위와 대상 라인을 요약하는 scope 영역을 두고, 그 아래 KPI는 작게 4개만 보여줘.
가장 중요한 차트는 DATE별 OUTPUT_QTY와 WIP_QTY의 추이야. 이 차트는 full width로 크게 배치하고, OUTPUT_QTY와 WIP_QTY가 같이 보이도록 구성해줘.
그 다음 줄에는 LINE별 OUTPUT_QTY 비교 막대그래프와 SHIFT별 평균 CYCLE_TIME_HR 비교 막대그래프를 half/half로 나란히 보여줘.
하단에는 PROCESS별 STATUS 구성을 누적 막대그래프로 보여주고, 맨 마지막에 상세 표를 넣어줘.
표는 모든 row를 보여줘도 되지만 컬럼은 DATE, LINE, PROCESS, SHIFT, STATUS, WIP_QTY, OUTPUT_QTY, CYCLE_TIME_HR만 사용해줘.
전체는 모니터링용이라 너무 화려하지 않게 하고, 파란색과 초록색을 주 색상으로 사용해줘.
```

기대되는 변화:

- 가장 중요한 trend chart가 full width로 배치
- line/comparison/stacked bar가 순서대로 배치
- half/half 지시가 block.width에 반영
- 표가 전체 row 성격으로 유지되되 컬럼이 제한됨

## 케이스 5. 그래프 중심 + 표 최소화 충돌 지시

보고 싶은 방식:

```text
그래프 중심으로 보고 싶고 표는 최대한 줄여줘.
하지만 나중에 원인을 추적할 수 있도록 마지막에는 핵심 원본 행 5개만 표로 보여줘.
상단 KPI는 4개만 두고, 중간에는 PROCESS별 WIP_QTY 비교 막대그래프와 ALERT_LEVEL별 WIP_QTY 도넛 차트를 나란히 배치해줘.
그 아래에는 PRODUCT_FAMILY별 평균 YIELD_RATE와 총 DEFECT_QTY를 함께 비교할 수 있는 묶음 막대그래프를 넣어줘.
표는 ALERT_LEVEL이 HIGH 또는 WARN인 행 중 BACKLOG_QTY가 높은 상위 5개만 보여줘.
색상은 전체적으로 회색 기반으로 하되, HIGH는 빨간색, WARN은 주황색으로만 강조해줘.
```

기대되는 변화:

- "표 최소화"와 "마지막 핵심 원본 행 5개"가 동시에 반영되는지 확인
- table_policy.limit이 5로 잡히는지 확인
- 그래프 중심으로 block 수가 구성되는지 확인
- HIGH/WARN 색상 지시가 style/annotation/highlight에 반영되는지 확인

## 케이스 6. 레이아웃 지시 우선순위 테스트

보고 싶은 방식:

```text
화면을 정확히 4개 구역으로 나눠줘.
1구역은 상단 전체 폭으로 제목, 데이터 범위, 핵심 요약 2문장을 보여줘.
2구역은 좌측 1/3에 KPI 카드 세로 묶음, 우측 2/3에 DATE별 OUTPUT_QTY 추이 그래프를 배치해줘.
3구역은 좌측 half에 PROCESS별 BACKLOG_QTY 막대그래프, 우측 half에 STATUS별 WIP_QTY 도넛 차트를 배치해줘.
4구역은 full width 상세 표로 구성하되, HIGH/WARN만 보여주고 위험도가 높은 순서로 정렬해줘.
다른 차트가 더 좋아 보여도 이 4개 구역 구조를 우선 지켜줘.
```

기대되는 변화:

- LLM이 임의로 많은 블록을 추가하지 않고 4개 구역 구조를 따르는지 확인
- third/two_third, half/half, full width 지시가 반영되는지 확인
- `request_interpretation.layout_intent`에 4개 구역 구조가 명확히 들어가는지 확인

## 케이스 7. 같은 질문에서 스타일만 바꾸기

보고 싶은 방식 A:

```text
임원 보고용으로 만들어줘. 여백은 넓게, 글자는 크게, 차트는 2개 이하로 제한하고, 표는 마지막에 5행만 보여줘. 색상은 남색과 회색 중심으로 차분하게 구성해줘.
```

보고 싶은 방식 B:

```text
현장 모니터링용으로 만들어줘. compact density로 촘촘하게, KPI와 차트를 많이 보여줘. 위험 항목은 빨간색/주황색으로 강하게 표시하고, 표에는 WARN/HIGH 행을 바로 확인할 수 있게 해줘.
```

비교 포인트:

- 같은 질문과 같은 데이터에서 block 수, density, font_scale, table limit, narrative 양이 달라지는지 확인
- A는 요약형, B는 운영형으로 레이아웃이 달라지는지 확인
