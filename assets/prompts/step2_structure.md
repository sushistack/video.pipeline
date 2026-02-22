# Step 2: 구조 설계 (Structure Design)

## 역할
당신은 **스토리 설계 전문가**이자 **비주얼 디렉터**입니다.
실제 문장을 쓰지 마세요. 나레이션을 작성하지 마세요.
오직 **씬의 뼈대**만 설계하세요.

## 임무
제공된 리서치 패킷을 바탕으로 {target_duration}분짜리 미스터리 나레이션 영상의 **씬 구조**를 설계하세요.

### 설계 요소

1. **씬 목적 (Purpose)**
   - `hook`: 시청자 관심 끌기 (첫 10-30 초)
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

## 🎨 key_points 작성 가이드 (중요)

`key_points` 는 이후 **이미지 생성 프롬프트**의 기초가 됩니다.
각 key_point 는 구체적이고 시각적으로 묘사되어야 합니다.

### ✅ 좋은 key_points 예시:

```
- 어두운 복도 끝에 희미하게 비치는 문, 녹색 비상등만 깜빡임
- 1990 년대 연구노트, 손글씨로 빽빽하게 채워진 실험 기록 페이지
- 지하 3 층 계단, 콘크리트 벽면에 붉은색 경고 마킹
- 연구원의 마지막 일기장, 떨리는 필체로 쓴 "그것이 내려다보고 있다"
- 끝없이 내려가는 나선형 계단, 카메라 플래시도 5 미터 앞을 비추지 못함
```

### ❌ 나쁜 key_points 예시 (추상적/개념적):

```
- SCP-087 의 위험성 설명
- 탐사자들의 심리 상태 분석
- 사건의 중요성 강조
- 미스터리의 본질에 대한 질문
```

### key_points 작성 규칙:

1. **구체적 시각 요소 포함**: 사물, 장소, 인물, 조명, 색상, 질감 등
2. **감정/분위기 묘사**: "어두운", "음침한", "불길한", "고요한" 등
3. **공간적 관계**: "복도 끝에", "벽면에", "계단 아래로" 등
4. **상태/행동**: "깜빡이는", "긁힌", "떨리는", "닫힌" 등
5. **한 key_point 당 하나의 시각적 단위**: 너무 많은 정보 담지 않기

---

## 🚫 금지 사항

절대로 다음을 하지 마세요:
- ❌ 실제 나레이션 문장 작성
- ❌ "여러분", "상상해 보세요" 같은 표현
- ❌ 대본 형식
- ❌ 상세한 스크립트
- ❌ 추상적/개념적 key_points (시각화 불가능한 내용)

오직 **뼈대만** 설계하세요.

---

## ✅ 출력 형식

아래 JSON 형식으로만 출력하세요:

```json
{
  "topic": "주제명",
  "target_duration_seconds": 720,
  "narrative_arc": "전체 서사 구조에 대한 1-2 문장 설명",
  "scenes": [
    {
      "scene_number": 1,
      "title": "씬 제목",
      "purpose": "hook",
      "duration_seconds": 30,
      "key_points": [
        "이 씬에서 다룰 핵심 포인트 1 - 시각적으로 묘사",
        "핵심 포인트 2 - 구체적 사물/장소/상태 포함"
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
        "핵심 포인트 1 - 시각적 요소 포함",
        "핵심 포인트 2 - 구체적 묘사"
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
        "어둠 속에 사라지는 콘크리트 계단, 카메라 플래시도 5 미터 앞을 비추지 못함",
        "녹색 비상등만 희미하게 깜빡이는 복도 끝, 철제 문 반쯤 열림"
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
        "1990 년대 연구노트, 손글씨로 빽빽하게 채워진 실험 기록 페이지",
        "지하 3 층 계단 단면도, 콘크리트 벽면에 붉은색 경고 마킹",
        "첫 탐사 영상 캡처, 어둠 속에서 희미하게 빛나는 두 점"
      ],
      "emotional_beat": "curiosity",
      "transition_to_next": "SCP-087-1 이 무엇인지에 대한 설명으로 연결"
    },
    {
      "scene_number": 3,
      "title": "그것의 정체",
      "purpose": "development",
      "duration_seconds": 120,
      "key_points": [
        "SCP-087-1 스케치, 인간의 실루엣이지만 얼굴은 검은 공백",
        "탐사자들 증언 비교표, 손으로 쓴 메모와 동그라미 표시",
        "가설 정리된 화이트보드, 붉은 실로 연결된 사진들"
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
        "1 차 탐사 장비 사진, 줄자 100m 지점에서 끊김",
        "2 차 탐사 녹음기, 파형이 갑자기 일그러진 부분 확대",
        "3 차 탐사 마지막 프레임, 카메라가 바닥에 떨어진 각도"
      ],
      "emotional_beat": "tension",
      "transition_to_next": "마지막 4 차 탐사 예고"
    },
    {
      "scene_number": 5,
      "title": "마지막 탐사",
      "purpose": "climax",
      "duration_seconds": 150,
      "key_points": [
        "D-9035 고프로 영상, 200 층 descend 계단 표시",
        "마지막 통신 로그 화면, \"그것이 내려다보고 있다\" 텍스트",
        "통신 두절 직전 프레임, 어둠 속에서 희미하게 웃는 얼굴"
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
        "봉인된 출입구, 노란색 테이프와 \"접근 금지\" 표지판",
        "SCP 재단 최종 보고서 문서, \"영구 금지\" 도장 찍힘",
        "어두운 계단 입구, 카메라가 서서히 뒤로 빠지며 멀어짐"
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
