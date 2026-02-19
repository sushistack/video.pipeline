"""Image Prompt Generator for Video Scenes"""

import os
import sys
import json
import asyncio
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

        # Initialize Gemini client
        self.gemini_client = genai.Client(api_key=self.gemini_api_key)
        self.gemini_model = "gemini-2.0-flash"

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
            prompt_json = self._parse_json_response(response.text)

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
                fallback = {"prompt": f"Cinematic image for: {section_content[:100]}"}
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
                "style_reference": prompts[0].get("style_reference", "") if isinstance(prompts[0], dict) else "cinematic, photorealistic, 8k",
                "continuity_notes": prompts[0].get("continuity_notes", "") if isinstance(prompts[0], dict) else "",
                "suggested_aspect_ratio": prompts[0].get("aspect_ratio", "16:9") if isinstance(prompts[0], dict) else "16:9",
                "suggested_camera": prompts[0].get("camera", "medium shot") if isinstance(prompts[0], dict) else "medium shot",
                "suggested_lighting": prompts[0].get("lighting", "cinematic") if isinstance(prompts[0], dict) else "cinematic",
                "priority_elements": prompts[0].get("priority_elements", []) if isinstance(prompts[0], dict) else [],
            }

            self.log(f"    [+] Generated 2 image prompts for '{section_title}'", log_callback)

            return prompt_data

        except Exception as e:
            self.log(f"    [!] Failed to generate prompt: {e}", log_callback)
            # Return fallback prompt
            fallback_prompt = f"High quality cinematic image related to: {section.get('content', '')[:200]}"
            return {
                "section_index": section_index,
                "section_title": section.get("title", "Unknown"),
                "section_type": self._classify_section(section_index, total_sections),
                "estimated_duration": section.get("estimated_duration", 30),
                "narration_text": section.get("content", ""),
                "image_prompt": fallback_prompt,
                "image_prompt_2": fallback_prompt + " (alternative angle)",
                "negative_prompt": "low quality, blurry, distorted, deformed, ugly, watermark, text",
                "style_reference": "cinematic, photorealistic, 8k",
                "continuity_notes": "",
                "suggested_aspect_ratio": "16:9",
                "suggested_camera": "medium shot",
                "suggested_lighting": "cinematic",
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
        try:
            section_title = section.get("title", "Unknown")
            section_content = section.get("content", "")
            image_prompt = image_prompt_data.get("image_prompt", "")
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
            video_json = self._parse_json_response(response.text)
            
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
        try:
            section_title = section.get("title", "Unknown")
            image_prompt = image_prompt_data.get("image_prompt" if prompt_type == "subject" else "image_prompt_2", "")

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
