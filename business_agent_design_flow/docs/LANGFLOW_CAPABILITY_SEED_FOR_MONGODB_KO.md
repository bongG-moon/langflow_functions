# MongoDB 카탈로그 등록용 Langflow 기능/개선 예시 Seed 문서

이 문서는 `기능/개선 사례 카탈로그 등록 Flow`에 넣기 위한 원문 seed입니다.
운영자는 이 문서 전체 또는 필요한 항목만 복사해 카탈로그 원문 입력에 넣을 수 있습니다.
등록 Flow는 아래 자연어 항목을 LLM으로 구조화해 MongoDB의 `agent_capability_catalog`와 `agent_improvement_cases`에 저장합니다.

권장 저장 필드:

```json
{
  "item_type": "capability | case | pattern",
  "title_ko": "항목명",
  "summary_ko": "짧은 설명",
  "categories": ["분류"],
  "trigger_signals": ["사용자 업무 설명에서 이 단어가 나오면 추천"],
  "recommended_when": ["추천 상황"],
  "not_recommended_when": ["비추천 상황"],
  "inputs": ["필요 입력"],
  "outputs": ["기대 출력"],
  "langflow_building_blocks": ["관련 Langflow 구성 요소"],
  "risk_level": "low | medium | high",
  "human_review_required": true,
  "source_links": ["참고 링크"]
}
```

---

## 1. Chat Input / Chat Output

유형: capability

설명: 사용자가 입력한 채팅 메시지를 Flow로 넣고, Flow의 최종 응답을 사용자에게 보여주는 기본 입출력 구성입니다.

추천 상황:

- 사용자가 자연어 질문이나 업무 설명을 넣는 Flow
- Playground에서 빠르게 테스트해야 하는 Flow
- API 호출 전 기본 동작을 확인해야 하는 Flow

비추천 상황:

- 여러 개의 독립 입력 필드를 강제로 나눠야 하는 운영자용 관리 화면
- 대용량 파일을 직접 업로드해 처리해야 하는 경우

대표 트리거:

- "사용자가 질문을 입력"
- "업무 설명을 자연어로 입력"
- "최종 답변을 채팅으로 출력"

입력: 사용자 메시지, 파일 첨부

출력: Message

관련 구성요소: Chat Input, Chat Output

위험도: low

사람 검토 필요: false

출처: https://docs.langflow.org/chat-input-and-output

---

## 2. Prompt Template

유형: capability

설명: LLM에게 전달할 지시문을 표준화하고, `{context}`, `{user_question}` 같은 변수를 연결해 재사용 가능한 프롬프트 구조를 만듭니다.

추천 상황:

- 사용자 질문, 업무 설명, 카탈로그 검색 결과를 하나의 LLM 입력으로 합칠 때
- 출력 형식이나 역할 지시를 일관되게 유지해야 할 때
- 초보 개발자가 프롬프트 구조를 눈으로 확인해야 할 때

비추천 상황:

- 프롬프트가 코드에서 동적으로 매우 복잡하게 생성되어야 하는 경우
- 조건 분기가 많아 별도 커스텀 컴포넌트가 더 명확한 경우

대표 트리거:

- "프롬프트 템플릿"
- "LLM에게 지시"
- "출력 형식을 고정"
- "컨텍스트와 질문을 합쳐서 전달"

입력: 사용자 질문, 컨텍스트, 지시사항

출력: Prompt 또는 Message

관련 구성요소: Prompt Template, Language Model

위험도: low

사람 검토 필요: false

출처: https://docs.langflow.org/components-prompts

---

## 3. Structured Output

유형: capability

설명: 자연어, 문서, 반정형 텍스트에서 필요한 필드만 추출해 JSON 또는 Table 구조로 변환합니다.

추천 상황:

- 업무 설명을 목적, 단계, 데이터, 제약, 결과물로 나눌 때
- 기능/개선 사례 원문을 MongoDB 저장용 JSON으로 변환할 때
- LLM 결과를 후속 컴포넌트가 처리 가능한 구조로 만들 때

비추천 상황:

- 단순 요약만 필요한 경우
- 구조화 필드가 거의 없고 자유로운 답변이 중요한 경우

대표 트리거:

- "자연어를 JSON으로 변환"
- "필드를 추출"
- "스키마에 맞게 정리"
- "표 형태로 뽑아줘"

입력: 원문 메시지, 포맷 지시, 출력 스키마, Language Model

