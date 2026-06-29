# AI 에이전트 기능 카탈로그

`02 AI 에이전트 기능 카탈로그` 노드는 LLM에게 "지금 사용할 수 있는 기능"을 알려주는 역할을 합니다.

기존 구현된 component와 flow를 통째로 넣지 않는 이유:

- 코드 전체는 너무 길어서 LLM이 핵심 기능을 놓칠 수 있습니다.
- 초보 개발자가 관리하기 어렵습니다.
- 업무 설계 단계에서는 "무엇을 할 수 있는지"가 "구현 코드 전체"보다 중요합니다.
- 실제 구현은 카탈로그가 추천한 기능을 보고 필요한 flow를 연결하는 방식이 더 안정적입니다.

## 기본 포함 기능

| capability_id | 설명 | 초보자 관점 용도 |
| --- | --- | --- |
| `prompt_template_structuring` | 프롬프트 템플릿으로 자연어를 구조화 | 업무 설명을 JSON 설계로 변환 |
| `custom_component` | 파이썬 커스텀 컴포넌트 | 반복되는 정규화/검증/출력 포맷을 안정화 |
| `agent_with_tools` | AI 에이전트가 도구를 선택해 사용 | 조회, 검색, 계산, 요약 등 여러 도구 사용 |
| `mcp_tools` | MCP 서버의 외부 도구 연결 | 사내/외부 시스템 도구 연동 아이디어 |
| `flow_api` | Flow API로 외부 호출 | 웹앱/서버/스케줄러에서 flow 호출 |
| `playground_validation` | 플레이그라운드에서 빠른 검증 | 초보자가 연결 결과를 즉시 확인 |
| `reusable_data_flow` | 기존 기능flow 데이터 조회 | DB/API/파일 조회 결과를 datasets 형태로 전달 |
| `html_report_flow` | 기존 기능flow HTML 리포트 | 데이터를 사람이 보기 좋은 HTML 리포트로 변환 |
| `human_review_gate` | 사람 검토/승인 Gate | 위험 작업은 초안/추천까지만 자동화 |

## 기본 설계 패턴

### 조회-분석-리포트

반복 데이터 조회 후 요약 리포트를 공유하는 업무에 적합합니다.

추천 기능:

- `reusable_data_flow`
- `prompt_template_structuring`
- `html_report_flow`

### 분류-추천-사람 검토

이슈, 요청, 메일, 알림을 분류하고 다음 조치를 추천하는 업무에 적합합니다.

추천 기능:

- `prompt_template_structuring`
- `agent_with_tools`
- `human_review_gate`

### 도구 호출 AI 에이전트 + 로그

여러 시스템 조회 또는 업데이트가 필요한 업무에 적합합니다.

추천 기능:

- `agent_with_tools`
- `mcp_tools`
- `flow_api`
- `human_review_gate`

## 사용자가 추가로 넣을 수 있는 정보

초보자는 자연어로 기능을 설명한 뒤, `02-1 추가 기능 JSON 프롬프트 준비`와 LLM을 통해 JSON으로 변환하는 방식이 가장 편합니다.

### 추천 흐름

```text
02-1 추가 기능 JSON 프롬프트 준비
  -> 프롬프트 템플릿
  -> LLM
  -> 02-2 추가 기능 JSON 정리
  -> 02 AI 에이전트 기능 카탈로그
```

`02-1 추가 기능 JSON 프롬프트 준비`의 `추가 기능 자연어 설명`에는 아래처럼 자연스럽게 적습니다.

```text
우리 팀에는 사내 티켓 조회 API가 있습니다.
티켓 ID를 넣으면 티켓 상태, 담당자, 최근 처리 이력을 조회할 수 있습니다.
처음에는 조회 전용으로만 쓰고, 티켓 수정이나 등록은 사람 승인 뒤에만 하도록 설계해주세요.

결과를 담당자에게 보낼 메일 초안 생성 기능도 있으면 좋겠습니다.
자동 발송은 하지 말고 제목과 본문 초안까지만 만들어야 합니다.
```

프롬프트 템플릿 본문은 아래 파일을 사용합니다.

```text
business_agent_design_flow/docs/FEATURE_CATALOG_PROMPT_TEMPLATE.md
```

`02-2 추가 기능 JSON 정리`는 LLM 응답을 검증해서 `02 AI 에이전트 기능 카탈로그`의 `추가 기능 카탈로그 JSON` 입력에 연결할 수 있는 JSON 문자열로 만듭니다.

JSON에 익숙한 사용자는 `02 AI 에이전트 기능 카탈로그`의 `추가 기능 카탈로그 JSON`에 아래 형태로 직접 붙여넣어도 됩니다.

```json
{
  "capabilities": [
    {
      "capability_id": "internal_ticket_api",
      "display_name": "사내 티켓 API",
      "category": "integration",
      "beginner_use_case": "AI 에이전트가 티켓 상태를 조회하거나 초안을 생성합니다.",
      "when_to_use": "업무가 티켓 시스템 조회/등록을 포함할 때",
      "needed_inputs": ["ticket_id", "user_id"],
      "typical_outputs": ["ticket_status", "draft_update"],
      "difficulty": "중급",
      "implementation_hint": "처음에는 조회 전용으로 연결하고 등록은 사람 승인 뒤 실행합니다."
    }
  ]
}
```

## 공식 문서 참고

| 한글 참조명 | 어떤 때 참고하는지 | 출처 링크 |
| --- | --- | --- |
| 프롬프트 템플릿 컴포넌트 | 프롬프트 본문에 변수를 연결해 LLM 입력을 표준화할 때 | https://docs.langflow.org/components-prompts |
| 커스텀 컴포넌트 | Python으로 Langflow 전용 입력/출력 노드를 만들 때 | https://docs.langflow.org/components-custom-components |
| 컴포넌트 개념 | Langflow 컴포넌트의 입력, 출력, 파라미터 구조를 이해할 때 | https://docs.langflow.org/concepts-components |
| Flow 개념 | 여러 컴포넌트를 연결해 하나의 업무 흐름으로 만드는 방식을 이해할 때 | https://docs.langflow.org/concepts-flows |
| AI 에이전트 | LLM이 도구를 선택해 업무를 수행하는 구조를 설계할 때 | https://docs.langflow.org/agents |
| AI 에이전트 도구 | AI 에이전트가 사용할 도구를 구성하는 방식을 확인할 때 | https://docs.langflow.org/agents-tools |
| MCP 도구 | 외부 시스템 도구를 Langflow에서 사용할 수 있게 연결하는 방식을 검토할 때 | https://docs.langflow.org/mcp-tools |
| Flow 실행 API | 완성된 flow를 웹앱, 서버, 스케줄러에서 호출할 때 | https://docs.langflow.org/api-flows-run |
