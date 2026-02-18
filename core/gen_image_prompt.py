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

        # API Keys
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in .env")

        # Initialize Gemini client
        self.gemini_client = genai.Client(api_key=self.gemini_api_key)
        self.gemini_model = "gemini-2.0-flash"

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
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=prompt_request + """

**CRITICAL: Analyze the narration content and identify 2 KEY VISUAL POINTS:**

1. **First, identify the PRIMARY VISUAL ELEMENTS from the narration:**
   - What is the main character doing? (standing, holding, looking, running, etc.)
   - What objects are important? (photos, weapons, tools, documents, etc.)
   - Where is the character looking? (at an object, at another character, at the horizon, etc.)
   - What is the character interacting with? (people, objects, environment)

2. **Extract 1-2 MOOD/ATMOSPHERE KEYWORDS from the narration context:**
   - Analyze the emotional tone of the narration
   - Identify the atmosphere (dread, tension, mystery, hope, isolation, despair, urgency, etc.)
   - These mood keywords MUST be included in both prompts
   - Examples: "cosmic dread", "clinical sterility", "primal isolation", "desperate urgency", "eerie silence"

3. **Generate 2 prompts based on these key points:**

   **PROMPT 1 - ESTABLISHING SHOT (Full Context):**
   - Show the CHARACTER in their FULL environment
   - Character's full body visible (or significant portion)
   - Show what they're doing/holding/looking at
   - Establish spatial relationship between character and key objects
   - Wide to medium shot that captures the complete scene
   - MUST INCLUDE: 1-2 mood keywords from step 2
   - Viewer understands: who, where, what they're doing

   **PROMPT 2 - FOCUS SHOT (Key Detail):**
   - Zoom in on the MOST IMPORTANT visual element from the narration
   - Examples:
     * If character is holding a photo → close-up of the photo (with character's hands/face partially visible)
     * If character is looking at something → show what they see (POV shot or over-the-shoulder)
     * If character is interacting with an object → close-up of that interaction (hands on object)
     * If character's expression is crucial → close-up of face showing that emotion
     * If there's a crucial background element → focus on that element with character in frame
   - MUST INCLUDE: Same 1-2 mood keywords from step 2
   - This shot emphasizes the narrative detail that drives the story forward
   - Medium to close-up shot

4. **SHARED ELEMENTS (Must match in both prompts):**
   - Same character appearance (clothing, physical features, pose base)
   - Same location, time, lighting
   - Same key objects (if visible in both)
   - **Same 1-2 mood keywords** (extracted from narration)
   - Same atmosphere and color palette

**EXAMPLE ANALYSIS:**
If narration says: "The researcher held the photograph of SCP-096, studying its pale features with growing dread."

- **Key Visual Points**: Researcher + Photograph of 096
- **Mood Keywords**: "growing dread", "clinical tension"
- **Prompt 1 (Establishing)**: Researcher in sterile lab, full body, holding photograph, fluorescent lighting, clinical tension, growing dread
- **Prompt 2 (Focus)**: Close-up of the photograph in researcher's hands, showing 096's pale face, researcher's fingers visible at edges, clinical tension, growing dread

**VISUAL CONTINUITY:** Both prompts must look like they're from the same scene, same moment - just different camera focus to tell different parts of the visual story. Both MUST include the same 1-2 mood keywords.

Return as JSON array with exactly 2 objects: [{"prompt": "...", ...}, {"prompt": "...", ...}]""",
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
You are an expert AI image prompt engineer for storytelling video production. Create image prompts focused on CHARACTERS and BACKGROUNDS for visual narrative.

**CRITICAL: ALL OUTPUT MUST BE IN ENGLISH ONLY.**

## Section Info
- **Title**: {section_title}
- **Type**: {section_type}
- **Duration**: {section_duration} sec
- **Position**: {section_index + 1}/{total_sections}
- **Narration**: {section_content}

## Context
{previous_context if previous_context else "First section."}

## Storytelling Image Prompt Structure

**Focus: CHARACTER + BACKGROUND for visual storytelling**

Format: `[CHARACTER KEYWORDS], [BACKGROUND KEYWORDS], [COMPOSITION KEYWORDS], [MOOD KEYWORDS]`

