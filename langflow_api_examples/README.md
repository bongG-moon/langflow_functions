# Langflow API 호출 예시

이 폴더는 Langflow Flow를 외부 Python 코드에서 호출하는 기본 예시를 모아둔 곳입니다.

## 파일 구성

```text
langflow_api_examples/
├─ README.md
├─ COMPONENT_ID_AND_TWEAKS_GUIDE.md
├─ requirements.txt
├─ .env.example
├─ run_flow_basic.py
├─ run_flow_with_tweaks.py
└─ payload_templates/
   ├─ basic_chat_payload.json
   ├─ multi_text_input_tweaks_payload.json
   └─ business_agent_design_tweaks_payload.json
```

## 1. 기본 실행 준비

```powershell
cd C:\Users\qkekt\Desktop\기능flow\langflow_api_examples
python -m pip install -r requirements.txt
```

`.env.example`을 참고해서 실행 환경에 값을 넣습니다.

```powershell
$env:LANGFLOW_API_KEY="발급받은_API_KEY"
$env:LANGFLOW_BASE_URL="http://localhost:7860"
$env:LANGFLOW_FLOW_ID="실행할_FLOW_ID"
```

Flow ID는 Langflow 화면의 API Access/Share/API 호출 예시 또는 브라우저 URL에서 확인할 수 있습니다.

## 2. 기본 Chat Input 호출

Flow가 일반 `Chat Input` 하나를 받아 실행되는 구조라면 아래처럼 호출합니다.

```powershell
python run_flow_basic.py --input "hello world!"
```

기본 실행 결과는 Langflow 응답 JSON 전체가 아니라 Chat Output의 최종 메시지만 출력합니다.

```text
hello world!
```

응답 구조를 디버깅해야 해서 원본 JSON 전체를 보고 싶으면 `--raw-json` 옵션을 붙입니다.

```powershell
python run_flow_basic.py --input "hello world!" --raw-json
```

핵심 payload는 아래 형태입니다.

```json
{
  "output_type": "chat",
  "input_type": "chat",
  "input_value": "hello world!",
  "session_id": "자동 생성 UUID"
}
```

## 3. 여러 Text Input 값을 넘기는 방법

Langflow에서 Text Input 또는 Custom Component 입력칸이 여러 개인 경우에는 `tweaks`를 사용합니다.

컴포넌트 ID와 입력 필드명을 찾는 방법은 [COMPONENT_ID_AND_TWEAKS_GUIDE.md](./COMPONENT_ID_AND_TWEAKS_GUIDE.md)에 자세히 정리했습니다.

```json
{
  "input_type": "chat",
  "output_type": "chat",
  "input_value": "",
  "tweaks": {
    "TextInput-abc12": {
      "input_value": "첫 번째 입력값"
    },
    "TextInput-def34": {
      "input_value": "두 번째 입력값"
    },
    "BusinessWorkInputLoader-xyz99": {
      "work_description": "사용자가 입력한 업무 설명"
    }
  }
}
```

중요한 점:

- `TextInput-abc12` 같은 값은 Langflow 캔버스의 **컴포넌트 ID**입니다.
- 일반 Text Input 컴포넌트의 필드명은 보통 `input_value`입니다.
- 커스텀 컴포넌트는 코드에서 정의한 입력 `name`을 사용합니다. 예를 들어 `00 업무 설명 입력`은 `work_description`입니다.
- 컴포넌트 ID는 Flow의 API Access 패널에서 `Input Schema`를 열면 가장 안전하게 확인할 수 있습니다.

`run_flow_with_tweaks.py`는 JSON 파일을 따로 읽지 않고, 파일 상단의 `TWEAKS` 변수를 직접 수정해서 사용합니다.

```python
TWEAKS = {
    "TextInput-abc12": {
        "input_value": "첫 번째 입력값"
    },
    "TextInput-def34": {
        "input_value": "두 번째 입력값"
    }
}
```

수정 후 아래처럼 실행합니다.

```powershell
python run_flow_with_tweaks.py
```

이 스크립트도 기본 실행 결과는 최종 메시지만 출력합니다. 전체 Langflow 응답 JSON이 필요하면 `--raw-json`을 붙입니다.

```powershell
python run_flow_with_tweaks.py --raw-json
```

## 4. 업무 AI 에이전트 설계 Flow 호출 예시

`business_agent_design_flow`처럼 커스텀 컴포넌트 입력값을 지정해야 하는 Flow도 `run_flow_with_tweaks.py`로 호출합니다.
`run_flow_with_tweaks.py` 파일 상단의 `TWEAKS`를 아래처럼 실제 Flow에 맞게 바꿔주세요.

```python
TWEAKS = {
    "BusinessWorkInputLoader-abc12": {
        "work_description": "매일 아침 생산 데이터를 확인하고 위험 설비를 정리합니다."
    }
}
```

```powershell
python run_flow_with_tweaks.py
```

전체 응답 JSON이 필요하면 `--raw-json`을 붙입니다.

```powershell
python run_flow_with_tweaks.py --raw-json
```

이 경우 payload 안에는 아래처럼 들어갑니다.

```json
{
  "input_value": "",
  "input_type": "chat",
  "output_type": "chat",
  "tweaks": {
    "BusinessWorkInputLoader-abc12": {
      "work_description": "매일 아침 생산 데이터를 확인하고 위험 설비를 정리합니다."
    }
  }
}
```

## 5. 참고

- Langflow 공식 문서에 따르면 `/api/v1/run/{FLOW_ID}` endpoint는 Flow ID 또는 Flow 이름으로 Flow를 실행할 수 있습니다.
- API Key는 보통 `x-api-key` header로 전달합니다.
- `tweaks`는 Flow의 컴포넌트 값을 한 번의 실행 동안만 임시로 바꾸는 방식입니다.
- Langflow 화면의 API Access 패널에서 자동 생성되는 Python/cURL 예시와 Input Schema를 먼저 확인하면 컴포넌트 ID를 가장 정확하게 알 수 있습니다.
