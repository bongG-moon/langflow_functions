# 카드뉴스 생성 Flow 구현 계획

## 1. 배경과 목표

회사는 매달 반복적으로 카드뉴스를 발행해야 합니다.
사용자는 매월 핵심 내용만 입력하고, Flow는 이를 카드뉴스용 메시지 구조, 페이지 구성, 버튼 동작, 애니메이션, 고정 캐릭터 이미지 배치까지 포함한 HTML 결과물로 만들어야 합니다.

핵심 요구사항은 아래 4가지입니다.

- 내용을 입력하면 카드뉴스를 자동 생성합니다.
- 캐릭터는 매번 새로 생성하지 않고, 생성 후 고정 자원 이미지로 등록해 반복 사용합니다.
- SK하이닉스 하냥이/하댕이처럼 회사 브랜드 캐릭터가 있는 경우, AI 관련 포즈 이미지를 포즈팩으로 등록해 카드 역할에 맞게 재사용합니다.
- 캐릭터 이미지는 base64 기반 `data:image/...;base64,...` 형태를 지원합니다.
- 버튼 동작과 페이지 이동이 가능한 결과물을 생성합니다.

## 2. 구현 원칙

기존 `html_report_flow`, `business_agent_design_flow`와 같은 구조를 따릅니다.

- LLM은 HTML을 직접 만들지 않고 JSON 계획만 생성합니다.
- HTML은 deterministic renderer가 템플릿과 안전한 CSS로 생성합니다.
- 같은 화면 수에서는 역할 순서와 layout을 고정하고, 매월 제목/본문/bullet/CTA 같은 내용만 바뀌게 합니다.
- 비이미지 페이지는 고정 SNS 카드 프레임 안에서 `topbar`, `character_area`, `action_area` 위치를 유지합니다.
- 중앙 `content_area` 안에서는 LLM이 허용된 `content_blocks`를 조합해 내용에 맞는 내부 디자인을 만들 수 있습니다.
- 사용자가 특정 페이지 이미지를 base64로 지정하면 기본적으로 기존 템플릿의 `content_area` 안에 이미지가 자연스럽게 삽입됩니다.
- 카드 전체를 완성 이미지로 대체해야 하는 경우에는 이미지 override의 `render_mode`를 `full_card`로 둡니다.
- 사용자 입력, LLM 텍스트, asset metadata는 모두 HTML escape 처리합니다.
- 버튼/페이지 이동은 v1에서 JavaScript 없이 anchor navigation과 CSS `:target` 화면 전환으로 구현합니다.
- 애니메이션은 whitelist된 CSS animation token만 허용합니다.
- 생성된 HTML 공유는 새 서버를 만들지 않고 기존 `html_report_flow/report_api/server.py`를 재사용합니다.

### 2.1 디자인 방향: 귀여운 사내 카드뉴스

기본 디자인은 딱딱한 기업형 캐러셀이 아니라, SNS에서 한 장씩 넘겨 보는 16:9 가로형 캐릭터 안내 카드뉴스로 잡습니다.

권장 무드:

- 회사 로고 색상인 SK RED `#EA002C`, SK Orange `#F47725`를 기준으로 한 파스텔 배경과 밝은 포인트 컬러
- 둥근 말풍선, 스티커, 포스트잇, 작은 배지
- 고정 캐릭터가 표지, 안내, 주의사항, 마지막 CTA 카드에 반복 등장
- 아래로 긴 문서가 아니라 한 화면 deck에서 카드가 전환되는 구조
- 캐릭터는 정지 화면에서도 살짝 떠오르거나 콕 움직이는 idle motion 유지
- 제목은 짧고 크게, 본문은 2-4줄 중심
- 카드마다 작은 장식 요소를 두되 업무 메시지 가독성을 해치지 않음
- 귀엽지만 유아용처럼 보이지 않도록 회사 공지에 맞는 정돈된 여백 유지

고정 서비스 템플릿:

