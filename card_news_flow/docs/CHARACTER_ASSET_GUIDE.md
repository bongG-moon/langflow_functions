# 브랜드 캐릭터 자산 가이드

이 문서는 `card_news_flow`에서 SK하이닉스 하냥이/하댕이처럼 회사 브랜드 캐릭터를 고정 자산으로 사용하는 방식을 정리합니다.

## 기본 방향

캐릭터는 Flow가 매번 새로 생성하지 않습니다.
사전에 승인된 이미지들을 AI 관련 포즈팩으로 준비하고, 카드뉴스 생성 시에는 `asset_id`로만 참조합니다.

```text
하냥이/하댕이 공식 또는 승인된 파생 이미지
-> PNG/WebP로 정리
-> base64 data URI 변환
-> character asset manifest 등록
-> LLM은 asset_id만 선택
-> renderer가 실제 이미지 삽입
```

## 권한과 저장 원칙

하냥이/하댕이는 회사 브랜드 캐릭터이므로 아래 원칙을 기본으로 둡니다.

- 공식 사용 권한이 있거나 내부 승인된 파생 이미지만 등록합니다.
- public 저장소에는 실제 이미지 base64를 넣지 않습니다.
- 실제 운영용 manifest는 private 저장소, 배포 환경 변수, Langflow Global Variables, 또는 사내 보안 저장소로 관리합니다.
- 이 저장소에는 구조 예시와 placeholder만 둡니다.
- 이미지 생성 도구로 새 포즈를 만들 경우에도 사내 브랜드/저작권 승인 절차를 먼저 거칩니다.

## 권장 포즈팩

포즈팩은 캐릭터별 파일 묶음이 아니라, 카드뉴스의 역할에 따라 선택 가능한 자산 라이브러리입니다.
기본 방향은 하냥이가 안내/보안/체크리스트를 맡고, 하댕이가 자동화/데이터/실무 활용을 맡으며, 두 캐릭터가 함께 나오는 이미지는 표지/마무리/교육 참여 CTA에 쓰는 것입니다.

### 하냥이 포즈

| asset_id | pose | ai_context | 권장 카드 |
| --- | --- | --- | --- |
| `hayangi_ai_hello` | `hello` | `cover_intro` | cover, intro |
| `hayangi_ai_guide_pointer` | `guide_pointer` | `instruction` | intro, guide, summary |
| `hayangi_prompt_note` | `note` | `prompt_tip` | tip, checklist |
| `hayangi_prompt_magic` | `prompt_magic` | `prompt_builder` | tip, idea |
| `hayangi_security_shield` | `security_shield` | `security_notice` | caution, security |
| `hayangi_private_data_stop` | `stop_sign` | `privacy_warning` | security, caution |
| `hayangi_checklist` | `checklist` | `action_list` | checklist, summary |
| `hayangi_question_mark` | `question_mark` | `quiz_question` | why, quiz |
| `hayangi_good_example` | `good_example` | `best_practice` | tip, example, checklist |
| `hayangi_warning_sign` | `warning_sign` | `caution` | caution, security |
| `hayangi_calendar_notice` | `calendar_notice` | `schedule` | notice, schedule, cta |
| `hayangi_thumbs_up` | `thumbs_up` | `success` | recap, summary, closing |

### 하댕이 포즈

| asset_id | pose | ai_context | 권장 카드 |
| --- | --- | --- | --- |
| `hadaengi_ai_helper` | `helper` | `automation_case` | case, example |
| `hadaengi_data_scan` | `data_scan` | `data_workflow` | case, workflow |
| `hadaengi_workflow_blocks` | `workflow_blocks` | `workflow` | workflow, case |
| `hadaengi_idea_bulb` | `idea` | `idea_suggestion` | why, idea |
| `hadaengi_toolbox` | `toolbox` | `tool_usage` | tip, workflow, checklist |
| `hadaengi_robot_chat` | `robot_chat` | `chatbot_usage` | tip, example |
| `hadaengi_code_window` | `code_window` | `code_assist` | case, tip |
| `hadaengi_chart_insight` | `chart_insight` | `report_insight` | case, recap, summary |
| `hadaengi_search_lens` | `search_lens` | `research` | case, tip, why |
| `hadaengi_retry_loop` | `retry_loop` | `improvement` | tip, recap |
| `hadaengi_time_saver` | `time_saver` | `productivity` | why, case, recap |
| `hadaengi_cta_point` | `pointing` | `cta` | closing, cta |

### 듀오 포즈

| asset_id | pose | ai_context | 권장 카드 |
| --- | --- | --- | --- |
| `duo_ai_welcome` | `welcome` | `cover_intro` | cover, intro |
| `duo_ai_team` | `team` | `closing` | closing, recap |
| `duo_security_promise` | `security_promise` | `security_notice` | security, caution, closing |
| `duo_quiz_answer` | `quiz_answer` | `quiz_answer` | quiz, answer |
| `duo_before_after` | `before_after` | `workflow_compare` | workflow, case |
| `duo_monthly_recap` | `monthly_recap` | `recap` | recap, summary |
| `duo_training_invite` | `training_invite` | `training` | cta, closing, notice |
| `duo_download_ready` | `download_ready` | `download` | cta, closing |

