# 카드뉴스 ver2 샘플 업로드 이미지

아래 파일을 Langflow 노드에 그대로 업로드해서 테스트할 수 있습니다.

## 01 내용 이미지 업로드/자동 배치

`content/` 폴더의 4개 파일을 업로드합니다.

```text
content/page1_cover_ai_culture.png
content/page3_prompt_tip.png
content/page4_security.png
content/page5_checklist.png
```

파일명에 `page1`, `page3`, `page4`, `page5`가 들어 있어 자동으로 해당 페이지에 배치됩니다.
자연어 입력에 `이미지 4개를 각각 1, 3, 4, 5페이지에 넣어줘`가 있으면 업로드 순서 기준 배치도 함께 동작합니다.

## 01-1 꾸미기/캐릭터 이미지 업로드

`decorative/` 폴더의 파일을 업로드합니다.

```text
decorative/my_prompt_helper.png
decorative/my_security_shield.png
decorative/my_cta_point.png
```

파일명에 `prompt`, `security`, `cta` 키워드가 들어 있어 역할을 자동 추정합니다.