| 슬롯 | 고정/변경 | 설명 |
| --- | --- | --- |
| `topbar` | 고정 | 시리즈명과 현재 페이지 번호 |
| `content_area` | 내부 구성 변경 가능 | headline, body, bullets, 발간호 정보, `content_blocks` |
| `character_area` | asset만 변경 | 등록된 하냥이/하댕이 포즈팩의 `asset_id` 선택 |
| `action_area` | 동작만 변경 | 이전/다음/CTA 버튼 |

따라서 같은 화면 수의 카드뉴스는 매달 동일한 바깥 구조를 유지하고, 사용자가 넣은 주제에 따라 중앙 내용 영역 안의 정보 배치와 캐릭터 포즈가 달라집니다.

`content_area` 내부 디자인 블록:

| block type | 용도 |
| --- | --- |
| `lead` | 한 줄 리드 문장 |
| `highlight` | 핵심 메시지 강조 박스 |
| `mini_cards` | 2-3개 정보 카드 |
| `steps` | 단계/흐름 |
| `checklist` | 실행 체크리스트 |
| `quote` | 짧은 인용/원칙 문장 |
| `metric` | 수치/키워드 강조 |
| `tag_row` | 키워드 칩 |

v1 renderer는 아래 theme token을 우선 지원합니다.

| theme token | 용도 |
| --- | --- |
| `sk_cute_soft` | SK RED/Orange 기반 귀여운 사내 카드뉴스 기본 테마 |
| `cute_soft` | 기본 파스텔 캐릭터 카드뉴스 |
| `sticker_note` | 포스트잇/스티커/체크리스트 중심 |
| `mascot_bubble` | 캐릭터 말풍선 안내 중심 |
| `pastel_notice` | 사내 공지와 캠페인 안내용 |
| `quiz_play` | 퀴즈, OX, 다음 카드 정답 확인용 |

## 3. 사용자 UX

사용자 입력은 기본적으로 한 칸입니다.

예시:

```text
이번 달 사내 카드뉴스 주제는 AI 활용 문화 확산입니다.
주요 내용은 1) 업무 자동화 사례 공유, 2) 보안 유의사항, 3) 프롬프트 작성 팁, 4) 다음 달 교육 안내입니다.
톤은 밝지만 너무 가볍지 않게, 직원들이 바로 읽고 행동할 수 있게 만들어주세요.
마지막 카드에는 교육 신청 버튼을 넣고 싶습니다.
```

고급 입력으로만 아래 값을 둡니다.

| 입력 | 용도 | 기본값 |
| --- | --- | --- |
| `지시사항` | 화면 수, 발간호, 페이지 이동 방식, CTA 요구사항 | 빈 값 |
| `카드 수` | 생성할 카드 장수 | `6` |
| `브랜드 톤` | 사내 뉴스레터, 공지, 캠페인 등 | `사내 카드뉴스` |
| `캐릭터 자산 JSON` | base64 이미지 자산 목록 | 내장 예시 또는 빈 값 |
| `주요 CTA URL` | 마지막 카드 버튼 링크 | 빈 값 |
| `페이지 비율` | 16:9, 1:1, 4:5, 9:16 | `16:9` |
| `애니메이션 강도` | none, subtle, standard | `standard` |
| `페이지 이미지 대체 JSON` | 특정 페이지를 사용자가 만든 base64 이미지로 그대로 대체 | 빈 값 |

페이지 이미지 대체 JSON 예시:

```json
[
  {
    "page": 3,
    "data_uri": "data:image/png;base64,PUT_APPROVED_BASE64_HERE",
    "alt": "사용자가 만든 3페이지 이미지",
    "fit": "contain",
    "render_mode": "content_area",
    "background_color": "#FFFDF7"
  }
]
```

## 4. 전체 아키텍처