## 선택 규칙

`03 캐릭터 자산 불러오기` 또는 `05 카드뉴스 계획 검증` 단계에서는 아래 우선순위로 자산을 고릅니다.

1. 카드 `role`에 맞는 `slide_role_defaults` 후보를 먼저 찾습니다.
2. 카드 제목/본문의 키워드가 `selection_rules.when_keywords`에 걸리면 해당 `ai_context`를 우선합니다.
3. 카드 레이아웃과 맞는 `recommended_layouts`가 있는 자산을 우선합니다.
4. 한 카드뉴스 안에서 같은 캐릭터가 너무 반복되면 `hayangi`, `hadaengi`, `duo`가 번갈아 나오도록 보정합니다.
5. `avoid_when`에 걸리는 자산은 제외합니다.
6. 최종 후보가 없으면 `default_asset_id`를 사용하고 warning을 남깁니다.

간단한 점수화 예시:

```text
score = 0
+4 if slide.role in recommended_slide_roles
+3 if keyword rule matches ai_context
+2 if layout in recommended_layouts
+1 if mood_tags matches tone keyword
-3 if avoid_when matches slide risk/context
-1 if same asset was used on previous slide
```

## Manifest 스키마

```json
{
  "asset_family": "sk_hynix_hayangi_hadaengi_ai_pose_pack",
  "version": "0.2.0",
  "default_asset_id": "duo_ai_welcome",
  "usage_scope": "internal_card_news",
  "approval": {
    "status": "pending",
    "owner": "brand_or_corp_comm_team",
    "note": "실제 운영 전 승인 필요"
  },
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
      "pose": "hello",
      "ai_context": "cover_intro",
      "mood_tags": ["friendly", "bright", "welcome"],
      "recommended_slide_roles": ["cover", "intro"],
      "recommended_layouts": ["cover_character", "character_speech"],
      "placement_hints": ["bottom_right", "center"],
      "animation_hints": ["float_in", "fade_up"],
      "avoid_when": ["serious_security_warning"],
      "mime_type": "image/png",
      "data_uri": "data:image/png;base64,...",
      "alt": "AI 카드뉴스를 안내하며 인사하는 하냥이",
      "width": 1024,
      "height": 1024
    }
  ]
}
```

## LLM에 전달하는 자산 요약

LLM에는 base64 원문을 넘기지 않습니다.
아래처럼 선택에 필요한 메타데이터만 전달합니다.

```json
{
  "available_character_assets": [
    {
      "asset_id": "hayangi_ai_hello",
      "character_key": "hayangi",
      "display_name": "하냥이 AI 인사 포즈",
      "pose": "hello",
      "ai_context": "cover_intro",
      "mood_tags": ["friendly", "bright", "welcome"],
      "recommended_slide_roles": ["cover", "intro"],
      "recommended_layouts": ["cover_character", "character_speech"],
      "placement_hints": ["bottom_right", "center"],
      "animation_hints": ["float_in", "fade_up"]
    }
  ]
}
```

## 카드뉴스 계획에서의 사용

```json
{
  "slide_id": "slide-5",
  "role": "caution",
  "headline": "AI에 넣으면 안 되는 정보가 있어요",
  "character": {
    "asset_id": "hayangi_security_shield",
    "character_key": "hayangi",
    "placement": "bottom_right",
    "animation": "float_in"
  }
}
```

## 이미지 변환

운영 서버에서는 사용자 PC의 로컬 경로를 직접 읽을 수 없습니다.
실제 Langflow 운영 환경에서는 [서버 환경 이미지 업로드 가이드](ASSET_UPLOAD_GUIDE.md)에 따라 `10 업로드 캐릭터 이미지 자산 등록` 노드로 이미지를 업로드하고 manifest에 등록하는 방식을 권장합니다.

PNG 파일을 base64 data URI로 변환하는 PowerShell 예시:

```powershell
$path = "C:\path\to\hayangi_ai_hello.png"
$bytes = [System.IO.File]::ReadAllBytes($path)
$base64 = [Convert]::ToBase64String($bytes)
"data:image/png;base64,$base64"
```

## 검증 규칙

- `data_uri`는 이미지 data URI만 허용합니다.
- 이미지 1개 기본 상한은 2MB로 둡니다.
- `asset_id`는 ASCII snake case를 사용합니다.
- `character_key`는 `hayangi`, `hadaengi`, `duo` 중 하나를 우선 사용합니다.
- `approval.status`가 `approved`가 아니면 운영 배포 전 경고를 표시합니다.
- LLM이 등록되지 않은 `asset_id`를 요청하면 기본 자산으로 대체하고 warning을 남깁니다.
