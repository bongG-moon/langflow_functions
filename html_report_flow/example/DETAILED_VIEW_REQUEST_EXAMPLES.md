# 보고 싶은 방식 상세 예시 3개

이 문서는 `sample_instruction_stress.csv`로 LLM이 상세 지시를 얼마나 잘 반영하는지 확인하기 위한 `보고 싶은 방식` 예시입니다.

테스트 데이터:

```text
C:\Users\qkekt\Desktop\기능flow\html_report_flow\sample_payloads\sample_instruction_stress.csv
```

`00 리포트 요청/데이터 불러오기`의 `질문`에는 아래 문장을 공통으로 넣고, `보고 싶은 방식`만 예시별로 바꿔 테스트합니다.

공통 질문:

```text
라인/공정별 WIP, 생산량, 불량, 수율, 지연 상태를 종합해서 병목과 위험 공정을 확인하고 싶어
```

## 예시 1. 운영 대시보드형

`보고 싶은 방식`:

```text
상단 첫 줄에는 KPI 카드 5개를 한 줄로 배치해줘.
두 번째 줄은 좌측 2/3 너비에 DATE별 OUTPUT_QTY 추이 선 그래프,
우측 1/3 너비에는 ALERT_LEVEL별 WIP_QTY 비중 도넛 차트를 배치해줘.
마지막에는 ALERT_LEVEL이 HIGH 또는 WARN인 행만 표로 보여줘.
표 컬럼은 DATE, LINE, PROCESS, STATUS, WIP_QTY, BACKLOG_QTY, DEFECT_QTY, YIELD_RATE만 사용하고,
BACKLOG_QTY 내림차순으로 정렬해줘.
```

확인 포인트:

- KPI 카드 5개가 상단 한 줄로 배치되는지
- 2/3 너비 추이 그래프와 1/3 너비 도넛 차트가 같은 줄에 배치되는지
- 위험 행만 표로 제한되는지
- 표 컬럼과 정렬 기준이 지시대로 반영되는지

## 예시 2. 품질 진단 리포트형

`보고 싶은 방식`:

```text
품질 엔지니어가 원인을 추적하는 진단 리포트로 만들어줘.
상단에는 KPI를 4개만 배치해줘. KPI는 평균 YIELD_RATE, 총 DEFECT_QTY, DEFECT_QTY가 가장 높은 PROCESS, ALERT_LEVEL이 HIGH인 건수로 구성해줘.
첫 번째 본문 영역은 full width로 YIELD_RATE 분포 히스토그램을 크게 보여줘. YIELD_RATE가 낮은 구간은 warning 느낌으로 강조해줘.
두 번째 본문 영역은 좌측 half에 DEFECT_QTY와 CYCLE_TIME_HR의 관계를 산점도로 보여주고, 우측 half에는 PROCESS와 PRODUCT_FAMILY를 교차한 평균 DEFECT_QTY heatmap을 보여줘.
하단에는 ALERT_LEVEL이 HIGH이거나 YIELD_RATE가 95 이하인 행만 표로 보여줘.
표는 DEFECT_QTY 내림차순으로 정렬하고, 컬럼은 DATE, LINE, PROCESS, PRODUCT_FAMILY, DEFECT_QTY, YIELD_RATE, CYCLE_TIME_HR, ALERT_LEVEL만 사용해줘.
전체 색상은 흰색/회색 기반으로 차분하게 하고, HIGH와 낮은 수율만 빨간색 또는 주황색으로 강조해줘.
```

확인 포인트:

- 히스토그램, 산점도, heatmap이 선택되는지
- 품질/수율/불량 중심의 제목과 narrative가 생성되는지
- HIGH 또는 낮은 수율 조건이 표와 강조 규칙에 반영되는지
- full width, half/half 배치가 반영되는지

## 예시 3. 임원 요약 보고형

`보고 싶은 방식`:

```text
임원이 1분 안에 읽는 요약 보고서처럼 만들어줘.
전체는 comfortable density로 여백을 넓게 쓰고, 글자는 normal보다 조금 크게 보여줘.
상단에는 제목과 함께 핵심 요약 문장 2개를 먼저 보여줘. 요약 문장은 WB 또는 PACK 공정의 병목 가능성, 그리고 HIGH/WARN 위험 상태를 중심으로 작성해줘.
KPI는 3개만 크게 보여줘. 총 BACKLOG_QTY, 평균 YIELD_RATE, HIGH/WARN 비율만 사용해줘.
차트는 2개만 넣어줘. 첫 번째 차트는 PROCESS별 BACKLOG_QTY 순위 막대그래프를 full width로 크게 보여주고, 두 번째 차트는 ALERT_LEVEL별 WIP_QTY 구성비를 도넛 차트로 보여줘.
표는 마지막에 "우선 확인 대상 TOP 5"라는 제목으로 BACKLOG_QTY가 높은 상위 5개만 보여줘.
표 컬럼은 DATE, LINE, PROCESS, STATUS, BACKLOG_QTY, WIP_QTY, YIELD_RATE, ALERT_LEVEL만 사용해줘.
색상은 남색과 회색 중심으로 차분하게 구성하고, HIGH만 빨간색 포인트로 강조해줘.
마지막에는 다음 조치 2개를 짧은 문장으로 제안해줘.
```

확인 포인트:

- KPI와 차트 수가 줄어드는지
- 요약 문장과 다음 조치가 narrative에 반영되는지
- executive/comfortable 스타일이 반영되는지
- 표가 TOP 5로 제한되는지
