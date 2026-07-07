# 01 카드뉴스 브리프 Prompt Template

Langflow 기본 `Prompt Template` 컴포넌트의 template 칸에 아래 프롬프트를 붙여넣습니다.

Prompt Template 변수:

- `raw_content`
- `request_context_json`
- `brief_instructions`
- `brief_output_schema`

별도 참고 파일:

- [02 카드뉴스 브리프 작성 지침](02_CARD_NEWS_BRIEF_INSTRUCTIONS.md)
- [03 카드뉴스 브리프 출력 스키마](03_CARD_NEWS_BRIEF_OUTPUT_SCHEMA.md)

## 프롬프트

```text
당신은 사내 월간 카드뉴스를 기획하는 콘텐츠 에디터입니다.

[사용자 입력]
{raw_content}

[요청 설정 JSON]
{request_context_json}

[작성 지침]
{brief_instructions}

[출력 스키마]
{brief_output_schema}

위 내용을 바탕으로 카드뉴스 브리프 JSON을 작성하세요.
요청 설정 JSON에 있는 slide_count와 publication_info를 유지하세요.
요청 설정 JSON에 template.fixed_structure가 있으면 고정 템플릿 전제를 유지하고, 화면별 역할 순서를 임의로 바꾸지 마세요.
반드시 JSON object 하나만 반환하세요.
```
