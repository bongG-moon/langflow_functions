# 귀여운 카드뉴스 디자인 레퍼런스

이 문서는 `card_news_flow`의 기본 시각 방향을 잡기 위한 레퍼런스 목록입니다.
목표는 SNS 피드에서 넘겨 보는 카드뉴스처럼 귀엽고 친근한 가로형 카드뉴스입니다. 다만 회사에서 매달 발행하는 콘텐츠이므로, 너무 유아용으로 보이지 않게 정보 구조와 여백은 정돈된 형태를 유지합니다.
SK하이닉스 하냥이/하댕이 같은 사내 브랜드 캐릭터를 사용할 경우, 캐릭터가 카드뉴스의 진행자처럼 느껴지도록 표지, 안내, 주의사항, 마무리 카드에 반복 배치합니다.
전체 색감은 회사 로고 색상인 SK RED `#EA002C`와 SK Orange `#F47725`를 기준으로 잡되, 귀여운 카드뉴스에 맞게 파스텔 파생색을 함께 사용합니다.

## 참고 링크

| 구분 | 링크 | 참고 포인트 |
| --- | --- | --- |
| 귀여운 카드뉴스 템플릿 | [Canva 귀여운 카드뉴스](https://www.canva.com/ko_kr/card-news/templates/cute/) | 파스텔, 손그림, 캐릭터, 스티커형 카드뉴스 무드 |
| 카드뉴스 전체 템플릿 | [Canva 카드뉴스](https://www.canva.com/ko_kr/card-news/templates/) | 귀여운 템플릿과 일반 공지형 템플릿의 균형 비교 |
| 캐러셀 템플릿 | [Canva Carousel Templates](https://www.canva.com/templates/s/carousel/) | 여러 장을 넘기는 구조와 CTA 마무리 패턴 |
| 국내 카드뉴스 레퍼런스 | [Pinterest 카드뉴스 디자인](https://kr.pinterest.com/ideas/card-news-%EC%B9%B4%EB%93%9C%EB%89%B4%EC%8A%A4-%EB%94%94%EC%9E%90%EC%9D%B8/912332434770/) | 한국어 정보 배치, 카드 제목/본문 크기감 |
| 귀여운 템플릿 무드 | [Pinterest Kawaii Template](https://www.pinterest.com/ideas/kawaii-template/930778662994/) | 너무 딱딱하지 않은 스티커/문구류 스타일 |
| 미리캔버스 카드뉴스 | [미리캔버스 카드뉴스](https://www.miricanvas.com/ko/template/card_news) | 국내 업무/교육/홍보 카드뉴스 분류 참고 |

## 디자인 타입

### 0. SNS 가로 캐러셀형

한 화면에 16:9 카드 한 장만 보여주고, 카드 클릭/페이지 점/이전·다음 버튼으로 화면이 전환되는 형태입니다.
아래로 긴 문서를 읽는 방식이 아니라 매 장이 독립적인 social post처럼 보여야 합니다.

적합한 콘텐츠:

- 월간 카드뉴스 표지와 본문 카드
- 교육/캠페인 안내
- AI 활용 팁처럼 짧은 메시지를 여러 장으로 나누는 콘텐츠

renderer token:

```json
{
  "aspect_ratio": "16:9",
  "navigation": {
    "mode": "screen_transition"
  }
}
```

### 1. 캐릭터 말풍선형

고정 캐릭터가 각 카드에서 짧게 안내하는 형태입니다.
표지와 마지막 카드에서는 캐릭터를 크게 쓰고, 본문 카드에서는 작은 말풍선이나 코너 장식으로 반복합니다.

적합한 콘텐츠:

- 월간 공지
- 교육 안내
- AI 활용 팁
- 보안 수칙 리마인드

renderer token:

```json
{
  "theme": "mascot_bubble",
  "layout": "character_speech"
}
```

### 2. 파스텔 스티커형

스티커, 라벨, 작은 아이콘을 활용해 여러 정보를 가볍게 나누는 형태입니다.
귀여운 느낌을 가장 쉽게 낼 수 있지만, 장식이 많아지면 본문 가독성이 떨어질 수 있어 카드당 포인트 장식은 3개 이하로 제한합니다.

적합한 콘텐츠:

- 체크리스트
- 캠페인 참여 방법
- 이번 달 핵심 포인트 3가지

renderer token:

```json
{
  "theme": "sticker_note",
  "layout": "sticker_grid"
}
```

### 3. 포스트잇 체크리스트형

카드 안에 포스트잇 또는 메모지를 배치하고, 항목별 체크 표시를 보여주는 형태입니다.
회사 업무 팁이나 보안 수칙처럼 실천 항목이 있는 콘텐츠에 잘 맞습니다.

적합한 콘텐츠:

- 보안 주의사항
- 업무 자동화 시작 가이드
- 이번 달 해야 할 일

renderer token:

```json
{
  "theme": "sticker_note",
  "layout": "checklist_note"
}
```

### 4. 귀여운 공지판형

공지사항을 게시판, 칠판, 노트, 파일철처럼 표현하는 형태입니다.
너무 발랄한 분위기가 부담스러운 사내 공지에 쓰기 좋습니다.

적합한 콘텐츠:

- 교육 일정
- 제도 변경 안내
- 월간 뉴스 요약

renderer token:

```json
{
  "theme": "pastel_notice",
  "layout": "notice_board"
}
```

### 5. 퀴즈/인터랙션형

카드 중간에 OX 퀴즈나 선택지를 넣고, 다음 카드에서 정답을 보여주는 구성입니다.
페이지 이동 버튼을 자연스럽게 활용할 수 있습니다.

적합한 콘텐츠:

- 보안 퀴즈
- AI 사용법 확인
- 사내 캠페인 참여 유도

renderer token:

```json
{
  "theme": "quiz_play",
  "layout": "quiz_card"
}
```

## 색상 방향

기본 팔레트는 SK RED와 SK Orange를 중심으로 두되, 넓은 면적에는 파스텔 파생색을 사용합니다.
한 화면이 너무 강해지지 않도록 원색은 제목, CTA, 배지, 진행 표시처럼 작은 면적에만 사용합니다.

| 역할 | 권장 색 |
| --- | --- |
| 브랜드 원색 | SK RED `#EA002C`, SK Orange `#F47725` |
| 배경 | `#FFF7ED`, `#FFF3F5`, `#FFFDF7` |
| 말풍선/스티커 | `#FFE8ED`, `#FFF0E6` |
| 텍스트 | `#17202A`, `#64748B` |
| 라인/그림자 | `#F2D9D0`, `rgba(15, 23, 42, .10)` |

기본 theme token:

```json
{
  "theme": "sk_cute_soft",
  "accent_color": "#EA002C",
  "secondary_color": "#F47725",
  "background_color": "#FFF7ED",
  "surface_color": "#FFFDF7"
}
```

## UI 요소

v1 renderer에서 우선 지원할 요소:

- 둥근 말풍선
- 스티커 라벨
- 포스트잇 카드
- 체크 배지
- 캐릭터 코너 배치
- 하냥이/하댕이 AI 포즈팩 배치
- 큰 CTA 버튼
- 페이지 점 navigation
- 이전/다음 화살표 버튼
- 한 화면 전환형 deck
- 캐릭터 idle motion

## 피해야 할 것

- 과하게 빽빽한 장식
- 모든 카드가 같은 파스텔색만 반복되는 구성
- 본문보다 캐릭터가 더 주목받는 화면
- 유치원/어린이집 공지처럼 보이는 과한 아동용 톤
- 긴 문장을 작은 글씨로 몰아넣는 구성

## 기본 추천안

`card_news_flow` v1의 기본 스타일은 아래 조합으로 둡니다.

```json
{
  "theme": "sk_cute_soft",
  "aspect_ratio": "16:9",
  "cover_layout": "cover_character",
  "body_layout": "sticker_grid",
  "caution_layout": "character_speech",
  "closing_layout": "cta_character",
  "navigation_mode": "screen_transition",
  "animation_level": "standard"
}
```

이 조합은 캐릭터 고정 자산을 자연스럽게 반복 사용하면서도, 매달 주제가 바뀌어도 안정적으로 적용할 수 있습니다.
