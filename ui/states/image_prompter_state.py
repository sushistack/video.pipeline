"""Image Prompter Tab State Management"""
import reflex as rx
from pathlib import Path
import sys
import asyncio
import json

# Add parent project to path
PARENT_DIR = Path(__file__).resolve().parent.parent.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

# Add ui_reflex to path
UI_DIR = Path(__file__).parent.parent
if str(UI_DIR) not in sys.path:
    sys.path.insert(0, str(UI_DIR))

from pydantic import BaseModel, Field
from core.gen_image_prompt import ImagePromptGenerator


class ShotBreakdown(BaseModel):
    camera_type: str = ""
    subject: str = ""
    lighting: str = ""
    mood: str = ""
    motion: str = ""


class ImagePromptResult(BaseModel):
    prompt: str = ""
    negative_prompt: str = ""
    style_tags: list[str] = Field(default_factory=list)


class ShotWithPrompt(BaseModel):
    shot: ShotBreakdown = Field(default_factory=ShotBreakdown)
    image_prompt: ImagePromptResult = Field(default_factory=ImagePromptResult)


class VideoPromptData(BaseModel):
    video_prompt: str = ""
    camera_directions: list[str] = Field(default_factory=list)
    motion_type: str = ""
    transition_style: str = ""


class SubSceneData(BaseModel):
    key_point: str = ""
    sub_scene_index: int = 0
    opening_shot: ShotWithPrompt = Field(default_factory=ShotWithPrompt)
    video_prompt: VideoPromptData = Field(default_factory=VideoPromptData)


class ScenePromptData(BaseModel):
    section_title: str = ""
    section_type: str = ""
    estimated_duration: int = 30
    narration_text: str = ""
    negative_prompt: str = ""
    continuity_notes: str = ""
    sub_scenes: list[SubSceneData] = Field(default_factory=list)


