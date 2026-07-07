# SK 브랜드 색상 가이드

첨부된 회사 로고 색상 이미지를 기준으로 `card_news_flow`의 기본 색상 토큰을 정의합니다.
카드뉴스는 귀여운 파스텔 무드를 유지하되, CTA와 핵심 강조에는 SK RED와 SK Orange를 사용합니다.

## 원본 브랜드 컬러

| 토큰 | 색상 | HEX | 용도 |
| --- | --- | --- | --- |
| `sk_red` | SK RED | `#EA002C` | 핵심 CTA, 주요 제목 강조, 경고/보안 포인트 |
| `sk_orange` | SK Orange | `#F47725` | 보조 CTA, 배지, 스티커, 진행 표시 |

첨부 이미지에는 SK RED가 `#EA002C`, SK Orange가 `#F47725`로 표기되어 있습니다.
카드뉴스 구현에서는 HEX 값을 기준으로 사용합니다.

## 귀여운 카드뉴스용 파생 팔레트

원색을 넓은 배경에 그대로 쓰면 사내 카드뉴스가 다소 강하게 보일 수 있습니다.
따라서 배경과 말풍선에는 아래처럼 밝은 파생색을 사용합니다.

| 토큰 | HEX | 용도 |
| --- | --- | --- |
| `sk_red_soft` | `#FFE8ED` | 붉은 계열 말풍선/주의 카드 배경 |
| `sk_red_lighter` | `#FFF3F5` | 표지/요약 카드의 부드러운 배경 |
| `sk_orange_soft` | `#FFF0E6` | 주황 계열 포스트잇/스티커 배경 |
| `sk_orange_lighter` | `#FFF7ED` | 전체 카드 배경, warm neutral |
| `sk_cream` | `#FFFDF7` | 기본 카드 면 |
| `sk_ink` | `#17202A` | 본문 텍스트 |
| `sk_muted` | `#64748B` | 보조 설명 |
| `sk_line` | `#F2D9D0` | 부드러운 경계선 |

## 테마 토큰

v1 renderer는 아래 테마를 우선 지원합니다.

```json
{
  "theme": "sk_cute_soft",
  "brand": "sk_hynix",
  "accent_color": "#EA002C",
  "secondary_color": "#F47725",
  "background_color": "#FFF7ED",
  "surface_color": "#FFFDF7"
}
```

## 사용 규칙

- `#EA002C`는 한 화면에서 1-2개 요소만 강하게 사용합니다.
- `#F47725`는 배지, 페이지 점, 작은 스티커, 보조 버튼에 사용합니다.
- 배경은 `sk_orange_lighter`, `sk_red_lighter`, `sk_cream`을 번갈아 사용합니다.
- 보안/주의 카드에서는 `sk_red`를 제목 또는 아이콘에 사용하되, 배경은 `sk_red_soft`로 낮춥니다.
- CTA 버튼은 기본적으로 `sk_red` 배경 + 흰색 텍스트를 사용합니다.
- 너무 유아용으로 보이지 않도록 텍스트 색은 `sk_ink`를 유지합니다.

## 카드 역할별 추천 색

| 카드 역할 | 배경 | 강조 | 비고 |
| --- | --- | --- | --- |
| cover | `sk_orange_lighter` | `sk_red`, `sk_orange` | 하냥이/하댕이 듀오 배치 |
| why | `sk_red_lighter` | `sk_red` | 문제 제기/공감 |
| case | `sk_cream` | `sk_orange` | 사례/자동화 흐름 |
| tip | `sk_orange_soft` | `sk_orange` | 포스트잇/체크리스트 |
| security | `sk_red_soft` | `sk_red` | 보안/주의 |
| quiz | `sk_cream` | `sk_orange`, `sk_red` | OX/참여형 |
| cta | `sk_orange_lighter` | `sk_red` | 신청/문의/다운로드 |

## CSS 변수 예시

```css
:root {
  --sk-red: #EA002C;
  --sk-orange: #F47725;
  --sk-red-soft: #FFE8ED;
  --sk-orange-soft: #FFF0E6;
  --sk-bg: #FFF7ED;
  --sk-surface: #FFFDF7;
  --sk-ink: #17202A;
  --sk-muted: #64748B;
  --sk-line: #F2D9D0;
}
```
