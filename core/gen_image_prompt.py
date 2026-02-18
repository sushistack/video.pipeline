"""Image Prompt Generator for Video Scenes"""

import os
import sys
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
    Generates high-quality image prompts for video scenes based on narration scripts.
    
    Features:
    - Reads narration script JSON (04.narration_final.json)
    - Generates detailed image prompts for each section
    - Maintains visual continuity between sections
    - Optimized for AI image generation models
    """
    
    def __init__(self, workspace_dir: Path | None = None):
        self.base_dir = Path(__file__).resolve().parent.parent
        self.workspace_dir = workspace_dir or (self.base_dir / "workspace")
        
        # API Keys
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in .env")
        
        # Initialize Gemini client
        self.gemini_client = genai.Client(api_key=self.gemini_api_key)
        self.gemini_model = "gemini-2.0-flash"  # Stable model
        
        # Prompts directory
        self.prompts_dir = self.base_dir / "assets" / "prompts"
        
    def log(self, message: str, callback: Callable[[str], None] | None = None):
        """Log message with optional callback"""
        print(message)
        if callback:
            callback(message)
    
    async def generate_image_prompts(
        self,
        script_path: Path | None = None,
        project_id: str | None = None,
        log_callback: Callable[[str], None] | None = None,
        generate_video_prompts: bool = True
    ) -> list[dict]:
        """
        Generate image prompts for all sections in the narration script.

        Args:
            script_path: Path to 04.narration_final.json
            project_id: Project ID to find script if path not provided
            log_callback: Optional callback for logging
            generate_video_prompts: Also generate video prompts

        Returns:
            List of image prompt dictionaries
        """
        self.log("[-] Loading narration script...", log_callback)
        
        try:
            # Find script path
            if script_path is None:
                if project_id:
                    script_path = self.workspace_dir / project_id / "scripts" / "04.narration_final.json"
                else:
                    # Find latest script
                    for project_dir in sorted(self.workspace_dir.glob("project_*"), reverse=True):
                        script_path = project_dir / "scripts" / "04.narration_final.json"
                        if script_path.exists():
                            break
            
            if not script_path or not script_path.exists():
                raise FileNotFoundError(f"Script not found: {script_path}")
            
            # Load script
            with open(script_path, "r", encoding="utf-8") as f:
                script_data = json.load(f)
            
            self.log(f"[+] Loaded script: {script_path.name} ({len(script_data)} sections)", log_callback)
            
            # Generate prompts for each section
            image_prompts = []
            previous_context = ""

            for idx, section in enumerate(script_data):
                self.log(f"[-] Generating prompt for section {idx + 1}/{len(script_data)}: {section.get('title', 'Unknown')}", log_callback)

                prompt_data = await self._generate_section_prompt(
                    section=section,
                    section_index=idx,
                    total_sections=len(script_data),
                    previous_context=previous_context,
                    log_callback=log_callback
                )

                # Generate video prompt if requested
                if generate_video_prompts:
                    self.log(f"    [-] Generating video prompt for section {idx + 1}...", log_callback)
                    video_prompt = await self._generate_video_prompt(
                        section=section,
                        image_prompt_data=prompt_data,
                        section_index=idx,
                        total_sections=len(script_data),
                        previous_context=previous_context,
                        log_callback=log_callback
                    )
                    prompt_data["video_prompt"] = video_prompt
                    
                    # Generate multi-angle camera prompt
                    self.log(f"    [-] Generating multi-angle camera prompt for section {idx + 1}...", log_callback)
                    multi_angle_prompt = await self._generate_multi_angle_camera_prompt(
                        section=section,
                        image_prompt_data=prompt_data,
                        section_index=idx,
                        total_sections=len(script_data),
                        log_callback=log_callback
                    )
                    prompt_data["multi_angle_camera_prompt"] = multi_angle_prompt

                image_prompts.append(prompt_data)

                # Update context for next section (continuity)
                previous_context = self._build_context(section, prompt_data)

                await asyncio.sleep(0.5)  # Rate limiting

            # Save image prompts with all data
            output_path = script_path.parent.parent / "prompts" / "05.image_prompts.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(image_prompts, f, indent=2, ensure_ascii=False)

            # Save individual prompt text files
            image_prompt_file = output_path.parent / "image.prompt.txt"
            video_prompt_file = output_path.parent / "video.prompt.txt"
            
            # Write image prompts
            with open(image_prompt_file, "w", encoding="utf-8") as f:
                for idx, prompt_data in enumerate(image_prompts, 1):
                    f.write(f"=== SECTION {idx}/{len(image_prompts)}: {prompt_data.get('section_title', 'Unknown')} ===\n\n")
                    f.write(f"{prompt_data.get('image_prompt', '')}\n\n")
                    f.write("-" * 80 + "\n\n")
            
            # Write video prompts (video_prompt + multi_angle_camera_prompt)
            with open(video_prompt_file, "w", encoding="utf-8") as f:
                for idx, prompt_data in enumerate(image_prompts, 1):
                    f.write(f"=== SECTION {idx}/{len(image_prompts)}: {prompt_data.get('section_title', 'Unknown')} ===\n\n")
                    
                    # Video prompt
                    video_prompt = prompt_data.get("video_prompt", {})
                    if isinstance(video_prompt, dict):
                        f.write(f"[VIDEO PROMPT]\n{video_prompt.get('video_prompt', '')}\n\n")
                        f.write(f"Camera Directions: {', '.join(video_prompt.get('camera_directions', []))}\n")
                        f.write(f"Motion: {video_prompt.get('motion_type', 'N/A')}\n")
                        f.write(f"Transitions: {video_prompt.get('transition_style', 'N/A')}\n")
                        f.write(f"Duration: {video_prompt.get('video_duration', 'N/A')}\n\n")
                    
                    # Multi-angle camera prompt
                    multi_angle = prompt_data.get("multi_angle_camera_prompt", "")
                    if multi_angle:
                        f.write(f"[MULTI-ANGLE CAMERA PROMPT]\n{multi_angle}\n\n")
                    
                    f.write("-" * 80 + "\n\n")

            # Log what was saved
            self.log(f"[+] Image prompts saved: {output_path}", log_callback)
            self.log(f"    📄 Total sections: {len(image_prompts)}", log_callback)
            
            # Count what's included
            has_video = sum(1 for p in image_prompts if p.get("video_prompt"))
            has_multi_angle = sum(1 for p in image_prompts if p.get("multi_angle_camera_prompt"))
            
            if has_video:
                self.log(f"    🎬 Video prompts: {has_video}/{len(image_prompts)}", log_callback)
            if has_multi_angle:
                self.log(f"    🎥 Multi-angle camera prompts: {has_multi_angle}/{len(image_prompts)}", log_callback)
            
            self.log(f"    💾 File size: {output_path.stat().st_size:,} bytes", log_callback)
            self.log(f"    📝 Image prompts text: {image_prompt_file}", log_callback)
            self.log(f"    🎬 Video prompts text: {video_prompt_file}", log_callback)

            return image_prompts
            
        except Exception as e:
            self.log(f"[!] Image prompt generation failed: {e}", log_callback)
            raise
    
    async def _generate_section_prompt(
        self,
        section: dict,
        section_index: int,
        total_sections: int,
        previous_context: str = "",
        log_callback: Callable[[str], None] | None = None
    ) -> dict:
        """
        Generate 2 image prompts for a single section with different angles/focus.
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

            # Call Gemini to generate 2 image prompts
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=prompt_request + "\n\nGenerate 2 DIFFERENT image prompts for this section - one focusing on the main subject/character, another focusing on the environment/context. Return as JSON array with 2 objects.",
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
        Build the prompt request for Gemini API.
        """
        return f"""
