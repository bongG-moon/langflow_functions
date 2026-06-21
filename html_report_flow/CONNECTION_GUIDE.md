# HTML 생성 FLOW 연결 가이드

이 가이드는 `sample_wip.csv` 기준으로 Langflow에서 바로 체험할 수 있는 연결 방법을 설명합니다.

이번 구조에서는 최종 출력 노드를 둘로 나눕니다.

- `05-1 HTML 원문 출력`: Report API 없이 Playground에 전체 HTML 코드를 출력합니다.
- `05-2 공유 링크 출력`: Report API에 HTML을 저장하고 다운로드 링크 메시지를 출력합니다.

기존 `06 HTML Report Response Builder`는 더 이상 사용하지 않습니다.

## 1. 샘플 입력

샘플 CSV:

```text
C:\Users\qkekt\Desktop\기능flow\html_report_flow\sample_payloads\sample_wip.csv
```

질문:

```text
공정별 WIP 비교와 날짜별 생산량 추이를 HTML 리포트로 보여줘
```

보고 싶은 방식:

```text
KPI 카드, 비교 그래프, 추이 그래프, 상세 표를 포함해줘
```

## 2. 전체 흐름

### A. Playground에 HTML 원문 출력

```text
00 리포트 요청/데이터 불러오기
-> 01 데이터 구조 분석
-> 02 리포트 요소 카탈로그
-> 03 기본 리포트 계획
-> 03a LLM 계획 프롬프트
-> LLM
-> 03b LLM 계획 검증
-> 04 HTML 렌더링
-> 05-1 HTML 원문 출력
-> Chat Output
```

### B. 로컬 Report API 저장 후 링크 출력

```text
00 리포트 요청/데이터 불러오기
-> 01 데이터 구조 분석
-> 02 리포트 요소 카탈로그
-> 03 기본 리포트 계획
-> 03a LLM 계획 프롬프트
-> LLM
-> 03b LLM 계획 검증
-> 04 HTML 렌더링
-> 05-2 공유 링크 출력
-> Chat Output
```

LLM 없이 빠르게 확인하려면 `03 기본 리포트 계획.기본 계획`을 `04 HTML 렌더링.최종 계획`에 바로 연결하면 됩니다.

## 3. 노드별 입력값

### 3.1 `00 리포트 요청/데이터 불러오기`

파일:

```text
langflow_components/html_report_flow/00_demo_report_request_loader.py
```

직접 CSV를 붙여넣을 때:

| 화면 입력명 | 값 |
| --- | --- |
| `질문` | `공정별 WIP 비교와 날짜별 생산량 추이를 HTML 리포트로 보여줘` |
| `보고 싶은 방식` | `KPI 카드, 비교 그래프, 추이 그래프, 상세 표를 포함해줘` |
| `데이터 직접 입력` | `sample_wip.csv` 전체 내용 |
| `파일 데이터` | 비워둠 |

File Read를 쓸 때:

| From | Output | To | Input |
| --- | --- | --- | --- |
| `Read File` | `Structured Content` | `00 리포트 요청/데이터 불러오기` | `파일 데이터` |

이 경우 `데이터 직접 입력`은 비워두면 됩니다. CSV/JSON/JSONL 형식은 `00` 노드가 자동으로 판별합니다.

`00` 출력 연결:

| From | Output | To | Input |
| --- | --- | --- | --- |
| `00 리포트 요청/데이터 불러오기` | `요청 데이터` | `01 데이터 구조 분석` | `요청 데이터` |
| `00 리포트 요청/데이터 불러오기` | `요청 데이터` | `03 기본 리포트 계획` | `요청 데이터` |

### 3.2 `01 데이터 구조 분석`

역할: 컬럼을 숫자/범주/날짜/상태 후보로 분류하고 row 수, preview 여부, 경고를 요약합니다.

| From | Output | To | Input |
| --- | --- | --- | --- |
| `01 데이터 구조 분석` | `데이터 분석 결과` | `02 리포트 요소 카탈로그` | `데이터 분석 결과` |
| `01 데이터 구조 분석` | `데이터 분석 결과` | `03 기본 리포트 계획` | `데이터 분석 결과` |

### 3.3 `02 리포트 요소 카탈로그`

역할: 데이터 구조와 사용자 요청을 보고 사용 가능한 리포트 요소와 추천 요소를 만듭니다.