class ImagePrompterState(rx.State):
    """State management for Image Prompter Tab"""

    # Project selection
    available_projects: list[str] = []
    selected_project: str = ""

    # Settings
    speed_mode: bool = True  # Skip Qwen review for faster generation
    parallel_processing: bool = True  # Process sub-scenes in parallel

    # Generation status
    is_generating: bool = False
    current_section: int = 0
    total_sections: int = 0
    progress: float = 0.0

    # Logs
    generation_logs: list[str] = []

    # Generated prompts
    image_prompts: list[ScenePromptData] = []
    prompts_file_path: str = ""

    # Content info
    content_title: str = ""
    aspect_ratio: str = "16:9"

    # Computed properties
    @rx.var
    def can_generate(self) -> bool:
        """Can start generation"""
        return bool(self.selected_project) and not self.is_generating

    @rx.var
    def progress_percentage(self) -> int:
        """Progress percentage"""
        if self.total_sections == 0:
            return 0
        return int((self.current_section / self.total_sections) * 100)

    @rx.var
    def status_text(self) -> str:
        """Current status text"""
        if not self.is_generating:
            return "Ready"
        if self.current_section == 0:
            return "Loading script..."
        return f"Processing sub-scene {self.current_section}/{self.total_sections}"

    # Setters

    def log(self, message: str):
        """Add log message"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}"
        self.generation_logs.append(formatted)
        print(formatted)

    def log_with_callback(self, message: str, callback=None):
        """Add log message with optional callback"""
        self.log(message)
        if callback:
            callback(message)

    def on_load(self):
        """Called when page loads"""
        self.load_projects()

    def load_projects(self):
        """Scan for available projects in workspace"""
        workspace_dir = PARENT_DIR / "workspace"

        if workspace_dir.exists():
            projects = []
            for project_dir in workspace_dir.iterdir():
                if project_dir.is_dir() and not project_dir.name.startswith("."):
                    # Check if it has 02_scene_structure.json (new pipeline input)
                    script_file = project_dir / "scripts" / "02_scene_structure.json"
                    if script_file.exists():
                        projects.append(project_dir.name)

            self.available_projects = sorted(projects, reverse=True)

            # Auto-select first project if none selected
            if self.available_projects and not self.selected_project:
                self.selected_project = self.available_projects[0]
                self.extract_content_title()
                self.load_existing_prompts()
        else:
            self.available_projects = []

    def extract_content_title(self):
        """Extract title from ko.content.md file"""
        if not self.selected_project:
            self.content_title = ""
            return

        content_file = PARENT_DIR / "workspace" / self.selected_project / "content" / "ko.content.md"
        if content_file.exists():
            try:
                with open(content_file, "r", encoding="utf-8") as f:
                    first_line = f.readline().strip()
                    # Remove markdown heading marker if present
                    if first_line.startswith("# "):
                        self.content_title = first_line[2:]
                    else:
                        self.content_title = first_line
            except Exception as e:
                print(f"Failed to extract title: {e}")
                self.content_title = ""
        else:
            self.content_title = ""

    def load_existing_prompts(self):
        """Load existing image prompts from workspace if available (new sub-scene schema)"""
        if not self.selected_project:
            return

        prompts_file = PARENT_DIR / "workspace" / self.selected_project / "scripts" / "05_image_prompts.json"
        if not prompts_file.exists():
            self.image_prompts = []
            self.prompts_file_path = ""
            return

        try:
            with open(prompts_file, "r", encoding="utf-8") as f:
                prompts_data = json.load(f)

            def raw_to_typed_shot(s: dict) -> ShotWithPrompt:
                shot_data = s.get("shot", {})
                img_data = s.get("image_prompt", {})
                return ShotWithPrompt(
                    shot=ShotBreakdown(
                        camera_type=shot_data.get("camera_type", ""),
                        subject=shot_data.get("subject", ""),
                        lighting=shot_data.get("lighting", ""),
                        mood=shot_data.get("mood", ""),
                        motion=shot_data.get("motion", ""),
                    ),
                    image_prompt=ImagePromptResult(
                        prompt=img_data.get("prompt", "") if isinstance(img_data, dict) else "",
                        negative_prompt=img_data.get("negative_prompt", "") if isinstance(img_data, dict) else "",
                        style_tags=img_data.get("style_tags", []) if isinstance(img_data, dict) else [],
                    ),
                )

            image_prompts_typed: list[ScenePromptData] = []

            for scene_data in prompts_data:
                # Handle new sub-scene schema
                raw_sub_scenes = scene_data.get("sub_scenes", [])
                sub_scenes_typed: list[SubSceneData] = []

                for sub in raw_sub_scenes:
                    vp_raw = sub.get("video_prompt", {})
                    typed_sub = SubSceneData(
                        key_point=sub.get("key_point", ""),
                        sub_scene_index=sub.get("sub_scene_index", 0),
                        opening_shot=raw_to_typed_shot(sub.get("opening_shot", {})),
                        video_prompt=VideoPromptData(
                            video_prompt=vp_raw.get("video_prompt", "") if isinstance(vp_raw, dict) else "",
                            camera_directions=vp_raw.get("camera_directions", []) if isinstance(vp_raw, dict) else [],
                            motion_type=vp_raw.get("motion_type", "") if isinstance(vp_raw, dict) else "",
                            transition_style=vp_raw.get("transition_style", "") if isinstance(vp_raw, dict) else "",
                        ),
                    )
                    sub_scenes_typed.append(typed_sub)

                scene_prompt = ScenePromptData(
                    section_title=scene_data.get("scene_title", ""),
                    section_type=scene_data.get("emotional_beat", ""),
                    estimated_duration=scene_data.get("estimated_duration", 30),
                    narration_text=scene_data.get("synopsis", ""),
                    negative_prompt="",
                    continuity_notes=f"Scene {scene_data.get('scene_number', 0)}: {len(sub_scenes_typed)} sub-scenes",
                    sub_scenes=sub_scenes_typed,
                )
                image_prompts_typed.append(scene_prompt)

            self.image_prompts = image_prompts_typed
            self.prompts_file_path = str(prompts_file)
            self.log(f"✅ Loaded {len(image_prompts_typed)} scenes with {sum(len(s.sub_scenes) for s in image_prompts_typed)} sub-scenes")

        except Exception as e:
            print(f"Failed to load existing prompts: {e}")
            self.image_prompts = []
            self.prompts_file_path = ""

    def set_selected_project(self, value: str):
        """Set selected project"""
        self.selected_project = value
        self.extract_content_title()
        self.load_existing_prompts()

    def set_speed_mode(self, value: bool):
        """Toggle speed mode"""
        self.speed_mode = value

    async def generate_prompts(self):
        """Generate image prompts for selected project using sub-scene pipeline (key_points -> sub-scenes)"""
        if not self.can_generate:
            yield rx.toast.error("Please select a project first!")
            return

        # Initialize state
        self.is_generating = True
        self.current_section = 0
        self.total_sections = 0
        self.generation_logs = []
        self.image_prompts = []
        self.prompts_file_path = ""
        yield  # Force UI update

        try:
            self.log("=" * 60)
            self.log(f"🎨 Starting Image Prompt Generation (Sub-scene Pipeline)")
            self.log(f"📁 Project: {self.selected_project}")
            self.log("=" * 60)
            yield

            workspace_dir = PARENT_DIR / "workspace"
            generator = ImagePromptGenerator(workspace_dir=workspace_dir)

            def log_callback(message: str):
                self.log_with_callback(message)

            # Load scene structure
            scene_path = workspace_dir / self.selected_project / "scripts" / "02_scene_structure.json"
            if not scene_path.exists():
                self.log(f"❌ Scene structure not found: {scene_path}")
                yield rx.toast.error("Scene structure file not found!")
                return

            with open(scene_path, "r", encoding="utf-8") as f:
                scene_structure = json.load(f)

            scenes = scene_structure.get("scenes", [])

            # Total sections = total key_points across all scenes
            total_key_points = sum(len(s.get("key_points", [])) for s in scenes)
            self.total_sections = total_key_points
            self.log(f"📄 Found {len(scenes)} scenes, {total_key_points} sub-scenes total")
            yield

            image_prompts_typed: list[ScenePromptData] = []
            image_prompts_raw: list[dict] = []
            previous_opening_shot = None
            section_counter = 0

            def _to_typed_shot(s: dict) -> ShotWithPrompt:
                shot_data = s.get("shot", {})
                img_data = s.get("image_prompt", {})
                return ShotWithPrompt(
                    shot=ShotBreakdown(
                        camera_type=shot_data.get("camera_type", ""),
                        subject=shot_data.get("subject", ""),
                        lighting=shot_data.get("lighting", ""),
                        mood=shot_data.get("mood", ""),
                        motion=shot_data.get("motion", ""),
                    ),
                    image_prompt=ImagePromptResult(
                        prompt=img_data.get("prompt", "") if isinstance(img_data, dict) else "",
                        negative_prompt=img_data.get("negative_prompt", "") if isinstance(img_data, dict) else "",
                        style_tags=img_data.get("style_tags", []) if isinstance(img_data, dict) else [],
                    ),
                )

            for idx, scene in enumerate(scenes):
                key_points = scene.get("key_points", [])
                total_sub = len(key_points)
                self.log(f"[-] Scene {idx + 1}/{len(scenes)}: {scene.get('title', 'Unknown')} ({total_sub} sub-scenes)")
                yield

                sub_scenes_typed: list[SubSceneData] = []
                sub_scenes_raw: list[dict] = []

                for kp_idx, key_point in enumerate(key_points):
                    section_counter += 1
                    self.current_section = section_counter
                    self.log(f"  [Sub-scene {kp_idx + 1}/{total_sub}] {key_point[:60]}...")
                    yield

                    sub_result = await generator.generate_sub_scene_prompts(
                        scene=scene,
                        key_point=key_point,
                        sub_scene_index=kp_idx + 1,
                        total_sub_scenes=total_sub,
                        previous_opening_shot=previous_opening_shot,
                        log_callback=log_callback,
                        speed_mode=self.speed_mode,  # Use speed mode setting
                    )
                    yield

                    # Convert to typed SubSceneData
                    vp_raw = sub_result.get("video_prompt", {})
                    typed_sub = SubSceneData(
                        key_point=key_point,
                        sub_scene_index=kp_idx,
                        opening_shot=_to_typed_shot(sub_result.get("opening_shot", {})),
                        video_prompt=VideoPromptData(
                            video_prompt=vp_raw.get("video_prompt", "") if isinstance(vp_raw, dict) else "",
                            camera_directions=vp_raw.get("camera_directions", []) if isinstance(vp_raw, dict) else [],
                            motion_type=vp_raw.get("motion_type", "") if isinstance(vp_raw, dict) else "",
                            transition_style=vp_raw.get("transition_style", "") if isinstance(vp_raw, dict) else "",
                        ),
                    )
                    sub_scenes_typed.append(typed_sub)
                    sub_scenes_raw.append(sub_result)

                    # Cross-sub-scene continuity chain
                    previous_opening_shot = sub_result.get("opening_shot")
                    await asyncio.sleep(0.3)
                    yield

                # Build typed ScenePromptData
                scene_prompt = ScenePromptData(
                    section_title=scene.get("title", ""),
                    section_type=scene.get("emotional_beat", ""),
                    estimated_duration=int(scene.get("duration_seconds", 30)),
                    narration_text="\n".join(key_points),
                    negative_prompt=(
                        sub_scenes_typed[0].opening_shot.image_prompt.negative_prompt
                        if sub_scenes_typed else ""
                    ),
                    continuity_notes=f"Scene {scene.get('scene_number', idx + 1)}: {len(key_points)} sub-scenes",
                    sub_scenes=sub_scenes_typed,
                )
                image_prompts_typed.append(scene_prompt)

                # Build raw dict for JSON
                scene_raw = {
                    "scene_number": scene.get("scene_number", idx + 1),
                    "scene_title": scene.get("title", ""),
                    "emotional_beat": scene.get("emotional_beat", ""),
                    "synopsis": "\n".join(key_points),
                    "sub_scenes": sub_scenes_raw,
                }
                image_prompts_raw.append(scene_raw)

            # Store results
            self.image_prompts = image_prompts_typed
            output_path = workspace_dir / self.selected_project / "scripts" / "05_image_prompts.json"
            self.prompts_file_path = str(output_path)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(image_prompts_raw, f, indent=2, ensure_ascii=False)

            self.log("=" * 60)
            self.log("🎉 Image Prompt Generation Complete!")
            self.log(f"📄 Generated {total_key_points} sub-scene prompts across {len(scenes)} scenes")
            self.log(f"💾 Saved to: {self.prompts_file_path}")
            self.log("=" * 60)
            yield rx.toast.success("Image Prompts Generated! 🚀")

        except Exception as e:
            self.log(f"❌ ERROR: {str(e)}")
            import traceback
            error_trace = traceback.format_exc()
            for line in error_trace.split('\n')[:5]:
                if line.strip():
                    self.log(f"   {line}")
            yield rx.toast.error(f"Generation Failed: {e}")

        finally:
            self.is_generating = False
            yield  # Final UI update

    def get_prompt_preview(self, index: int) -> ScenePromptData | None:
        """Get preview of specific prompt"""
        if 0 <= index < len(self.image_prompts):
            return self.image_prompts[index]
        return None
