# 카드뉴스 ver2

`card_news_ver2`는 기존 `card_news_flow`보다 단순한 카드뉴스 생성 flow입니다.

목표는 다음 3가지입니다.

- 전체 페이지 내용을 한 번에 입력합니다.
- 여러 이미지를 한 번에 올리고 원하는 페이지에 자동 또는 수동 배치합니다.
- 모든 페이지가 들어간 독립 실행 HTML 파일 하나를 생성합니다.

## 핵심 차이

기존 flow는 브리프 생성, LLM 기획, 정규화, 캐릭터 로딩, 렌더링 단계가 세분화되어 있었습니다.
ver2는 실사용 입력 흐름을 줄이기 위해 권장 흐름을 아래처럼 단순화했습니다.

```text
00-1 LLM 입력 정리 프롬프트
  -> LLM
  -> 00-2 LLM 입력 정리 결과 검증
  -> 01 내용 이미지 업로드/자동 배치
  -> 01-1 꾸미기/캐릭터 이미지 업로드
  -> 02 카드뉴스 전체 덱 기획
  -> 03 단일 HTML 렌더링
  -> 05 카드뉴스 공유 링크 출력
```

`00 카드뉴스 전체 입력`은 LLM 없이 사용자가 JSON/마크다운을 직접 넣고 싶을 때 쓰는 선택 노드입니다.
LLM 정리 흐름을 쓰는 경우에는 `00-2`의 구조화 결과를 `01`에 바로 연결하면 됩니다.

수동 입력만으로 구성할 때는 아래처럼 연결합니다.

```text
00 카드뉴스 전체 입력
  -> 01 내용 이미지 업로드/자동 배치
  -> 01-1 꾸미기/캐릭터 이미지 업로드
  -> 02 카드뉴스 전체 덱 기획
  -> 03 단일 HTML 렌더링
  -> 05 카드뉴스 공유 링크 출력
```

이 흐름에서는 사용자가 아래처럼 대충 적어도 LLM이 `series_title`, `issue_label`, `cover_title`, `pages`, `closing`, `image_placement_instruction`이 있는 표준 JSON으로 정리합니다.

```text
소식지: P&T AI INSIGHT
호수: 2026년 7월호
Vol: Vol. 3
표지 제목: AI 활용 문화 확산
이미지 배치: 이미지 4개를 각각 1, 3, 4, 5페이지에 넣어줘

[2페이지]
제목: 왜 지금 AI 활용이 중요할까요?
본문: 반복 업무를 줄이고...
```

`00-2`의 `00/01 연결용 Data` 출력을 `01 내용 이미지 업로드/자동 배치`의 `카드뉴스 요청 payload`에 바로 연결하면 됩니다.
중간에서 값을 사람이 다시 보정하고 싶을 때만 `00-2 -> 00 -> 01`로 연결해도 됩니다.

## LLM 역할

ver2에서 LLM은 필수가 아닙니다.

LLM을 연결하는 경우에도 사용자가 별도 JSON 힌트를 작성할 필요는 없습니다.
LLM은 `00-1/00-2`에서 자연어 입력을 표준 카드뉴스 요청으로 정리하는 역할만 합니다.
이후 페이지 역할, 레이아웃, 캐릭터 `asset_id`, 크기, 위치, 이미지와 겹치지 않는 배치는 `02 카드뉴스 전체 덱 기획` 노드가 자동으로 결정합니다.

## 이미지 배치

내용 이미지는 `01 내용 이미지 업로드/자동 배치` 노드에 파일만 업로드합니다.
업로드한 파일은 자동으로 base64 data URI로 변환되고, 페이지 배치는 아래 순서로 정해집니다.

1. LLM이 정리한 자연어 배치 지시

```text
이미지 4개를 각각 1, 3, 4, 5페이지에 넣어줘
```

2. 파일명 자동 인식

```text
page1_cover.png
page3_prompt_tip.png
page4_security.png
page5_summary.png
```

3. 페이지 내용의 `이미지: prompt_tip` 같은 image_ref

```text
prompt_tip.png
security.png
```

## 꾸미기/캐릭터 이미지 업로드

꾸미기용 캐릭터나 이미지 소스는 `01-1 꾸미기/캐릭터 이미지 업로드` 노드에 파일만 업로드합니다.
이 노드는 기본적으로 기존 `card_news_flow`의 생성 캐릭터 manifest를 자동으로 읽고, 업로드 파일이 있으면 그 앞에 우선 배치합니다.

업로드된 꾸미기 이미지는 자동으로 base64 `data:image/...;base64,...`로 변환되고, `character_assets.assets`에 추가됩니다.
같은 파일명 기반 `asset_id`가 있으면 업로드한 이미지가 기존 asset을 대체합니다.

파일명 또는 `asset_id`에 아래 키워드가 있으면 역할을 자동 추정합니다.

```text
cover, intro, hello, welcome, 표지, 인사 -> 표지/도입 캐릭터
helper, tip, prompt, guide, 프롬프트, 팁 -> 팁/체크리스트 캐릭터
security, shield, privacy, 보안, 개인정보, 기밀 -> 보안 안내 캐릭터
cta, closing, point, apply, 마무리, 신청 -> 마지막 CTA 캐릭터
```

## 첫 페이지와 마지막 페이지

- 첫 페이지는 표지 전용 템플릿입니다. 소식지명, 발행호, Vol, 표지 제목을 크게 보여줍니다.
- 중간 페이지는 본문/이미지/체크리스트/보안 안내 등 내용에 맞게 자동 구성합니다.
- 마지막 페이지는 CTA 전용 템플릿입니다. 신청/문의/처음으로 이동 버튼을 제공합니다.

## 공유 링크 출력

`05 카드뉴스 공유 링크 출력`은 `html_report_flow`의 기존 Report API 서버에 카드뉴스 HTML을 저장하고, 브라우저에서 바로 볼 수 있는 링크를 출력합니다.

기본 주소는 아래와 같습니다.

```text
http://127.0.0.1:8010
```

서버가 켜져 있으면 `보기 링크`가 생성되고, HTML 원문을 직접 확인하고 싶을 때만 `04 HTML 결과 출력`을 선택적으로 연결합니다.

## 파일 구조

```text
card_news_ver2/
  README.md
  CONNECTION_GUIDE.md
  samples/
    sample_bulk_input.json
    sample_page_text_input.md
  langflow_components/
    card_news_ver2/
      00_bulk_card_news_input.py
      00a_llm_input_prompt_builder.py
      00b_llm_input_normalizer.py
      01_image_bundle_builder.py
      01a_decorative_asset_uploader.py
      02_card_news_deck_planner.py
      03_one_file_html_renderer.py
      04_html_output.py
      05_card_news_api_publisher.py
```
