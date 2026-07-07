# Generated Character Assets

이 폴더는 카드뉴스 Flow 검증용으로 생성한 오리지널 AI 마스코트 PNG 자산입니다.
공식 하냥이/하댕이 이미지를 복제한 것이 아니며, 실제 사내 배포 전에는 브랜드/저작권 승인이 필요합니다.

## PNG Assets

| asset_id | file | 권장 용도 |
| --- | --- | --- |
| `hayangi_ai_hello` | `png/hayangi_ai_hello.png` | cover, intro |
| `hayangi_security_shield` | `png/hayangi_security_shield.png` | security, caution |
| `hadaengi_ai_helper` | `png/hadaengi_ai_helper.png` | case, workflow |
| `hadaengi_cta_point` | `png/hadaengi_cta_point.png` | cta, closing |
| `duo_ai_team` | `png/duo_ai_team.png` | cover, recap, closing |

## Manifest

`generated_character_assets.local.json`에는 위 PNG를 base64 data URI로 변환한 manifest가 들어 있습니다.
Langflow에서 업로드 노드를 거치지 않고 바로 테스트하려면 `03 캐릭터 자산 불러오기`의 `캐릭터 자산 JSON` 입력에 이 JSON 내용을 붙여넣으면 됩니다.

업로드 흐름을 테스트하려면 개별 PNG 파일을 Langflow에 업로드한 뒤 `10 업로드 캐릭터 이미지 자산 등록` 노드에 연결하세요.