You are an expert AI image prompt engineer for video production. Create strategic, focused image prompts.

**CRITICAL: ALL OUTPUT MUST BE IN ENGLISH ONLY.**

## Section Info
- **Title**: {section_title}
- **Type**: {section_type}
- **Duration**: {section_duration} sec
- **Position**: {section_index + 1}/{total_sections}
- **Narration**: {section_content}

## Context
{previous_context if previous_context else "First section."}

## Prompt Engineering Principles

**Be Strategic, Not Exhaustive:**
1. **Core First**: Lead with the most important subject and action
2. **Progressive Detail**: Establish the big picture first, then add key details
3. **Subtract, Don't Add**: Use negative prompts to remove unwanted elements rather than stacking descriptors
4. **Focus**: Like a buffet plate—too many items ruin the experience. Prioritize the main "flavors"

**Quality Over Quantity:**
- One strong, clear image > cluttered description
- Strategic details > exhaustive lists
- Clean composition > visual chaos

## Required Elements (Prioritized)

1. **Subject**: Main character/object (physical traits, clothing, expression, position)
2. **Scene**: Location, time, weather, atmosphere
3. **Technical**: Camera angle, shot size, lighting direction
4. **Mood**: Emotional tone, color palette

## Output Format

Return ONLY JSON with these fields. **ALL VALUES IN ENGLISH:**

