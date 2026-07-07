# 서버 환경 이미지 업로드 가이드

운영 서버에서는 사용자 PC의 `C:\...` 로컬 경로를 사용할 수 없습니다.
카드뉴스 Flow는 이미지를 최종 HTML에 포함하기 위해 `data:image/...;base64,...` data URI를 사용합니다.
따라서 Langflow 내부에서는 아래 흐름으로 처리합니다.

```text
Langflow File/Upload 컴포넌트
-> 업로드 이미지 변환 노드
-> base64 data URI가 들어간 payload
-> 캐릭터 자산 로더 또는 카드뉴스 요청 payload
-> HTML renderer
```

## 1. 반복 사용 캐릭터 자산 업로드

하냥이/하댕이 AI 포즈팩처럼 여러 달 반복 사용할 이미지는 `10 업로드 캐릭터 이미지 자산 등록` 노드로 등록합니다.

Langflow 기본 컴포넌트는 버전에 따라 이름이 조금 다를 수 있습니다.
이미지 업로드는 우선 `Chat Input`의 파일/이미지 첨부를 사용하거나, 서버의 파일 관리 화면 `My Files` 또는 `/files`에 이미지를 업로드한 뒤 해당 파일 path/base64를 넘기는 방식을 권장합니다.
`Read File`은 주로 문서/텍스트 계열 파일을 파싱하는 컴포넌트라 PNG/JPEG/WebP를 직접 읽지 못할 수 있습니다.
이 Flow에서는 이미지 첨부 Message, File 출력, file path, data URI, 순수 base64 중 하나를 `10 업로드 캐릭터 이미지 자산 등록`의 `업로드 이미지/File 출력` 입력에 연결하면 됩니다.

권장 연결:

| 순서 | From | Output | To | Input |
| --- | --- | --- | --- | --- |
| 1 | Langflow File/Upload | File 또는 Data 출력 | 10 업로드 캐릭터 이미지 자산 등록 | 업로드 이미지/File 출력 |
| 2 | 02 카드뉴스 브리프 정리 | 카드뉴스 브리프 | 10 업로드 캐릭터 이미지 자산 등록 | 기존 payload |
| 3 | 10 업로드 캐릭터 이미지 자산 등록 | 자산 등록 payload | 03 캐릭터 자산 불러오기 | 카드뉴스 브리프 |

`10 업로드 캐릭터 이미지 자산 등록`에서 입력할 값:

| 입력 | 예시 |
| --- | --- |
| `asset_id` | `hayangi_ai_hello` |
| `캐릭터 키` | `hayangi`, `hadaengi`, `duo` |
| `표시 이름` | `하냥이 AI 인사 포즈` |
| `AI 맥락` | `cover_intro`, `security_notice`, `prompt_tip`, `cta` |
| `권장 slide 역할` | `cover,intro` |
| `권장 layout` | `cover_character,character_speech` |
| `배치 후보` | `bottom_right,center` |
| `애니메이션 후보` | `float_in,fade_up` |

이 노드는 업로드된 PNG/JPEG/WebP를 base64 data URI로 변환해서 `character_assets.assets[]`에 넣습니다.
LLM에는 base64 원문이 아니라 `asset_id`, `pose`, `recommended_slide_roles` 같은 요약만 전달됩니다.

`03 캐릭터 자산 불러오기`의 `캐릭터 자산 JSON` 입력은 직접 manifest JSON을 붙여넣는 대체 경로입니다.
업로드 방식에서는 이 입력에 연결하지 않고, `10 업로드 캐릭터 이미지 자산 등록`의 `자산 등록 payload`를 `03 캐릭터 자산 불러오기`의 `카드뉴스 브리프/계획` 입력으로 연결합니다.

## 2. 특정 페이지 이미지 대체 업로드

디자인팀이 만든 완성 이미지를 특정 페이지에 그대로 넣고 싶으면 `11 페이지 이미지 대체 업로드` 노드를 사용합니다.

권장 연결:

| 순서 | From | Output | To | Input |
| --- | --- | --- | --- | --- |
| 1 | 00 카드뉴스 요청 입력 | 카드뉴스 요청 | 11 페이지 이미지 대체 업로드 | 카드뉴스 요청 payload |
| 2 | Langflow File/Upload | File 또는 Data 출력 | 11 페이지 이미지 대체 업로드 | 업로드 이미지/File 출력 |
| 3 | 11 페이지 이미지 대체 업로드 | 이미지 대체 payload | 01 카드뉴스 브리프 프롬프트 변수 준비 | 카드뉴스 요청 |
| 4 | 11 페이지 이미지 대체 업로드 | 이미지 대체 payload | 02 카드뉴스 브리프 정리 | 카드뉴스 요청 |

`11 페이지 이미지 대체 업로드`에서 입력할 값:

| 입력 | 예시 |
| --- | --- |
| `대체할 페이지 번호` | `3` |
| `대체 텍스트` | `AI 활용 우수 사례 소개 이미지` |
| `이미지 맞춤` | `contain`, `cover`, `fill` |
| `배경색` | `#FFFDF7` |

이렇게 등록된 페이지는 최종 plan에서 `role=image`가 됩니다.
해당 slide의 `headline`, `body`, `bullets`, `buttons`, `character`는 비워지고, 업로드 이미지만 카드 영역에 맞춰 표시됩니다.

## 3. 업로드 입력 형태

두 업로드 노드는 Langflow 버전별 File 출력 차이를 흡수하기 위해 아래 형태를 모두 시도합니다.

- `Data.data.path`
- `Data.data.file_path`
- `Data.data.filepath`
- `Data.data.data_uri`
- `Data.data.base64`
- `Data.data.content`
- 순수 `data:image/png;base64,...` 문자열
- 서버 파일 경로 문자열

운영에서는 사용자가 임의 경로를 직접 넣는 방식보다 Langflow File/Upload 컴포넌트를 통해 서버에 업로드된 파일 출력을 연결하는 방식을 권장합니다.

## 4. 용량과 보안 기준

- 캐릭터 자산 기본 최대 크기: 2MB
- 페이지 대체 이미지 기본 최대 크기: 4MB
- 허용 포맷: PNG, JPEG, WebP
- 최종 HTML은 외부 이미지 URL을 참조하지 않고 data URI만 사용합니다.
- public 저장소에는 실제 하냥이/하댕이 base64를 커밋하지 않습니다.
- 장기 운영 자산은 Langflow Global Variables, private DB, 사내 object storage, 또는 배포 시 주입되는 manifest로 관리합니다.

## 5. 운영 권장안

반복 캐릭터 포즈팩은 매 실행마다 업로드하지 않는 편이 좋습니다.
운영자가 승인된 이미지를 한 번 등록해 manifest로 관리하고, 일반 카드뉴스 생성 Flow는 그 manifest를 읽어 `asset_id`만 선택하게 두는 구성이 안정적입니다.

월별로 바뀌는 완성 이미지 페이지는 `11 페이지 이미지 대체 업로드`로 매 실행마다 넣어도 괜찮습니다.
