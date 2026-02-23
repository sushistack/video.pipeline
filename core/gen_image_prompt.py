"""Image Prompt Generator for Video Scenes"""

import os
import json
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


class ImagePromptGenerator:
    """
    Generates image prompts for video scenes based on narration scripts.
    Supports SCP facts injection for character consistency (Frozen Descriptor).
    """

    def __init__(self, workspace_dir: Path | None = None, scp_facts: dict | None = None):
        self.base_dir = Path(__file__).resolve().parent.parent
        self.workspace_dir = workspace_dir or (self.base_dir / "workspace")
        self.prompts_dir = self.base_dir / "assets" / "prompts" / "image_prompt"

        # SCP facts for character consistency
        self.scp_facts = scp_facts
        self._frozen_descriptor: str | None = None
        self._entity_visual_identity: str | None = None

        # Build frozen descriptor if SCP facts provided
        if scp_facts:
            self._frozen_descriptor = self._build_frozen_descriptor(scp_facts)
            self._entity_visual_identity = self._build_entity_visual_identity(scp_facts)

        # Load prompt templates
        self._prompt_templates = {}

        # API Keys
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in .env")
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        self.dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")

        # Initialize Gemini client
        self.gemini_client = genai.Client(api_key=self.gemini_api_key)

        # Model configurations
        # STEP 1 (Shot Breakdown): DeepSeek Reasoner - strong narrative/logical reasoning
        # STEP 2 (Image Prompts): Gemini Flash - strong visual/creative description
        # STEP 3 (Review):        Qwen - strong creative writing critique
        self.gemini_model = "gemini-2.0-flash"
        self.deepseek_model = "deepseek-reasoner"
        self.qwen_model = "qwen-plus"

    def _build_frozen_descriptor(self, scp_facts: dict) -> str:
        """Build a frozen character descriptor from SCP facts for image consistency.

        This descriptor will be used VERBATIM in every prompt where the entity appears.
        """
        visual = scp_facts.get("visual_elements", {})

        # Start with physical description
        parts = []

        # Height/build from physical_description
        phys_desc = scp_facts.get("physical_description", "")
        if phys_desc:
            # Extract key visual attributes
            parts.append(phys_desc.split(".")[0])  # First sentence usually has build

        # Appearance from visual_elements
        appearance = visual.get("appearance", "")
        if appearance:
            parts.append(appearance)

        # Distinguishing features
        features = visual.get("distinguishing_features", [])
        if features:
            parts.extend(features)

        # Combine and clean
        full_desc = ", ".join(parts)

        # Convert to image-gen-friendly format (lowercase, remove narrative language)
        full_desc = full_desc.lower()
        full_desc = full_desc.replace("scp-", "the entity, SCP-")
        full_desc = full_desc.replace("it ", "")
        full_desc = full_desc.replace("its ", "")

        return full_desc

    def _build_entity_visual_identity(self, scp_facts: dict) -> str:
        """Build entity visual identity section for prompt injection."""
        visual = scp_facts.get("visual_elements", {})

        lines = [
            f"**SCP ID**: {scp_facts.get('scp_id', 'Unknown')}",
            f"**Object Class**: {scp_facts.get('object_class', 'Unknown')}",
            "",
            "**Physical Description**:",
            scp_facts.get("physical_description", "N/A"),
            "",
            "**Visual Appearance**:",
            visual.get("appearance", "N/A"),
            "",
            "**Distinguishing Features**:",
        ]

        for feature in visual.get("distinguishing_features", []):
            lines.append(f"- {feature}")

        lines.extend([
            "",
            "**Environment Setting**:",
            visual.get("environment_setting", "N/A"),
        ])

        return "\n".join(lines)

    def set_scp_facts(self, scp_facts: dict):
        """Set or update SCP facts and rebuild frozen descriptor."""
        self.scp_facts = scp_facts
        self._frozen_descriptor = self._build_frozen_descriptor(scp_facts)
        self._entity_visual_identity = self._build_entity_visual_identity(scp_facts)

    @property
    def frozen_descriptor(self) -> str:
        """Get the frozen character descriptor."""
        return self._frozen_descriptor or "(No entity descriptor available)"

    @property
    def entity_visual_identity(self) -> str:
        """Get the entity visual identity section."""
        return self._entity_visual_identity or "(No entity visual identity available)"

    def _load_prompt(self, name: str) -> str:
        """Load prompt template from file with caching."""
        if name not in self._prompt_templates:
            prompt_path = self.prompts_dir / f"{name}.txt"
            if prompt_path.exists():
                self._prompt_templates[name] = prompt_path.read_text(encoding="utf-8")
            else:
                raise FileNotFoundError(f"Prompt template not found: {prompt_path}")
        return self._prompt_templates[name]

    def log(self, message: str, callback: Callable[[str], None] | None = None):
        """Log message with optional callback"""
        print(message)
        if callback:
            callback(message)

    # ─────────────────────────────────────────────────────────────────────────
    # Multi-LLM API Helpers
    # ─────────────────────────────────────────────────────────────────────────

    async def _call_deepseek_json(self, prompt: str) -> dict:
        """Call DeepSeek Reasoner API for JSON response (strong at logical reasoning)."""
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.deepseek_api_key}",
        }
        payload = {
            "model": self.deepseek_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.6,
            "max_tokens": 4000,
            "response_format": {"type": "json_object"},
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json=payload, headers=headers,
                timeout=aiohttp.ClientTimeout(total=180)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"DeepSeek API error: {response.status} - {error_text}")
                result = await response.json()
                content = result["choices"][0]["message"]["content"]
                return self._parse_json_response(content)

    async def _call_qwen_json(self, prompt: str) -> list | dict:
        """Call Qwen (DashScope) API for JSON response (strong at creative critique)."""
        url = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.dashscope_api_key}",
        }
        payload = {
            "model": self.qwen_model,
            "messages": [
                {"role": "system", "content": "You are a visual prompt quality reviewer. Output ONLY valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.5,
            "max_tokens": 4000,
            "response_format": {"type": "json_object"},
        }
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    url, json=payload, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status != 200:
                        # Fallback to China endpoint
                        url_cn = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
                        async with session.post(
                            url_cn, json=payload, headers=headers,
                            timeout=aiohttp.ClientTimeout(total=120)
                        ) as response_cn:
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
            return json.loads(clean)
        except json.JSONDecodeError as e:
            print(f"[!] JSON Parse Error: {e}")
            print(f"    Raw text: {text[:200]}...")
            return {}

    # ─────────────────────────────────────────────────────────────────────────
    # Opening Shot Pipeline (Simplified)
    # OPENING (DeepSeek): scene → opening shot breakdown
    # OPENING (Gemini):   opening shot → image prompt
    # ─────────────────────────────────────────────────────────────────────────

    async def _generate_opening_shot_breakdown(
        self,
        scene: dict,
        previous_scene_prompt: dict | None = None,
        log_callback: Callable[[str], None] | None = None
    ) -> dict:
        """
        Generate ONE opening shot description for a scene.
        Uses DeepSeek Reasoner → Gemini fallback.
        """
        scene_number = scene.get("scene_number", 0)
        synopsis = "\n".join(scene.get("key_points", []))
        emotional_beat = scene.get("emotional_beat", "dramatic")

        # Build continuity context from previous scene
        previous_context = ""
        if previous_scene_prompt:
            prev_shot = previous_scene_prompt.get("shot", previous_scene_prompt)
            prev_img = previous_scene_prompt.get("image_prompt", {})
            context_lines = [
                "## Previous Scene — Opening Shot Context",
                "Connect the atmosphere of this opening shot naturally to the previous scene.",
                f"- Camera type: {prev_shot.get('camera_type', '')}",
                f"- Subject: {prev_shot.get('subject', '')}",
                f"- Lighting: {prev_shot.get('lighting', '')}",
                f"- Mood: {prev_shot.get('mood', '')}",
            ]
            if prev_img.get("prompt"):
                context_lines.append(f"- Image prompt: {prev_img['prompt'][:300]}")
            previous_context = "\n".join(context_lines) + "\n"

        template = self._load_prompt("01_shot_first_breakdown")
        prompt = template.format(
            scene_number=scene_number,
            synopsis=synopsis,
            emotional_beat=emotional_beat,
            previous_last_shot_context=previous_context,
            entity_visual_identity=self.entity_visual_identity,
            frozen_descriptor=self.frozen_descriptor,
        )

        try:
            if self.deepseek_api_key:
                self.log(f"    [OPENING] Using DeepSeek Reasoner for opening shot...", log_callback)
                result = await self._call_deepseek_json(prompt)
            else:
                self.log(f"    [OPENING] Using Gemini fallback for opening shot...", log_callback)
                response = self.gemini_client.models.generate_content(
                    model=self.gemini_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.7, top_p=0.9, max_output_tokens=1024,
                        response_mime_type="application/json",
                    )
                )
                result = self._parse_json_response(response.text or "")
            # Ensure shot_number is set
            if isinstance(result, dict):
                result["shot_number"] = 1
                result["role"] = "opening"
            self.log(f"    [OPENING] Scene {scene_number}: opening shot breakdown done", log_callback)
            return result
        except Exception as e:
            self.log(f"    [!] Opening shot breakdown failed for scene {scene_number}: {e}", log_callback)
            return {
                "shot_number": 1, "role": "opening",
                "camera_type": "wide",
                "subject": synopsis[:200],
                "lighting": "cinematic, dramatic shadows",
                "mood": emotional_beat,
                "motion": "static",
            }

    async def _step2_shot_to_image_prompt(
        self,
        shot: dict,
        log_callback: Callable[[str], None] | None = None
    ) -> dict:
        """
        STEP 2: Convert a single shot dict into an image generation prompt.
        Returns dict with prompt, negative_prompt, style_tags, recommended_aspect_ratio.
        """
        shot_number = shot.get("shot_number", 0)
        shot_json = json.dumps(shot, ensure_ascii=False, indent=2)

        template = self._load_prompt("02_shot_to_image_prompt")
        prompt = template.format(
            shot_json=shot_json,
            shot_number=shot_number,
            frozen_descriptor=self.frozen_descriptor,
        )

        try:
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    top_p=0.9,
                    max_output_tokens=1024,
                    response_mime_type="application/json",
                )
            )
            result = self._parse_json_response(response.text or "")
            # Unwrap if API returned a list
            if isinstance(result, list):
                result = result[0] if result else {}
            self.log(f"    [STEP 2] Shot {shot_number}: image prompt generated", log_callback)
            return result
        except Exception as e:
            self.log(f"    [!] Image prompt generation failed for shot {shot_number}: {e}", log_callback)
            return {
                "shot_number": shot_number,
                "prompt": f"{shot.get('subject', '')} {shot.get('camera_type', 'wide shot')}, {shot.get('lighting', 'cinematic lighting')}, {shot.get('mood', 'dramatic')}, cinematic still, dark horror photography, highly detailed, 8k, sharp focus, volumetric lighting, film grain, 16:9",
                "negative_prompt": "cartoon, anime, bright colors, cheerful, blurry, low quality, deformed hands, extra fingers, watermark, text, signature, cropped",
                "style_tags": ["horror", "cinematic", "dark"],
                "recommended_aspect_ratio": "16:9",
            }

    async def _generate_sub_scene_video_prompt(
        self,
        scene: dict,
        key_point: str,
        opening_shot: dict,
        sub_scene_index: int,
        total_sub_scenes: int,
        log_callback=None,
    ) -> dict:
        """Generate a video prompt describing the visual journey from opening shot."""
        if log_callback:
            log_callback(f"    [VIDEO] Generating sub-scene video prompt (Gemini)...")

        # Load template from assets/prompts/image_prompt/03_shot_video.txt
        template = self._load_prompt("03_shot_video")

        opening_shot_prompt = opening_shot.get("image_prompt", {}).get("prompt", "")

        prompt = template.format(
            scene_title=scene.get("title", ""),
            key_point=key_point,
            emotional_beat=scene.get("emotional_beat", ""),
            sub_scene_index=sub_scene_index,
            total_sub_scenes=total_sub_scenes,
            first_shot_prompt=opening_shot_prompt,
            last_shot_prompt=opening_shot_prompt,
            frozen_descriptor=self.frozen_descriptor,
        )

        video_prompt = {"video_prompt": "", "camera_directions": [], "motion_type": "", "transition_style": ""}
        try:
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.7,
                ),
            )
            parsed = self._parse_json_response(response.text)
            if isinstance(parsed, dict):
                video_prompt = parsed
        except Exception as e:
            if log_callback:
                log_callback(f"    [!] Video prompt generation failed: {e}")

        return video_prompt

    async def generate_sub_scene_prompts(
        self,
        scene: dict,
        key_point: str,
        sub_scene_index: int,
        total_sub_scenes: int,
        previous_opening_shot: dict | None = None,
        log_callback=None,
        speed_mode: bool = False,  # Skip review for faster generation
    ) -> dict:
        """
        Generate opening image prompt + video prompt for a single sub-scene (key_point).

        Simplified pipeline: only generates opening shot prompt.
        Cross-sub-scene continuity: previous_opening_shot from prior sub-scene feeds this one.

        Speed Mode: Skips review step for faster generation.
        """
        # Build synthetic scene dict scoped to this single key_point
        synthetic_scene = {
            "scene_number": scene.get("scene_number", 1),
            "title": scene.get("title", ""),
            "key_points": [key_point],  # SINGLE key_point only
            "emotional_beat": scene.get("emotional_beat", ""),
            "duration_seconds": max(10, scene.get("duration_seconds", 30) // max(1, total_sub_scenes)),
        }

        # Step 1: Opening shot breakdown (DeepSeek)
        if log_callback:
            log_callback(f"    [1/2] Opening shot breakdown (DeepSeek)...")
        opening_shot_desc = await self._generate_opening_shot_breakdown(
            synthetic_scene, previous_opening_shot, log_callback
        )

        # Step 2: Opening shot image prompt (Gemini)
        if log_callback:
            log_callback(f"    [2/2] Opening shot image prompt (Gemini)...")
        opening_img_prompt = await self._step2_shot_to_image_prompt(opening_shot_desc, log_callback)
        opening_shot = {"shot": opening_shot_desc, "image_prompt": opening_img_prompt}

        # Step 3: Video prompt (Gemini)
        if log_callback:
            log_callback(f"    [+] Video prompt (Gemini)...")
        video_prompt_data = await self._generate_sub_scene_video_prompt(
            scene=scene,
            key_point=key_point,
            opening_shot=opening_shot,
            sub_scene_index=sub_scene_index,
            total_sub_scenes=total_sub_scenes,
            log_callback=log_callback,
        )

        return {
            "sub_scene_index": sub_scene_index,
            "key_point": key_point,
            "opening_shot": opening_shot,
            "video_prompt": video_prompt_data,
        }

    async def generate_scene_prompts(
        self,
        scene: dict,
        previous_opening_shot: dict | None = None,
        log_callback: Callable[[str], None] | None = None
    ) -> dict:
        """
        Run the opening shot pipeline for a single scene:
          OPENING (DeepSeek): key_points → opening shot breakdown
          OPENING (Gemini):   opening shot → image prompt
        Returns scene result with opening_shot, plus opening_shot for cross-scene continuity.
        """
        scene_number = scene.get("scene_number", 0)
        scene_title = scene.get("title", "Unknown")

        self.log(f"  [*] Scene {scene_number}: {scene_title}", log_callback)

        # OPENING SHOT: breakdown → image prompt
        opening_shot_desc = await self._generate_opening_shot_breakdown(scene, previous_opening_shot, log_callback)
        opening_img_prompt = await self._step2_shot_to_image_prompt(opening_shot_desc, log_callback)
        opening_shot = {"shot": opening_shot_desc, "image_prompt": opening_img_prompt}

        return {
            "scene_number": scene_number,
            "scene_title": scene_title,
            "emotional_beat": scene.get("emotional_beat", ""),
            "synopsis": "\n".join(scene.get("key_points", [])),
            "opening_shot": opening_shot,
        }

    async def generate_all_scene_prompts(
        self,
        project_id: str,
        log_callback: Callable[[str], None] | None = None
    ) -> list[dict]:
        """
        Generate image prompts for all scenes in a project using the opening shot pipeline.
        Reads from workspace/{project_id}/scripts/02_scene_structure.json.
        Saves output to workspace/{project_id}/scripts/05_image_prompts.json.
        """
        scene_structure_path = self.workspace_dir / project_id / "scripts" / "02_scene_structure.json"

        if not scene_structure_path.exists():
            raise FileNotFoundError(f"Scene structure not found: {scene_structure_path}")

        scene_structure = json.loads(scene_structure_path.read_text(encoding="utf-8"))
        scenes = scene_structure.get("scenes", [])
        topic = scene_structure.get("topic", project_id)

        self.log(f"[*] Generating image prompts for '{topic}' ({len(scenes)} scenes)", log_callback)

        results = []
        previous_opening_shot = None

        for scene in scenes:
            scene_result = await self.generate_scene_prompts(scene, previous_opening_shot, log_callback)
            results.append(scene_result)
            previous_opening_shot = scene_result.get("opening_shot")

        # Save results
        output_path = self.workspace_dir / project_id / "scripts" / "05_image_prompts.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

        total_shots = len(results)  # 1 opening shot per scene
        self.log(f"[+] Done: {len(scenes)} scenes, {total_shots} shots → {output_path}", log_callback)

        return results