출력: JSON 또는 Table

관련 구성요소: Structured Output, Language Model, Parser

위험도: medium

사람 검토 필요: false

출처: https://docs.langflow.org/structured-output

---

## 4. Language Model

유형: capability

설명: LLM을 호출해 텍스트 생성, 요약, 분류, 설계, 변환 작업을 수행합니다.

추천 상황:

- 업무 설명을 해석해야 할 때
- 여러 개선 후보를 비교하고 추천해야 할 때
- 문장형 설계서나 요약을 만들어야 할 때

비추천 상황:

- 정확한 수치 계산만 필요한 경우
- 규칙 기반 처리로 충분한 경우
- 비밀 정보가 포함되어 외부 모델 호출이 제한되는 경우

대표 트리거:

- "LLM이 판단"
- "요약"
- "추천"
- "자연어 생성"
- "업무 설명 이해"

입력: Message, Prompt, 파일, 지시사항

출력: Message 또는 LanguageModel

관련 구성요소: Language Model, Prompt Template, Structured Output

위험도: medium

사람 검토 필요: false

출처: https://docs.langflow.org/components-models

---

## 5. Agent + Tools

유형: capability

설명: Agent가 LLM과 연결된 도구를 사용해 조회, 계산, 검색, 요약 같은 작업을 선택적으로 수행합니다.

추천 상황:

- 사용자 요청에 따라 어떤 도구를 쓸지 달라지는 업무
- API 조회, 문서 검색, 계산, 리포트 작성이 함께 필요한 업무
- 여러 시스템을 순차적으로 확인해야 하는 업무

비추천 상황:

- 고정된 단일 절차로 항상 같은 작업만 수행하는 경우
- 승인 없이 시스템 변경이나 발송을 수행해야 하는 위험 업무

대표 트리거:

- "여러 도구를 상황에 따라 사용"
- "AI Agent"
- "API 조회 후 판단"
- "문서 검색과 데이터 조회를 같이"

입력: 사용자 요청, 도구 목록, 모델

출력: Agent 응답, tool call 결과

관련 구성요소: Agent, Tool Mode, MCP Tools, Run Flow

위험도: high

사람 검토 필요: true

출처: https://docs.langflow.org/components-agents

---

## 6. Custom Component

유형: capability

설명: Python으로 직접 Langflow 컴포넌트를 만들어 정규화, 검증, API 연동, HTML 렌더링 같은 전용 로직을 구현합니다.

추천 상황:

- 여러 Flow에서 반복되는 규칙을 안정적으로 재사용해야 할 때
- LLM 응답을 검증하거나 fallback을 넣어야 할 때
- MongoDB 저장/조회, HTML 생성, 사내 API 호출 같은 특수 로직이 필요할 때

비추천 상황:

- 기본 컴포넌트 조합만으로 충분한 간단한 Flow
- 사용자가 직접 코드를 관리하기 어려운 일회성 실험

대표 트리거:

- "커스텀 컴포넌트"
- "파이썬으로 처리"
- "검증 로직"
- "MongoDB 저장"
- "HTML 렌더링"

입력: 필요에 따라 Message, Data, Table, Text

출력: Data, Message, Tool

관련 구성요소: Component, DataInput, MessageTextInput, Output

위험도: medium

사람 검토 필요: false

출처: https://docs.langflow.org/components-custom-components

---

## 7. Tool Mode / Run Flow as Tool

유형: capability

설명: 컴포넌트나 다른 Flow를 Agent가 호출할 수 있는 도구로 노출합니다.

추천 상황:

- 기존 Flow를 새로운 Agent Flow에서 재사용하고 싶을 때
- 데이터 조회 Flow, HTML 리포트 Flow를 Agent가 필요할 때 호출하게 하고 싶을 때
- 특정 컴포넌트를 도구처럼 호출해야 할 때

비추천 상황:

- 도구 설명이 불명확해 Agent가 잘못 호출할 위험이 큰 경우
- 쓰기/삭제/발송 같은 위험 작업을 승인 없이 도구화하는 경우

대표 트리거:

- "기존 Flow 재사용"
- "Run Flow"
- "도구로 연결"
- "Agent Tools 포트"

입력: Agent 요청, 도구 입력값

출력: 도구 실행 결과

관련 구성요소: Agent, Run Flow, Tool Mode

위험도: high

사람 검토 필요: true

