<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-01-30 | Updated: 2026-01-30 -->

# Pages

## Purpose
비디오 파이프라인의 각 기능별 페이지 컴포넌트입니다. 각 페이지는 특정 워크플로우 단계를 담당합니다.

## Key Files
| File | Description |
|------|-------------|
| `__init__.py` | 패키지 초기화 |
| `index.py` | 홈/대시보드 - 기능 카드 그리드 표시 |
| `extract.py` | 자막 추출 - 오디오에서 STT로 자막 생성 |
| `review.py` | 자막 편집 - 다국어 자막 검토 및 수정 |
| `scenario.py` | 시나리오 생성 - XML 스크립트 생성 |
| `audio.py` | TTS 생성 - GPT-SoVITS 음성 합성 |
| `subtitle.py` | 자막 미리보기 - 싱크 확인 및 조정 |
| `project.py` | 프로젝트 생성 - CapCut 내보내기 |

## For AI Agents

### Working In This Directory
- 각 페이지는 `page()` 함수를 export
- 상태 클래스는 같은 파일 또는 `states/`에 정의
- `on_load` 핸들러로 페이지 진입 시 초기화

### Page Pattern
```python
class PageState(rx.State):
    # 상태 변수
    data: list = []

    def on_load(self):
        # 초기화 로직
        pass

    async def some_action(self):
        # 비동기 작업
        pass

def page() -> rx.Component:
    return page_container([
        page_header("Title", "Description"),
        # 컴포넌트들...
    ])
```

### Common Patterns
- `page_container()` 래퍼 사용
- `page_header()` 헤더 컴포넌트 사용
- 카드 레이아웃 (`rx.card`)
- 그리드 레이아웃 (`rx.grid`)
- 비동기 작업 시 로딩 상태 표시

## Dependencies

### Internal
- `../components/` - 공통 UI 컴포넌트
- `../states/` - 상태 관리 클래스
- `core/` - 비즈니스 로직

<!-- MANUAL: -->
