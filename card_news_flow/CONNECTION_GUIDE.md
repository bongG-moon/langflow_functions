# 카드뉴스 생성 Flow 연결 가이드

이 문서는 Langflow 캔버스에서 `card_news_flow`를 구성할 때 어떤 노드의 출력과 입력을 연결해야 하는지 설명합니다.

## 1. 컴포넌트 등록 경로

```text
C:\Users\qkekt\Desktop\기능flow\card_news_flow\langflow_components\card_news_flow
```

각 커스텀 컴포넌트는 기존 `business_agent_design_flow`처럼 로컬 공통 모듈 import 없이 단독 복사/등록 가능한 standalone 구조입니다.

구현된 컴포넌트:

```text
00_card_news_request_loader.py
01_card_news_brief_prompt_builder.py
02_card_news_brief_normalizer.py
03_character_asset_loader.py
04_card_news_plan_prompt_builder.py
05_card_news_plan_normalizer.py
06_card_news_html_renderer.py
07_user_summary_output.py
08_html_source_output.py
09_report_api_publisher.py
10_uploaded_character_asset_builder.py
11_page_image_override_builder.py
```

## 2. LLM 포함 권장 연결

Langflow 기본 컴포넌트에서 `Prompt Template`을 2개 추가합니다.

- Prompt 전체 인덱스: [00_PROMPT_INDEX.md](docs/prompts/00_PROMPT_INDEX.md)
- 브리프 생성 Prompt Template: [01_CARD_NEWS_BRIEF_PROMPT_TEMPLATE.md](docs/prompts/01_CARD_NEWS_BRIEF_PROMPT_TEMPLATE.md)
- 카드뉴스 계획 생성 Prompt Template: [04_CARD_NEWS_PLAN_PROMPT_TEMPLATE.md](docs/prompts/04_CARD_NEWS_PLAN_PROMPT_TEMPLATE.md)

작성 지침과 출력 스키마도 각각 별도 `.md` 파일로 분리되어 있습니다.

- 브리프 작성 지침: [02_CARD_NEWS_BRIEF_INSTRUCTIONS.md](docs/prompts/02_CARD_NEWS_BRIEF_INSTRUCTIONS.md)
- 브리프 출력 스키마: [03_CARD_NEWS_BRIEF_OUTPUT_SCHEMA.md](docs/prompts/03_CARD_NEWS_BRIEF_OUTPUT_SCHEMA.md)
- 카드뉴스 계획 작성 지침: [05_CARD_NEWS_PLAN_INSTRUCTIONS.md](docs/prompts/05_CARD_NEWS_PLAN_INSTRUCTIONS.md)
- 카드뉴스 계획 출력 스키마: [06_CARD_NEWS_PLAN_OUTPUT_SCHEMA.md](docs/prompts/06_CARD_NEWS_PLAN_OUTPUT_SCHEMA.md)
- 서버 환경 이미지 업로드 가이드: [ASSET_UPLOAD_GUIDE.md](docs/ASSET_UPLOAD_GUIDE.md)

`00 카드뉴스 요청 입력`에는 아래처럼 넣습니다.

| 입력 | 예시 |
| --- | --- |
| `카드뉴스 내용` | 이번 달 AI 활용 문화 확산 카드뉴스를 만들어주세요. 업무 자동화 사례, 보안 유의사항, 프롬프트 작성 팁, 다음 달 교육 안내를 포함해주세요. |
| `지시사항` | 총 7개 화면으로 구성. 첫 화면에는 제목과 2026년 7월호 발간호 정보를 표시. 카드를 누르면 다음 화면으로 이동. 마지막 화면에는 교육 신청 CTA 포함. |

`지시사항`의 `총 N개 화면/페이지/장` 표현은 `slide_count`로 자동 반영됩니다.
`발간호`, `발행호`, `호수`, `2026년 7월호`, `제12호` 같은 표현은 첫 cover 카드의 발간 정보로 표시됩니다.
같은 화면 수에서는 `cover -> why -> case -> tip -> security -> ... -> cta` 역할 순서와 layout이 고정됩니다. 매월 바뀌는 것은 제목, 본문, bullet, CTA 같은 내용입니다.
기본 결과물은 SNS 카드뉴스처럼 `16:9` 가로형 한 화면 deck이며, 아래로 스크롤하지 않고 클릭/버튼/페이지 점으로 화면이 전환됩니다.
캐릭터 이미지는 각 화면에서 고정 자산을 사용하되, 정지 화면에서도 살짝 움직이는 idle animation이 적용됩니다.

