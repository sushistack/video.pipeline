# 🎯 Extract 페이지 - Story-to-Script 기능 구현 완료

## 📋 구현 개요

기존 Extract 페이지를 수정하여 **2 개의 탭**으로 구성:
1. **STT 자막 추출** (기존 기능)
2. **📖 스토리 → 대본** (새로운 기능)

---

## 🚀 새로운 워크플로우

### 6 단계 자동화 파이프라인

```
스토리 제목 입력 
    ↓
[Step 1] 콘텐츠 리서치 (Gemini) → ko.content.md
    ↓
[Step 2] 내레이션 대본 생성 → 01.narration_raw.json
    ↓
[Step 3] 대본 개선 1 (Gemini) → 02.narration_improved_gemini.json
    ↓
[Step 4] 대본 개선 2 (DeepSeek) → 03.narration_improved_deepseek.json
    ↓
[Step 5] 대본 개선 3 (Qwen) → 04.narration_final.json
    ↓
[Step 6] 자막 생성 → ko.srt
```

---

## 📁 생성된 파일 구조

```
video.pipeline/
├── core/
│   └── gen_story_script.py          # ✨ 새로운 코어 모듈
├── ui/
│   ├── states/
│   │   └── story_script_state.py    # ✨ 새로운 상태 관리
│   ├── components/
│   │   └── story_script_tab.py      # ✨ 새로운 UI 컴포넌트
│   └── pages/
│       └── extract.py               # 🔧 수정됨 (탭 추가)
├── assets/
│   └── prompts/
│       ├── generate_content.md      # ✨ 콘텐츠 생성 프롬프트
│       ├── generate_narration.md    # ✨ 내레이션 생성 프롬프트
│       ├── improve_script_step1.md  # ✨ Gemini 개선 프롬프트
│       ├── improve_script_step2.md  # ✨ DeepSeek 개선 프롬프트
│       ├── improve_script_step3.md  # ✨ Qwen 개선 프롬프트
│       └── generate_subtitle.md     # ✨ 자막 생성 프롬프트
├── workspace/
│   └── project/
│       ├── content/
│       │   └── ko.content.md        # 생성됨
│       ├── scripts/
│       │   ├── 01.narration_raw.json
│       │   ├── 02.narration_improved_gemini.json
│       │   ├── 03.narration_improved_deepseek.json
│       │   └── 04.narration_final.json
│       └── subtitles/
│           └── ko.srt
├── docs/
│   └── STORY_TO_SCRIPT.md           # ✨ 사용 가이드
├── .env                             # 🔧 API 키 추가
└── requirements.txt                 # 🔧 aiohttp 추가
```

---

## 🔧 사용 방법

### 1. API 키 설정

`.env` 파일에 API 키를 추가하세요:

```bash
# 필수
GEMINI_API_KEY=AIzaSyDp1xfoRX9p3hZXzFEcJ85qKWRccBxHNfA

# 선택 (Step 4 에서 사용)
DEEPSEEK_API_KEY=your_deepseek_api_key

# 선택 (Step 5 에서 사용)
DASHSCOPE_API_KEY=your_dashscope_api_key
```

**API 키 발급처:**
- Gemini: https://aistudio.google.com/apikey
- DeepSeek: https://platform.deepseek.com/
- DashScope: https://dashscope.console.aliyun.com/

> 💡 **참고**: DeepSeek 또는 Qwen API 키가 없으면 해당 단계는 자동으로 스킵되고 이전 버전의 대본이 사용됩니다.

### 2. 의존성 설치

```bash
cd /mnt/work/projects/video.pipeline
source .venv/bin/activate
pip install aiohttp>=3.9.0
```

### 3. 앱 실행

```bash
reflex run
```

### 4. 기능 사용

1. 브라우저에서 `http://localhost:3000/extract` 로 이동
2. **"📖 스토리 → 대본"** 탭 선택
3. **스토리 제목** 입력 (필수)
4. **추가 컨텍스트** 입력 (선택사항)
5. **"🚀 스토리 → 대본 생성 시작"** 클릭
6. 실시간 진행 상황 확인
7. 완료 후 `workspace/project/` 에서 생성된 파일 확인

---

## 🎨 UI 기능

### 입력 섹션
- 스토리 제목 / 주제 입력
- 추가 컨텍스트 (선택)
- Gemini 모델 선택

### 진행 상황
- 실시간 진행률 표시 (0-100%)
- 현재 단계 표시
- 단계별 로그 출력

### 결과 미리보기
- 대본 섹션별 accordion 미리보기
- 각 섹션의 예상 재생 시간 표시
- 생성된 파일 경로 표시