| 화면 입력명 | 값 |
| --- | --- |
| `데이터 분석 결과` | `01 데이터 구조 분석.데이터 분석 결과` 연결 |
| `요소 양식 JSON` | 기본 내장 양식만 쓸 때는 비워둠 |

정형화된 양식값은 `요소 양식 JSON`에 넣습니다. 예시는 아래 폴더에 있습니다.

```text
C:\Users\qkekt\Desktop\기능flow\html_report_flow\sample_catalogs
```

예를 들어 운영 compact 양식을 쓰려면 `sample_catalogs/catalog_operations_compact.json` 전체 내용을 복사해서 `02`의 `요소 양식 JSON`에 붙여넣습니다.

`02` 출력 연결:

| From | Output | To | Input |
| --- | --- | --- | --- |
| `02 리포트 요소 카탈로그` | `요소 추천 결과` | `03 기본 리포트 계획` | `요소 추천 결과` |

## 4. LLM 연결

### 4.1 `03 기본 리포트 계획`

| 화면 입력명 | 연결 |
| --- | --- |
| `요청 데이터` | `00 리포트 요청/데이터 불러오기.요청 데이터` |
| `데이터 분석 결과` | `01 데이터 구조 분석.데이터 분석 결과` |
| `요소 추천 결과` | `02 리포트 요소 카탈로그.요소 추천 결과` |
| `최대 블록 수` | 보통 `8` 또는 `10` |

출력:

| From | Output | To | Input |
| --- | --- | --- | --- |
| `03 기본 리포트 계획` | `기본 계획` | `03a LLM 계획 프롬프트` | `기본 계획` |
| `03 기본 리포트 계획` | `기본 계획` | `03b LLM 계획 검증` | `기본 계획` |

`03` 출력 payload에는 렌더링용 `report_plan`과 함께 03a/03b가 쓸 작은 `llm_context` 요약이 들어갑니다. 그래서 `03a`, `03b`에 `데이터 분석 결과`나 `요소 추천 결과`를 다시 연결하지 않아도 됩니다.

### 4.2 `03a LLM 계획 프롬프트`

| 화면 입력명 | 연결 또는 값 |
| --- | --- |
| `기본 계획` | `03 기본 리포트 계획.기본 계획` |
| `추가 디자인 지시` | 선택. 예: `운영자가 빠르게 볼 수 있게 compact하게 구성` |

출력 연결:

| From | Output | To | Input |
| --- | --- | --- | --- |
| `03a LLM 계획 프롬프트` | `LLM 프롬프트` | LLM 노드 | prompt/message 입력 |

LLM은 HTML 코드가 아니라 JSON report plan만 반환해야 합니다.

### 4.3 `03b LLM 계획 검증`

| 화면 입력명 | 연결 |
| --- | --- |
| `기본 계획` | `03 기본 리포트 계획.기본 계획` |
| `LLM 응답` | LLM 노드의 text/message 출력 |

출력 연결:

| From | Output | To | Input |
| --- | --- | --- | --- |
| `03b LLM 계획 검증` | `최종 계획` | `04 HTML 렌더링` | `최종 계획` |

## 5. 최종 출력 두 가지

### 5.1 HTML 원문을 Playground에 출력

| From | Output | To | Input |
| --- | --- | --- | --- |
| `04 HTML 렌더링` | `HTML 생성 결과` | `05-1 HTML 원문 출력` | `HTML 생성 결과` |
| `05-1 HTML 원문 출력` | `HTML 원문` | `Chat Output` | `input` |

### 5.2 로컬 Report API 저장 후 링크 출력

먼저 Report API 서버가 실행 중이어야 합니다.

처음 한 번만 설치:

