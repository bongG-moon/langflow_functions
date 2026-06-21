# 샘플 데이터

이 CSV/JSON 파일들은 `00 리포트 요청/데이터 불러오기`의 `데이터 직접 입력`에 붙여넣거나 Langflow `Read File -> 00.파일 데이터`로 연결해서 사용할 수 있습니다.

| 파일 | 추천 테스트 질문 | 기대 시각화 |
| --- | --- | --- |
| `sample_wip.csv` | `공정별 WIP와 생산량을 비교하고 날짜별 추이를 보여줘` | 추이 선 그래프, 비교 막대, KPI 카드, 상세 표 |
| `sample_sales_channel_mix.csv` | `채널별 매출 비중을 도넛 차트로 보고 지역별 매출/주문을 비교해줘` | 도넛, 묶음 막대, 추이 선 그래프 |
| `sample_quality_diagnostics.csv` | `불량 수 분포와 수율 관계, warning row를 진단해줘` | 분포 히스토그램, 산점도, 이상/예외 표 |
| `sample_inventory_flow.csv` | `재고 상태 구성비와 창고별 입출고를 비교해줘` | 도넛, 누적 구성 막대, 묶음 막대 |
| `sample_energy_usage.csv` | `kWh 추이와 downtime 상관관계, 장비별 사용량을 보여줘` | 추이 선 그래프, 산점도, 비교 막대 |
| `sample_customer_funnel.csv` | `stage별 전환율과 segment breakdown을 보여줘` | 누적 구성 막대, 도넛, 순위 표 |

PowerShell 화면에서 한글이 깨져 보여도 파일은 UTF-8입니다. Langflow 입력칸이나 UTF-8 환경에서 테스트하면 정상적으로 읽힙니다.
