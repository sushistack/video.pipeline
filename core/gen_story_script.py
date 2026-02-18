"""Story-to-Script Generation Pipeline"""

import os
import sys
import json
import time
import typing
import asyncio
import aiohttp
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

from google import genai
from google.genai import types


class StoryToScriptGenerator:
    """
    Generates YouTube narration scripts from story topics through multi-step AI processing.

    Workflow:
    1. Content Research: Generate comprehensive content markdown using Gemini
    2. Narration Script: Convert content to YouTube narration format
    3. 3-Step Improvement: Gemini → DeepSeek → Qwen refinement
    4. Subtitle Generation: Create SRT subtitle file
    """

    def __init__(self, workspace_dir: Path | None = None, project_id: str | None = None):
        self.base_dir = Path(__file__).resolve().parent.parent
        self.workspace_dir = workspace_dir or (self.base_dir / "workspace")

        # Generate project ID if not provided
        if project_id:
            self.project_id = project_id
        else:
            # Auto-generate project ID with timestamp
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.project_id = f"project_{timestamp}"

        # Directory setup (per project)
        self.project_dir = self.workspace_dir / self.project_id
        self.content_dir = self.project_dir / "content"
        self.scripts_dir = self.project_dir / "scripts"
        self.subtitles_dir = self.project_dir / "subtitles"

        for dir_path in [self.content_dir, self.scripts_dir, self.subtitles_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # API Keys
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        self.dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")  # For Qwen
        
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in .env")
        
        # Initialize Gemini client
        self.gemini_client = genai.Client(api_key=self.gemini_api_key)
        
        # Model configurations
        self.gemini_model = "gemini-3-flash-preview"  # gemini-3-pro-preview equivalent
        self.deepseek_model = "deepseek-reasoner"
        self.qwen_model = "qwen-plus"  # qwen3.5-plus equivalent
        
        # Prompts directory
        self.prompts_dir = self.base_dir / "assets" / "prompts"
        
        # State tracking
        self.current_step = 0
        self.total_steps = 7
        
    def log(self, message: str, callback: typing.Callable[[str], None] | None = None):
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
    
    # ========== Step 1: Content Research ==========
    
    async def generate_content(
        self, 
        topic: str, 
        context: str = "",
        log_callback: typing.Callable[[str], None] | None = None
    ) -> Path:
        """
        Step 1: Generate comprehensive content markdown using Gemini.
        
        Args:
            topic: Story title or topic
            context: Additional context (optional)
            log_callback: Optional callback for logging
            
        Returns:
            Path to generated ko.content.md file
        """
        self.current_step = 1
        self.log(f"[-] Step 1/7: Generating content research for '{topic}'...", log_callback)
        
        try:
            # Load prompt
            prompt_template = self._load_prompt("generate_content.md")
            prompt = prompt_template.replace("{topic}", topic).replace("{context}", context or "None")
            
            # Generate content using Gemini
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    top_p=0.9,
                    max_output_tokens=8192,
                )
            )
            
            content_md = response.text.strip()
            
            # Clean up if wrapped in code blocks
            if content_md.startswith("```markdown"):
                content_md = content_md[11:]
            if content_md.startswith("```"):
                content_md = content_md[3:]
            if content_md.endswith("```"):
                content_md = content_md[:-3]
            content_md = content_md.strip()
            
            # Save to file
            output_path = self.content_dir / "ko.content.md"
            output_path.write_text(content_md, encoding="utf-8")
            
            self.log(f"[+] Content generated: {output_path}", log_callback)
            self.log(f"    Characters: {len(content_md)}", log_callback)
            
            return output_path
            
        except Exception as e:
            self.log(f"[!] Content generation failed: {e}", log_callback)
            raise
    
    # ========== Step 2: Narration Script Generation ==========
    
    async def generate_narration_script(
        self,
        content_path: Path | None = None,
        log_callback: typing.Callable[[str], None] | None = None
    ) -> Path:
        """
        Step 2: Generate YouTube narration script from content.
        
        Args:
            content_path: Path to ko.content.md (default: workspace/project/content/ko.content.md)
            log_callback: Optional callback for logging
            
        Returns:
            Path to generated narration script JSON
        """
        self.current_step = 2
        self.log("[-] Step 2/7: Generating narration script from content...", log_callback)
        
        try:
            # Load content
            content_path = content_path or (self.content_dir / "ko.content.md")
            if not content_path.exists():
                raise FileNotFoundError(f"Content file not found: {content_path}")
            
            content_md = content_path.read_text(encoding="utf-8")
            
            # Load prompt
            prompt_template = self._load_prompt("generate_narration.md")
            prompt = prompt_template.replace("{content_md}", content_md)
            
            # Generate script using Gemini
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    top_p=0.9,
                    max_output_tokens=8192,
                    response_mime_type="application/json",
                )
            )
            
            script_json = self._parse_json_response(response.text)
            
            # Save script
            output_path = self.scripts_dir / "01.narration_raw.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(script_json, f, indent=2, ensure_ascii=False)
            
            self.log(f"[+] Narration script generated: {output_path}", log_callback)
            self.log(f"    Sections: {len(script_json)}", log_callback)
            
            return output_path
            
        except Exception as e:
            self.log(f"[!] Narration generation failed: {e}", log_callback)
            raise
    
    # ========== Step 3-5: Script Improvement (3 Steps) ==========
    
    async def improve_script_step1(
        self,
        script_path: Path | None = None,
        log_callback: typing.Callable[[str], None] | None = None
    ) -> Path:
        """
        Step 3: Improve script using Gemini (Focus: Clarity, Flow, Engagement).
        """
        self.current_step = 3
        self.log("[-] Step 3/7: Improving script (Gemini - Clarity & Flow)...", log_callback)
        
        return await self._improve_script_generic(
            step_name="step1",
            model=self.gemini_model,
            client="gemini",
            script_path=script_path,
            output_filename="02.narration_improved_gemini.json",
            log_callback=log_callback
        )
    
    async def improve_script_step2(
        self,
        script_path: Path | None = None,
        log_callback: typing.Callable[[str], None] | None = None
    ) -> Path:
        """
        Step 4: Improve script using DeepSeek Reasoner (Focus: Logical Consistency).
        """
        self.current_step = 4
        self.log("[-] Step 4/7: Improving script (DeepSeek - Logical Reasoning)...", log_callback)
        
        return await self._improve_script_generic(
            step_name="step2",
            model=self.deepseek_model,
            client="deepseek",
            script_path=script_path,
            output_filename="03.narration_improved_deepseek.json",
            log_callback=log_callback
        )
    
    async def improve_script_step3(
        self,
        script_path: Path | None = None,
        log_callback: typing.Callable[[str], None] | None = None
    ) -> Path:
        """
        Step 5: Improve script using Qwen (Focus: Final Polish).
        """
        self.current_step = 5
        self.log("[-] Step 5/7: Improving script (Qwen - Final Polish)...", log_callback)
        
        return await self._improve_script_generic(
            step_name="step3",
            model=self.qwen_model,
            client="qwen",
            script_path=script_path,
            output_filename="04.narration_final.json",
            log_callback=log_callback
        )
    
    async def _improve_script_generic(
        self,
        step_name: str,
        model: str,
        client: str,
        script_path: Path | None = None,
        output_filename: str = "",
        log_callback: typing.Callable[[str], None] | None = None
    ) -> Path:
        """Generic script improvement method for different models"""
        
        try:
            # Load script
            script_path = script_path or (self.scripts_dir / "01.narration_raw.json")
            if not script_path.exists():
                # Try previous step's output
                prev_files = sorted(self.scripts_dir.glob("*.json"))
                if len(prev_files) > 0:
                    script_path = prev_files[-1]
                else:
                    raise FileNotFoundError(f"Script file not found: {script_path}")
            
            with open(script_path, "r", encoding="utf-8") as f:
                script_json = json.load(f)
            
            # Load prompt
            prompt_template = self._load_prompt(f"improve_script_{step_name}.md")
            prompt = prompt_template.replace("{script_json}", json.dumps(script_json, ensure_ascii=False, indent=2))
            
            # Call appropriate API
            if client == "gemini":
                improved_json = await self._call_gemini_for_improvement(prompt, model)
            elif client == "deepseek":
                improved_json = await self._call_deepseek_for_improvement(prompt, model)
            elif client == "qwen":
                improved_json = await self._call_qwen_for_improvement(prompt, model)
            else:
                raise ValueError(f"Unknown client: {client}")
            
            # Save improved script
            output_path = self.scripts_dir / output_filename
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(improved_json, f, indent=2, ensure_ascii=False)
            
            self.log(f"[+] Script improved ({client}): {output_path}", log_callback)
            
            return output_path
            
        except Exception as e:
            self.log(f"[!] Script improvement ({client}) failed: {e}", log_callback)
            raise
    
    async def _call_gemini_for_improvement(self, prompt: str, model: str) -> list[dict]:
        """Call Gemini API for script improvement"""
        response = self.gemini_client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.5,
                top_p=0.9,
                max_output_tokens=8192,
                response_mime_type="application/json",
            )
        )
        return self._parse_json_response(response.text)
    
    async def _call_deepseek_for_improvement(self, prompt: str, model: str) -> list[dict]:
        """Call DeepSeek API for script improvement"""
        if not self.deepseek_api_key:
            self.log("[!] DeepSeek API key not found, skipping DeepSeek improvement...", None)
            # Return current script unchanged
            prev_files = sorted(self.scripts_dir.glob("*.json"))
            if prev_files:
                with open(prev_files[-1], "r", encoding="utf-8") as f:
                    return json.load(f)
            raise ValueError("DeepSeek API key not found and no previous script available")
        
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.deepseek_api_key}"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5,
            "max_tokens": 8000,
            "response_format": {"type": "json_object"}
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"DeepSeek API error: {response.status} - {error_text}")
                
                result = await response.json()
                content = result["choices"][0]["message"]["content"]
                return self._parse_json_response(content)
    
    async def _call_qwen_for_improvement(self, prompt: str, model: str) -> list[dict]:
        """Call Qwen (DashScope) API for script improvement"""
        if not self.dashscope_api_key:
            self.log("[!] DashScope API key not found, skipping Qwen improvement...", None)
            # Return current script unchanged
            prev_files = sorted(self.scripts_dir.glob("*.json"))
            if prev_files:
                with open(prev_files[-1], "r", encoding="utf-8") as f:
                    return json.load(f)
            raise ValueError("DashScope API key not found and no previous script available")

        # Using DashScope OpenAI-compatible API
        # Try international endpoint first, fallback to China endpoint
        url = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"
        
        # Use qwen3.5-plus model (latest)
        actual_model = "qwen3.5-plus" if model == "qwen-plus" else model
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.dashscope_api_key}"
        }
        payload = {
            "model": actual_model,
            "messages": [
                {"role": "system", "content": "You are a professional script editor. Output ONLY valid JSON."},
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
                        # Try fallback to China endpoint
                        url_cn = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
                        self.log(f"[!] International endpoint failed, trying China endpoint...", None)
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
    
    # ========== Step 6: Subtitle Generation ==========
    
    async def generate_subtitle(
        self,
        script_path: Path | None = None,
        log_callback: typing.Callable[[str], None] | None = None
    ) -> Path:
        """
        Step 6: Generate SRT subtitle file from final script.
        """
        self.current_step = 6
        self.log("[-] Step 6/7: Generating subtitle file (ko.srt)...", log_callback)
        
        try:
            # Load final script
            script_path = script_path or (self.scripts_dir / "04.narration_final.json")
            if not script_path.exists():
                # Try to find the latest script
                prev_files = sorted(self.scripts_dir.glob("*.json"))
                if prev_files:
                    script_path = prev_files[-1]
                else:
                    raise FileNotFoundError("No script file found")
            
            with open(script_path, "r", encoding="utf-8") as f:
                script_json = json.load(f)
            
            # Load prompt
            prompt_template = self._load_prompt("generate_subtitle.md")
            prompt = prompt_template.replace("{script_json}", json.dumps(script_json, ensure_ascii=False, indent=2))
            
            # Generate SRT using Gemini
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=prompt,
            )
            
            srt_content = response.text.strip()
            
            # Clean up if wrapped in code blocks
            if srt_content.startswith("```"):
                srt_content = srt_content.split("```", 1)[1]
                if srt_content.startswith("srt"):
                    srt_content = srt_content[3:]
                srt_content = srt_content.split("```")[0].strip()
            
            # Save subtitle
            output_path = self.subtitles_dir / "ko.srt"
            output_path.write_text(srt_content, encoding="utf-8")
            
            self.log(f"[+] Subtitle generated: {output_path}", log_callback)
            
            # Count subtitles
            subtitle_count = len([l for l in srt_content.split('\n') if l.strip().isdigit()])
            self.log(f"    Subtitle entries: {subtitle_count}", log_callback)
            
            return output_path
            
        except Exception as e:
            self.log(f"[!] Subtitle generation failed: {e}", log_callback)
            raise
    
    # ========== Full Pipeline ==========
    
    async def run_full_pipeline(
        self,
        topic: str,
        context: str = "",
        log_callback: typing.Callable[[str], None] | None = None
    ) -> dict[str, Path]:
        """
        Run the complete story-to-script pipeline.
        
        Args:
            topic: Story title or topic
            context: Additional context (optional)
            log_callback: Optional callback for logging
            
        Returns:
            Dictionary with paths to all generated files
        """
        self.log("=" * 60, log_callback)
        self.log(f"🎬 Starting Story-to-Script Pipeline", log_callback)
        self.log(f"   Topic: {topic}", log_callback)
        self.log("=" * 60, log_callback)
        
        results = {}
        
        try:
            # Step 1: Generate content
            results["content"] = await self.generate_content(topic, context, log_callback)
            await asyncio.sleep(1)  # Rate limiting
            
            # Step 2: Generate narration script
            results["narration_raw"] = await self.generate_narration_script(log_callback=log_callback)
            await asyncio.sleep(1)
            
            # Step 3: Improve with Gemini
            results["improved_gemini"] = await self.improve_script_step1(log_callback=log_callback)
            await asyncio.sleep(1)
            
            # Step 4: Improve with DeepSeek
            results["improved_deepseek"] = await self.improve_script_step2(log_callback=log_callback)
            await asyncio.sleep(1)
            
            # Step 5: Improve with Qwen
            results["improved_qwen"] = await self.improve_script_step3(log_callback=log_callback)
            await asyncio.sleep(1)
            
            # Step 6: Generate subtitle
            results["subtitle"] = await self.generate_subtitle(log_callback=log_callback)
            
            self.log("=" * 60, log_callback)
            self.log("✅ Pipeline Complete!", log_callback)
            self.log("=" * 60, log_callback)
            
            return results
            
        except Exception as e:
            self.log(f"[!] Pipeline failed at step {self.current_step}: {e}", log_callback)
            raise
    
    # ========== Utility Methods ==========
    
    def _parse_json_response(self, text: str) -> list[dict]:
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
            return json.loads(clean)
        except json.JSONDecodeError as e:
            print(f"[!] JSON Parse Error: {e}")
            print(f"    Raw text: {text[:200]}...")
            raise