출처: https://docs.langflow.org/agents-tools

---

## 8. MCP Tools

유형: capability

설명: MCP 서버를 통해 외부 도구나 사내 시스템 기능을 Agent가 사용할 수 있게 연결합니다.

추천 상황:

- 사내 시스템 조회, 티켓 조회, 문서 검색 같은 외부 도구를 표준 방식으로 연결할 때
- 여러 도구를 Agent에게 제공해야 할 때
- 기존 MCP 서버가 이미 있는 경우

비추천 상황:

- 단순한 HTTP API 하나만 호출하면 되는 경우
- 인증/권한/감사 로그가 준비되지 않은 쓰기 작업

대표 트리거:

- "MCP"
- "외부 도구"
- "사내 시스템 도구"
- "Agent가 시스템 조회"

입력: MCP 서버 연결 정보, 도구 요청

출력: 도구 실행 결과

관련 구성요소: Agent, MCP Tools

위험도: high

사람 검토 필요: true

출처: https://docs.langflow.org/mcp-tools

---

## 9. API Request

유형: capability

설명: URL 또는 curl 기반으로 HTTP 요청을 보내고 JSON 응답을 받습니다.

추천 상황:

- 사내 REST API를 조회해야 할 때
- 외부 서비스에서 상태, 이력, 메타데이터를 가져와야 할 때
- 간단한 API 호출을 Flow 안에서 테스트할 때

비추천 상황:

- 복잡한 인증, 재시도, 페이징, 감사 로그가 필요한 운영 API
- 시스템 변경 또는 삭제 API를 사람 승인 없이 호출하는 경우

대표 트리거:

- "API 조회"
- "HTTP 호출"
- "curl"
- "URL로 데이터 가져오기"

입력: URL, method, headers, query params, body

출력: JSON

관련 구성요소: API Request, Custom Component

위험도: medium

사람 검토 필요: 쓰기 작업이면 true

출처: https://docs.langflow.org/api-request

---

## 10. URL

유형: capability

설명: 하나 이상의 URL에서 내용을 가져와 plain text, Markdown, raw HTML 등으로 반환합니다.

추천 상황:

- 웹 문서나 가이드 페이지를 읽어 요약해야 할 때
- 공개 문서 기반 RAG를 만들 때
- 링크 목록을 재귀적으로 수집해야 할 때

비추천 상황:

- 로그인/권한이 필요한 사내 페이지
- 크롤링 정책을 확인하지 않은 외부 사이트

대표 트리거:

- "웹페이지 읽기"
- "URL 내용 가져오기"
- "문서 링크 요약"

입력: URL 목록

출력: 텍스트, Markdown, HTML

관련 구성요소: URL, Split Text, Vector Store, RAG

위험도: medium

사람 검토 필요: false

출처: https://docs.langflow.org/url

---

## 11. Split Text

유형: capability

설명: 긴 Message, JSON, Table 데이터를 chunk로 나누어 embedding 또는 검색에 적합하게 만듭니다.

추천 상황:

- 문서나 기능 카탈로그가 길어 embedding 저장이 필요한 경우
- RAG 검색용 지식 베이스를 만들 때
- 긴 개선 사례 문서를 여러 조각으로 저장해야 할 때

비추천 상황:

- 짧은 단일 문장이나 이미 구조화된 작은 JSON

대표 트리거:

- "문서를 쪼개서 저장"
- "chunk"
- "embedding"
- "RAG"

입력: Message, JSON, Table

출력: Chunks 또는 DataFrame

관련 구성요소: Split Text, Embedding Model, Vector Store

위험도: low

사람 검토 필요: false

출처: https://docs.langflow.org/split-text

---

## 12. MongoDB Atlas Vector Store

유형: capability

설명: MongoDB Atlas Vector Search를 통해 문서나 카탈로그를 저장하고 의미 기반 검색 결과를 downstream 컴포넌트에 전달합니다.

추천 상황:

- 기능 목록과 개선 사례를 MongoDB에 저장하고 업무 설명과 의미적으로 가까운 항목을 찾을 때
- 카탈로그 항목이 많아 단순 키워드 검색만으로 부족한 경우
- 기존 MongoDB Atlas 인프라가 있는 경우

비추천 상황:

- 로컬 MongoDB만 사용하고 Atlas Vector Search를 쓸 수 없는 환경
- 항목 수가 적어 단순 text index로 충분한 경우