```text
사용자 내용 입력
-> 00 카드뉴스 요청 입력
-> 01 브리프 프롬프트 변수 준비
-> Prompt Template
-> LLM
-> 02 브리프 정리
-> 03 캐릭터 자산 불러오기
-> 04 카드뉴스 생성 프롬프트 변수 준비
-> Prompt Template
-> LLM
-> 05 카드뉴스 계획 검증
-> 06 HTML 렌더링
-> 07 요약 출력
-> Chat Output

06 HTML 렌더링
-> 09 공유 링크 발행
-> html_report_flow/report_api/server.py
-> 다운로드 링크
```

## 5. 컴포넌트 계획

### 00 카드뉴스 요청 입력

사용자 자연어 입력과 고급 옵션을 표준 request payload로 변환합니다.

출력 예시:

```json
{
  "payload_version": "card-news-flow-v1",
  "flow_type": "card_news",
  "request": {
    "raw_content": "...",
    "target_audience": "전 직원",
    "brand_tone": "사내 카드뉴스",
    "slide_count": 6,
    "aspect_ratio": "16:9",
    "animation_level": "standard",
    "primary_cta": {
      "label": "교육 신청하기",
      "url": "https://example.com/apply"
    }
  }
}
```

### 01 카드뉴스 브리프 프롬프트 변수 준비

카드뉴스 목적, 독자, 메시지 우선순위, CTA, 제약사항을 추출하도록 Prompt Template 변수를 만듭니다.

주요 출력:

- `raw_content`
- `brief_instructions`
- `brief_output_schema`

### 02 카드뉴스 브리프 정리

LLM 응답을 검증하고, 비정상 JSON이면 사용자 원문 기반 fallback 브리프를 만듭니다.

브리프 스키마:

```json
{
  "brief": {
    "campaign_title": "AI 활용 문화 확산 카드뉴스",
    "audience": "전 직원",
    "communication_goal": "AI 활용 사례와 보안 유의사항을 쉽게 전달",
    "tone_keywords": ["명확한", "실용적인", "친근한"],
    "must_include": ["업무 자동화 사례", "보안 유의사항", "프롬프트 팁", "교육 안내"],
    "cta": {"label": "교육 신청하기", "url": "https://example.com/apply"},
    "constraints": ["과장된 성과 표현 금지", "외부 공개용 표현 피하기"]
  }
}
```

### 03 캐릭터 자산 불러오기

base64 캐릭터 이미지를 검증하고 브리프에 연결합니다.

자산 스키마:

```json
{
  "asset_family": "sk_hynix_hayangi_hadaengi_ai_pose_pack",
  "version": "0.2.0",
  "default_asset_id": "duo_ai_welcome",
  "pose_groups": [
    {
      "group_id": "security_notice",
      "description": "보안, 개인정보, 민감정보 입력 금지",
      "preferred_assets": ["hayangi_security_shield", "hayangi_private_data_stop"]
    }
  ],
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
      "width": 1024,
      "height": 1024,
      "pose": "hello",
      "ai_context": "cover_intro",
      "mood_tags": ["friendly", "bright", "welcome"],
      "recommended_slide_roles": ["cover", "intro"],
      "recommended_layouts": ["cover_character", "character_speech"],
      "placement_hints": ["bottom_right", "center"],
      "animation_hints": ["float_in", "fade_up"],
      "usage_policy": {
        "allow_crop": true,
        "allow_css_filter": false,
        "regenerate_each_run": false
      }
    }
  ]
}
```

검증 규칙:

- `data_uri`는 `data:image/png;base64,`, `data:image/jpeg;base64,`, `data:image/webp;base64,`만 허용합니다.
- base64 decode가 실패하면 해당 자산은 사용하지 않습니다.
- 이미지 1개 기본 상한은 2MB로 둡니다.
- LLM은 `data_uri` 전체를 보지 않고 `asset_id`, `character_key`, `display_name`, `pose`, `ai_context`, `recommended_slide_roles`, `recommended_layouts` 요약만 봅니다.

### 04 카드뉴스 생성 프롬프트 변수 준비

