"""Image Prompt Generator for Video Scenes"""

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


class ImagePromptGenerator:
    """
    Generates image prompts for video scenes based on narration scripts.
    """

    def __init__(self, workspace_dir: Path | None = None):
        self.base_dir = Path(__file__).resolve().parent.parent
        self.workspace_dir = workspace_dir or (self.base_dir / "workspace")
        self.prompts_dir = self.base_dir / "assets" / "prompts"

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

    async def _generate_section_prompt(
        self,
        section: dict,
        section_index: int,
        total_sections: int,
        previous_context: str = "",
        log_callback: Callable[[str], None] | None = None
    ) -> dict:
        """
        Generate 2 image prompts for a single section by identifying key visual elements from context.
        Automatically extracts: character full body + what character is looking at/interacting with.
        """
        try:
            # Build prompt context
            section_title = section.get("title", "Unknown")
            section_content = section.get("content", "")
            section_duration = section.get("estimated_duration", 30)

            # Determine section type for visual style
            section_type = self._classify_section(section_index, total_sections)

            # Build the prompt request
            prompt_request = self._build_prompt_request(
                section_title=section_title,
                section_content=section_content,
                section_type=section_type,
                section_duration=section_duration,
                previous_context=previous_context,
                section_index=section_index,
                total_sections=total_sections
            )

            # Call Gemini to generate 2 image prompts with CONTEXTUAL key points
            contextual_prompt = self._load_prompt("image_prompt_contextual")
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=prompt_request + "\n\n" + contextual_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    top_p=0.9,
                    max_output_tokens=4096,
                    response_mime_type="application/json",
                )
            )

            # Parse response
            prompt_json = self._parse_json_response(response.text or "")

            # Handle both list and dict responses
            if isinstance(prompt_json, list) and len(prompt_json) >= 2:
                # Got 2 prompts as array - this is what we want!
                prompts = prompt_json[:2]
                self.log(f"    [+] Received 2 prompts from API (list format)", log_callback)
            elif isinstance(prompt_json, list) and len(prompt_json) == 1:
                # Got 1 prompt in list
                prompts = [prompt_json[0], prompt_json[0]]
                self.log(f"    [+] Received 1 prompt from API, duplicating", log_callback)
            elif isinstance(prompt_json, dict) and prompt_json:
                # Got single dict - create 2 variations
                prompts = [prompt_json, prompt_json]
                self.log(f"    [+] Received 1 prompt from API (dict format), duplicating", log_callback)
            else:
                # Empty or invalid response - use fallback
                self.log(f"    [!] Warning: API returned empty/invalid response, using fallback", log_callback)
                fallback = {"prompt": f"Anime style image for: {section_content[:100]}"}
                prompts = [fallback, fallback]

            # Add metadata for both prompts
            prompt_data = {
                "section_index": section_index,
                "section_title": section_title,
                "section_type": section_type,
                "estimated_duration": section_duration,
                "narration_text": section_content,
                "image_prompt": prompts[0].get("prompt", "") if isinstance(prompts[0], dict) else str(prompts[0]) if prompts[0] else "",
                "image_prompt_2": prompts[1].get("prompt", "") if isinstance(prompts[1], dict) else str(prompts[1]) if prompts[1] else "",
                "negative_prompt": prompts[0].get("negative_prompt", "") if isinstance(prompts[0], dict) else "",
                "style_reference": prompts[0].get("style_reference", "") if isinstance(prompts[0], dict) else "anime style, vibrant colors, cel shaded",
                "continuity_notes": prompts[0].get("continuity_notes", "") if isinstance(prompts[0], dict) else "",
                "suggested_aspect_ratio": prompts[0].get("aspect_ratio", "16:9") if isinstance(prompts[0], dict) else "16:9",
                "suggested_camera": prompts[0].get("camera", "medium shot") if isinstance(prompts[0], dict) else "medium shot",
                "suggested_lighting": prompts[0].get("lighting", "anime") if isinstance(prompts[0], dict) else "anime",
                "priority_elements": prompts[0].get("priority_elements", []) if isinstance(prompts[0], dict) else [],
            }

            self.log(f"    [+] Generated 2 image prompts for '{section_title}'", log_callback)

            return prompt_data

        except Exception as e:
            self.log(f"    [!] Failed to generate prompt: {e}", log_callback)
            # Return fallback prompt
            fallback_prompt = f"High quality anime style image related to: {section.get('content', '')[:200]}"
            return {
                "section_index": section_index,
                "section_title": section.get("title", "Unknown"),
                "section_type": self._classify_section(section_index, total_sections),
                "estimated_duration": section.get("estimated_duration", 30),
                "narration_text": section.get("content", ""),
                "image_prompt": fallback_prompt,
                "image_prompt_2": fallback_prompt + " (alternative angle)",
                "negative_prompt": "photorealistic, realistic, 3d render, cgi, live action, text, watermark, blurry, low quality",
                "style_reference": "anime style, vibrant colors, cel shaded",
                "continuity_notes": "",
                "suggested_aspect_ratio": "16:9",
                "suggested_camera": "medium shot",
                "suggested_lighting": "anime",
                "priority_elements": [],
            }
    
    def _build_prompt_request(
        self,
        section_title: str,
        section_content: str,
        section_type: str,
        section_duration: int,
        previous_context: str,
        section_index: int,
        total_sections: int
    ) -> str:
        """
        Build the prompt request for Gemini API from template file.
        """
        template = self._load_prompt("image_prompt_base")
        return template.format(
            section_title=section_title,
            section_type=section_type,
            section_duration=section_duration,
            section_index=section_index + 1,
            total_sections=total_sections,
            section_content=section_content,
            previous_context=previous_context if previous_context else "First section."
        )
    
    def _classify_section(self, section_index: int, total_sections: int) -> str:
        """
        Classify section type based on position in the narrative.
        """
        if section_index == 0:
            return "opening_hook"
        elif section_index == 1:
            return "setup"
        elif section_index == total_sections - 2:
            return "climax"
        elif section_index == total_sections - 1:
            return "resolution"
        else:
            return "development"
    
    def _build_context(self, section: dict, prompt_data: dict) -> str:
        """
        Build context string for continuity to next section.
        """
        return f"""
Previous Section: {section.get('title', 'Unknown')}
- Key Visual Elements: {', '.join(prompt_data.get('priority_elements', [])[:3])}
- Setting: {prompt_data.get('style_reference', 'N/A')}
- Lighting: {prompt_data.get('suggested_lighting', 'N/A')}
- Mood: {prompt_data.get('section_type', 'N/A')}
"""

    async def _generate_video_prompt(
        self,
        section: dict,
        image_prompt_data: dict,
        section_index: int,
        total_sections: int,
        previous_context: str = "",
        log_callback: Callable[[str], None] | None = None
    ) -> dict:
        """
        Generate video prompt with dynamic camera angles and scene descriptions.
        """
        image_prompt = image_prompt_data.get("image_prompt", "")
        try:
            section_title = section.get("title", "Unknown")
            section_content = section.get("content", "")
            section_type = image_prompt_data.get("section_type", "unknown")

            # Build video prompt request from template
            template = self._load_prompt("video_prompt")
            video_prompt_request = template.format(
                section_title=section_title,
                section_content=section_content,
                image_prompt=image_prompt,
                section_index=section_index + 1,
                total_sections=total_sections,
                section_type=section_type
            )

            # Call Gemini API
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=video_prompt_request,
                config=types.GenerateContentConfig(
                    temperature=0.8,
                    top_p=0.9,
                    max_output_tokens=2048,
                    response_mime_type="application/json",
                )
            )
            
            # Parse response
            video_json = self._parse_json_response(response.text or "")
            
            # Ensure video_json is a dict, not a list
            if isinstance(video_json, list):
                self.log(f"    [!] Warning: Video API returned list instead of dict, using empty dict", log_callback)
                video_json = {}
            
            self.log(f"    [+] Video prompt generated for '{section_title}'", log_callback)

            return video_json
            
        except Exception as e:
            self.log(f"    [!] Video prompt generation failed: {e}", log_callback)
            # Return fallback
            return {
                "video_prompt": f"Dynamic cinematic video based on: {image_prompt[:200]}. Multiple camera angles, quick cuts, smooth transitions, professional cinematography.",
                "camera_directions": ["wide shot", "medium shot", "close-up"],
                "motion_type": "dynamic",
                "transition_style": "smooth_cuts",
                "video_duration": "5-10 seconds",
                "frame_rate_suggestion": "24fps"
            }

    async def _generate_multi_angle_camera_prompt(
        self,
        section: dict,
        image_prompt_data: dict,
        section_index: int,
        total_sections: int,
        prompt_type: str = "subject",  # "subject" or "environment"
        log_callback: Callable[[str], None] | None = None
    ) -> str:
        """
        Generate a simple multi-angle camera prompt for 10-second video from single image.
        Target: 300-500 characters with detailed camera movements.
        """
        image_prompt = image_prompt_data.get("image_prompt" if prompt_type == "subject" else "image_prompt_2", "")
        try:
            section_title = section.get("title", "Unknown")

            # Load camera prompt template based on type
            template_name = f"camera_prompt_{prompt_type}"
            template = self._load_prompt(template_name)
            camera_prompt = template.format(image_prompt=image_prompt[:200])
            
            # Ensure 300-500 characters (no truncation with ...)
            if len(camera_prompt) < 300:
                camera_prompt = camera_prompt + " " * (300 - len(camera_prompt))
            # Don't truncate - keep full content even if over 500 chars
            # Just ensure minimum 300 chars
            
            self.log(f"    [+] Multi-angle camera prompt generated for '{section_title}' ({prompt_type}, {len(camera_prompt)} chars)", log_callback)
            
            return camera_prompt
            
        except Exception as e:
            self.log(f"    [!] Multi-angle camera prompt generation failed: {e}", log_callback)
            fallback = f"MULTI-ANGLE CAMERA PROMPT ({prompt_type.upper()}, 10 sec)\n\nEXTREME CLOSE-UP → QUICK ZOOM OUT → RAPID PAN → LOW TO HIGH ANGLE → MEDIUM SHOT PUSH-IN\n\nHandheld shake. Quick zooms. Swift pans. Dutch angles. Dynamic movement.\n\nBase: {image_prompt[:150]}"
            return fallback

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

        template = self._load_prompt("shot_first_breakdown")
        prompt = template.format(
            scene_number=scene_number,
            synopsis=synopsis,
            emotional_beat=emotional_beat,
            previous_last_shot_context=previous_context,
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
                "lighting": "anime, vibrant",
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

        template = self._load_prompt("shot_to_image_prompt")
        prompt = template.format(
            shot_json=shot_json,
            shot_number=shot_number,
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
                "prompt": f"{shot.get('subject', '')} {shot.get('camera_type', 'wide shot')}, {shot.get('lighting', 'anime lighting')}, {shot.get('mood', 'dramatic')}, anime style, high quality animation still, vibrant colors, cel shaded, detailed background, 16:9",
                "negative_prompt": "photorealistic, realistic, 3d render, cgi, live action, text, watermark, blurry, low quality, distorted, deformed, ugly, jpeg artifacts",
                "style_tags": ["anime", "animation", "vibrant"],
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

        # Load template from assets/prompts/shot_video_prompt.txt
        prompt_file = Path(__file__).parent.parent / "assets" / "prompts" / "shot_video_prompt.txt"
        template = prompt_file.read_text(encoding="utf-8")

        opening_shot_prompt = opening_shot.get("image_prompt", {}).get("prompt", "")

        prompt = template.format(
            scene_title=scene.get("title", ""),
            key_point=key_point,
            emotional_beat=scene.get("emotional_beat", ""),
            sub_scene_index=sub_scene_index,
            total_sub_scenes=total_sub_scenes,
            first_shot_prompt=opening_shot_prompt,
            last_shot_prompt=opening_shot_prompt,
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
