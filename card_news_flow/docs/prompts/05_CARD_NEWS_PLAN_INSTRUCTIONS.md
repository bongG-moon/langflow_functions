# 05 카드뉴스 계획 작성 지침

`04 카드뉴스 생성 프롬프트 변수 준비` 컴포넌트가 `card_news_instructions` 변수로 제공하는 지침입니다.

```text
- 카드뉴스 전체 HTML을 만들지 말고 JSON 계획만 작성하세요.
- theme은 기본적으로 sk_cute_soft를 사용하고 SK RED #EA002C, SK Orange #F47725 색감을 반영하세요.
- 기본 화면 비율은 SNS 카드뉴스형 16:9 가로형입니다. 세로형/긴 문서형으로 설계하지 마세요.
- request_json.slide_count와 같은 개수의 slide를 생성하세요.
- request_json.template.fixed_structure가 true이면 brief_json.suggested_slide_roles 순서를 그대로 사용하세요. 역할/레이아웃 순서를 새로 설계하지 말고 각 슬롯의 내용만 작성하세요.
- request_json.publication_info 또는 brief_json.publication_info의 발간호 정보를 card_news_plan.publication_info와 첫 cover slide에 반영하세요.
- 첫 slide는 반드시 role=cover로 두고 제목, 발간호/호수, 발행 정보를 보여주는 표지로 구성하세요.
- 화면은 아래로 내려가는 스크롤 문서가 아니라 한 장씩 전환되는 carousel/deck 구조입니다. 각 slide는 한 화면 안에서 독립적으로 읽히도록 작성하세요.
- request_json.page_image_overrides에 지정된 page 또는 slide_id는 사용자가 만든 이미지를 그대로 보여주는 페이지입니다. 해당 slide는 role=image, layout=image_full로 두고 headline/body/bullets/buttons/character를 비워두세요.
- 캐릭터 이미지는 새로 만들지 말고 available_character_assets 중 asset_id만 선택하세요.
- 각 slide는 한눈에 읽히도록 headline은 짧게, body는 2-4줄 분량으로 작성하세요.
- 일반 slide role은 cover, why, case, workflow, tip, checklist, security, caution, quiz, recap, cta, closing 중에서 고르세요. 이미지 대체 slide에만 image를 사용하세요.
- 보안/개인정보/기밀/외부 AI 관련 내용은 security 또는 caution slide로 분리하세요.
- 버튼은 anchor 또는 external_link만 사용하세요. 내부 이동 target은 slide id여야 합니다.
- 애니메이션은 none, fade_up, slide_in, float_in, pulse_soft, stagger 중 하나만 사용하세요.
- 캐릭터가 있는 slide는 character.animation에 float_in, pulse_soft, slide_in 중 하나를 우선 사용해 가만히 있어도 살짝 움직이는 느낌을 유지하세요.
- 출력은 JSON object 하나만 반환하고 Markdown 설명은 붙이지 마세요.
```