특정 페이지를 사용자가 만든 이미지로 그대로 보여주고 싶으면 `00 카드뉴스 요청 입력`의 고급 입력 `페이지 이미지 대체 JSON`에 아래처럼 넣습니다.
해당 페이지는 LLM이 문구/캐릭터/버튼을 만들지 않고, 지정한 이미지만 카드 영역에 맞춰 렌더링합니다.

```json
[
  {
    "page": 3,
    "data_uri": "data:image/png;base64,PUT_APPROVED_BASE64_HERE",
    "alt": "사용자가 만든 3페이지 이미지",
    "fit": "contain",
    "background_color": "#FFFDF7"
  }
]
```

`fit` 값은 `contain`, `cover`, `fill` 중 하나입니다. `page` 대신 `"slide_id": "slide-3"`으로 지정해도 됩니다.

서버 환경에서는 사용자의 PC 로컬 경로를 직접 쓰지 말고 Langflow File/Upload 컴포넌트 출력과 `10 업로드 캐릭터 이미지 자산 등록`, `11 페이지 이미지 대체 업로드` 노드를 사용합니다.
업로드 이미지는 Flow 내부에서 base64 data URI로 변환되어 뒤 노드로 전달됩니다.

| 순서 | From | Output | To | Input |
| --- | --- | --- | --- | --- |
| 1 | 00 카드뉴스 요청 입력 | 카드뉴스 요청 | 01 카드뉴스 브리프 프롬프트 변수 준비 | 카드뉴스 요청 |
| 2 | 01 카드뉴스 브리프 프롬프트 변수 준비 | 입력 원문 | 브리프 Prompt Template | `raw_content` |
| 3 | 01 카드뉴스 브리프 프롬프트 변수 준비 | 요청 설정 JSON | 브리프 Prompt Template | `request_context_json` |
| 4 | 01 카드뉴스 브리프 프롬프트 변수 준비 | 브리프 작성 지침 | 브리프 Prompt Template | `brief_instructions` |
| 5 | 01 카드뉴스 브리프 프롬프트 변수 준비 | 출력 스키마 JSON | 브리프 Prompt Template | `brief_output_schema` |
| 6 | 브리프 Prompt Template | Prompt 또는 Message | Agent/LLM | input |
| 7 | 00 카드뉴스 요청 입력 | 카드뉴스 요청 | 02 카드뉴스 브리프 정리 | 카드뉴스 요청 |
| 8 | Agent/LLM | text 또는 message | 02 카드뉴스 브리프 정리 | Agent/LLM 브리프 응답 |
| 9 | 02 카드뉴스 브리프 정리 | 카드뉴스 브리프 | 03 캐릭터 자산 불러오기 | 카드뉴스 payload |
| 10 | 03 캐릭터 자산 불러오기 | 캐릭터 자산 포함 브리프 | 04 카드뉴스 생성 프롬프트 변수 준비 | 캐릭터 자산 포함 브리프 |
| 11 | 04 카드뉴스 생성 프롬프트 변수 준비 | 브리프 JSON | 카드뉴스 생성 Prompt Template | `brief_json` |
| 12 | 04 카드뉴스 생성 프롬프트 변수 준비 | 요청 JSON | 카드뉴스 생성 Prompt Template | `request_json` |
| 13 | 04 카드뉴스 생성 프롬프트 변수 준비 | 캐릭터 자산 요약 JSON | 카드뉴스 생성 Prompt Template | `character_assets_json` |
| 14 | 04 카드뉴스 생성 프롬프트 변수 준비 | 카드뉴스 작성 지침 | 카드뉴스 생성 Prompt Template | `card_news_instructions` |
| 15 | 04 카드뉴스 생성 프롬프트 변수 준비 | 출력 스키마 JSON | 카드뉴스 생성 Prompt Template | `card_news_output_schema` |
| 16 | 카드뉴스 생성 Prompt Template | Prompt 또는 Message | Agent/LLM | input |
| 17 | 03 캐릭터 자산 불러오기 | 캐릭터 자산 포함 브리프 | 05 카드뉴스 계획 검증 | 캐릭터 자산 포함 브리프 |
| 18 | Agent/LLM | text 또는 message | 05 카드뉴스 계획 검증 | Agent/LLM 카드뉴스 응답 |
| 19 | 05 카드뉴스 계획 검증 | 카드뉴스 계획 | 06 카드뉴스 HTML 렌더링 | 카드뉴스 계획 |
| 20 | 06 카드뉴스 HTML 렌더링 | HTML 생성 결과 | 07 사용자 요약 출력 | HTML 생성 결과 |
| 21 | 07 사용자 요약 출력 | 요약 메시지 | Chat Output | input |
| 22 | 06 카드뉴스 HTML 렌더링 | HTML 생성 결과 | 08 HTML 코드 출력 | HTML 생성 결과 |
| 23 | 08 HTML 코드 출력 | HTML 코드 | Chat Output | input |
| 24 | 06 카드뉴스 HTML 렌더링 | HTML 생성 결과 | 09 공유 링크 발행 | HTML 생성 결과 |
| 25 | 09 공유 링크 발행 | 다운로드 링크 메시지 | Chat Output | input |

