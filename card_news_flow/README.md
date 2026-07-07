# 카드뉴스 생성 Flow

`card_news_flow`는 사용자가 카드뉴스에 넣고 싶은 내용을 한 번에 입력하면 월간 사내 카드뉴스 초안을 HTML 결과물로 생성하는 Langflow 기능 flow 설계안입니다.

핵심 방향은 LLM이 HTML을 직접 작성하지 않고, 카드뉴스 기획 JSON만 만들도록 한 뒤 deterministic renderer가 안전한 HTML/CSS로 변환하는 구조입니다. 캐릭터 이미지는 매번 새로 생성하지 않고, 한 번 확정한 base64 이미지 자산을 `asset_id`로 반복 호출합니다.

## 목표

- 사용자는 카드뉴스에 넣을 내용, 대상 독자, 톤, 발행 목적을 자연어로 입력합니다.
- Flow는 내용을 카드별 메시지, 제목, 본문, 버튼, 페이지 이동 구조로 나눕니다.
- 캐릭터는 승인된 고정 base64 이미지 자산을 사용합니다.
- SK하이닉스 하냥이/하댕이처럼 브랜드 캐릭터가 있는 경우, AI 관련 포즈팩을 미리 등록하고 카드 역할에 맞는 `asset_id`를 반복 사용합니다.
- 같은 화면 수에서는 표준 역할/레이아웃 틀을 유지하고 월별 내용만 바뀌게 합니다.
- 특정 페이지는 사용자가 만든 base64 이미지를 그대로 넣는 이미지 전용 화면으로 대체할 수 있습니다.
- 결과 HTML은 SNS 카드뉴스처럼 16:9 가로형 한 화면 deck으로 표시되며, 클릭/버튼/페이지 점으로 화면이 전환됩니다.
- 캐릭터 이미지는 slide가 멈춰 있어도 살짝 떠오르거나 콕 움직이는 idle animation을 포함합니다.
- `html_report_flow/report_api/server.py`를 재사용하면 생성 HTML을 다운로드 링크로 받을 수 있습니다.

## 권장 폴더 구성

```text
card_news_flow/
├─ README.md
├─ CONNECTION_GUIDE.md
├─ docs/
│  ├─ IMPLEMENTATION_PLAN.md
│  ├─ DESIGN_REFERENCES.md
│  ├─ BRAND_COLOR_GUIDE.md
│  ├─ CHARACTER_ASSET_GUIDE.md
│  ├─ ASSET_UPLOAD_GUIDE.md
│  └─ prompts/
├─ samples/
│  └─ ONE_FILE_TEST_CASES.md
├─ assets/
│  ├─ character_assets.example.json
│  ├─ skhynix_mascot_assets.example.json
│  └─ skhynix_brand_tokens.example.json
└─ langflow_components/
   └─ card_news_flow/
      ├─ 00_card_news_request_loader.py
      ├─ 01_card_news_brief_prompt_builder.py
      ├─ 02_card_news_brief_normalizer.py
      ├─ 03_character_asset_loader.py
      ├─ 04_card_news_plan_prompt_builder.py
      ├─ 05_card_news_plan_normalizer.py
      ├─ 06_card_news_html_renderer.py
      ├─ 07_user_summary_output.py
      ├─ 08_html_source_output.py
      ├─ 09_report_api_publisher.py
      ├─ 10_uploaded_character_asset_builder.py
      └─ 11_page_image_override_builder.py
```

현재 버전은 Langflow 커스텀 컴포넌트가 standalone 형식으로 구현되어 있습니다.
각 `.py` 파일은 로컬 공통 모듈 import 없이 단독 등록할 수 있습니다.

## 메인 Flow

```text
00 카드뉴스 요청 입력
  -> 01 카드뉴스 브리프 프롬프트 변수 준비
  -> Prompt Template
  -> Agent 또는 LLM
  -> 02 카드뉴스 브리프 정리
  -> 03 캐릭터 자산 불러오기
  -> 04 카드뉴스 생성 프롬프트 변수 준비
  -> Prompt Template
  -> Agent 또는 LLM
  -> 05 카드뉴스 계획 검증
  -> 06 카드뉴스 HTML 렌더링
  -> 07 사용자 요약 출력
  -> Chat Output

06 카드뉴스 HTML 렌더링
  -> 08 HTML 코드 출력
  -> Chat Output

06 카드뉴스 HTML 렌더링
  -> 09 공유 링크 발행
  -> Chat Output
```

`08 HTML 코드 출력`은 Playground/Chat Output에서 HTML이 바로 렌더링되지 않도록 기본적으로 코드블록 형태로 출력합니다. 실제 카드뉴스 화면은 `09 공유 링크 발행` 또는 저장된 HTML 파일로 확인하는 구성을 권장합니다.

기본 화면 비율은 `16:9` 가로형이며, renderer는 아래로 긴 문서를 만들지 않고 한 장씩 전환되는 `screen_transition` 방식으로 동작합니다.

## 설계 문서

- [구현 계획](docs/IMPLEMENTATION_PLAN.md)
- [귀여운 카드뉴스 디자인 레퍼런스](docs/DESIGN_REFERENCES.md)
- [SK 브랜드 색상 가이드](docs/BRAND_COLOR_GUIDE.md)
- [브랜드 캐릭터 자산 가이드](docs/CHARACTER_ASSET_GUIDE.md)
- [서버 환경 이미지 업로드 가이드](docs/ASSET_UPLOAD_GUIDE.md)
- [Prompt Template 모음](docs/prompts/00_PROMPT_INDEX.md)
- [연결 가이드](CONNECTION_GUIDE.md)
- [샘플 입력](samples/ONE_FILE_TEST_CASES.md)
