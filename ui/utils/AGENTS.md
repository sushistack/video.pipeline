<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-01-30 | Updated: 2026-01-30 -->

# Utils

## Purpose
UI에서 사용하는 유틸리티 함수들입니다. 데이터 포맷팅, 파싱, 변환 등의 헬퍼 함수를 제공합니다.

## Key Files
| File | Description |
|------|-------------|
| `__init__.py` | 패키지 초기화 |
| `formatters.py` | 데이터 포맷팅 함수 (시간, 숫자 등) |
| `subtitle_utils.py` | 자막 관련 유틸리티 |
| `srt_parser.py` | SRT 파일 파서 |
| `speaker_extractor.py` | 화자 정보 추출 |

## For AI Agents

### Working In This Directory
- 순수 함수로 구현 (사이드 이펙트 없음)
- 타입 힌트 사용 권장
- 단위 테스트 작성 가능

### Common Functions

#### formatters.py
```python
format_duration(seconds: float) -> str  # "01:23"
format_timestamp(ms: int) -> str  # "00:01:23,456"
```

#### srt_parser.py
```python
parse_srt(content: str) -> list[dict]
write_srt(items: list[dict]) -> str
```

#### speaker_extractor.py
```python
extract_speaker(text: str) -> tuple[str, str]  # (speaker, content)
```

### Common Patterns
- 정규표현식으로 파싱
- 예외 처리로 안전한 파싱
- 타입 힌트로 명확한 인터페이스

## Dependencies

### External
- `re` - 정규표현식

<!-- MANUAL: -->