> Playground에서 HTML이 바로 렌더링되면 `06 카드뉴스 HTML 렌더링`을 Chat Output에 직접 연결했거나, `08 HTML 코드 출력`의 `출력 모드`가 `raw`로 되어 있는 상태입니다. 코드만 보고 싶으면 `08`의 기본값 `code_block`을 사용하고, 실제 화면 미리보기는 `09 공유 링크 발행` 또는 다운로드 HTML로 확인하세요.

### 2.1 서버 이미지 업로드를 포함하는 연결

반복 사용 캐릭터 포즈팩을 업로드로 등록할 때:

| 순서 | From | Output | To | Input |
| --- | --- | --- | --- | --- |
| 1 | Langflow File/Upload | File 또는 Data 출력 | 10 업로드 캐릭터 이미지 자산 등록 | 업로드 이미지/File 출력 |
| 2 | 02 카드뉴스 브리프 정리 | 카드뉴스 브리프 | 10 업로드 캐릭터 이미지 자산 등록 | 기존 payload |
| 3 | 10 업로드 캐릭터 이미지 자산 등록 | 자산 등록 payload | 03 캐릭터 자산 불러오기 | 카드뉴스 payload |

특정 페이지를 완성 이미지로 대체할 때:

| 순서 | From | Output | To | Input |
| --- | --- | --- | --- | --- |
| 1 | 00 카드뉴스 요청 입력 | 카드뉴스 요청 | 11 페이지 이미지 대체 업로드 | 카드뉴스 요청 payload |
| 2 | Langflow File/Upload | File 또는 Data 출력 | 11 페이지 이미지 대체 업로드 | 업로드 이미지/File 출력 |
| 3 | 11 페이지 이미지 대체 업로드 | 이미지 대체 payload | 01 카드뉴스 브리프 프롬프트 변수 준비 | 카드뉴스 요청 |
| 4 | 11 페이지 이미지 대체 업로드 | 이미지 대체 payload | 02 카드뉴스 브리프 정리 | 카드뉴스 요청 |

## 3. LLM 없이 빠른 확인

컴포넌트 구현 후 fallback 카드뉴스 계획과 renderer만 확인하려면 아래처럼 연결합니다.

| 순서 | From | Output | To | Input |
| --- | --- | --- | --- | --- |
| 1 | 00 카드뉴스 요청 입력 | 카드뉴스 요청 | 02 카드뉴스 브리프 정리 | 카드뉴스 요청 |
| 2 | 02 카드뉴스 브리프 정리 | 카드뉴스 브리프 | 03 캐릭터 자산 불러오기 | 카드뉴스 payload |
| 3 | 03 캐릭터 자산 불러오기 | 캐릭터 자산 포함 브리프 | 05 카드뉴스 계획 검증 | 캐릭터 자산 포함 브리프 |
| 4 | 05 카드뉴스 계획 검증 | 카드뉴스 계획 | 06 카드뉴스 HTML 렌더링 | 카드뉴스 계획 |
| 5 | 06 카드뉴스 HTML 렌더링 | HTML 생성 결과 | 07 사용자 요약 출력 | HTML 생성 결과 |
| 6 | 07 사용자 요약 출력 | 요약 메시지 | Chat Output | input |

