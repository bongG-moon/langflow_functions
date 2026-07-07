# 카드뉴스 Flow Prompt Index

이 폴더는 Langflow `Prompt Template` 컴포넌트에 붙여넣을 프롬프트와, 각 Prompt Template에 연결되는 작성 지침/출력 스키마를 분리해서 보관합니다.

## 브리프 생성 단계

| 파일 | 용도 |
| --- | --- |
| `01_CARD_NEWS_BRIEF_PROMPT_TEMPLATE.md` | 사용자 원문과 요청 설정을 브리프 JSON으로 바꾸는 Prompt Template |
| `02_CARD_NEWS_BRIEF_INSTRUCTIONS.md` | `01 카드뉴스 브리프 프롬프트 변수 준비`가 제공하는 브리프 작성 지침 |
| `03_CARD_NEWS_BRIEF_OUTPUT_SCHEMA.md` | 브리프 LLM 응답 JSON 스키마 |

## 카드뉴스 계획 생성 단계

| 파일 | 용도 |
| --- | --- |
| `04_CARD_NEWS_PLAN_PROMPT_TEMPLATE.md` | 브리프와 캐릭터 자산을 카드뉴스 계획 JSON으로 바꾸는 Prompt Template |
| `05_CARD_NEWS_PLAN_INSTRUCTIONS.md` | `04 카드뉴스 생성 프롬프트 변수 준비`가 제공하는 카드뉴스 작성 지침 |
| `06_CARD_NEWS_PLAN_OUTPUT_SCHEMA.md` | 카드뉴스 계획 LLM 응답 JSON 스키마 |

## 운영 메모

- LLM은 HTML/CSS를 직접 만들지 않고 JSON만 반환합니다.
- 같은 화면 수에서는 고정 템플릿 구조를 유지하고 내용만 변경합니다.
- 하냥이/하댕이 캐릭터는 새로 생성하지 않고 등록된 `asset_id` 중 하나만 선택합니다.
- `page_image_overrides`가 지정된 페이지는 이미지 전용 화면이므로 문구/캐릭터/버튼을 만들지 않습니다.
