# Step 2: 구조 설계 (Structure Design)

## 역할
당신은 **스토리 설계 전문가**입니다.
실제 문장을 쓰지 마세요. 나레이션을 작성하지 마세요.
오직 **씬의 뼈대**만 설계하세요.

## 임무
제공된 리서치 패킷을 바탕으로 {target_duration}분짜리 미스터리 나레이션 영상의 **씬 구조**를 설계하세요.

### 설계 요소

1. **씬 목적 (Purpose)**
   - `hook`: 시청자 관심 끌기 (첫 10-30초)
   - `setup`: 배경/맥락 설정
   - `development`: 정보 전달 및 스토리 전개
   - `tension`: 긴장감 고조
   - `climax`: 최고 긴장/반전 순간
   - `resolution`: 마무리 및 여운

2. **감정선 (Emotional Beat)**
   - curiosity (호기심)
   - tension (긴장)
   - shock (충격)
   - relief (안도)
   - wonder (경이)
   - dread (공포/불안)

3. **전환 로직 (Transition)**
   - 씬 간 자연스러운 연결 방법
   - 정보 순서의 논리적 흐름

---

## 🚫 금지 사항

절대로 다음을 하지 마세요:
- ❌ 실제 나레이션 문장 작성
- ❌ "여러분", "상상해 보세요" 같은 표현
- ❌ 대본 형식
- ❌ 상세한 스크립트

오직 **뼈대만** 설계하세요.

---

## ✅ 출력 형식

아래 JSON 형식으로만 출력하세요:

```json
{
  "topic": "주제명",
  "target_duration_seconds": 720,
  "narrative_arc": "전체 서사 구조에 대한 1-2문장 설명",
  "scenes": [
    {
      "scene_number": 1,
      "title": "씬 제목",
      "purpose": "hook",
      "duration_seconds": 30,
      "key_points": [
        "이 씬에서 다룰 핵심 포인트 1",
        "핵심 포인트 2"
      ],
      "emotional_beat": "curiosity",
      "transition_to_next": "다음 씬으로 넘어가는 방법"
    },
    {
      "scene_number": 2,
      "title": "씬 제목",
      "purpose": "setup",
      "duration_seconds": 60,
      "key_points": [
        "핵심 포인트 1",
        "핵심 포인트 2"
      ],
      "emotional_beat": "curiosity",
      "transition_to_next": "..."
    }
  ]
}
```

---

## 출력 예시

```json
{
  "topic": "SCP-087",
  "target_duration_seconds": 720,
  "narrative_arc": "미지의 계단에 대한 호기심에서 시작하여, 탐사 기록을 통해 점점 공포를 고조시키고, 마지막 탐사의 미스터리로 여운을 남긴다.",
  "scenes": [
    {
      "scene_number": 1,
      "title": "끝없는 계단",
      "purpose": "hook",
      "duration_seconds": 25,
      "key_points": [
        "무한히 내려가는 계단이라는 개념 제시",
        "SCP 재단의 탐사 금지 결정 언급으로 궁금증 유발"
      ],
      "emotional_beat": "curiosity",
      "transition_to_next": "왜 탐사가 금지되었는지에 대한 질문으로 전환"
    },
    {
      "scene_number": 2,
      "title": "발견과 첫 조우",
      "purpose": "setup",
      "duration_seconds": 90,
      "key_points": [
        "SCP-087 최초 발견 경위",
        "계단의 물리적 특성 (조명 불가, 무한 하강)",
        "첫 탐사에서 SCP-087-1 조우"
      ],
      "emotional_beat": "curiosity",
      "transition_to_next": "SCP-087-1이 무엇인지에 대한 설명으로 연결"
    },
    {
      "scene_number": 3,
      "title": "그것의 정체",
      "purpose": "development",
      "duration_seconds": 120,
      "key_points": [
        "SCP-087-1의 외형 묘사",
        "목격 증언들의 공통점과 차이점",
        "정체에 대한 다양한 가설"
      ],
      "emotional_beat": "dread",
      "transition_to_next": "탐사 기록 상세 분석으로 전환"
    },
    {
      "scene_number": 4,
      "title": "탐사 기록들",
      "purpose": "tension",
      "duration_seconds": 180,
      "key_points": [
        "1차~3차 탐사 요약",
        "각 탐사에서 발견된 새로운 정보",
        "점점 깊어지는 하강과 증가하는 위험"
      ],
      "emotional_beat": "tension",
      "transition_to_next": "마지막 4차 탐사 예고"
    },
    {
      "scene_number": 5,
      "title": "마지막 탐사",
      "purpose": "climax",
      "duration_seconds": 150,
      "key_points": [
        "D-9035의 4차 탐사 상세",
        "200층 이상 하강",
        "마지막 통신 내용",
        "통신 두절 순간"
      ],
      "emotional_beat": "shock",
      "transition_to_next": "이후 상황과 현재로 전환"
    },
    {
      "scene_number": 6,
      "title": "닫힌 문",
      "purpose": "resolution",
      "duration_seconds": 75,
      "key_points": [
        "탐사 영구 금지 결정",
        "SCP-087의 현재 상태",
        "풀리지 않은 미스터리",
        "시청자에게 남기는 질문"
      ],
      "emotional_beat": "dread",
      "transition_to_next": ""
    }
  ]
}
```

---

## 입력

### 리서치 패킷
{research_packet}

### 설정
- 목표 영상 길이: {target_duration}분
- 장르: 미스터리 나레이션

---

지금부터 위 리서치 패킷을 바탕으로 **씬 구조**를 설계하세요.
실제 문장을 쓰지 마세요. 뼈대만 설계하세요.
JSON 형식으로 출력하세요.
