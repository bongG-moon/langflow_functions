# 03 카드뉴스 브리프 출력 스키마

`01 카드뉴스 브리프 프롬프트 변수 준비` 컴포넌트가 `brief_output_schema` 변수로 제공하는 JSON 스키마입니다.

```json
{
  "brief": {
    "campaign_title": "카드뉴스 제목",
    "audience": "대상 독자",
    "communication_goal": "커뮤니케이션 목표",
    "tone_keywords": ["귀여운", "명확한", "실용적인"],
    "must_include": ["반드시 포함할 핵심 내용"],
    "content_pillars": [
      {
        "pillar_id": "P1",
        "title": "메시지 묶음 제목",
        "summary": "카드뉴스에서 다룰 내용",
        "priority": "high"
      }
    ],
    "cta": {
      "label": "CTA 문구",
      "url": "https://example.com"
    },
    "constraints": ["주의할 표현 또는 반드시 지켜야 하는 제약"],
    "template_id": "monthly_ai_news_standard",
    "fixed_structure": true,
    "suggested_slide_roles": ["cover", "why", "case", "tip", "security", "cta"]
  }
}
```
