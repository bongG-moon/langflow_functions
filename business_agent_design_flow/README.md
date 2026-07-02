# 업무 AI 에이전트 설계 Flow

사람이 본인의 업무를 자연어로 풀어 쓰면, 업무 프로세스 로직을 보기 좋게 정리하고 이 업무를 AI 에이전트로 만들 때 어떤 부분을 개선할 수 있는지 제안하는 Langflow 컴포넌트 세트입니다.

대상 사용자는 초보 Langflow 개발자입니다. 그래서 사용자가 직접 넣는 입력은 `00 업무 설명 입력`의 **업무 설명 한 칸**으로 줄였습니다.

## 할 수 있는 일

- 자연어 업무 설명을 단계, 입력, 출력, 판단 기준, 사람 검토 구간으로 정리
- 반복 업무, 데이터 조회, 조건 판단, 보고/공유 같은 AI 에이전트화 후보 식별
- 기존 기능flow인 `reusable_data_flow`, `html_report_flow`를 어디에 붙이면 좋은지 추천
- 업무 설명 안에 적힌 사내 API, 기존 flow, 추가 기능 후보를 자동으로 카탈로그에 반영
- Langflow에서 어떤 노드를 어떤 순서로 만들면 되는지 초보자용 구현 순서 출력
- 사용자가 입력한 업무 흐름을 Mermaid 업무 Flow 다이어그램으로 출력
- LLM 없이도 기본 설계 결과를 볼 수 있고, LLM을 연결하면 더 풍부한 설계 결과 생성

## 기본 사용 방식

사용자는 `00 업무 설명 입력`의 `업무 설명`에 아래처럼 업무를 자연스럽게 풀어 쓰면 됩니다. 항목명을 나눠 적지 않아도 됩니다.

```text
매일 아침 설비별 생산량과 불량률을 엑셀로 내려받아 전일 대비 급증한 설비를 확인합니다.
이상 설비가 있으면 생산량, 불량률, 최근 작업 이력을 같이 보고 원인 후보를 정리합니다.
정리한 내용은 담당자에게 메일 초안으로 공유하고, 긴급 건은 팀장 승인 후 후속 조치를 사내 시스템에 등록합니다.

생산/품질 담당자가 아침 회의 전에 위험 설비를 빠르게 파악하고 후속 조치 우선순위를 정하는 것이 목적입니다.
사용하는 정보는 Excel 생산 실적 파일, 품질 불량률 파일, 사내 설비 이력 시스템, 메일입니다.
메일은 자동 발송하지 말고 초안까지만 만들고, 사내 시스템 등록은 팀장 승인 이후에만 진행해야 합니다.
결과는 위험 설비 요약, 원인 후보, 담당자 공유 메일 초안, 초보자용 Langflow 구현 순서로 보고 싶습니다.
우리 팀에는 설비 이력 조회 API가 있어서 설비 ID와 기준 일자를 넣으면 최근 작업 이력과 정비 이력을 조회할 수 있습니다.
```

## 기본 노드 흐름

```text
00 업무 설명 입력
  -> 01 업무 프로세스 구조화
  -> 02 AI 에이전트 기능 카탈로그
  -> 03 AI 에이전트 설계 프롬프트 준비
  -> LLM
  -> 04 AI 에이전트 설계 결과 정리
  -> 05 사용자용 설계서 출력
  -> Chat Output

04 AI 에이전트 설계 결과 정리
  -> 06 업무 Flow 다이어그램 출력
  -> Chat Output
```

LLM 없이 빠르게 확인할 때는 아래처럼 연결합니다.

```text
00 -> 01 -> 02 -> 04 -> 05 -> Chat Output
```

이 경우 `04 AI 에이전트 설계 결과 정리`의 `LLM 설계 응답`은 비워둡니다.

## 폴더 구성

```text
business_agent_design_flow/
├─ README.md
├─ CONNECTION_GUIDE.md
├─ docs/
│  ├─ AGENT_CAPABILITY_CATALOG.md
│  ├─ FEATURE_CATALOG_PROMPT_TEMPLATE.md
│  ├─ OUTPUT_SCHEMA.md
│  └─ PROMPT_TEMPLATE.md
├─ legacy_components/
│  ├─ 02_1_feature_catalog_json_prompt_builder.py
│  └─ 02_2_feature_catalog_json_normalizer.py
├─ samples/
│  └─ ONE_FILE_TEST_CASES.md
└─ langflow_components/
   └─ business_agent_design_flow/
      ├─ 00_business_work_input_loader.py
      ├─ 01_work_process_structurer.py
      ├─ 02_agent_capability_catalog.py
      ├─ 03_agent_design_prompt_builder.py
      ├─ 04_agent_design_normalizer.py
      ├─ 05_user_friendly_markdown_output.py
      └─ 06_business_flow_diagram_output.py
```

`legacy_components`는 이전 방식의 추가 기능 JSON 변환 노드입니다. 현재 기본 사용 방식에서는 필요하지 않습니다.

## 핵심 설계 원칙

- 사용자의 업무 설명은 가능한 자연어 그대로 받습니다.
- 추가 기능, 제약사항, 원하는 출력 형태도 별도 입력칸이 아니라 업무 설명 안에 함께 적습니다.
- 기존 flow/component 코드를 LLM에 통째로 넣지 않고, 사용할 수 있는 기능을 짧은 카탈로그로 제공합니다.
- 실제 실행 자동화보다 업무 이해, AI 에이전트화 후보, Langflow 구현 순서 제안에 집중합니다.
- 고객 발송, 승인, 시스템 업데이트, 민감 데이터 처리는 사람 검토 단계를 남기도록 권장합니다.
- 최종 출력은 JSON만이 아니라 사람이 바로 읽을 수 있는 Markdown 설계서로 반환합니다.

## 참고 공식 문서

- **프롬프트 템플릿 컴포넌트**: 프롬프트 본문에 변수를 연결해 LLM 입력을 표준화할 때 참고합니다.  
  출처: https://docs.langflow.org/components-prompts
- **커스텀 컴포넌트**: Python으로 Langflow 전용 입력/출력 노드를 만들 때 참고합니다.  
  출처: https://docs.langflow.org/components-custom-components
- **컴포넌트 개념**: Langflow 컴포넌트가 입력, 출력, 파라미터를 어떻게 다루는지 확인할 때 참고합니다.  
  출처: https://docs.langflow.org/concepts-components
- **Flow 개념**: 여러 컴포넌트를 연결해 하나의 업무 흐름으로 만드는 방식을 이해할 때 참고합니다.  
  출처: https://docs.langflow.org/concepts-flows
- **AI 에이전트**: LLM이 도구를 선택해 업무를 수행하는 구조를 설계할 때 참고합니다.  
  출처: https://docs.langflow.org/agents
- **AI 에이전트 도구**: AI 에이전트가 사용할 도구를 구성하는 방식을 확인할 때 참고합니다.  
  출처: https://docs.langflow.org/agents-tools
- **MCP 도구**: 외부 시스템 도구를 Langflow에서 사용할 수 있게 연결하는 방식을 검토할 때 참고합니다.  
  출처: https://docs.langflow.org/mcp-tools
- **Flow 실행 API**: 완성된 flow를 웹앱, 서버, 스케줄러에서 호출할 때 참고합니다.  
  출처: https://docs.langflow.org/api-flows-run