### Keyword Categories (Prioritize Character & Background):

1. **CHARACTER/ SUBJECT** (5-8 keywords): This is the MOST IMPORTANT element
   - Physical traits: age, gender, height, build, skin tone, hair style/color, eye color
   - Clothing: specific outfit, colors, textures, accessories, shoes
   - Expression: facial expression, emotional state, eye direction
   - Pose: body posture, hand position, action, gesture
   - Position: where in frame (center, left, right, foreground, background)
   - Example: "tall humanoid male, 2.4 meters, emaciated build, alabaster white skin, no pigmentation, extremely long arms past knees, sparse white hair matted, sharp angular jawline, tattered gray fabric draped over shoulder, center frame, facing away, head turned slightly left"

2. **BACKGROUND/ENVIRONMENT** (5-8 keywords): Second most important - sets the scene
   - Location: specific place (indoor/outdoor, mountain, city, room, forest)
   - Time: time of day (dawn, dusk, midnight, noon)
   - Weather: rain, snow, fog, storm, clear, cloudy
   - Atmosphere: mist, dust, particles, haze, smoke
   - Background elements: buildings, trees, rocks, furniture, objects
   - Depth layers: foreground, midground, background elements
   - Example: "snow-covered mountain peak, jagged ridges, blizzard conditions, swirling snow particles, dense fog, darkening purple-orange sky, fading light, isolated wilderness, Himalayan landscape, atmospheric perspective"

3. **COMPOSITION & TECHNICAL** (3-5 keywords): How to frame the shot
   - Camera angle: eye-level, low angle, high angle, dutch angle, overhead
   - Shot size: extreme wide shot, wide shot, medium shot, close-up, extreme close-up
   - Lens: 24mm wide, 35mm, 50mm, 85mm portrait
   - Depth of field: shallow, deep, bokeh, focus on subject
   - Framing: rule of thirds, centered, leading lines, symmetry
   - Example: "24mm wide angle lens, low angle shot, shallow depth of field, subject centered, rule of thirds, dramatic perspective"

4. **MOOD & LIGHTING** (3-5 keywords): Emotional tone and visual atmosphere
   - Lighting type: natural light, rim lighting, chiaroscuro, volumetric, ambient
   - Lighting direction: front lit, side lit, backlit, top lit, underlit
   - Color palette: warm tones, cool tones, desaturated, vibrant, monochromatic
   - Mood: isolation, dread, hope, tension, peace, mystery, epic
   - Style: cinematic, photorealistic, 8K, dramatic, documentary
   - Example: "dramatic rim lighting from setting sun, cold blue fill light from snow reflection, desaturated whites and grays, cold blues, muted purple sky, isolation, primal dread, 8K cinematic photorealistic"

## Output Format

Return ONLY JSON with these fields. **ALL VALUES IN ENGLISH:**

```json
{{
  "prompt": "character keywords (5-8), background keywords (5-8), composition keywords (3-5), mood/lighting keywords (3-5)",
  "negative_prompt": "cluttered, busy, distracting elements, low quality, blurry, distorted, deformed, ugly, watermark, text, signature, cropped, worst quality, jpeg artifacts, out of focus, bad anatomy",
  "style_reference": "cinematic storytelling, dramatic narrative, photorealistic 8K",
  "continuity_notes": "Visual consistency notes for previous/next scenes (IN ENGLISH)",
  "aspect_ratio": "16:9",
  "camera": "wide shot, 35mm, eye-level or low angle",
  "lighting": "dramatic lighting with specific direction",
  "priority_elements": ["main character trait", "key background element", "mood descriptor"]
}}
```

## Examples

### Good (Character + Background Focused for Storytelling):
"tall humanoid figure, 2.4 meters tall, emaciated build, alabaster white skin, no pigmentation, extremely long arms past knees, sparse white hair, sharp angular jawline, tattered gray fabric, center frame, snow-covered mountain peak, jagged ridges, blizzard swirling, dense fog, darkening purple-orange sky, fading dusk light, isolated wilderness, 24mm wide lens, low angle, shallow depth of field, dramatic rim lighting, cold blue fill, desaturated whites, cold blues, isolation, primal dread, 8K cinematic"

