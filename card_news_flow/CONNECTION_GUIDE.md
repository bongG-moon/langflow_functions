# 카드뉴스 ver2 연결 가이드

## 권장 연결

```text
00-1 LLM 입력 정리 프롬프트.prompt
  -> LLM 입력

LLM 출력
  -> 00-2 LLM 입력 정리 결과 검증.llm_response

00-2 LLM 입력 정리 결과 검증.structured_data
  -> 01 내용 이미지 업로드/자동 배치.payload

01 내용 이미지 업로드/자동 배치.payload_out
  -> 01-1 꾸미기/캐릭터 이미지 업로드.payload

01-1 꾸미기/캐릭터 이미지 업로드.payload_out
  -> 02 카드뉴스 전체 덱 기획.image_payload

02 카드뉴스 전체 덱 기획.card_news_plan
  -> 03 단일 HTML 렌더링.card_news_plan

03 단일 HTML 렌더링.html_result
  -> 05 카드뉴스 공유 링크 출력.payload

05 카드뉴스 공유 링크 출력.link_message
  -> Chat Output
```

HTML 원문을 직접 보고 싶을 때만 아래 선택 연결을 추가합니다.

```text
03 단일 HTML 렌더링.html_result
  -> 04 HTML 결과 출력.html_result
```

## 00 노드를 쓰는 경우

`00 카드뉴스 전체 입력`은 LLM 없이 JSON/마크다운을 직접 넣을 때 쓰는 선택 노드입니다.

```text
00 카드뉴스 전체 입력.payload
  -> 01 내용 이미지 업로드/자동 배치.payload
```

LLM 정리 결과를 사람이 한 번 보정하고 싶다면 `00-2.structured_data -> 00.llm_structured_input -> 01.payload`로 연결해도 됩니다.
이때 `00 카드뉴스 전체 입력`의 `전체 카드뉴스 내용`은 비워도 되고, `LLM 정리 JSON 입력`이 우선 적용됩니다.

## LLM이 출력해야 하는 JSON

LLM이 출력해야 하는 JSON 예시는 아래와 같습니다.

```json
{
  "series_title": "P&T AI INSIGHT",
  "issue_label": "2026년 7월호",
  "issue_no": "Vol. 3",
  "cover_title": "AI 활용 문화 확산",
  "cover_subtitle": "이번 달 꼭 알아야 할 AI 업무 활용 팁",
  "pages": [
    {
      "page": 2,
      "title": "왜 지금 AI 활용이 중요할까요?",
      "content": "반복 업무를 줄이고 중요한 판단에 더 많은 시간을 쓰기 위해 AI 활용 기준을 함께 맞춰야 합니다.",
      "bullets": ["반복 업무 자동화", "팀별 활용 사례 공유", "보안 기준 함께 확인"]
    }
  ],
  "closing": {
    "title": "다음 소식에서 만나요",
    "content": "교육 신청과 문의 채널을 확인해주세요.",
    "cta": {
      "label": "교육 신청하기",
      "url": "https://example.com/apply"
    }
  },
  "image_placement_instruction": "이미지 4개를 각각 1, 3, 4, 5페이지에 넣어줘"
}
```

## 이미지 4개를 1, 3, 4, 5페이지에 넣는 방법

`01 내용 이미지 업로드/자동 배치` 노드에는 내용 이미지 파일만 업로드합니다.
아래 배치 문장은 00-2가 만든 JSON의 `image_placement_instruction` 안에 들어갑니다.

```text
이미지 4개를 각각 1, 3, 4, 5페이지에 넣어줘
```

업로드 순서대로 1, 3, 4, 5페이지에 들어갑니다.

파일명에 `page1`, `page3`, `페이지4`처럼 페이지 번호가 있으면 그 값도 자동 인식합니다.

## 꾸미기/캐릭터 이미지

`01-1 꾸미기/캐릭터 이미지 업로드` 노드에는 꾸미기용 캐릭터나 이미지 소스 파일만 업로드합니다.
기본값은 기존 flow의 생성 캐릭터 manifest를 자동으로 재사용합니다.

```text
card_news_flow/assets/generated_characters/generated_character_assets.local.json
```

파일명에 역할 키워드를 넣으면 자동 분류됩니다.

```text
my_cover_character.png
my_prompt_helper.png
my_security_shield.png
my_cta_point.png
```

업로드한 꾸미기 이미지는 자동으로 base64 manifest asset이 되고, 추정된 페이지 역할에서 기존 캐릭터보다 우선 선택됩니다.

`02 카드뉴스 전체 덱 기획`에는 별도 LLM 보조 입력을 넣지 않습니다.
페이지 역할, 레이아웃, 캐릭터 위치는 00-2의 표준 카드뉴스 요청과 업로드 파일 정보를 바탕으로 자동 결정됩니다.

## 공유 서버에 올려서 보기

`05 카드뉴스 공유 링크 출력`은 기존 `html_report_flow`의 Report API 서버를 그대로 사용합니다.

| 입력 | 값 |
| --- | --- |
| `단일 HTML 결과` | `03 단일 HTML 렌더링.html_result` 연결 |
| `Report API 주소` | `http://127.0.0.1:8010` |
| `링크 유효시간` | 기본 `24` |

서버가 실행 중이면 메시지에 `보기 링크`와 `다운로드 링크`가 출력됩니다.
서버는 아래 파일을 실행해서 켭니다.

```text
html_report_flow/report_api/server.py
```