## 4. 캐릭터 자산 입력

`03 캐릭터 자산 불러오기`는 `캐릭터 자산 JSON` 입력을 받습니다.
이 입력은 직접 manifest JSON을 붙여넣을 때 사용합니다.
서버 업로드 방식에서는 `10 업로드 캐릭터 이미지 자산 등록`의 `자산 등록 payload`를 `03 캐릭터 자산 불러오기`의 `카드뉴스 payload` 입력에 연결하면 되므로, `캐릭터 자산 JSON`은 비워둬도 됩니다.

```json
{
  "default_asset_id": "hayangi_ai_hello",
  "asset_family": "sk_hynix_hayangi_hadaengi_ai_pose_pack",
  "slide_role_defaults": {
    "cover": ["duo_ai_welcome", "hayangi_ai_hello"],
    "tip": ["hayangi_prompt_note", "hadaengi_toolbox"],
    "security": ["hayangi_security_shield", "hayangi_private_data_stop"],
    "cta": ["hadaengi_cta_point", "duo_training_invite"]
  },
  "assets": [
    {
      "asset_id": "hayangi_ai_hello",
      "character_key": "hayangi",
      "display_name": "하냥이 AI 인사 포즈",
      "mime_type": "image/png",
      "data_uri": "data:image/png;base64,...",
      "alt": "AI 카드뉴스를 안내하며 인사하는 하냥이",
      "pose": "hello",
      "ai_context": "cover_intro",
      "mood_tags": ["friendly", "bright", "welcome"],
      "recommended_slide_roles": ["cover", "intro"],
      "recommended_layouts": ["cover_character", "character_speech"]
    },
    {
      "asset_id": "hadaengi_toolbox",
      "character_key": "hadaengi",
      "display_name": "하댕이 AI 도구상자 포즈",
      "mime_type": "image/png",
      "data_uri": "data:image/png;base64,...",
      "alt": "AI 도구 활용 방법을 알려주는 하댕이",
      "pose": "toolbox",
      "ai_context": "tool_usage",
      "mood_tags": ["tools", "practical", "how_to"],
      "recommended_slide_roles": ["tip", "workflow", "checklist"],
      "recommended_layouts": ["checklist_note", "sticker_grid"]
    }
  ]
}
```

초기 구현에서는 캐릭터 이미지를 코드로 생성하지 않습니다. 승인된 하냥이/하댕이 포즈 이미지를 base64 `data_uri`로 등록하고, renderer는 `asset_id`만 참조합니다.
실제 사내 캐릭터 이미지를 public repository에 넣을 수 있는지는 별도 승인 범위에 맞춰 결정합니다.

## 5. 다운로드 링크 출력

카드뉴스 HTML도 기존 Report API 서버를 재사용합니다.

```powershell
cd C:\Users\qkekt\Desktop\기능flow\html_report_flow\report_api
python server.py
```

`09 공유 링크 발행` 입력값:

| 입력 | 값 |
| --- | --- |
| `HTML 생성 결과` | `06 카드뉴스 HTML 렌더링`의 `HTML 생성 결과` |
| `Report API 주소` | `http://127.0.0.1:8010` |
| `링크 유효시간` | `24` |

## 6. 출력 확인 포인트

- `05 카드뉴스 계획`에 `slides`, `navigation`, `animations`, `used_assets`가 들어 있는지 확인합니다.
- `00 카드뉴스 요청`의 `instruction_derived.slide_count`가 지시사항의 화면 수와 일치하는지 확인합니다.
- 첫 cover 카드에 `publication_info`와 발간호 배지가 들어 있는지 확인합니다.
- 각 카드에는 `click_target`이 들어 있고, 카드 영역 클릭으로 다음 slide anchor로 이동해야 합니다.
- `06 HTML 생성 결과`에서 `security_report.passed=true`인지 확인합니다.
- HTML에서 이전/다음 버튼, 목차 버튼, CTA 버튼이 모두 실제 anchor 이동으로 동작하는지 확인합니다.
- `prefers-reduced-motion` 환경에서는 애니메이션이 과하게 재생되지 않는지 확인합니다.
