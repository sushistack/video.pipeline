<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-01-30 | Updated: 2026-01-30 -->

# Components

## Purpose
재사용 가능한 UI 컴포넌트들입니다. 레이아웃, 파일 선택, 로그 뷰어 등 공통 UI 요소를 제공합니다.

## Key Files
| File | Description |
|------|-------------|
| `__init__.py` | 패키지 초기화 |
| `layout.py` | 레이아웃 컴포넌트 - page_container, page_header, navbar |
| `file_selector.py` | 파일/폴더 선택 UI |
| `log_viewer.py` | 실시간 로그 출력 컴포넌트 |
| `pagination.py` | 페이지네이션 컴포넌트 |
| `subtitle_row.py` | 자막 행 편집 컴포넌트 |

## For AI Agents

### Working In This Directory
- 컴포넌트는 함수로 정의 (`def component_name(...) -> rx.Component`)
- 스타일은 Radix UI 테마 사용
- 반응형 디자인 고려

### Key Components

#### layout.py
```python
page_container(children, max_width="1400px") -> rx.Component
page_header(title, description) -> rx.Component
navbar() -> rx.Component  # 상단 네비게이션
```

#### log_viewer.py
```python
log_viewer(logs: list[str], height="300px") -> rx.Component
```

#### subtitle_row.py
```python
subtitle_row(item, on_edit, on_delete) -> rx.Component
```

### Common Patterns
- `rx.cond()`로 조건부 렌더링
- `rx.foreach()`로 리스트 렌더링
- `rx.match()`로 패턴 매칭 렌더링
- Radix 컬러 스킴 사용 (`color_scheme="blue"`)

## Dependencies

### External
- `reflex` - UI 프레임워크

<!-- MANUAL: -->