```json
{{
  "prompt": "Clear, focused prompt. Structure: [SUBJECT: key traits] + [SCENE: location/time] + [TECHNICAL: angle/lighting] + [MOOD: tone/colors]. Strategic details only.",
  "negative_prompt": "cluttered, complex, busy, low quality, blurry, distorted, deformed, watermark, text",
  "style_reference": "e.g., 'cinematic thriller', 'documentary', 'neo-noir'",
  "continuity_notes": "Visual consistency notes (IN ENGLISH)",
  "aspect_ratio": "16:9 or 9:16 or 21:9",
  "camera": "e.g., 'wide shot, 35mm, eye-level'",
  "lighting": "e.g., 'dramatic chiaroscuro, rim lighting'",
  "priority_elements": ["element 1", "element 2", "element 3"]
}}
```

## Examples

### Good (Focused & Strategic):
"Tall humanoid figure, center frame—pale white skin, extremely long arms past knees, sparse white hair, sharp angular jaw. Snow-covered mountain peak at dusk, blizzard swirling. 24mm wide lens, low angle, dramatic rim lighting from sunset, cold blue fill from snow. Mood: isolation, dread. Desaturated whites/grays, cold blues. 8K, cinematic."

### Bad (Cluttered):
"A scary monster on a mountain, very tall and white, with long arms and weird hair, looking scary, dark sky, cold, snowy, wide shot, dramatic, cinematic, 8k, detailed, realistic" ← Vague, disorganized, no strategy!

## Section Types
- **Opening/Hook**: Mysterious, partial reveals, atmospheric
- **Setup**: Clear setting, full character descriptions
- **Development**: Dynamic action, changing expressions
- **Climax**: Maximum impact, dramatic lighting, intense
- **Resolution**: Visual closure, softer lighting

Generate the JSON now. Output ONLY JSON in ENGLISH.
"""
    
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
            
            # Build video prompt request
            video_prompt_request = f"""
You are an expert video prompt engineer for AI video generation (Runway, Pika, Sora, etc.).

**CRITICAL: ALL OUTPUT MUST BE IN ENGLISH ONLY.**

## Task
Generate a detailed VIDEO prompt based on the image prompt and narration. This prompt will be used to create short video clips (5-10 seconds) with dynamic camera movements and scene transitions.

## Section Information
- **Title**: {section_title}
- **Narration**: {section_content}
- **Base Image Prompt**: {image_prompt}
- **Position**: Section {section_index + 1} of {total_sections}

## Required Elements for Video Prompt

### 1. Scene Description (Detailed)
Describe the complete scene with:
- **Environment**: Full 360-degree awareness of the space
- **Time & Weather**: Specific conditions and how they change
- **Atmospheric Effects**: Fog, dust, rain, snow, particles, etc.
- **Background Activity**: What's happening in the distance

### 2. Character/Subject Actions
- **Movement**: How subjects move through the space
- **Gestures**: Hand movements, head turns, body language
- **Facial Expressions**: Changes in expression during the clip
- **Interaction**: How subjects interact with environment

### 3. Camera Movement (Dynamic & Fast-Paced)
Use MULTIPLE camera angles that change rapidly:
- **Opening Shot**: How the clip starts (e.g., "extreme close-up on eyes")
- **Camera Moves**: Pan, tilt, dolly, zoom, tracking, crane shots
- **Angle Changes**: Quick cuts between wide, medium, close-up
- **Special Shots**: Dutch angle, overhead, low angle, POV
- **Pacing**: "Rapid cuts", "Quick zoom in", "Swift pan to"

### 4. Transitions
- **Internal**: How camera moves within the shot
- **External**: How this shot connects to next

### 5. Motion & Energy
- **Subject Motion**: Fast, slow, sudden stops, accelerations
- **Camera Motion**: Smooth, shaky, handheld, stabilized
- **Energy Level**: High energy with quick movements

## Output Format

Return ONLY a JSON object:

```json
{{
  "video_prompt": "Complete video prompt with all elements. Example: 'OPENING: Extreme close-up on pale eyes widening in terror. QUICK ZOOM OUT to reveal full figure - 2.4m tall emaciated humanoid standing in blizzard. RAPID PAN LEFT as figure turns head sharply. CUT TO: Low angle Dutch tilt shot showing impossibly long arms swinging. CAMERA TRACKS BACKWARD as figure takes menacing step forward. QUICK CUTS BETWEEN: Wide shot (full figure in storm), Medium shot (torso and arms), Close-up (face contorting). DYNAMIC CAMERA: Handheld shake, rapid zooms, swift pans. ENERGY: High tension, sudden movements, predatory grace. ATMOSPHERE: Snow particles swirling violently, fabric whipping in wind, visible breath plumes.'",
  "camera_directions": ["extreme close-up on eyes", "quick zoom out to full figure", "rapid pan left", "low angle Dutch tilt", "camera tracks backward", "quick cuts between angles"],
  "motion_type": "dynamic_fast",
  "transition_style": "quick_cuts",
  "video_duration": "5-10 seconds",
  "frame_rate_suggestion": "24fps cinematic or 60fps smooth"
}}
```

