# 06 카드뉴스 계획 출력 스키마

`04 카드뉴스 생성 프롬프트 변수 준비` 컴포넌트가 `card_news_output_schema` 변수로 제공하는 JSON 스키마입니다.

```json
{
  "card_news_plan": {
    "title": "카드뉴스 제목",
    "subtitle": "짧은 부제목",
    "template_id": "monthly_ai_news_standard",
    "fixed_structure": true,
    "template_contract": "비이미지 slide는 topbar, 우측 character_area, 하단 action_area가 고정된 SNS 가로 카드 템플릿에 렌더링되며 content_area 내부는 허용된 content_blocks로 디자인할 수 있습니다.",
    "aspect_ratio": "16:9",
    "publication_info": {
      "series_name": "AI 카드뉴스",
      "issue_label": "2026년 7월호",
      "issue_date": "2026년 7월",
      "publisher": "SK hynix"
    },
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
        "layout": "cover_character",
        "headline": "짧은 제목",
        "body": "본문",
        "bullets": ["선택 bullet"],
        "content_blocks": [
          {
            "type": "highlight",
            "title": "핵심 메시지",
            "text": "강조할 문장",
            "tone": "orange"
          },
          {
            "type": "mini_cards",
            "items": [
              {
                "title": "포인트 1",
                "text": "짧은 설명"
              }
            ],
            "tone": "soft"
          }
        ],
        "character": {
          "asset_id": "duo_ai_welcome",
          "character_key": "duo",
          "placement": "bottom_right",
          "animation": "float_in"
        },
        "animation": "fade_up",
        "image_override": {
          "data_uri": "",
          "alt": "",
          "fit": "contain",
          "render_mode": "content_area",
          "background_color": "#FFFDF7"
        },
        "buttons": [
          {
            "label": "다음",
            "action_type": "anchor",
            "target": "slide-2",
            "style": "primary"
          }
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