브리프와 캐릭터 자산 요약을 LLM이 카드뉴스 계획 JSON으로 만들 수 있게 정리합니다.

LLM에 전달하는 지침:

- 카드별 제목은 짧고 명확하게 작성합니다.
- 본문은 모바일에서 읽히도록 2-4줄 안으로 제한합니다.
- `fixed_structure=true`이면 `suggested_slide_roles` 순서를 그대로 따르고, 역할/레이아웃을 새로 설계하지 않습니다.
- `page_image_overrides`가 지정된 페이지는 기본적으로 기존 템플릿 역할을 유지하고 `content_area` 안에 이미지를 삽입합니다.
- `render_mode=full_card`인 이미지 대체 페이지는 `role=image`, `layout=image_full`로 두고 문구/캐릭터/버튼을 비웁니다.
- 캐릭터는 필요한 카드에서 `asset_id`로만 참조합니다.
- 하냥이/하댕이 포즈팩을 사용할 때는 `character_key`, `pose`, `ai_context`, `recommended_slide_roles`를 보고 가장 맞는 `asset_id`를 선택합니다.
- 애니메이션은 허용 목록에서만 고릅니다.
- 버튼은 `anchor`, `external_link`, `download_hint` 중 하나의 action type만 사용합니다.
- 외부 URL은 사용자가 준 CTA 또는 `https://` 링크만 허용합니다.

### 05 카드뉴스 계획 검증

LLM이 만든 카드뉴스 계획을 검증하고 renderer용 안전 payload로 바꿉니다.

계획 스키마:

```json
{
  "card_news_plan": {
    "title": "AI 활용 문화 확산",
    "subtitle": "이번 달 실천할 수 있는 AI 업무 팁",
    "aspect_ratio": "16:9",
    "style": {
      "theme": "sk_cute_soft",
      "brand": "sk_hynix",
      "accent_color": "#EA002C",
      "secondary_color": "#F47725",
      "background_color": "#FFF7ED",
      "surface_color": "#FFFDF7",
      "density": "comfortable"
    },
    "slides": [
      {
        "slide_id": "slide-1",
        "role": "cover",
        "headline": "AI, 이번 달에는 이렇게 써보세요",
        "body": "업무 자동화 사례부터 보안 팁까지 한 번에 정리했습니다.",
        "character": {
          "asset_id": "hayangi_ai_hello",
          "character_key": "hayangi",
          "pose": "hello",
          "placement": "bottom_right",
          "animation": "float_in"
        },
        "layout": "cover_character",
        "animation": "fade_up",
        "buttons": [
          {"label": "다음", "action_type": "anchor", "target": "slide-2", "style": "primary"}
        ]
      }
    ],
    "navigation": {
      "mode": "screen_transition",
      "show_progress": true,
      "show_home_button": true
    }
  }
}
```

검증 규칙:

- slide 수가 3장 미만이면 cover, body, closing 최소 3장을 보강합니다.
- 요청된 slide 수에 맞춰 부족한 slide를 고정 템플릿 슬롯으로 보강하고 초과 slide를 제거합니다.
- LLM이 다른 role/layout을 반환해도 최종 role/layout은 표준 템플릿 순서로 재정렬합니다.
- `render_mode=content_area` 이미지 대체 페이지는 템플릿 프레임과 이동 버튼을 유지하고 중앙 내용 영역에 이미지를 배치합니다.
- `render_mode=full_card` 이미지 대체 페이지는 `image_override`만 유지하고 headline/body/bullets/buttons/character를 제거합니다.
- `character.asset_id`가 등록된 자산에 없으면 기본 캐릭터로 대체합니다.
- `animation`은 `none`, `fade_up`, `slide_in`, `float_in`, `pulse_soft`, `stagger` 중 하나만 허용합니다.
- `layout`은 허용된 layout token만 사용합니다.
- 버튼 `target`은 실제 slide id 또는 허용된 `https://` URL만 허용합니다.
- HTML에 들어갈 모든 문구는 escape 전제로 보관합니다.

