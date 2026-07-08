# 유연 데이터 조회 Flow 발표안

대상 발표 시간: 10~15분
권장 장표 수: 8장
핵심 메시지: 코딩에 익숙하지 않은 사람도 자연어로 실제 업무 데이터를 불러오고, 그 결과를 다른 Agent/Flow의 출발점으로 재사용할 수 있게 만든다.

---

## 1. 왜 이 Flow를 만들었나

### 슬라이드 문구

**Agent 개발의 첫 장벽은 "LLM 사용"보다 "내 업무 데이터 연결"이었다.**

- Agent Builder(Langflow)를 처음 접하는 사람도 쉽게 Agent 개발에 관심을 갖게 만들고 싶었다.
- 큐브, 메일링, LLM 연계는 이미 비교적 쉽게 할 수 있었다.
- 반대로 실제로 내가 자주 쓰는 업무 데이터를 가져오는 과정은 여전히 코드, 쿼리, API, 인증 정보에 의존했다.
- 그래서 "데이터만 쉽게 불러올 수 있으면 간단한 Agent Flow는 누구나 만들 수 있겠다"는 생각에서 시작했다.

### 발표자 노트

처음부터 거대한 Agent를 만들기보다, 입문자가 바로 체감할 수 있는 지점을 찾았다. 업무 자동화에서 가장 먼저 막히는 부분은 LLM 호출 자체가 아니라 "내가 보던 데이터를 어떻게 가져오느냐"였다. 이 Flow는 그 시작 장벽을 낮추는 실험이다.

---

## 2. 풀고 싶었던 문제를 정확히 정의하면

### 슬라이드 문구

**문제 정의**

코딩에 익숙하지 않은 사용자가 Agent를 만들 때, 데이터 조회 로직을 직접 수정하지 않고도 자연어만으로 필요한 소스와 조건을 선택해 실행할 수 있어야 한다.

**기존 방식의 어려움**

- 데이터마다 조회 코드, SQL, API body, 문서 ID, 인증 방식이 다르다.
- 사용자가 매번 어떤 source를 써야 하는지, 어떤 parameter가 필요한지 알아야 한다.
- 조회 코드가 개인 PC나 특정 프로젝트에 묶여 있어 다른 Flow에서 재사용하기 어렵다.
- 자연어 요청과 실제 실행 payload 사이의 변환 규칙이 명확하지 않으면 Flow가 쉽게 깨진다.

**이 Flow의 목표**

- 기존 조회 코드를 source별 component로 분리한다.
- 사용자는 코드를 수정하지 않고 자연어로 요청한다.
- LLM은 source 이름과 parameter만 고른다.
- 실제 실행 정보는 `source_catalog`와 Normalizer가 채운다.
- 결과는 `data_json` 형태로 다른 Flow가 바로 읽을 수 있게 만든다.

### 발표자 노트

여기서 중요한 점은 "LLM이 모든 것을 만들게 하자"가 아니라, LLM의 역할을 제한했다는 것이다. LLM은 어떤 데이터를 볼지와 조건값을 고르고, SQL/API URL/문서 ID 같은 실행 정보는 사람이 관리하는 catalog에서 가져오도록 했다.

---

## 3. 사용 대상과 사용 시나리오

### 슬라이드 문구

**사용 대상**

- Langflow 기반 Agent 개발을 시작해보고 싶은 입문자
- 코딩보다 업무 요구사항 설명에 익숙한 사용자
- 이미 반복적으로 조회하는 데이터가 있지만 Flow로 재사용하고 싶은 사용자

**사용 시나리오**

1. 자주 쓰는 데이터 조회 코드를 source별 component로 등록한다.
2. source 설명, parameter, query/API/doc 정보를 `source_catalog`로 정리한다.
3. 사용자는 Chat Input에 자연어로 요청한다.
4. LLM이 적절한 source와 parameter를 선택한다.
5. Flow가 Oracle, H-API, Datalake, Goodocs 중 필요한 node만 실행한다.
6. 결과는 Chat Output에서 확인하거나 다른 Flow의 입력으로 넘긴다.

### 발표자 노트

사용자는 "2026년 5월 20일 FAB1 D/A1 공정에서 DDR5 생산 실적 가져와줘"처럼 말하면 된다. 사용자가 SQL을 수정하거나 API body를 직접 만들 필요가 없게 하는 것이 핵심이다.

---

## 4. Flow 전체 구조

