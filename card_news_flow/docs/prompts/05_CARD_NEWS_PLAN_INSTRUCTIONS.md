# 05 카드뉴스 계획 작성 지침

`04 카드뉴스 생성 프롬프트 변수 준비` 컴포넌트가 `card_news_instructions` 변수로 제공하는 지침입니다.

```text
- 카드뉴스 전체 HTML을 만들지 말고 JSON 계획만 작성하세요.
- theme은 기본적으로 sk_cute_soft를 사용하고 SK RED #EA002C, SK Orange #F47725 색감을 반영하세요.
- 기본 화면 비율은 SNS 카드뉴스형 16:9 가로형입니다. 세로형/긴 문서형으로 설계하지 마세요.
- request_json.slide_count와 같은 개수의 slide를 생성하세요.
- request_json.template.fixed_structure가 true이면 brief_json.suggested_slide_roles 순서를 그대로 사용하세요. 바깥 프레임/역할 순서는 유지하되 content_area 안의 정보 구성은 주제에 맞게 설계할 수 있습니다.
- 비이미지 slide는 renderer의 고정 서비스 템플릿을 사용합니다. topbar, 우측 character_area, 하단 action_area 위치는 새로 바꾸지 마세요.
- content_area 안에서는 content_blocks를 사용해 예쁘게 구성하세요. 허용 block type은 lead, highlight, mini_cards, steps, checklist, quote, metric, tag_row입니다.
- 카드당 content_blocks는 1-3개를 권장합니다. 긴 문장 나열보다 핵심 강조, 2-3개 미니카드, 단계형 흐름, 체크리스트, 지표 강조 중 가장 어울리는 구성을 선택하세요.
- 매월 바뀌는 것은 content_area의 내부 디자인/문구, action_area의 버튼 문구/대상, character_area의 asset_id/pose 선택입니다.
- request_json.publication_info 또는 brief_json.publication_info의 발간호 정보를 card_news_plan.publication_info와 첫 cover slide에 반영하세요.
- 첫 slide는 반드시 role=cover로 두고 제목, 발간호/호수, 발행 정보를 보여주는 표지로 구성하세요.
- 화면은 아래로 내려가는 스크롤 문서가 아니라 한 장씩 전환되는 carousel/deck 구조입니다. 각 slide는 한 화면 안에서 독립적으로 읽히도록 작성하세요.
- request_json.page_image_overrides에 지정된 page 또는 slide_id는 사용자가 만든 이미지를 사용하는 페이지입니다. render_mode가 content_area이면 기존 템플릿의 중앙 내용 영역에 이미지를 넣고, full_card이면 role=image, layout=image_full로 두세요.
- 캐릭터 이미지는 새로 만들지 말고 available_character_assets 중 asset_id만 선택하세요.
- 각 slide는 한눈에 읽히도록 headline은 짧게, body는 2-4줄 분량으로 작성하세요.
- 일반 slide role은 cover, why, case, workflow, tip, checklist, security, caution, quiz, recap, cta, closing 중에서 고르세요. 이미지 대체 slide에만 image를 사용하세요.
- 보안/개인정보/기밀/외부 AI 관련 내용은 security 또는 caution slide로 분리하세요.
- 버튼은 anchor 또는 external_link만 사용하세요. 내부 이동 target은 slide id여야 합니다.
- 애니메이션은 none, fade_up, slide_in, float_in, pulse_soft, stagger 중 하나만 사용하세요.
- 캐릭터가 있는 slide는 character.animation에 float_in, pulse_soft, slide_in 중 하나를 우선 사용해 가만히 있어도 살짝 움직이는 느낌을 유지하세요.
- 출력은 JSON object 하나만 반환하고 Markdown 설명은 붙이지 마세요.
```