### 06 카드뉴스 HTML 렌더링

안전 검증된 plan을 독립 실행 가능한 HTML로 만듭니다.

렌더링 구성:

- 전체 shell: 카드뉴스 뷰어
- slide section: `id="slide-1"` 형태
- navigation: 이전/다음 버튼, 페이지 점, 홈 버튼
- page movement: anchor link, 카드 전체 click target, CSS `:target` 전환
- animation: CSS keyframes와 slide별 class
- character image: `<img src="data:image/png;base64,...">`
- page override image: `<img src="data:image/png;base64,...">`를 카드 영역 전체에 `contain`, `cover`, `fill` 방식으로 맞춤
- CTA: 내부 anchor 또는 `https://` 링크

JavaScript 없는 v1 동작:

- 이전/다음 버튼은 `href="#slide-2"`처럼 이동합니다.
- 마지막 카드를 제외한 각 카드에는 투명 anchor hit area가 있어 카드 영역을 누르면 다음 slide로 이동합니다.
- 목차/페이지 점은 각 slide anchor로 이동합니다.
- closing 카드의 CTA는 사용자가 제공한 `https://` URL로 이동합니다.
- 자동 재생, 복잡한 상태 저장, drag swipe는 v2 이후 선택 기능으로 둡니다.

필수 CSS:

- `body overflow:hidden`
- `slide-stage` 안의 absolute slide 전환
- `:target` 기반 opacity/translate transition
- SK brand CSS variables: `--sk-red`, `--sk-orange`, `--sk-bg`, `--sk-surface`
- `@keyframes fadeUp`, `copySlideIn`, `mascotIdle`, `mascotPulse`, `mascotPeek`
- `@media (prefers-reduced-motion: reduce)`
- 모바일/데스크톱 반응형 카드 비율

색상 토큰은 [SK 브랜드 색상 가이드](BRAND_COLOR_GUIDE.md)와 `assets/skhynix_brand_tokens.example.json`을 기준으로 구현합니다.

### 07 사용자 요약 출력

Chat Output에는 HTML 전체가 아니라 생성 결과 요약을 표시합니다.

예시:

```text
카드뉴스 초안이 생성되었습니다.

- 제목: AI 활용 문화 확산
- 카드 수: 6장
- 캐릭터 자산: monthly_news_guide
- 포함 기능: 이전/다음 이동, 목차 이동, 교육 신청 CTA

HTML 코드 또는 다운로드 링크 출력 노드를 연결해 결과를 확인하세요.
```

### 08 HTML 코드 출력

Langflow Playground에서 HTML 코드를 직접 확인하고 싶을 때 사용합니다.
기본 출력은 fenced code block이므로 Chat Output에서 카드뉴스 화면으로 바로 렌더링되지 않습니다.
실제 화면 미리보기는 `09 공유 링크 발행` 또는 저장된 HTML 파일로 확인합니다.

### 09 공유 링크 발행

기존 `html_report_flow/langflow_components/html_report_flow/05_report_api_publisher.py`의 로직을 카드뉴스 payload 이름에 맞게 복제하거나 얇게 변형합니다.
서버는 새로 만들지 않고 `html_report_flow/report_api/server.py`를 재사용합니다.

## 6. 캐릭터 이미지 운영 방식

하냥이/하댕이 같은 사내 브랜드 캐릭터는 단순 장식이 아니라 카드뉴스의 진행자 역할로 사용합니다.
따라서 "캐릭터 1개"가 아니라 "캐릭터별 AI 포즈팩"으로 관리하는 것이 좋습니다.

권장 포즈 그룹:

| 그룹 | 대표 asset_id | 용도 |
| --- | --- | --- |
| `cover_intro` | `duo_ai_welcome`, `hayangi_ai_hello` | 표지, 인사, 월간 소식 시작 |
| `ai_tip` | `hayangi_prompt_note`, `hayangi_prompt_magic`, `hadaengi_toolbox` | 프롬프트 작성 팁, 업무 활용 팁 |
| `automation_case` | `hadaengi_ai_helper`, `hadaengi_data_scan`, `hadaengi_workflow_blocks` | AI 도우미, 자동화 사례, 데이터 업무 |
| `security_notice` | `hayangi_security_shield`, `hayangi_private_data_stop`, `duo_security_promise` | 보안 주의사항, 민감정보 입력 금지 |
| `quiz_interaction` | `hayangi_question_mark`, `duo_quiz_answer` | OX 퀴즈, 다음 카드 정답 확인 |
| `cta_closing` | `hadaengi_cta_point`, `duo_training_invite`, `duo_download_ready` | 신청/문의/다운로드/마무리 |

운영 원칙:

- 실제 이미지는 공식 승인된 원본 또는 승인된 파생 이미지만 사용합니다.
- Flow 실행 중에는 캐릭터를 새로 생성하지 않습니다.
- LLM은 `data_uri` 전체를 보지 않고 자산 요약만 보고 `asset_id`를 선택합니다.
- renderer가 `asset_id`를 실제 base64 이미지로 치환합니다.
- public 저장소에 실제 사내 캐릭터 이미지를 넣는 것은 피하고, 필요하면 private 저장소 또는 Langflow Global Variables로 주입합니다.

자동 선택 규칙:

- `slide.role`이 `security`, `caution`이면 보안/주의 포즈를 우선합니다.
- `slide.role`이 `tip`, `checklist`이고 본문에 프롬프트/질문/예시가 있으면 하냥이 프롬프트 포즈를 우선합니다.
- 본문에 자동화/데이터/리포트/분석이 있으면 하댕이 실무 포즈를 우선합니다.
- 마지막 CTA/교육 신청/다운로드 카드에는 하댕이 CTA 또는 듀오 마무리 포즈를 우선합니다.
- 직전 카드와 같은 `asset_id`를 반복 사용하지 않도록 점수를 낮춥니다.

### 6.1 최초 생성

캐릭터 이미지는 별도 이미지 생성 도구, 디자이너 산출물, 또는 사내 승인된 원본 자산 기반으로 한 번 만듭니다.
Flow 내부에서는 매 실행마다 이미지를 생성하지 않습니다.

### 6.2 base64 등록

생성된 PNG/WebP를 아래 형태로 변환해 asset manifest에 넣습니다.

```text
data:image/png;base64,iVBORw0KGgoAAA...
```

권장 저장 위치:

```text
card_news_flow/assets/character_assets.json
```

실제 사내 캐릭터 이미지는 민감하거나 용량이 클 수 있으므로, 저장소에는 예시 파일만 두고 운영 환경에서는 Langflow Global Variables 또는 고급 입력으로 주입하는 방식을 권장합니다.

### 6.3 반복 사용

LLM은 캐릭터 이미지를 직접 만들거나 바꾸지 못합니다.
카드뉴스 계획에는 아래처럼 `asset_id`만 들어갑니다.

```json
{
  "character": {
    "asset_id": "hayangi_security_shield",
    "character_key": "hayangi",
    "pose": "security_shield",
    "placement": "bottom_right",
    "animation": "float_in"
  }
}
```

renderer가 `asset_id`를 실제 base64 `data_uri`로 치환합니다.

## 7. 버튼과 페이지 이동 설계

v1은 HTML 파일 하나로 동작해야 하므로 anchor 기반 이동을 기본으로 합니다.

| 버튼 유형 | action_type | 동작 |
| --- | --- | --- |
| 다음 | `anchor` | 다음 slide id로 이동 |
| 이전 | `anchor` | 이전 slide id로 이동 |
| 목차/점 | `anchor` | 선택 slide로 이동 |
| 홈 | `anchor` | cover slide로 이동 |
| CTA | `external_link` | 사용자가 제공한 `https://` URL 열기 |