### 슬라이드 문구

**두 단계 구조**

1. `source_catalog` 작성/관리
   - 사람이 쓴 source 설명을 LLM이 정규화한다.
   - 필요하면 MongoDB에 source별로 저장하고 다시 불러온다.

2. 자연어 기반 데이터 조회
   - 자연어 요청을 LLM이 `name + params`로 변환한다.
   - Normalizer가 catalog를 참조해 실행 가능한 `data_request`를 만든다.
   - source별 data node가 자기 source_type만 실행한다.
   - Merger와 Output Builder가 결과를 downstream용 JSON으로 정리한다.

**주요 component**

- `07 Catalog Normalizer`: source 설명을 표준 catalog로 변환
- `09/10 MongoDB Store/Loader`: 긴 SQL이 포함된 catalog 저장/재사용
- `08 LLM Caller`: Prompt Template 결과를 LLM으로 호출
- `00 Data Request Normalizer`: LLM 결과와 catalog를 합쳐 실행 요청 생성
- `01~04 Data Nodes`: Oracle, H-API, Datalake, Goodocs 조회
- `05 Data Result Merger`: source별 결과 병합
- `06 Data Output Builder`: `data_json`과 테스트용 message 생성
- `11 HTML Report Datasets Adapter`: HTML Report Flow 입력으로 변환

### 발표자 노트

전체 구조를 보여줄 때는 `source_catalog`가 두 번 쓰인다는 점을 강조하면 좋다. Prompt Template에서는 LLM이 source를 고르기 위해 catalog를 보고, Normalizer에서는 실행에 필요한 정보를 채우기 위해 같은 catalog를 다시 본다.

---

## 5. 기술 핵심: Payload가 어떻게 전달되는가

### 슬라이드 문구

**Payload 흐름**

```text
Chat Input
-> Prompt Template
-> LLM Caller
-> Data Request Normalizer
-> Oracle/H-API/Datalake/Goodocs Data
-> Data Result Merger
-> Data Output Builder
-> data_json / HTML datasets
```

**1단계: LLM은 최소 요청만 만든다**

```json
{
  "name": "production_summary",
  "params": {
    "DATE": "20260520",
    "FACTORY": "FAB1",
    "OPER_NAME": "D/A1",
    "MODE": "DDR5",
    "PRODUCT_KEYWORD": "DDR5"
  }
}
```

**2단계: Normalizer가 실행 가능한 요청으로 보강한다**

```json
{
  "source_type": "oracle",
  "name": "production_summary",
  "params": {
    "DATE": "20260520",
    "FACTORY": "FAB1"
  },
  "required_params": ["DATE", "FACTORY"],
  "param_formats": {
    "DATE": "YYYYMMDD",
    "FACTORY": "text"
  },
  "source_config": {
    "db_key": "PKG_RPT",
    "query_template": "SELECT ..."
  }
}
```

**3단계: source별 data node가 결과를 만든다**

```json
{
  "source_type": "oracle",
  "items": [
    {
      "name": "production_summary",
      "success": true,
      "row_count": 10,
      "data_result": [],
      "request_params": {}
    }
  ]
}
```

**4단계: 최종 출력은 downstream이 읽기 쉬운 `data_json`으로 정리된다**

```json
{
  "success": true,
  "mode": "single",
  "data_result": [
    [
      {"WORK_DT": "20260520", "PRODUCTION": 1000}
    ]
  ],
  "source_results": [
    {
      "name": "production_summary",
      "source_type": "oracle",
      "row_count": 1,
      "request_params": {}
    }
  ]
}
```

### 발표자 노트

기술 설명은 이 장에서 집중하면 된다. 보안상 credential은 LLM output이나 catalog에 넣지 않고 각 data node input에만 둔다. 또한 data node들은 모두 같은 `data_request`를 받지만, 자기 `source_type`이 아니면 `skipped` 처리한다. 그래서 Langflow 연결은 단순하고, source가 늘어나도 구조를 유지하기 쉽다.

---

## 6. 문제를 풀 때 가장 어려웠던 부분

### 슬라이드 문구

**가장 어려웠던 부분은 "LLM의 유연함"과 "실행 payload의 안정성" 사이의 경계였다.**

