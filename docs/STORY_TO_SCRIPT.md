# 📖 Story-to-Script Feature Guide

## Overview

The **Story-to-Script** feature automatically generates YouTube narration scripts from a simple story title or topic. It uses a multi-step AI pipeline to research, write, refine, and produce a complete script with subtitles.

## Workflow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Step 1    │ →   │    Step 2    │ →   │    Step 3    │ →   │    Step 4    │ →   │    Step 5    │ →   │    Step 6    │
│  Content    │     │  Narration   │     │  Improve     │     │  Improve     │     │  Improve     │     │  Subtitle   │
│  Research   │     │   Script     │     │  (Gemini)    │     │  (DeepSeek)  │     │   (Qwen)     │     │ Generation  │
└─────────────┘     └──────────────┘     └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
     ↓                     ↓                     ↓                     ↓                     ↓                     ↓
ko.content.md      01.narration_raw.json  02.improved_     03.improved_     04.narration_       ko.srt
                    (initial draft)       gemini.json      deepseek.json    final.json
```

## Features

### 1. Content Research (Step 1)
- **Model**: Gemini 2.5 Pro Preview
- **Output**: `workspace/project/content/ko.content.md`
- Generates comprehensive research content (2000+ Korean characters)
- Structured markdown with sections: overview, background, main content, examples, conclusion

### 2. Narration Script Generation (Step 2)
- **Model**: Gemini 2.5 Pro Preview
- **Output**: `workspace/project/scripts/01.narration_raw.json`
- Converts content to YouTube-friendly narration format
- 4-6 sections with estimated durations
- Target: 5-10 minutes of narration

### 3. Script Improvement - Step 3 (Gemini)
- **Model**: Gemini 2.5 Pro Preview
- **Output**: `workspace/project/scripts/02.narration_improved_gemini.json`
- **Focus**: Clarity, Flow, Engagement
- Improves readability and natural speech patterns

### 4. Script Improvement - Step 4 (DeepSeek)
- **Model**: deepseek-reasoner
- **Output**: `workspace/project/scripts/03.narration_improved_deepseek.json`
- **Focus**: Logical Consistency, Depth, Reasoning
- Enhances argumentation and logical flow

### 5. Script Improvement - Step 5 (Qwen)
- **Model**: qwen-plus (via DashScope)
- **Output**: `workspace/project/scripts/04.narration_final.json`
- **Focus**: Final Polish, Tone, Emotional Impact
- Professional refinement for maximum engagement

### 6. Subtitle Generation (Step 6)
- **Model**: Gemini 2.5 Pro Preview
- **Output**: `workspace/project/subtitles/ko.srt`
- Standard SRT format with proper timing
- Optimized for Korean reading speed

## Usage

### Via UI (Recommended)

1. Navigate to **Extract** page
2. Select the **"📖 스토리 → 대본"** tab
3. Enter:
   - **Story Title/Topic**: Main subject (required)
   - **Additional Context**: Extra information (optional)
   - **Gemini Model**: Select model version
4. Click **"🚀 스토리 → 대본 생성 시작"**
5. Monitor progress in real-time
6. Download generated files from workspace directory

### Via API (Programmatic)

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
        context="장영실과 측우기 개발 과정"
    )
    
    print(f"Content: {results['content']}")
    print(f"Final Script: {results['improved_qwen']}")
    print(f"Subtitle: {results['subtitle']}")

asyncio.run(main())
```

## Configuration

### API Keys Required

Add to `.env` file:

```bash
# Required
GEMINI_API_KEY=your_gemini_api_key

# Optional (for step 4)
DEEPSEEK_API_KEY=your_deepseek_api_key

# Optional (for step 5)
DASHSCOPE_API_KEY=your_dashscope_api_key
```

### Getting API Keys

- **Gemini**: https://aistudio.google.com/apikey
- **DeepSeek**: https://platform.deepseek.com/
- **DashScope (Qwen)**: https://dashscope.console.aliyun.com/

> **Note**: If DeepSeek or Qwen API keys are not provided, those steps will be skipped and the previous version will be used.

## Output Files

### Directory Structure

```
workspace/project/
├── content/
│   └── ko.content.md              # Research content
├── scripts/
│   ├── 01.narration_raw.json      # Initial draft
│   ├── 02.narration_improved_gemini.json
│   ├── 03.narration_improved_deepseek.json
│   └── 04.narration_final.json    # Final version
└── subtitles/
    └── ko.srt                     # Subtitle file
```

### File Formats

#### Content (ko.content.md)
```markdown
# 주제 제목

## 1. 개요
- 소개 내용

## 2. 배경 및 역사
- 배경 정보
```

#### Script (JSON)
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

#### Subtitle (ko.srt)
```
1
00:00:00,000 --> 00:00:03,500
첫 번째 자막입니다.

2
00:00:03,500 --> 00:00:07,000
두 번째 자막입니다.
```

## Performance

- **Total Time**: ~3-5 minutes (depends on content complexity)
- **Content Length**: 2000+ Korean characters
- **Script Duration**: 5-10 minutes of narration
- **Subtitle Entries**: ~50-100 segments

## Troubleshooting

### Common Issues

#### "API Key not found"
- Check `.env` file exists in project root
- Verify API key is correct and active
- Restart application after adding keys

#### "Step failed at Step X"
- Check API quota/limits
- Verify network connectivity
- Review logs for specific error messages

#### "JSON Parse Error"
- Model may return malformed JSON
- Automatically retries up to 3 times
- Check logs for raw response

### Logs

All operations are logged to:
- UI log viewer (real-time)
- Console output

Log format: `[HH:MM:SS] [Step] Message`

## Best Practices

1. **Be Specific with Topics**: Clear topics generate better content
2. **Add Context**: Additional context improves relevance
3. **Review Intermediate Results**: Check each step's output
4. **Manual Refinement**: Final polish may still be needed for production use

## Future Enhancements

- [ ] Support for multiple languages
- [ ] Custom prompt templates
- [ ] Voice-over audio generation integration
- [ ] Scene suggestion based on script
- [ ] One-click export to video editing software
