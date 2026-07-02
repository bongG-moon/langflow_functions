# Langflow 컴포넌트 ID와 tweaks 상세 가이드

이 문서는 API 호출 시 `TextInput-abc12`, `BusinessWorkInputLoader-xyz99` 같은 값이 무엇인지, 어디서 찾는지, payload에 어떻게 넣는지 설명합니다.

## 1. 컴포넌트 ID란?

Langflow 캔버스의 각 노드는 내부적으로 고유 ID를 가집니다.

예를 들어 화면에는 같은 `Text Input` 노드가 여러 개 있을 수 있습니다.

```text
Text Input
Text Input
Text Input
```

API에서는 이 노드들을 구분해야 하므로 내부 ID를 사용합니다.

```text
TextInput-a1B2c
TextInput-d3E4f
TextInput-g5H6i
```

문서의 `TextInput-abc12`, `BusinessWorkInputLoader-xyz99`는 이해를 돕기 위한 예시 ID입니다. 실제 API 호출에서는 본인 flow에 있는 실제 ID로 바꿔야 합니다.

## 2. 컴포넌트 ID 찾는 방법

가장 안전한 방법은 Langflow의 API Access 패널에서 확인하는 것입니다.

1. Langflow에서 실행할 Flow를 엽니다.
2. 화면의 `API Access`, `Share`, `Code`, 또는 비슷한 API 호출 메뉴를 엽니다.
3. Python 또는 cURL 예시 코드를 확인합니다.
4. `Input Schema` 또는 `Tweaks` 섹션을 엽니다.
5. `tweaks` 안에 나오는 키 값을 확인합니다.

예를 들어 API Access에 아래처럼 보이면:

```json
{
  "tweaks": {
    "BusinessWorkInputLoader-a1B2c": {
      "work_description": "..."
    }
  }
}
```

여기서 실제 컴포넌트 ID는 아래 값입니다.

```text
BusinessWorkInputLoader-a1B2c
```

Python 코드나 payload에서도 이 값을 그대로 써야 합니다.

## 3. tweaks란?

`tweaks`는 Flow를 실행할 때 특정 컴포넌트의 입력값을 임시로 바꾸는 API payload 항목입니다.

즉, Langflow 화면에 저장된 노드 설정을 영구적으로 바꾸는 것이 아니라, **이번 API 호출에서만** 값을 바꿉니다.

기본 구조는 아래와 같습니다.

```json
{
  "input_value": "",
  "input_type": "chat",
  "output_type": "chat",
  "tweaks": {
    "컴포넌트ID": {
      "입력필드명": "이번 실행에 넣을 값"
    }
  }
}
```

## 4. Text Input 값을 API로 넣는 예

Langflow에 `Text Input` 노드가 있고, API Access에서 ID가 `TextInput-a1B2c`로 확인되었다고 가정합니다.

이 경우 payload는 아래처럼 씁니다.

```json
{
  "input_value": "",
  "input_type": "chat",
  "output_type": "chat",
  "tweaks": {
    "TextInput-a1B2c": {
      "input_value": "여기에 Text Input으로 넣을 값을 작성합니다."
    }
  }
}
```

일반 Text Input은 대체로 필드명이 `input_value`입니다.

## 5. 여러 Text Input 값을 동시에 넣는 예

Text Input이 두 개라면 `tweaks` 안에 컴포넌트 ID를 두 개 넣습니다.

```json
{
  "input_value": "",
  "input_type": "chat",
  "output_type": "chat",
  "tweaks": {
    "TextInput-a1B2c": {
      "input_value": "첫 번째 입력값"
    },
    "TextInput-d3E4f": {
      "input_value": "두 번째 입력값"
    }
  }
}
```

포인트는 아래 두 가지입니다.

- `TextInput-a1B2c`, `TextInput-d3E4f`는 각 Text Input 노드의 실제 ID입니다.
- 두 노드 모두 필드명이 `input_value`일 수 있지만, 컴포넌트 ID가 다르기 때문에 서로 다른 노드에 값이 들어갑니다.

## 6. 커스텀 컴포넌트 값을 API로 넣는 예

커스텀 컴포넌트는 코드에서 정의한 input `name`을 필드명으로 사용합니다.

예를 들어 `00 업무 설명 입력` 컴포넌트 코드에는 아래 입력이 있습니다.

```python
MessageTextInput(
    name="work_description",
    display_name="업무 설명",
)
```

그러면 API payload에서는 `work_description`을 사용합니다.

