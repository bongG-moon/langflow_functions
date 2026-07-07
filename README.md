# Langflow Functions

Langflow에서 체험하거나 재사용할 수 있는 기능 flow 모음입니다.

현재 포함된 flow:

- `html_report_flow`: CSV/JSON 데이터와 사용자 질문을 기반으로 HTML 분석 리포트를 생성하는 Langflow 컴포넌트 세트
- `reusable_data_flow`: 여러 데이터 소스 조회 결과를 표준 payload로 정리하고 HTML 리포트 flow와 연결할 수 있는 재사용 데이터 조회 컴포넌트 세트
- `business_agent_design_flow`: 자연어 업무 설명을 업무 프로세스 로직과 AI 에이전트 구현 아이디어로 정리하는 초보 Langflow 개발자용 설계 flow
- `card_news_flow`: 입력 내용을 월간 카드뉴스로 구조화하고, 고정 캐릭터 base64 이미지 자산과 CSS 애니메이션/페이지 이동을 포함한 HTML 카드뉴스를 생성하는 설계 flow

저장소에는 소스 코드, 문서, 샘플 입력 데이터, 샘플 카탈로그, 로컬 Report API 서버 코드만 포함합니다.
로컬 실행 중 생성되는 HTML 공유 파일, 테스트 출력물, 압축 파일, 캐시, 환경 파일은 `.gitignore`로 제외했습니다.