버튼 스키마:

```json
{
  "label": "교육 신청하기",
  "action_type": "external_link",
  "target": "https://example.com/apply",
  "style": "primary"
}
```

보안 규칙:

- `javascript:`, `data:text/html`, `vbscript:` URL 금지
- CTA URL은 `https://` 기본 권장
- target이 내부 slide라면 실제 slide id와 일치해야 함
- 버튼 label은 20자 이하 권장, 길면 renderer에서 줄바꿈 처리

## 8. 애니메이션 설계

애니메이션은 CSS token 방식으로만 허용합니다.

| token | 용도 |
| --- | --- |
| `none` | 정적 카드 |
| `fade_up` | 제목/본문이 부드럽게 올라옴 |
| `slide_in` | 강조 블록이 좌우에서 등장 |
| `float_in` | 캐릭터가 살짝 떠오르며 등장 |
| `pulse_soft` | CTA 버튼이나 핵심 배지를 약하게 강조 |
| `stagger` | bullet list가 순차적으로 등장 |

접근성:

- `prefers-reduced-motion: reduce`에서는 duration을 매우 짧게 하거나 transform을 제거합니다.
- 반복 애니메이션은 캐릭터 float처럼 장식성이 강한 요소에만 제한합니다.
- CTA pulse는 과하지 않게 2-3회 또는 hover 중심으로 둡니다.

## 9. HTML 보안 정책

카드뉴스는 사용자 입력과 LLM 생성 문구를 포함하므로 renderer 보안이 중요합니다.

필수 규칙:

- LLM이 임의 HTML/CSS/JS를 반환해도 텍스트로 escape합니다.
- renderer는 허용된 layout, animation, button action만 사용합니다.
- inline event handler는 생성하지 않습니다.
- `<script>`, `<iframe>`, `<object>`, `<embed>`는 v1에서 금지합니다.
- 외부 이미지/폰트/CDN은 기본 금지합니다.
- 이미지 source는 검증된 base64 data URI만 허용합니다.
- 링크는 내부 anchor 또는 `http/https`만 허용합니다.

권장 CSP:

```text
default-src 'none';
img-src 'self' data:;
style-src 'unsafe-inline';
base-uri 'none';
form-action 'none';
frame-ancestors 'none';
```

## 10. 샘플 카드 구성

6장 카드뉴스 기본 구성:

| 카드 | 역할 | 내용 |
| --- | --- | --- |
| 1 | Cover | 주제와 한 줄 메시지 |
| 2 | Why | 왜 지금 중요한지 |
| 3 | Case | 이번 달 사례 또는 핵심 정보 |
| 4 | Tip | 바로 적용할 수 있는 방법 |
| 5 | Caution | 보안/주의사항 |
| 6 | CTA | 다음 행동, 신청/문의/다운로드 |

화면 수별 기본 슬롯은 고정입니다. 예를 들어 7장은 `cover, why, case, tip, security, workflow, cta`, 8장은 `cover, why, case, tip, security, workflow, checklist, cta` 순서로 유지됩니다.
특정 페이지가 이미지 대체로 지정되면 해당 위치만 `image` 페이지가 되고, 앞뒤 페이지 순서는 유지됩니다.

귀여운 안내형 6장 구성:

| 카드 | 역할 | 화면 느낌 |
| --- | --- | --- |
| 1 | Cover | 캐릭터가 제목 옆에서 인사, 큰 타이틀과 월간 배지 |
| 2 | Why | 말풍선 2-3개로 이번 주제가 필요한 이유 설명 |
| 3 | Case | 스티커 카드 3개로 사례/핵심 포인트 정리 |
| 4 | Tip | 체크리스트 또는 포스트잇 형태의 실천 팁 |
| 5 | Caution | 캐릭터가 주의 팻말을 든 형태의 보안/주의사항 |
| 6 | CTA | 캐릭터와 큰 버튼, 다음 행동 안내 |

## 11. 구현 단계

