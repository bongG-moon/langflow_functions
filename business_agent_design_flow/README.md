# 업무 AI Agent 설계 Flow

업무 설명 한 칸만 입력하면 현재 업무 Flow와 AI Agent 적용 후 개선 Flow를 설계하고, 보안 검사된 HTML 결과로 보여주는 Langflow 커스텀 컴포넌트 세트입니다.

이번 버전은 기존 체험형 비즈니스 디자인 Flow를 제거하고 `SERVICE_REDESIGN_SPEC.md` 기준으로 새로 구현한 서비스형 초안입니다.

## 핵심 원칙

- 사용자가 직접 넣는 값은 `00 업무 설명 입력`의 **업무 설명** 한 칸입니다.
- 기능 목록과 기존 개선 사례는 MongoDB에서 검색합니다.
- MongoDB 연결이 없으면 내장 seed 카탈로그로 fallback되어 체험이 가능합니다.
- 추천 결과에는 `recommendation_trace`가 포함되어 어떤 카탈로그 항목이 왜 선택됐는지 추적할 수 있습니다.
- HTML 결과에는 현재 업무 단계별 개선 명세가 포함되며, 적용 기능, 구현 방법, 검증 기준, 참고 링크를 함께 보여줍니다.
- HTML은 LLM이 직접 만든 코드를 사용하지 않고, 검증된 JSON을 deterministic secure renderer가 렌더링합니다.
- `html_report_flow/report_api/server.py`를 함께 실행하면 HTML 결과를 저장하고 다운로드 링크를 바로 받을 수 있습니다.
- 카탈로그 등록은 별도 운영자용 Flow인 `2.1-2.5` 노드로 처리합니다.
- 각 Langflow 컴포넌트 py 파일은 로컬 공통 모듈 import 없이 단독으로 복사/등록 가능한 standalone 구조이며, 해당 노드에 필요한 최소 helper만 포함합니다.
- 웹에서 확인한 Langflow 기본 기능은 카탈로그 항목과 추천 HTML 카드에 참고 링크가 함께 표시됩니다.

## 폴더 구성

```text
business_agent_design_flow/
├─ README.md
├─ CONNECTION_GUIDE.md
├─ docs/
│  ├─ SERVICE_REDESIGN_SPEC.md
│  ├─ LANGFLOW_CAPABILITY_SEED_FOR_MONGODB_KO.md
│  └─ prompts/
├─ samples/
│  └─ ONE_FILE_TEST_CASES.md
└─ langflow_components/
   └─ business_agent_design_flow/
      ├─ __init__.py
      ├─ 00_business_work_input_loader.py
      ├─ 01_business_profile_prompt_builder.py
      ├─ 02_business_profile_normalizer.py
      ├─ 03_mongodb_catalog_retriever.py
      ├─ 04_agent_design_prompt_builder.py
      ├─ 05_agent_design_normalizer.py
      ├─ 06_secure_html_renderer.py
      ├─ 07_user_summary_output.py
      ├─ 08_html_source_output.py
      ├─ 09_report_api_publisher.py
      └─ catalog_json_flow/
```

## 메인 Flow

```text
00 업무 설명 입력
  -> 01 업무 구조화 프롬프트 변수 준비
  -> Langflow Prompt Template
  -> Langflow Agent
  -> 02 업무 구조화 결과 정리
  -> 03 MongoDB 기능/사례 검색
  -> 04 AI Agent 설계 프롬프트 변수 준비
  -> Langflow Prompt Template
  -> Langflow Agent
  -> 05 AI Agent 설계 결과 검증
  -> 06 HTML 업무 Flow 렌더링
  -> 07 사용자 요약 출력
  -> Chat Output

06 HTML 업무 Flow 렌더링
  -> 08 HTML 원문 출력
  -> Chat Output

06 HTML 업무 Flow 렌더링
  -> 09 공유 링크 발행
  -> Chat Output
```

LLM 없이 빠르게 확인할 때는 아래처럼 연결합니다.

```text
00 -> 02 -> 03 -> 05 -> 06 -> 07, 08 또는 09 -> Chat Output
```

## 카탈로그 등록 Flow

운영자가 사용할 수 있는 기능 목록이나 기존 개선 사례를 자연어로 넣으면, Langflow Agent 또는 LLM이 MongoDB 저장용 JSON으로 변환하고 검증 후 저장합니다.

```text
2.1 카탈로그 원문 입력
  -> 2.2 카탈로그 JSON 프롬프트 변수 준비
  -> Langflow Prompt Template
  -> Langflow Agent
  -> 2.3 카탈로그 JSON 검증
  -> 2.4 MongoDB 카탈로그 저장
  -> 2.5 카탈로그 저장 결과 출력
  -> Chat Output
```

LLM 없이 seed 문서 형식을 빠르게 테스트할 때는 아래처럼 연결할 수 있습니다.

```text
2.1 -> 2.3 -> 2.4 -> 2.5 -> Chat Output
```

## MongoDB 컬렉션

기본 컬렉션 이름은 아래와 같습니다.

| 컬렉션 | 용도 |
| --- | --- |
| `agent_capability_catalog` | 사용 가능한 기능 목록 |
| `agent_improvement_cases` | 기존 개선 사례와 설계 패턴 |
| `agent_design_runs` | 추후 설계 실행 이력 저장용 |

`03 MongoDB 기능/사례 검색`과 `2.4 MongoDB 카탈로그 저장`의 `Mongo URI`, `DB 이름`, 컬렉션명은 고급 입력값으로 둡니다.
일반 사용자는 이 값을 만지지 않고, 운영자가 Flow 배포 시 설정합니다.

Mongo URI가 비어 있으면:

- `03`은 내장 seed 카탈로그로 fallback합니다.
- `23`은 저장을 건너뛰고 저장 preview를 출력합니다.

## 참고 문서

- [서비스형 재설계 상세 설계서](docs/SERVICE_REDESIGN_SPEC.md)
- [MongoDB 카탈로그 등록용 Langflow 기능 seed](docs/LANGFLOW_CAPABILITY_SEED_FOR_MONGODB_KO.md)
- [Prompt Template 모음](docs/prompts)
- [연결 가이드](CONNECTION_GUIDE.md)
- [샘플 입력](samples/ONE_FILE_TEST_CASES.md)