### Bad (Too Technical, Not Enough Character/Background):
"wide shot, 24mm lens, dramatic lighting, cinematic, 8K, mountain landscape, figure standing" ← Missing character details, vague background!

### Bad (Vague, Not Storytelling-Ready):
"monster, mountain, scary, dark, cinematic" ← No specific character or background details!

## Critical Guidelines for Storytelling

**CHARACTER IS KING:**
- Spend 40% of keywords on character/subject details
- Be extremely specific: not "tall man" but "2.4 meter tall emaciated humanoid with alabaster skin"
- Include clothing, expression, pose, position in frame
- Make the character readable and emotionally resonant

**BACKGROUND IS QUEEN:**
- Spend 35% of keywords on background/environment
- Establish where, when, what conditions
- Include atmospheric elements (fog, rain, dust, particles)
- Create depth with foreground/midground/background layers
- Make the background support the story mood

**COMPOSITION & MOOD SUPPORT:**
- Spend 25% on technical and mood
- Choose angles that enhance storytelling (low angle = power, high angle = vulnerability)
- Lighting should match emotional tone
- Color palette reinforces the mood

**DON'T:**
- Prioritize camera specs over character details
- Use generic terms: "nice background", "scary monster"
- Forget the story context - every image must advance the narrative
- Overuse technical jargon at the expense of visual clarity

## Section Types - Character & Background Emphasis

- **Opening/Hook**: Character partial reveal + mysterious atmospheric background
- **Setup**: Full character view + clear establishing background
- **Development**: Character action/expression + dynamic background elements
- **Climax**: Character intense emotion + dramatic extreme background
- **Resolution**: Character resolved state + softer background, visual closure

## Two Prompt Variations - CONTEXTUAL STORYTELLING

You will generate 2 prompts that work together to tell the complete visual story.

**STEP 1: Analyze the narration to find KEY VISUAL POINTS:**
- What is the character DOING? (action, interaction, gaze direction)
- What OBJECTS are narratively important? (photos, documents, weapons, tools)
- What RELATIONSHIP matters? (character-to-object, character-to-character, character-to-environment)

**STEP 2: Extract 1-2 MOOD/ATMOSPHERE KEYWORDS from the narration:**
- Analyze the emotional tone: dread, tension, mystery, hope, isolation, despair, urgency, etc.
- These mood keywords MUST appear in BOTH prompts
- Examples: "cosmic dread", "clinical sterility", "primal isolation", "desperate urgency"

**STEP 3: Generate two complementary shots:**

**PROMPT 1 - ESTABLISHING SHOT (Full Scene):**
- Character + environment + key objects together
- Shows spatial relationships and complete context
- Wide to medium shot
- MUST INCLUDE: 1-2 mood keywords from Step 2
- Answers: Who is here? Where are they? What are they doing?

**PROMPT 2 - DETAIL/FOCUS SHOT (Key Story Element):**
- Focus on the most narratively important detail:
  * Object character is holding/using → close-up of that object
  * Character's gaze target → what they're looking at (POV or over-shoulder)
  * Critical facial expression → close-up showing emotion
  * Important interaction → hands + object interaction
  * Environmental storytelling element → focus on that background detail
- Medium to close-up
- MUST INCLUDE: Same 1-2 mood keywords from Step 2
- Answers: What specific detail drives this moment of the story?

**SHARED ELEMENTS (Must be consistent):**
- Character appearance, clothing, base pose
- Location, time, weather
- Lighting direction, color palette
- **Same 1-2 mood keywords** (from narration analysis)
- Mood, atmosphere

**Think like a film director:**
- Shot 1 (Establishing): "Here's the researcher in the lab, holding a photograph" + mood keywords
- Shot 2 (Detail): "Here's what's in that photograph - and why it matters" + same mood keywords

Both shots are from the same scene, same moment - but Shot 2 reveals the story detail that Shot 1 sets up. Both MUST include the same 1-2 mood keywords extracted from the narration.

Generate the JSON now. Output ONLY JSON in ENGLISH. Focus on CHARACTER and BACKGROUND for visual storytelling.
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