```json
{
  "input_value": "",
  "input_type": "chat",
  "output_type": "chat",
  "tweaks": {
    "BusinessWorkInputLoader-a1B2c": {
      "work_description": "매일 아침 생산 데이터를 확인하고 위험 설비를 정리합니다."
    }
  }
}
```

여기서:

- `BusinessWorkInputLoader-a1B2c`: Langflow가 붙인 실제 컴포넌트 ID
- `work_description`: 커스텀 컴포넌트 코드의 input `name`
- 오른쪽 문자열: 이번 API 호출에서 넣을 업무 설명

## 7. 업무 AI 에이전트 설계 Flow 예시

업무 설계 Flow를 API로 호출할 때는 두 가지 방식이 있습니다.

### 방식 A. Chat Input으로 업무 설명 전달

Flow 앞단에 `Chat Input`이 있고, 그 값이 `00 업무 설명 입력`으로 연결되어 있다면 `input_value`에 업무 설명을 넣으면 됩니다.

```json
{
  "input_value": "매일 아침 생산 데이터를 확인하고 위험 설비를 정리합니다.",
  "input_type": "chat",
  "output_type": "chat"
}
```

이 방식은 가장 단순합니다.

### 방식 B. 00 업무 설명 입력 컴포넌트에 직접 전달

Flow가 Chat Input 없이 `00 업무 설명 입력` 컴포넌트 값을 직접 사용한다면 `tweaks`를 씁니다.

```json
{
  "input_value": "",
  "input_type": "chat",
  "output_type": "chat",
  "tweaks": {
    "BusinessWorkInputLoader-a1B2c": {
      "work_description": "매일 아침 생산 데이터를 확인하고 위험 설비를 정리합니다."
    }
  }
}
```

`BusinessWorkInputLoader-a1B2c`는 예시입니다. 반드시 본인 Flow의 API Access에서 실제 ID를 확인해 바꿔야 합니다.

## 8. 필드명 찾는 방법

필드명은 컴포넌트 종류에 따라 다릅니다.

| 컴포넌트 유형 | 보통 사용하는 필드명 | 예 |
| --- | --- | --- |
| Text Input | `input_value` | `"input_value": "텍스트"` |
| Chat Input | 보통 payload의 최상위 `input_value` | `"input_value": "질문"` |
| 커스텀 컴포넌트 | 코드의 input `name` | `"work_description": "업무 설명"` |
| Prompt Template | 템플릿 변수명 또는 API Access Input Schema 기준 | `"question": "질문"` |

가장 정확한 기준은 API Access의 `Input Schema`입니다.

## 9. 자주 나는 문제

### tweaks에 예시 ID를 그대로 넣은 경우

잘못된 예:

```json
{
  "tweaks": {
    "TextInput-abc12": {
      "input_value": "값"
    }
  }
}
```

`TextInput-abc12`가 실제 Flow에 없는 ID라면 값이 적용되지 않습니다.

해결:

- API Access에서 실제 ID를 확인합니다.
- 예시 ID를 실제 ID로 바꿉니다.

### 필드명을 잘못 넣은 경우

잘못된 예:

```json
{
  "tweaks": {
    "BusinessWorkInputLoader-a1B2c": {
      "input_value": "업무 설명"
    }
  }
}
```

`00 업무 설명 입력`은 필드명이 `input_value`가 아니라 `work_description`입니다.

올바른 예:

```json
{
  "tweaks": {
    "BusinessWorkInputLoader-a1B2c": {
      "work_description": "업무 설명"
    }
  }
}
```

### Chat Input과 tweaks를 혼동한 경우

Flow가 `Chat Input`을 시작점으로 사용한다면 보통 최상위 `input_value`에 넣는 것이 단순합니다.

Flow 안의 특정 컴포넌트 입력칸을 직접 바꿔야 할 때만 `tweaks`를 사용합니다.

## 10. 추천 확인 순서

1. 먼저 Langflow Playground에서 Flow가 정상 동작하는지 확인합니다.
2. API Access에서 Python 예시 코드를 복사합니다.
3. Input Schema에서 실제 컴포넌트 ID와 필드명을 확인합니다.
4. `payload_templates`의 예시 JSON에서 ID와 필드명만 실제 값으로 교체합니다.
5. `run_flow_with_tweaks.py`로 호출합니다.

```powershell
python run_flow_with_tweaks.py --tweaks-file payload_templates\multi_text_input_tweaks_payload.json
```