### 1단계: 문서/스키마 확정

- `card_news_flow` 폴더와 문서 생성
- 귀여운 카드뉴스 디자인 레퍼런스와 theme token 확정
- SK RED/Orange 기반 브랜드 색상 토큰 확정
- request, brief, asset manifest, card_news_plan 스키마 확정
- 하냥이/하댕이 AI 포즈팩 목록과 asset id naming 확정
- Prompt Template 초안 작성
- 샘플 입력 5-10개 작성

### 2단계: LLM 없는 fallback 컴포넌트 구현

- `00`, `02`, `03`, `05`, `06`, `07`, `08`, `09` 구현
- 원문 입력만으로 기본 6장 카드뉴스 생성
- 기본 캐릭터 자산이 없을 때 placeholder 없이 텍스트 중심으로 안전하게 렌더링

### 3단계: Prompt Template + LLM 연동

- `01`, `04` 구현
- 브리프 생성 Prompt Template 분리
- 카드뉴스 계획 생성 Prompt Template 분리
- LLM 응답 검증/fallback 강화

### 4단계: 애니메이션/페이지 이동 고도화

- CSS `:target` 화면 전환 적용
- 이전/다음/홈/페이지 점 이동 확인
- animation token별 렌더링
- `prefers-reduced-motion` 대응

### 5단계: 자산 운영 개선

- `assets/character_assets.example.json` 추가
- `assets/skhynix_mascot_assets.example.json` 구조 추가
- base64 이미지 크기/형식 검증
- 여러 pose가 있을 경우 카드 역할별 pose 선택 지원
- 운영 환경에서 Global Variables로 주입하는 가이드 작성

### 6단계: 검증과 샘플 산출물

- `py_compile`로 컴포넌트 문법 검증
- 대표 입력 10건 실행
- HTML 보안 검사
- 데스크톱/모바일 브라우저 스크린샷 검증
- Report API 다운로드 링크 발행 확인

## 12. Acceptance Criteria

| 영역 | 합격 기준 |
| --- | --- |
| 단일 입력 UX | 대표 입력 10건이 내용 입력 한 칸만으로 기본 카드뉴스 생성 |
| 캐릭터 고정 자산 | 하냥이/하댕이 같은 `asset_id`가 여러 실행에서 동일 base64 이미지로 렌더링 |
| 캐릭터 권한 관리 | 공식 승인/내부 사용 범위가 확인된 자산만 실제 manifest에 등록 |
| LLM 안정성 | LLM이 HTML을 반환해도 renderer는 JSON plan만 사용 |
| 버튼 동작 | 이전/다음/홈/페이지 점/CTA가 모두 유효한 링크로 동작 |
| 애니메이션 | 허용 token만 렌더링되고 reduce motion에서 완화 |
| 보안 | 금지 태그, inline event handler, 위험 URL scheme 0건 |
| 링크 발행 | Report API 서버 실행 시 다운로드 링크 생성 |
| 모바일 품질 | 390px 폭에서 텍스트 겹침 없이 카드뉴스 확인 가능 |

## 13. 구현 시 우선순위

가장 먼저 만들 것은 `06_card_news_html_renderer.py`입니다.
카드뉴스는 최종 화면 품질이 핵심이므로 renderer 계약을 먼저 잡고, LLM은 그 계약에 맞는 JSON plan만 생성하도록 붙이는 편이 안정적입니다.

권장 순서:

1. plan schema 수동 샘플 작성
2. renderer 구현
3. fallback plan normalizer 구현
4. base64 asset loader 구현
5. Prompt Template/LLM 연결
6. 공유 링크 발행 연결
`지시사항`에 `총 7개 화면`, `총 5페이지`, `8장 구성`처럼 적으면 해당 숫자가 `slide_count`로 우선 적용됩니다.
`2026년 7월호`, `제12호`, `발간호: Vol. 3` 같은 표현은 첫 cover 카드의 발간 정보로 표시됩니다.
