# AI 에이전트 설계 결과 출력 스키마

`04 AI 에이전트 설계 결과 정리` 노드는 최종 payload 안에 `agent_design` 객체를 만듭니다.

## 최상위 구조

```json
{
  "agent_design": {
    "title": "업무 AI 에이전트 설계 제목",
    "executive_summary": [],
    "process_logic": {},
    "agent_opportunities": [],
    "recommended_flow_architecture": {},
    "required_information": {},
    "beginner_build_plan": [],
    "user_friendly_view": {},
    "reference_information": [],
    "warnings": []
  },
  "agent_design_meta": {
    "source": "llm | deterministic_fallback",
    "warnings": [],
    "llm_text_preview": ""
  }
}
```

## process_logic

업무 프로세스 로직입니다.

```json
{
  "trigger": "업무 시작 조건",
  "main_inputs": ["입력 데이터/시스템/사람 입력"],
  "main_outputs": ["산출물"],
  "steps": [
    {
      "step_no": 1,
      "step_name": "단계명",
      "actor": "human | llm | tool | system | reviewer",
      "input": "이 단계의 입력",
      "action": "수행 작업",
      "output": "이 단계의 출력",
      "decision": "판단 기준 또는 조건",
      "automation_level": "manual | assist | semi_auto | auto"
    }
  ],
  "decision_points": ["조건/판단 기준"],
  "human_checkpoints": ["사람 검토/승인 구간"]
}
```

## agent_opportunities

AI 에이전트로 개선할 수 있는 영역입니다.

```json
{
  "area": "개선 영역",
  "current_pain": "현재 불편함",
  "agent_idea": "AI 에이전트가 도울 방식",
  "expected_impact": "기대 효과",
  "suggested_capabilities": ["카탈로그 기능 ID"],
  "difficulty": "초급 | 중급 | 고급",
  "guardrail": "보안/검토/승인 주의사항"
}
```

## recommended_flow_architecture

초보 Langflow 개발자가 따라 만들 수 있는 노드 구조입니다.

```json
{
  "flow_summary": "권장 Langflow 구조 한 줄 요약",
  "nodes": [
    {
      "order": 1,
      "node_name": "노드명",
      "role": "노드 역할",
      "input": "연결할 입력",
      "output": "다음 노드로 넘길 출력",
      "beginner_tip": "초보자 팁"
    }
  ],
  "reuse_existing_flows": [
    {
      "flow_name": "reusable_data_flow | html_report_flow",
      "where_to_use": "어느 단계에서 쓰는지",
      "why": "왜 필요한지"
    }
  ]
}
```

## required_information

구현 전에 더 필요한 정보입니다.

```json
{
  "must_have": ["반드시 필요한 정보"],
  "nice_to_have": ["있으면 좋은 정보"],
  "missing_information": ["사용자에게 물어볼 질문"]
}
```

## user_friendly_view

`05 사용자용 설계서 출력`이 보기 좋은 Markdown을 만들 때 우선 사용하는 구조입니다.

```json
{
  "card_sections": [
    {
      "title": "카드 제목",
      "body": "짧은 설명",
      "tone": "info | success | warning | danger | neutral"
    }
  ],
  "process_table": [
    {
      "step": "단계",
      "human_work": "사람 업무",
      "agent_support": "AI 에이전트 지원",
      "output": "산출물"
    }
  ],
  "roadmap": [
    {
      "phase": "1단계",
      "goal": "목표",
      "deliverable": "산출물"
    }
  ]
}
```

## reference_information

참고한 Langflow 기능이나 공식 문서 정보를 한글 설명과 링크로 보여주는 구조입니다.

```json
{
  "title": "프롬프트 템플릿 컴포넌트",
  "description": "프롬프트 본문에 변수를 연결해 LLM 입력을 표준화할 때 사용합니다.",
  "used_for": "03 프롬프트 준비 노드가 업무 요청, 기능 카탈로그, 출력 스키마를 하나의 LLM 프롬프트로 만들 때 참고했습니다.",
  "source_link": "https://docs.langflow.org/components-prompts"
}
```
