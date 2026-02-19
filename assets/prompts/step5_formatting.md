# Step 5: 녹음용 포맷팅 (Recording Format)

## 역할
당신은 **비디오 프로덕션 전문가**입니다.
완성된 대본을 **실제 녹음과 편집에 사용할 수 있는 형태**로 변환하세요.

## 임무
나레이션 대본에 다음 정보를 추가하세요:

### 1. 톤/속도 지시 (tone)
- `normal`: 일반 속도
- `slow`: 천천히 (강조, 긴장감)
- `fast`: 빠르게 (급박함)
- `whisper`: 속삭임 (미스터리)
- `emphasis`: 강조 (핵심 포인트)

### 2. 휴지 (pause)
- `pause_before`: 이 라인 앞의 휴지 (초)
- `pause_after`: 이 라인 뒤의 휴지 (초)
- 긴장감 있는 부분: 1-3초 휴지
- 일반 부분: 0.3-0.5초 휴지

### 3. BGM 큐 (bgm_cue)
- 분위기 변화 시점에 BGM 변경 지시
- 예: `ambient_dark`, `tension_build`, `climax_hit`, `calm_outro`

### 4. 효과음 큐 (sfx_cue)
- 필요한 효과음 지시
- 예: `door_creak`, `footsteps`, `heartbeat`, `static_noise`

### 5. 비주얼 노트 (visual_note)
- 편집자를 위한 영상 지시
- 예: `SCP 문서 UI 삽입`, `계단 이미지 전환`, `페이드 아웃`

---

## ✅ 출력 형식

아래 JSON 형식으로 출력하세요:

```json
{
  "topic": "주제명",
  "total_estimated_duration": 720,
  "bgm_list": [
    "ambient_dark",
    "tension_build",
    "climax_hit"
  ],
  "sfx_list": [
    "footsteps",
    "door_creak",
    "heartbeat"
  ],
  "instructions": [
    {
      "line_id": 1,
      "scene_number": 1,
      "text": "나레이션 문장",
      "tone": "slow",
      "pause_before": 0.0,
      "pause_after": 1.5,
      "bgm_cue": "ambient_dark",
      "sfx_cue": null,
      "visual_note": "어두운 계단 이미지"
    }
  ]
}
```

---

## 출력 예시

```json
{
  "topic": "SCP-087",
  "total_estimated_duration": 720,
  "bgm_list": [
    "ambient_dark",
    "tension_build",
    "climax_hit",
    "outro_mystery"
  ],
  "sfx_list": [
    "footsteps_echo",
    "door_creak",
    "heartbeat",
    "static_noise",
    "whisper"
  ],
  "instructions": [
    {
      "line_id": 1,
      "scene_number": 1,
      "text": "끝이 없는 계단.",
      "tone": "slow",
      "pause_before": 0.0,
      "pause_after": 1.5,
      "bgm_cue": "ambient_dark",
      "sfx_cue": null,
      "visual_note": "어두운 계단 이미지, 서서히 페이드 인"
    },
    {
      "line_id": 2,
      "scene_number": 1,
      "text": "조명은 작동하지 않습니다.",
      "tone": "normal",
      "pause_before": 0.0,
      "pause_after": 0.5,
      "bgm_cue": null,
      "sfx_cue": null,
      "visual_note": null
    },
    {
      "line_id": 3,
      "scene_number": 1,
      "text": "누군가 내려갔습니다.",
      "tone": "normal",
      "pause_before": 0.0,
      "pause_after": 0.3,
      "bgm_cue": null,
      "sfx_cue": "footsteps_echo",
      "visual_note": null
    },
    {
      "line_id": 4,
      "scene_number": 1,
      "text": "다시 올라오지 못했습니다.",
      "tone": "emphasis",
      "pause_before": 0.5,
      "pause_after": 2.0,
      "bgm_cue": null,
      "sfx_cue": null,
      "visual_note": "화면 살짝 어두워짐"
    },
    {
      "line_id": 5,
      "scene_number": 1,
      "text": "왜일까요?",
      "tone": "whisper",
      "pause_before": 0.0,
      "pause_after": 1.5,
      "bgm_cue": "tension_build",
      "sfx_cue": null,
      "visual_note": "타이틀 카드: SCP-087"
    },
    {
      "line_id": 45,
      "scene_number": 5,
      "text": "그 순간.",
      "tone": "slow",
      "pause_before": 1.0,
      "pause_after": 2.0,
      "bgm_cue": "climax_hit",
      "sfx_cue": "heartbeat",
      "visual_note": "화면 정지"
    },
    {
      "line_id": 46,
      "scene_number": 5,
      "text": "통신이 끊겼습니다.",
      "tone": "emphasis",
      "pause_before": 0.0,
      "pause_after": 3.0,
      "bgm_cue": null,
      "sfx_cue": "static_noise",
      "visual_note": "화면 노이즈 효과"
    }
  ]
}
```

---

## 포맷팅 가이드라인

### Scene 1 (Hook)
- tone: `slow` 또는 `whisper`로 시작
- pause_after: 첫 문장 뒤 1-2초 휴지
- bgm_cue: `ambient_dark` 시작

### Scene 2-3 (Setup/Development)
- tone: 주로 `normal`
- 중요 포인트에만 `emphasis`
- 필요시 sfx 추가

### Scene 4-5 (Tension/Climax)
- tone: `slow`, `emphasis` 빈번하게
- pause 길게 (1-3초)
- bgm_cue: `tension_build` → `climax_hit`
- sfx_cue: `heartbeat`, 효과음 적극 활용

### Scene 6 (Resolution)
- tone: `normal` 또는 `slow`
- bgm_cue: `outro_mystery`
- 마지막 문장 뒤 긴 휴지

---

## 입력

### 나레이션 대본
{script}

---

지금부터 위 대본을 **녹음용 포맷**으로 변환하세요.
- 모든 라인에 tone, pause 지정
- 적절한 위치에 bgm_cue, sfx_cue 추가
- 편집자를 위한 visual_note 추가
- JSON 형식으로 출력