```powershell
cd C:\Users\qkekt\Desktop\기능flow\html_report_flow\report_api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

매번 서버 실행:

```powershell
cd C:\Users\qkekt\Desktop\기능flow\html_report_flow\report_api
.\.venv\Scripts\Activate.ps1
python server.py
```

정상 실행 확인:

```text
http://127.0.0.1:8010/
```

브라우저에서 `alive!`가 보이면 됩니다.

생성된 HTML 파일은 기본적으로 아래 폴더에 저장됩니다.

```text
C:\Users\qkekt\Desktop\기능flow\html_report_flow\report_api\storage\reports
```

포트, 저장 위치, 기본 만료시간을 바꾸고 싶으면 `.env` 파일이 아니라 아래 파일 맨 위 설정값을 수정합니다.

```text
C:\Users\qkekt\Desktop\기능flow\html_report_flow\report_api\server.py
```

주로 수정하는 값:

| 설정값 | 기본값 | 의미 |
| --- | --- | --- |
| `SERVER_PORT` | `8010` | 로컬 서버 포트 |
| `BASE_URL` | `http://127.0.0.1:8010` | Langflow 응답에 표시될 링크 주소 |
| `STORAGE_DIR` | `report_api\storage` | HTML/JSON 저장 폴더 |
| `DEFAULT_TTL_HOURS` | `24` | 기본 링크 유효시간 |
| `MAX_TTL_HOURS` | `168` | 최대 링크 유효시간 |
| `MAX_STORAGE_BYTES` | `536870912` | 전체 저장 용량 제한 |

`05-2 공유 링크 출력` 입력:

| 화면 입력명 | 값 또는 연결 |
| --- | --- |
| `HTML 생성 결과` | `04 HTML 렌더링.HTML 생성 결과` |
| `Report API 주소` | `http://127.0.0.1:8010` |
| `링크 유효시간` | `24` |

출력 연결:

| From | Output | To | Input |
| --- | --- | --- | --- |
| `05-2 공유 링크 출력` | `링크 메시지` | `Chat Output` | `input` |

`링크 메시지`에는 짧은 생성 안내, 다운로드 링크, 만료 시간만 표시됩니다.

더 자세한 서버 실행 안내는 아래 문서를 보면 됩니다.

```text
docs/LOCAL_REPORT_API_GUIDE.md
```

## 6. LLM 없이 빠른 확인

LLM 노드를 빼고 HTML 생성만 확인하려면 아래처럼 연결합니다.

| 순서 | From | Output | To | Input |
| --- | --- | --- | --- | --- |
| 1 | `00 리포트 요청/데이터 불러오기` | `요청 데이터` | `01 데이터 구조 분석` | `요청 데이터` |
| 2 | `01 데이터 구조 분석` | `데이터 분석 결과` | `02 리포트 요소 카탈로그` | `데이터 분석 결과` |
| 3 | `00 리포트 요청/데이터 불러오기` | `요청 데이터` | `03 기본 리포트 계획` | `요청 데이터` |
| 4 | `01 데이터 구조 분석` | `데이터 분석 결과` | `03 기본 리포트 계획` | `데이터 분석 결과` |
| 5 | `02 리포트 요소 카탈로그` | `요소 추천 결과` | `03 기본 리포트 계획` | `요소 추천 결과` |
| 6 | `03 기본 리포트 계획` | `기본 계획` | `04 HTML 렌더링` | `최종 계획` |
| 7 | `04 HTML 렌더링` | `HTML 생성 결과` | `05-1 HTML 원문 출력` | `HTML 생성 결과` |
| 8 | `05-1 HTML 원문 출력` | `HTML 원문` | `Chat Output` | `input` |

## 7. 문제 해결

| 증상 | 확인할 것 |
| --- | --- |
| `row_count`가 0 | `00`의 `데이터 직접 입력` 또는 `파일 데이터` 연결 확인 |
| File Read 연결이 안 됨 | 기존 edge 삭제 후 `Read File.Structured Content -> 00.파일 데이터`로 다시 연결 |
| LLM 결과가 반영되지 않음 | `03a.LLM 프롬프트 -> LLM`, `LLM 출력 -> 03b.LLM 응답`, `03.기본 계획 -> 03b.기본 계획` 확인 |
| 다양한 차트가 안 나옴 | 질문/보고 싶은 방식에 `도넛`, `묶음 막대`, `히트맵`, `분포`, `산점도`처럼 원하는 시각화를 구체적으로 적기 |
| HTML 원문만 보고 싶음 | `04.HTML 생성 결과 -> 05-1.HTML 생성 결과`, `05-1.HTML 원문 -> Chat Output.input` 연결 |
| 공유 링크가 없음 | `05-2`의 `Report API 주소`와 로컬 서버 실행 여부 확인 |
| 다른 사람 PC에서 링크가 안 열림 | `127.0.0.1`은 자기 PC 전용 주소입니다. 체험자는 각자 로컬 서버를 실행해야 합니다 |
| 링크 만료 | `05-2`에서 다시 생성. `링크 유효시간` 값만큼 유효합니다. |
