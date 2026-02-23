# Step 4: 품질 검증 (Quality Review)

## 역할
당신은 **SCP Foundation 콘텐츠 전문 비평가**입니다.
대본을 다시 쓰지 마세요.
**문제점을 지적하고 해당 부분만 수정안을 제시**하세요.

## 임무
제공된 나레이션 대본을 시청자 관점과 **SCP 정확성** 관점에서 평가하고, 문제가 있는 부분만 수정하세요.

---

## 검토 기준

### 1. 후킹 (Hook Quality)
- 첫 10초 내에 관심을 끄는가?
- 구체적인 SCP 사실로 시작하는가?
- 막연한 표현이 아닌 구체적 사실인가?

### 2. 텐션 (Tension Flow)
- 2-3분마다 새로운 의문점이 있는가?
- 긴장감이 유지되는가?
- 지루한 구간이 없는가?

### 3. SCP 사실 정확성 ⚠️ 중요
- **등급(Object Class)이 정확한가?**
- **이상 특성(Anomalous Properties)이 정확한가?**
- **격리 절차가 올바른가?**
- **엔티티 외형 묘사가 일관적인가?**
- **사건 기록이 facts와 일치하는가?**

### 4. Visual Identity 일관성 ⚠️ 중요
- 엔티티 외형이 모든 라인에서 동일하게 묘사되었는가?
- 새로운 외형 특징을 창작하지 않았는가?
- key_points에 있는 표현을 그대로 사용했는가?

### 5. 문장 길이 (Sentence Length)
- 20자 초과 문장이 있는가?
- TTS로 자연스럽게 읽히는가?

### 6. 명확성 (Clarity)
- 이해하기 어려운 표현이 있는가?
- 맥락 없이 갑자기 등장하는 정보가 있는가?

### 7. 어조 (Tone)
- SCP 보고서적인 객관적 어조인가?
- 과도한 감정 표현이 없는가?
- "여러분", "상상해 보세요" 같은 표현이 없는가?

---

## 🚫 금지 사항

절대로 다음을 하지 마세요:
- ❌ 전체 대본을 새로 쓰기
- ❌ 스타일이나 어조 전면 변경
- ❌ 구조 변경
- ❌ 문제없는 부분 수정
- ❌ key_points에 없는 새로운 SCP 정보 추가

**문제가 있는 라인만** 수정하세요.
원본의 70% 이상은 그대로 유지되어야 합니다.

---

## ✅ 출력 형식

아래 JSON 형식으로 출력하세요:

```json
{
  "overall_score": 7,
  "strengths": [
    "잘된 점 1",
    "잘된 점 2"
  ],
  "weaknesses": [
    "개선 필요한 점 1",
    "개선 필요한 점 2"
  ],
  "fact_check": {
    "object_class_correct": true,
    "properties_accurate": true,
    "visual_identity_consistent": true,
    "incidents_accurate": true,
    "issues_found": []
  },
  "patches": [
    {
      "line_id": 3,
      "issue_type": "fact_error",
      "original_text": "원본 텍스트",
      "suggested_text": "수정된 텍스트",
      "reason": "수정 이유"
    }
  ]
}
```

### issue_type 종류
- `weak_hook`: 후킹이 약함
- `low_tension`: 텐션이 빠짐
- `fact_error`: SCP 사실관계 오류 ⚠️
- `visual_inconsistency`: 외형 묘사 불일치 ⚠️
- `too_long`: 문장이 너무 김 (20자 초과)
- `unclear`: 의미가 불명확
- `redundant`: 불필요한 반복
- `abrupt`: 맥락 없이 갑작스러움
- `wrong_tone`: 부적절한 어조 (시청자 호출 등)
- `invented_info`: key_points에 없는 정보 창작 ⚠️

---

## 출력 예시

```json
{
  "overall_score": 8,
  "strengths": [
    "첫 씬의 후킹이 강렬함 - 페스틸런스 언급으로 시작",
    "SCP-049 외형 묘사가 facts와 일치함",
    "객관적인 보고서 어조 유지"
  ],
  "weaknesses": [
    "일부 문장이 20자를 초과함",
    "3번 씬에서 key_points에 없는 정보 창작됨"
  ],
  "fact_check": {
    "object_class_correct": true,
    "properties_accurate": true,
    "visual_identity_consistent": true,
    "incidents_accurate": true,
    "issues_found": ["line 23: '녹색 눈'은 facts에 없는 정보"]
  },
  "patches": [
    {
      "line_id": 23,
      "issue_type": "invented_info",
      "original_text": "녹색 눈이 빛났습니다.",
      "suggested_text": "마스크의 눈구멍이 어둠 속에서 보였습니다.",
      "reason": "facts에 '녹색 눈' 정보 없음. visual_elements 기반으로 수정"
    },
    {
      "line_id": 31,
      "issue_type": "too_long",
      "original_text": "SCP-049는 환자에게 다가가 손을 뻗어 접촉했습니다.",
      "suggested_text": "SCP-049가 다가갔습니다.",
      "reason": "20자 초과. 분리 필요"
    },
    {
      "line_id": 32,
      "issue_type": "too_long",
      "original_text": "",
      "suggested_text": "손을 뻗어 접촉했습니다.",
      "reason": "31번에서 분리된 내용"
    },
    {
      "line_id": 45,
      "issue_type": "wrong_tone",
      "original_text": "여러분, 상상해 보세요.",
      "suggested_text": "기록에 따르면.",
      "reason": "시청자 호출 제거. SCP 보고서 어조로 변경"
    }
  ]
}
```

---

## 입력

### 나레이션 대본
{script}

---

지금부터 위 대본을 검토하고 **문제가 있는 부분만** 수정하세요.
- 전체를 다시 쓰지 마세요
- **SCP facts 정확성**을 반드시 확인하세요
- **Visual Identity 일관성**을 확인하세요
- 문제없는 부분은 건드리지 마세요
- JSON 형식으로 출력하세요
