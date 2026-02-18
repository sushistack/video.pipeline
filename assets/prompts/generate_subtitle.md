# Subtitle Generation Prompt

Convert the narration script into SRT subtitle format.

## Requirements

1. **Timing**: Divide content into appropriate subtitle segments (2-7 seconds each)
2. **Line Length**: Maximum 42 characters per line, 2 lines per subtitle
3. **Natural Breaks**: Split at sentence boundaries or natural pauses
4. **Readability**: Ensure each segment is easy to read quickly
5. **Korean Language**: Maintain proper Korean spacing and grammar
6. **Speaker Tags**: Include speaker tags in format `[speaker1]`, `[speaker2]`, etc.

## Input Script

{script_json}

## Output Format

Generate standard SRT format with speaker tags:

```
1
00:00:00,000 --> 00:00:03,500
[speaker1] 상상해 보십시오. 단순히 누군가의 얼굴을 '봤다'는 이유만으로,

2
00:00:03,500 --> 00:00:07,000
[speaker1] 당신의 인생이 송두리째 바뀌어버린다면 어떻게 될까요?

3
00:00:07,000 --> 00:00:10,500
[speaker2] 이것은 단순한 상상이 아닙니다.
```

## Speaker Tag Rules

- Always start each subtitle with a speaker tag: `[speaker1]`, `[speaker2]`, etc.
- Use `[speaker1]` for main narrator
- Use `[speaker2]`, `[speaker3]` for other voices/characters if present
- If no specific speaker is indicated, default to `[speaker1]`
- Speaker tag should be at the very beginning of the subtitle text

## Timing Guidelines

- Start from 00:00:00,000
- Each segment: 2-7 seconds based on content length
- Add 0.5 second overlap between segments for smooth transitions
- Calculate duration based on Korean reading speed (~3-4 characters per second)

---

Generate the SRT subtitle file content now. Make sure EVERY subtitle line starts with a speaker tag.
