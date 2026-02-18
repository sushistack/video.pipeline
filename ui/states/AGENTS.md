<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-01-30 | Updated: 2026-01-30 -->

# States

## Purpose
Reflex 상태 관리 클래스들입니다. 각 페이지의 데이터와 비즈니스 로직을 캡슐화합니다.

## Key Files
| File | Description |
|------|-------------|
| `__init__.py` | 패키지 초기화 |
| `project_state.py` | 프로젝트 상태 - 폴더 선택, 프로젝트 목록 |
| `audio_state.py` | TTS 상태 - 음성 생성, 레퍼런스 관리 |
| `extract_state.py` | 추출 상태 - STT 처리, 자막 저장 |
| `review_state.py` | 리뷰 상태 - 자막 편집, 번역 |

## For AI Agents

### Working In This Directory
- `rx.State` 클래스 상속
- 상태 변수는 클래스 속성으로 정의
- 이벤트 핸들러는 메서드로 정의
- 비동기 작업은 `async def` 사용

### State Pattern
```python
class MyState(rx.State):
    # 상태 변수
    items: list[dict] = []
    loading: bool = False
    error: str = ""

    def on_load(self):
        """페이지 로드 시 호출"""
        self.items = self._load_items()

    async def async_action(self):
        """비동기 작업"""
        self.loading = True
        try:
            # 작업 수행
            pass
        except Exception as e:
            self.error = str(e)
        finally:
            self.loading = False

    @rx.var
    def computed_value(self) -> int:
        """계산된 값 (캐싱됨)"""
        return len(self.items)
```

### Common Patterns
- `on_load` 메서드로 초기화
- `@rx.var` 데코레이터로 계산된 속성
- `yield` 로 중간 상태 업데이트 (로그 스트리밍)
- try/except로 에러 핸들링

## Dependencies

### Internal
- `core/` - 비즈니스 로직 호출
- `workspace/` - 파일 시스템 접근

<!-- MANUAL: -->