## Examples

### Good Video Prompt:
"OPENING: Extreme close-up on pale eyes widening in terror. QUICK ZOOM OUT to reveal full figure - 2.4m tall emaciated humanoid standing in blizzard. RAPID PAN LEFT as figure turns head sharply. CUT TO: Low angle Dutch tilt shot showing impossibly long arms swinging. CAMERA TRACKS BACKWARD as figure takes menacing step forward. QUICK CUTS BETWEEN: Wide shot (full figure in storm), Medium shot (torso and arms), Close-up (face contorting). DYNAMIC CAMERA: Handheld shake, rapid zooms, swift pans. ENERGY: High tension, sudden movements, predatory grace."

### Bad Video Prompt (DO NOT):
"A monster stands in snow. Camera is still." ← Too static, no movement!

## For This Section (Type: {image_prompt_data.get('section_type', 'unknown')})
- **Opening/Hook**: Mysterious reveals, slow build to sudden shock
- **Setup**: Clear establishing shots, introduce subject with full body view
- **Development**: Action sequences, multiple angles, dynamic movement
- **Climax**: Maximum intensity, rapid cuts, extreme angles, chaotic motion
- **Resolution**: Slower pace, smooth transitions, resolving composition

Generate the JSON now. Output ONLY the JSON in ENGLISH, no other text. **ENGLISH ONLY!**
"""

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
            image_prompt = image_prompt_data.get(f"image_prompt" if prompt_type == "subject" else "image_prompt_2", "")
            
            # Different focus based on prompt type
            if prompt_type == "subject":
                camera_prompt = f"""MULTI-ANGLE CAMERA PROMPT - SUBJECT FOCUS (10 seconds)

OPENING: Extreme close-up on subject's most distinctive feature - eyes, face, or defining characteristic. Shallow depth of field isolates the subject from background.

QUICK ZOOM OUT: Rapid pull-back to reveal full subject in environment. Subject fills center frame, commanding attention.

RAPID PAN: Swift 180-degree pan around subject, showing relationship to surroundings. Handheld shake adds tension and immediacy.

ANGLE TRANSITION: Dynamic cut from low angle hero shot (subject dominates frame) to high angle overhead view (subject in context). Creates dramatic perspective shift.

CLOSING: Medium shot with slow, deliberate push-in toward subject. Building tension, drawing viewer into intimate connection.

CAMERA TECHNIQUES: Handheld camera shake throughout for realism and urgency. Quick snap zooms on key subject features. Swift pans with controlled motion blur. Dutch angles for psychological unease. Rack focus between subject and foreground elements. Subject-centered framing maintains focus on character.

MOOD & ENERGY: High tension, dynamic movement, cinematic pacing. Build from intimate close-up to epic establishing shot to personal medium push-in. Predator's grace, controlled intensity.

Base Image: {image_prompt[:200]}
"""
            else:  # environment
                camera_prompt = f"""MULTI-ANGLE CAMERA PROMPT - ENVIRONMENT FOCUS (10 seconds)

OPENING: Extreme close-up on critical environmental detail - texture, object, or atmospheric element. Macro-level observation draws viewer into world.

QUICK ZOOM OUT: Rapid pull-back to reveal full environment and landscape. Context expands dramatically, showing scale and scope of location.

RAPID PAN: Swift panoramic sweep across environment, left to right or right to left. Reveals background elements, depth layers, and atmospheric conditions.

ANGLE TRANSITION: Dynamic cut from overhead establishing shot (bird's eye view showing layout) to ground level worm's eye view (immersive perspective). Creates spatial awareness and dramatic contrast.

CLOSING: Wide shot with slow push-in through environment, moving deeper into scene. Drawing viewer into the world, building immersion and anticipation.

CAMERA TECHNIQUES: Handheld camera shake for documentary realism. Quick snap zooms on environmental details and textures. Swift landscape pans with controlled motion blur. Dutch angles for psychological unease and disorientation. Overhead establishing shots for geographic context. Environment-centered framing emphasizes location over character.

MOOD & ENERGY: Atmospheric tension, epic scale, cinematic world-building. Build from microscopic detail to macroscopic vista to immersive journey. Environmental storytelling through camera movement.

Base Image: {image_prompt[:200]}
"""
            
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