### 로그 뷰어
- 실시간 로그 스트리밍
- 컬러 코딩된 로그 (에러, 성공, 경고)
- 자동 스크롤

---

## 📊 각 단계 상세

### Step 1: 콘텐츠 리서치
- **모델**: Gemini 2.5 Pro Preview
- **출력**: `workspace/project/content/ko.content.md`
- **내용**: 
  - 2000 자 이상의 한국어 콘텐츠
  - 개요, 배경, 주요 내용, 사례, 결론 구조
  - YouTube 대본으로 변환하기 위한 풍부한 정보

### Step 2: 내레이션 대본 생성
- **모델**: Gemini 2.5 Pro Preview
- **출력**: `workspace/project/scripts/01.narration_raw.json`
- **형식**:
  ```json
  [
    {
      "section": "intro",
      "title": "오프닝",
      "content": "내레이션 대본 내용...",
      "estimated_duration": 30
    }
  ]
  ```
- **타겟**: 5-10 분 내레이션 (800-1500 자)
- **섹션**: 4-6 개 논리적 구간

### Step 3: Gemini 개선
- **모델**: Gemini 2.5 Pro Preview
- **출력**: `02.narration_improved_gemini.json`
- **개선 포인트**:
  - 명확성 (Clarity)
  - 흐름 (Flow)
  - 몰입도 (Engagement)
  - 자연스러운 구어체

### Step 4: DeepSeek 개선
- **모델**: deepseek-reasoner
- **출력**: `03.narration_improved_deepseek.json`
- **개선 포인트**:
  - 논리적 일관성
  - 깊이 있는 통찰
  - 증거 기반 주장
  - 구조 최적화

### Step 5: Qwen 개선 (최종)
- **모델**: qwen-plus
- **출력**: `04.narration_final.json`
- **개선 포인트**:
  - 언어 다듬기
  - 톤 일관성
  - 감정적 영향력
  - 기억에 남는 표현

### Step 6: 자막 생성
- **모델**: Gemini 2.5 Pro Preview
- **출력**: `workspace/project/subtitles/ko.srt`
- **형식**: 표준 SRT
- **가이던스**:
  - 2-7 초 구간
  - 줄당 최대 42 자
  - 한국어 읽기 속도 (초당 3-4 자)

---

## ⚙️ 프로그래밍 방식 사용

```python
import asyncio
from pathlib import Path
from core.gen_story_script import StoryToScriptGenerator

async def main():
    generator = StoryToScriptGenerator(
        workspace_dir=Path("workspace/project")
    )
    
    results = await generator.run_full_pipeline(
        topic="조선시대 과학자의 이야기",
        context="장영실과 측우기 개발 과정에 대한 스토리"
    )
    
    print(f"콘텐츠: {results['content']}")
    print(f"최종 대본: {results['improved_qwen']}")
    print(f"자막: {results['subtitle']}")

asyncio.run(main())
```

---

## 🔍 문제 해결

### "API Key not found"
- `.env` 파일이 프로젝트 루트에 있는지 확인
- API 키가 올바른지 확인
- 앱 재시작

### "Step X 에서 실패"
- API 할당량/제한 확인
- 네트워크 연결 확인
- 로그에서 구체적인 오류 메시지 확인

### "JSON Parse Error"
- 모델이 잘못된 JSON 을 반환할 수 있음
- 자동으로 최대 3 회 재시도
- 로그에서 원본 응답 확인

---

## 📈 성능

- **총 소요 시간**: 약 3-5 분 (콘텐츠 복잡도에 따라 다름)
- **콘텐츠 길이**: 2000+ 한국어 문자
- **대본 길이**: 5-10 분 내레이션
- **자막 항목**: 약 50-100 개 세그먼트

---

## 🎯 다음 단계 (선택사항)

1. **TTS 연동**: 생성된 대본으로 오디오 생성
2. **영상 편집**: 자막과 오디오를 결합하여 영상 생성
3. **추가 개선**: 수동 편집을 위한 대본 편집기 기능 추가

---

## 📝 참고 문서

- `docs/STORY_TO_SCRIPT.md` - 상세 사용 가이드 (영문)
- `assets/prompts/` - 모든 프롬프트 템플릿

---

## ✅ 체크리스트

- [x] 디렉토리 구조 생성
- [x] 프롬프트 파일 생성 (6 개)
- [x] 코어 모듈 구현
- [x] 상태 관리 구현
- [x] UI 컴포넌트 구현
- [x] Extract 페이지 탭 추가
- [x] API 키 설정
- [x] 의존성 추가
- [x] 문서화
- [x] 컴파일 테스트 통과