- LLM이 SQL, API URL, credential을 직접 만들지 않게 역할을 제한해야 했다.
- 사용자의 자연어 표현이 다양해도 source와 parameter는 표준 형태로 정리되어야 했다.
- Langflow에서는 Data, Message, Text, JSON wrapper가 섞여 들어오기 때문에 payload parsing을 견고하게 만들어야 했다.
- 긴 `query_template`은 UI preview나 Freeze text에서 잘릴 수 있어 MongoDB Store/Loader 경로가 필요했다.
- 여러 source를 한 번에 조회할 때 결과 순서와 metadata를 잃지 않도록 `source_results`를 따로 보존해야 했다.
- 코딩에 익숙하지 않은 사용자도 이해할 수 있는 입력 방식과, downstream Flow가 읽기 쉬운 출력 구조를 동시에 맞춰야 했다.

### 발표자 노트

핵심은 "자연어니까 대충 받아도 된다"가 아니라, 자연어 입력을 받더라도 실행 직전에는 반드시 안정적인 JSON 계약으로 바꿔야 한다는 점이었다. 이 경계를 `00 Data Request Normalizer`가 맡는다.

---

## 7. 생각보다 쉽게 풀린 부분

### 슬라이드 문구

**이미 반복해서 쓰던 조회 코드가 있었기 때문에 component화는 빠르게 진행할 수 있었다.**

- Oracle, H-API, Datalake, Goodocs처럼 source 종류가 명확했다.
- 기존 조회 코드를 source별 node로 분리하니 역할이 자연스럽게 나뉘었다.
- Langflow의 component 연결 방식 덕분에 입력과 출력 단계를 시각적으로 확인하기 쉬웠다.
- `source_type` 기준으로 각 node가 자기 요청만 실행하게 하니 전체 wiring이 단순해졌다.
- dummy row를 유지해 실제 외부 시스템 호출 없이도 배선과 payload 구조를 검증할 수 있었다.
- 최종 결과를 `data_json`으로 정리하니 HTML Report Flow 같은 다른 Flow와 연결하기 쉬웠다.

### 발표자 노트

쉽게 풀린 부분은 "업무에서 이미 자주 쓰는 조회 패턴이 있었다"는 점이다. 완전히 새로운 데이터 시스템을 만든 것이 아니라, 기존에 있던 조회 방식을 재사용 가능한 형태로 감싼 것이기 때문에 빠르게 Flow로 옮길 수 있었다.

---

## 8. 앞으로의 보완과 확장 방향

### 슬라이드 문구

**이 Flow는 시작점이고, 목표는 누구나 자기 업무 Flow를 만들 수 있는 재사용 패턴을 늘리는 것이다.**

**보완할 점**

- 실제 운영 source 연결 시 credential 관리와 권한 체계를 더 명확히 한다.
- `source_catalog` 작성 UX를 개선해 비개발자도 source를 쉽게 등록하게 한다.
- 실행 전 parameter 누락, format 오류, source 선택 오류를 더 친절하게 피드백한다.
- payload observability를 강화해 어느 단계에서 어떤 값이 바뀌었는지 쉽게 추적한다.
- source catalog versioning과 공유/검증 프로세스를 만든다.

**확장 방향**

- 업무를 서술하면 Agent를 설계해주는 Flow
- 데이터를 넘기고 보고서 양식을 지정하면 HTML을 생성하는 Flow
- 내용을 입력하면 카드 뉴스를 만들어주는 Flow
- 데이터 조회 Flow와 다른 Flow들을 연결해 "조회 -> 분석 -> 보고서/콘텐츠 생성"까지 이어지는 reusable Agent kit 구성

### 발표자 노트

마무리는 "유연 데이터 조회 Flow 하나를 소개하는 것"에서 끝내지 않고, 앞으로 공유 가능한 Flow가 늘어날수록 누구든 자기 업무에 맞는 Agent를 만들 수 있다는 방향으로 가져가면 좋다. 데이터 조회는 그 생태계의 첫 번째 블록이다.

---

## 발표 시간 배분 제안

| 장표 | 내용 | 시간 |
| --- | --- | --- |
| 1 | 배경과 문제의식 | 1.5분 |
| 2 | 문제 정의 | 2분 |
| 3 | 사용자와 시나리오 | 1.5분 |
| 4 | 전체 구조 | 2분 |
| 5 | payload 기술 설명 | 3분 |
| 6 | 어려웠던 점 | 1.5분 |
| 7 | 쉽게 풀린 점 | 1분 |
| 8 | 개선/확장 방향 | 1.5분 |

총 14분 내외
