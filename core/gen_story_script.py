"""Story-to-Script Generation Pipeline (5-Step Architecture)

Pipeline Flow:
1. Research (Gemini) → 순수 자료 수집 (대본 X)
2. Structure (DeepSeek) → 씬 뼈대 설계 (문장 X)
3. Writing (Qwen) → 실제 대본 집필
4. Review (Gemini) → 비평 + 부분 수정만
5. SRT → TTS 용 자막 파일
"""

import os
import json
import asyncio
import aiohttp
from pathlib import Path
from typing import Callable

from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

from google import genai
from google.genai import types

from core.models.script_models import (
    ResearchPacket,
    SceneStructure,
    NarrationScript,
    NarrationLine,
    ReviewResult,
    RecordingScript,
    RecordingInstruction,
)
class StoryScriptPipeline:
    """5단계 스토리 스크립트 파이프라인

    각 단계는 명확히 다른 역할을 수행:
    - Step 1: 리서치 (자료 수집만, 대본 X)
    - Step 2: 구조 설계 (뼈대만, 문장 X)
    - Step 3: 대본 집필 (실제 문장 작성)
    - Step 4: 품질 검증 (부분 수정만, 전체 재작성 X)
    - Step 5: SRT 생성 (자막 파일)
    """

    def __init__(self, workspace_dir: Path | None = None, project_id: str | None = None):
        self.base_dir = Path(__file__).resolve().parent.parent
        self.workspace_dir = workspace_dir or (self.base_dir / "workspace")

        # Generate project ID if not provided
        if project_id:
            self.project_id = project_id
        else:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.project_id = f"project_{timestamp}"

        # Directory setup
        self.project_dir = self.workspace_dir / self.project_id
        self.scripts_dir = self.project_dir / "scripts"
        self.subtitles_dir = self.project_dir / "subtitles"

        for dir_path in [self.scripts_dir, self.subtitles_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # API Keys
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        self.dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")

        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in .env")

        # Initialize Gemini client
        self.gemini_client = genai.Client(api_key=self.gemini_api_key)

        # Model configurations
        self.gemini_model = "gemini-3-pro-preview"
        self.deepseek_model = "deepseek-reasoner"
        self.qwen_model = "qwen3.5-plus"

        # Prompts directory
        self.prompts_dir = self.base_dir / "assets" / "prompts" / "story_script"

        # State
        self.current_step = 0
        self.total_steps = 5

    def log(self, message: str, callback: Callable[[str], None] | None = None):
        """Log message with optional callback"""
        print(message)
        if callback:
            callback(message)

    def _load_prompt(self, filename: str) -> str:
        """Load prompt template from file"""
        prompt_path = self.prompts_dir / filename
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        return prompt_path.read_text(encoding="utf-8")

    # ========== Step 1: Research (Gemini) ==========

    async def step1_research(
        self,
        topic: str,
        context: str = "",
        log_callback: Callable[[str], None] | None = None
    ) -> ResearchPacket:
        """Step 1: 리서치 - 순수 자료 수집 (대본 X)

        Model: Gemini (웹 접근 강점)
        입력: topic, context
        출력: ResearchPacket (Markdown)
        """
        self.current_step = 1
        self.log(f"[-] Step 1/5: Research - Collecting facts for '{topic}'...", log_callback)

        try:
            prompt_template = self._load_prompt("01_research.md")
            prompt = prompt_template.replace("{topic}", topic).replace("{context}", context or "없음")

            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    top_p=0.9,
                    max_output_tokens=8192,
                )
            )

            raw_content = self._clean_markdown(response.text)

            # Create ResearchPacket
            packet = ResearchPacket(
                topic=topic,
                raw_content=raw_content,
            )

            # Save to file
            output_path = self.scripts_dir / "01_research_packet.md"
            output_path.write_text(raw_content, encoding="utf-8")

            self.log(f"[+] Research complete: {output_path}", log_callback)
            self.log(f"    Characters: {len(raw_content)}", log_callback)

            return packet

        except Exception as e:
            self.log(f"[!] Research failed: {e}", log_callback)
            raise

    # ========== Step 2: Structure (DeepSeek Reasoner) ==========

    async def step2_structure(
        self,
        research: ResearchPacket,
        target_duration_minutes: int = 12,
        log_callback: Callable[[str], None] | None = None
    ) -> SceneStructure:
        """Step 2: 구조 설계 - 씬 뼈대만 (문장 X)

        Model: DeepSeek Reasoner (추론 강점)
        입력: ResearchPacket
        출력: SceneStructure (JSON)
        """
        self.current_step = 2
        self.log("[-] Step 2/5: Structure - Designing scene skeleton...", log_callback)

        try:
            prompt_template = self._load_prompt("02_structure.md")
            prompt = (
                prompt_template
                .replace("{research_packet}", research.raw_content)
                .replace("{target_duration}", str(target_duration_minutes))
            )

            if not self.deepseek_api_key:
                self.log("[!] DeepSeek API key not found, using Gemini fallback...", log_callback)
                structure_json = await self._call_gemini_json(prompt)
            else:
                structure_json = await self._call_deepseek_json(prompt)

            # Parse into SceneStructure
            structure = SceneStructure.from_dict(structure_json)
            structure.topic = research.topic

            # Save to file
            output_path = self.scripts_dir / "02_scene_structure.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(structure.to_dict(), f, indent=2, ensure_ascii=False)

            self.log(f"[+] Structure complete: {output_path}", log_callback)
            self.log(f"    Scenes: {len(structure.scenes)}", log_callback)

            return structure

        except Exception as e:
            self.log(f"[!] Structure design failed: {e}", log_callback)
            raise

    # ========== Step 3: Writing (Qwen) ==========

    async def step3_writing(
        self,
        structure: SceneStructure,
        log_callback: Callable[[str], None] | None = None
    ) -> NarrationScript:
        """Step 3: 대본 집필 - 실제 나레이션 문장 작성

        Model: Qwen (작문 강점)
        입력: SceneStructure
        출력: NarrationScript (JSON)
        """
        self.current_step = 3
        self.log("[-] Step 3/5: Writing - Drafting narration script...", log_callback)

        try:
            prompt_template = self._load_prompt("03_writing.md")
            prompt = prompt_template.replace("{scene_structure}", structure.to_json())

            if not self.dashscope_api_key:
                self.log("[!] DashScope API key not found, using Gemini fallback...", log_callback)
                script_json = await self._call_gemini_json(prompt)
            else:
                script_json = await self._call_qwen_json(prompt)

            # Parse into NarrationScript
            script = NarrationScript.from_dict(script_json)
            script.topic = structure.topic

            # Save to file
            output_path = self.scripts_dir / "03_narration_draft.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(script.to_dict(), f, indent=2, ensure_ascii=False)

            self.log(f"[+] Writing complete: {output_path}", log_callback)
            self.log(f"    Lines: {script.total_lines}", log_callback)

            return script

        except Exception as e:
            self.log(f"[!] Writing failed: {e}", log_callback)
            raise

    # ========== Step 4: Review (Gemini) ==========

    async def step4_review(
        self,
        script: NarrationScript,
        log_callback: Callable[[str], None] | None = None
    ) -> NarrationScript:
        """Step 4: 품질 검증 - 부분 수정만 (전체 재작성 X)

        Model: Gemini (비평가 역할)
        입력: NarrationScript
        출력: NarrationScript (패치 적용됨)
        """
        self.current_step = 4
        self.log("[-] Step 4/5: Review - Critiquing and patching...", log_callback)

        try:
            prompt_template = self._load_prompt("04_review.md")
            prompt = prompt_template.replace("{script}", script.to_json())

            review_json = await self._call_gemini_json(prompt)

            # Parse ReviewResult
            review = ReviewResult.from_dict(review_json)

            # Save review result
            review_path = self.scripts_dir / "04_review_result.json"
            with open(review_path, "w", encoding="utf-8") as f:
                json.dump(review.to_dict(), f, indent=2, ensure_ascii=False)

            self.log(f"[+] Review complete: {review_path}", log_callback)
            self.log(f"    Score: {review.overall_score}/10", log_callback)
            self.log(f"    Patches: {len(review.patches)}", log_callback)

            # Apply patches
            reviewed_script = review.apply_to_script(script)

            # Save reviewed script
            output_path = self.scripts_dir / "04_narration_reviewed.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(reviewed_script.to_dict(), f, indent=2, ensure_ascii=False)

            return reviewed_script

        except Exception as e:
            self.log(f"[!] Review failed: {e}", log_callback)
            raise

    # ========== Step 5: SRT Generation ==========

    async def step5_srt(
        self,
        script: NarrationScript,
        log_callback: Callable[[str], None] | None = None
    ) -> Path:
        """Step 5: SRT 생성 - TTS용 자막 파일

        API 호출 없이 프로그래밍적으로 생성합니다.
        입력: NarrationScript
        출력: ko.srt (SRT file)
        """
        self.current_step = 5
        self.log("[-] Step 5/5: SRT - Generating subtitle file...", log_callback)

        # Generate SRT programmatically from NarrationScript
        srt_content = self._generate_srt_from_script(script)

        # Save to file
        output_path = self.subtitles_dir / "ko.srt"
        output_path.write_text(srt_content, encoding="utf-8")

        self.log(f"[+] SRT complete: {output_path}", log_callback)

        # Count subtitles
        subtitle_count = len([l for l in srt_content.split('\n') if l.strip().isdigit()])
        self.log(f"    Subtitle entries: {subtitle_count}", log_callback)

        return output_path

    def _generate_srt_from_script(self, script: NarrationScript) -> str:
        """Generate SRT file from NarrationScript programmatically without API calls"""
        srt_lines = []
        current_time_ms = 0

        for i, line in enumerate(script.lines, 1):
            # Calculate duration: ~5 seconds per line (adjust based on text length)
            duration_ms = max(2000, min(5000, len(line.text) * 150))

            # Start time
            start_ms = current_time_ms

            # End time
            end_ms = start_ms + duration_ms

            # Format timestamps
            start_str = self._format_srt_time(start_ms)
            end_str = self._format_srt_time(end_ms)

            # SRT entry with speaker label
            srt_lines.append(f"{i}")
            srt_lines.append(f"{start_str} --> {end_str}")
            srt_lines.append(f"[speaker]: {line.text}")
            srt_lines.append("")

            # Add pause after (default 0.3s for NarrationLine which doesn't have pause_after)
            pause_ms = int(0.3 * 1000)
            current_time_ms = end_ms + pause_ms

        return "\n".join(srt_lines)

    def _format_srt_time(self, ms: int) -> str:
        """Convert milliseconds to SRT timestamp format (HH:MM:SS,mmm)"""
        hours = ms // 3600000
        minutes = (ms % 3600000) // 60000
        seconds = (ms % 60000) // 1000
        milliseconds = ms % 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

    # ========== Full Pipeline ==========

    async def run(
        self,
        topic: str,
        context: str = "",
        target_duration_minutes: int = 12,
        log_callback: Callable[[str], None] | None = None
    ) -> dict[str, Path]:
        """전체 5단계 파이프라인 실행

        Args:
            topic: 스토리 주제
            context: 추가 컨텍스트
            target_duration_minutes: 목표 영상 길이 (분)
            log_callback: 로그 콜백

        Returns:
            각 단계별 출력 파일 경로
        """
        self.log("=" * 60, log_callback)
        self.log(f"🎬 Story Script Pipeline (5-Step Architecture)", log_callback)
        self.log(f"   Topic: {topic}", log_callback)
        self.log(f"   Target: {target_duration_minutes} minutes", log_callback)
        self.log("=" * 60, log_callback)

        results = {}

        try:
            # Step 1: Research
            research = await self.step1_research(topic, context, log_callback)
            results["research"] = self.scripts_dir / "01_research_packet.md"
            await asyncio.sleep(1)

            # Step 2: Structure
            structure = await self.step2_structure(research, target_duration_minutes, log_callback)
            results["structure"] = self.scripts_dir / "02_scene_structure.json"
            await asyncio.sleep(1)

            # Step 3: Writing
            script = await self.step3_writing(structure, log_callback)
            results["draft"] = self.scripts_dir / "03_narration_draft.json"
            await asyncio.sleep(1)

            # Step 4: Review
            reviewed = await self.step4_review(script, log_callback)
            results["reviewed"] = self.scripts_dir / "04_narration_reviewed.json"
            await asyncio.sleep(1)

            # Step 5: SRT
            srt_path = await self.step5_srt(reviewed, log_callback)
            results["srt"] = srt_path

            self.log("=" * 60, log_callback)
            self.log("✅ Pipeline Complete!", log_callback)
            self.log("=" * 60, log_callback)

            return results

        except Exception as e:
            self.log(f"[!] Pipeline failed at step {self.current_step}: {e}", log_callback)
            raise

    # ========== Backward Compatible Methods ==========

    async def run_full_pipeline(
        self,
        topic: str,
        context: str = "",
        log_callback: Callable[[str], None] | None = None
    ) -> dict[str, Path]:
        """Backward compatible alias for run()"""
        return await self.run(topic, context, 12, log_callback)

    # ========== API Helpers ==========

    async def _call_gemini_json(self, prompt: str) -> dict:
        """Call Gemini API for JSON response"""
        response = self.gemini_client.models.generate_content(
            model=self.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.5,
                top_p=0.9,
                max_output_tokens=8192,
                response_mime_type="application/json",
            )
        )
        return self._parse_json_response(response.text)

    async def _call_deepseek_json(self, prompt: str) -> dict:
        """Call DeepSeek API for JSON response"""
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.deepseek_api_key}"
        }
        payload = {
            "model": self.deepseek_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.5,
            "max_tokens": 8000,
            "response_format": {"type": "json_object"}
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=180)) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"DeepSeek API error: {response.status} - {error_text}")

                result = await response.json()
                content = result["choices"][0]["message"]["content"]
                return self._parse_json_response(content)

    async def _call_qwen_json(self, prompt: str) -> dict:
        """Call Qwen (DashScope) API for JSON response"""
        url = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.dashscope_api_key}"
        }
        payload = {
            "model": self.qwen_model,
            "messages": [
                {"role": "system", "content": "You are a professional script writer. Output ONLY valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5,
            "max_tokens": 8000,
            "response_format": {"type": "json_object"}
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=120)) as response:
                    if response.status != 200:
                        # Fallback to China endpoint
                        url_cn = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
                        async with session.post(url_cn, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=120)) as response_cn:
                            if response_cn.status != 200:
                                error_text = await response_cn.text()
                                raise Exception(f"Qwen API error: {response_cn.status} - {error_text}")
                            result = await response_cn.json()
                    else:
                        result = await response.json()

                    content = result["choices"][0]["message"]["content"]
                    return self._parse_json_response(content)
            except aiohttp.ClientError as e:
                raise Exception(f"Qwen API connection error: {str(e)}")

    # ========== Utility Methods ==========

    def _parse_json_response(self, text: str) -> dict:
        """Parse JSON from model response"""
        try:
            clean = text.strip()

            # Remove markdown code blocks
            if clean.startswith("```json"):
                clean = clean[7:]
            if clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]

            clean = clean.strip()
            
            # Fix common JSON issues
            # Replace single quotes with double quotes (if not inside strings)
            # Fix trailing commas
            import re
            # Remove trailing commas before } or ]
            clean = re.sub(r',\s*([\]}])', r'\1', clean)
            
            return json.loads(clean)
        except json.JSONDecodeError as e:
            print(f"[!] JSON Parse Error: {e}")
            print(f"    Error at approximately character: {e.pos}")
            print(f"    Raw text (first 1000 chars): {text[:1000]}...")
            print(f"    Raw text (around error): {text[max(0, e.pos-100):e.pos+100] if e.pos else 'N/A'}...")
            raise

    def _clean_markdown(self, text: str) -> str:
        """Clean markdown response"""
        clean = text.strip()
        if clean.startswith("```markdown"):
            clean = clean[11:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        return clean.strip()

    def _clean_srt(self, text: str) -> str:
        """Clean SRT response"""
        clean = text.strip()
        if clean.startswith("```"):
            clean = clean.split("```", 1)[1]
            if clean.startswith("srt"):
                clean = clean[3:]
            clean = clean.split("```")[0]
        return clean.strip()
# Backward compatibility alias
StoryToScriptGenerator = StoryScriptPipeline