대표 트리거:

- "MongoDB에 저장된 기능 목록 검색"
- "비슷한 개선 사례 찾기"
- "semantic search"
- "vector search"

입력: query text, embedding, collection, index

출력: JSON 또는 Table 검색 결과

관련 구성요소: MongoDB Atlas, Embedding Model, Vector Store

위험도: medium

사람 검토 필요: false

출처: https://docs.langflow.org/bundles-mongodb

---

## 13. Message History / Memory

유형: capability

설명: 대화 기록을 저장하거나 검색해 이전 맥락을 Flow에 전달합니다.

추천 상황:

- 사용자가 여러 번에 걸쳐 업무 설계를 보완하는 경우
- 이전 설계 결과를 참고해 다음 답변을 만들어야 하는 경우
- Flow 실행 이력을 세션별로 확인해야 하는 경우

비추천 상황:

- 매 실행이 독립적이어야 하는 업무
- 개인정보나 기밀 업무 설명을 저장하면 안 되는 환경

대표 트리거:

- "이전 대화 참고"
- "세션별 기록"
- "설계 이력"
- "후속 질문"

입력: Message, session_id

출력: Memory 또는 Message

관련 구성요소: Message History, Agent memory

위험도: medium

사람 검토 필요: 저장 정책에 따라 true

출처: https://docs.langflow.org/message-history

---

## 14. Flow API 실행

유형: capability

설명: 완성된 Langflow Flow를 외부 Python 코드, 웹앱, 서버, 스케줄러에서 `/api/v1/run/{flow_id}`로 호출합니다.

추천 상황:

- 사내 웹 화면에서 Flow를 실행해야 할 때
- 배치/스케줄러에서 정기적으로 Flow를 돌려야 할 때
- 다른 시스템이 Langflow 결과를 받아 사용해야 할 때

비추천 상황:

- 아직 Playground에서 기본 검증이 끝나지 않은 Flow
- 인증/권한 체계가 정리되지 않은 서비스 배포

대표 트리거:

- "API로 호출"
- "웹앱에서 실행"
- "서버에서 Flow 실행"
- "스케줄러"

입력: input_value, session_id, tweaks, API key

출력: Flow 실행 응답 JSON

관련 구성요소: Flow Run API, API Access

위험도: medium

사람 검토 필요: 운영 배포 전 true

출처: https://docs.langflow.org/api-flows-run

---

## 15. 현재 기능flow - 재사용 데이터 조회 Flow

유형: capability

설명: 사용자의 질의를 기반으로 데이터를 조회하고, 이후 HTML 생성 Flow나 분석 Flow가 사용할 수 있는 datasets 형태로 전달하는 기존 기능flow입니다.

추천 상황:

- 업무 설명에 DB, API, 파일, 조회 조건이 등장하는 경우
- 리포트 생성 전 데이터셋을 먼저 확보해야 하는 경우
- 단일 데이터 또는 여러 데이터를 하나의 결과로 묶어야 하는 경우

비추천 상황:

- 데이터 조회가 필요 없는 문서 작성/분류 업무
- 조회 조건과 데이터 소스가 전혀 정의되지 않은 경우

대표 트리거:

- "데이터 조회"
- "DB에서 가져오기"
- "API에서 가져오기"
- "여러 데이터 기반"
- "datasets"

입력: 사용자 질의, 데이터 소스 설명, 조회 조건

출력: datasets 배열, 데이터 설명

관련 구성요소: reusable_data_flow, adapter, data_json

위험도: medium

사람 검토 필요: 데이터 권한에 따라 true

출처: 로컬 기능flow `reusable_data_flow`

---

## 16. 현재 기능flow - HTML 리포트 생성 Flow

유형: capability

설명: 데이터 조회 결과와 사용자가 보고 싶은 방식을 기반으로 KPI 카드, 그래프, 표, 설명을 조합해 HTML 리포트를 생성하는 기존 기능flow입니다.

추천 상황:

- 분석 결과나 조회 결과를 사람이 보기 좋은 페이지로 보여줘야 할 때
- 그래프, 표, KPI, 요약이 필요한 보고 업무
- 다운로드 가능한 HTML 결과물이 필요한 경우

비추천 상황:

- 시스템 제어, 등록, 승인 처리 자체가 핵심인 업무
- 데이터가 없고 순수 대화형 답변만 필요한 경우

대표 트리거:

- "HTML 리포트"
- "대시보드"
- "KPI"
- "그래프"
- "표"
- "다운로드 링크"

입력: question, view_request, datasets

출력: HTML, 요약 메시지, 다운로드 링크

관련 구성요소: html_report_flow, HTML renderer, report API

위험도: low

사람 검토 필요: 외부 공유 전 true

출처: 로컬 기능flow `html_report_flow`

---

## 17. 개선 사례: 조회-분석-리포트 자동화

유형: case

설명: 사람이 반복적으로 데이터를 조회하고 엑셀로 비교한 뒤 보고서를 만드는 업무를 자동 조회, 이상 후보 선별, HTML 리포트 생성으로 개선합니다.

Before:

- 사용자가 여러 파일 또는 시스템에서 데이터를 내려받음
- 엑셀에서 수작업 필터와 비교 수행
- 결과를 메일이나 회의자료로 정리

After:

- 데이터 조회 Flow가 필요한 데이터를 모음
- AI 또는 규칙 기반 로직이 이상 후보를 선별
- HTML 리포트 생성 Flow가 회의용 결과물을 만듦
- 사람은 결과를 확인하고 공유 여부를 결정

추천 기능:

- reusable_data_flow
- html_report_flow
- prompt_template
- human_review_gate

대표 트리거:

- "매일 조회"
- "엑셀로 비교"
- "회의 전 리포트"
- "이상 징후"
- "대시보드"

위험도: medium

사람 검토 필요: true

---

## 18. 개선 사례: 분류-추천-사람 검토

유형: case

설명: 메일, 티켓, 알림, 요청사항을 자동 분류하고 우선순위와 다음 조치를 추천하되, 실제 발송/등록/처리는 사람이 승인합니다.

Before:

- 담당자가 모든 요청을 읽고 분류
- 우선순위와 담당자를 수동 판단
- 답변 또는 후속 조치도 직접 작성

After:

- LLM이 요청 유형과 긴급도를 분류
- Agent가 필요한 추가 정보를 조회
- 답변 초안과 후속 조치안을 생성
- 사람 검토 후 발송 또는 등록

추천 기능:

- structured_output
- agent_with_tools
- api_request
- human_review_gate

대표 트리거:

- "메일 분류"
- "티켓 분류"
- "우선순위 추천"
- "답변 초안"
- "승인 후 처리"

위험도: high

사람 검토 필요: true

---

## 19. 개선 사례: 도구 호출 AI Agent + 감사 로그

유형: case

설명: 여러 사내 시스템을 조회해야 하는 업무에서 Agent가 필요한 도구를 선택해 실행하고, 모든 조회/판단 근거를 로그로 남깁니다.

Before:

- 사용자가 시스템 여러 개를 순서대로 열어 조회
- 필요한 조건을 사람이 기억해서 입력
- 판단 근거가 문서화되지 않음

After:

- Agent가 사용자 요청을 해석
- 필요한 도구를 선택해 조회
- 결과를 요약하고 판단 근거를 남김
- 위험 작업은 사람 승인 뒤 진행

추천 기능:

- agent_with_tools
- mcp_tools
- api_request
- message_history
- human_review_gate

대표 트리거:

- "여러 시스템 조회"
- "API 여러 개"
- "판단 근거"
- "로그"
- "승인"

위험도: high

사람 검토 필요: true

---

## 20. 개선 패턴: Human Review Gate

유형: pattern

설명: 메일 발송, 고객 공유, 시스템 등록, 삭제, 결재 요청처럼 위험하거나 책임 소재가 있는 작업은 AI가 초안/추천까지만 만들고 사람이 승인해야 다음 단계로 넘어가는 패턴입니다.

추천 상황:

- 자동 발송 또는 자동 등록이 위험한 경우
- 고객, 협력사, 외부 시스템에 영향이 있는 경우
- 사내 승인 프로세스가 있는 경우

비추천 상황:

- 단순 읽기 전용 조회
- 개인용 임시 요약

대표 트리거:

- "승인 후"
- "검토 후"
- "자동 발송 금지"
- "등록은 사람이"
- "팀장 승인"

입력: AI 초안, 검토자, 승인 조건

출력: 승인 대기 상태, 승인 후 실행 요청

관련 구성요소: custom_component, Agent, API Request, Flow API

위험도: high

사람 검토 필요: true

출처: 내부 안전 설계 패턴
