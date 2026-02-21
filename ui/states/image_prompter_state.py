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

from pydantic import BaseModel
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
    style_tags: list[str] = []


class ShotWithPrompt(BaseModel):
    shot: ShotBreakdown = ShotBreakdown()
    image_prompt: ImagePromptResult = ImagePromptResult()


class ScenePromptData(BaseModel):
    section_title: str = ""
    section_type: str = ""
    estimated_duration: int = 30
    narration_text: str = ""
    negative_prompt: str = ""
    continuity_notes: str = ""
    first_shot: ShotWithPrompt = ShotWithPrompt()
    last_shot: ShotWithPrompt = ShotWithPrompt()


class ImagePrompterState(rx.State):
    """State management for Image Prompter Tab"""

    # Project selection
    available_projects: list[str] = []
    selected_project: str = ""

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
        return f"Generating prompt {self.current_section}/{self.total_sections}"

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
        """Load existing image prompts from workspace if available"""
        if not self.selected_project:
            return

        prompts_file = PARENT_DIR / "workspace" / self.selected_project / "scripts" / "05_image_prompts.json"
        if prompts_file.exists():
            try:
                with open(prompts_file, "r", encoding="utf-8") as f:
                    prompts_data = json.load(f)

                # Convert to typed objects for UI display
                image_prompts_typed: list[ScenePromptData] = []
                for prompt_data in prompts_data:
                    first_raw = prompt_data.get("first_shot", {})
                    last_raw = prompt_data.get("last_shot", {})

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

                    typed_first = raw_to_typed_shot(first_raw)
                    typed_last = raw_to_typed_shot(last_raw)

                    scene_prompt = ScenePromptData(
                        section_title=prompt_data.get("section_title", ""),
                        section_type=prompt_data.get("section_type", ""),
                        estimated_duration=prompt_data.get("estimated_duration", 30),
                        narration_text=prompt_data.get("narration_text", ""),
                        negative_prompt=prompt_data.get("negative_prompt", ""),
                        continuity_notes=prompt_data.get("continuity_notes", ""),
                        first_shot=typed_first,
                        last_shot=typed_last,
                    )
                    image_prompts_typed.append(scene_prompt)

                self.image_prompts = image_prompts_typed
                self.prompts_file_path = str(prompts_file)
                self.log(f"✅ Loaded {len(image_prompts_typed)} existing image prompts")
                print(f"Loaded existing prompts: {len(image_prompts_typed)} scenes")

            except Exception as e:
                print(f"Failed to load existing prompts: {e}")
                self.image_prompts = []
                self.prompts_file_path = ""
        else:
            # No existing prompts file
            self.image_prompts = []
            self.prompts_file_path = ""

    def set_selected_project(self, value: str):
        """Set selected project"""
        self.selected_project = value
        self.extract_content_title()
        self.load_existing_prompts()

    async def generate_prompts(self):
        """Generate image prompts for selected project using 2-step shot breakdown pipeline"""
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
            self.log(f"🎨 Starting Image Prompt Generation (2-Step Pipeline)")
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
            self.total_sections = len(scenes)
            self.log(f"📄 Found {self.total_sections} scenes in scene structure")
            yield

            # Generate prompts scene by scene with progress tracking
            image_prompts_typed: list[ScenePromptData] = []
            image_prompts_raw: list[dict] = []
            previous_last_shot = None

            for idx, scene in enumerate(scenes):
                self.current_section = idx + 1
                yield  # Update progress UI

                self.log(f"[-] Scene {idx + 1}/{self.total_sections}: {scene.get('title', 'Unknown')}")
                yield

                # Run 3-step pipeline for this scene
                scene_result = await generator.generate_scene_prompts(
                    scene=scene,
                    previous_last_shot=previous_last_shot,
                    log_callback=log_callback,
                )
                yield

                shots = [
                    scene_result.get("first_shot", {}),
                    scene_result.get("last_shot", {}),
                ]

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
                            prompt=img_data.get("prompt", ""),
                            negative_prompt=img_data.get("negative_prompt", ""),
                            style_tags=img_data.get("style_tags", []),
                        ),
                    )

                typed_first = _to_typed_shot(scene_result.get("first_shot", {}))
                typed_last = _to_typed_shot(scene_result.get("last_shot", {}))

                scene_prompt = ScenePromptData(
                    section_title=scene_result["scene_title"],
                    section_type=scene_result["emotional_beat"],
                    estimated_duration=int(scene.get("duration_seconds", 30)),
                    narration_text=scene_result["synopsis"],
                    negative_prompt=typed_first.image_prompt.negative_prompt,
                    continuity_notes=f"Scene {scene_result['scene_number']}: opening \u2192 closing",
                    first_shot=typed_first,
                    last_shot=typed_last,
                )
                image_prompts_typed.append(scene_prompt)

                # Build raw dict for JSON file saving
                first_raw = scene_result.get("first_shot", {})
                last_raw = scene_result.get("last_shot", {})
                prompt_data_raw = {
                    "section_title": scene_result["scene_title"],
                    "section_type": scene_result["emotional_beat"],
                    "estimated_duration": scene.get("duration_seconds", 30),
                    "narration_text": scene_result["synopsis"],
                    "image_prompt": first_raw.get("image_prompt", {}).get("prompt", ""),
                    "image_prompt_2": last_raw.get("image_prompt", {}).get("prompt", ""),
                    "negative_prompt": first_raw.get("image_prompt", {}).get("negative_prompt", ""),
                    "continuity_notes": f"Scene {scene_result['scene_number']}: opening \u2192 closing",
                    "first_shot": first_raw,
                    "last_shot": last_raw,
                }
                image_prompts_raw.append(prompt_data_raw)

                previous_last_shot = scene_result.get("last_shot")
                await asyncio.sleep(0.3)  # Rate limiting
                yield

            # Store typed results in state
            self.image_prompts = image_prompts_typed
            output_path = workspace_dir / self.selected_project / "scripts" / "05_image_prompts.json"
            self.prompts_file_path = str(output_path)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(image_prompts_raw, f, indent=2, ensure_ascii=False)

            self._save_prompt_text_files(output_path, image_prompts_raw)

            self.log("=" * 60)
            self.log("🎉 Image Prompt Generation Complete!")
            self.log(f"📄 Generated {len(image_prompts_typed)} scene prompts")
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

    def _save_prompt_text_files(self, output_path: Path, image_prompts: list):
        """Save image and video prompts as text files - one file per section"""
        try:
            # Save individual files for each section
            for idx, prompt_data in enumerate(image_prompts, 1):
                section_num = f"{idx:02d}"
                section_title = prompt_data.get('section_title', 'Unknown')
                
                # Write image prompts for this section (2 prompts)
                image_prompt_file = output_path.parent / f"image.prompt.{section_num}.txt"
                with open(image_prompt_file, "w", encoding="utf-8") as f:
                    f.write(f"=== SECTION {idx}/{len(image_prompts)}: {section_title} ===\n\n")
                    f.write(f"[IMAGE PROMPT 1 - Subject Focus]\n{prompt_data.get('image_prompt', '')}\n\n")
                    f.write(f"[IMAGE PROMPT 2 - Environment Focus]\n{prompt_data.get('image_prompt_2', '')}\n")
                
                # Write video prompt for this section
                video_prompt_file = output_path.parent / f"video.prompt.{section_num}.txt"
                with open(video_prompt_file, "w", encoding="utf-8") as f:
                    f.write(f"=== SECTION {idx}/{len(image_prompts)}: {section_title} ===\n\n")
                    
                    # Video prompt
                    video_prompt = prompt_data.get("video_prompt", {})
                    if isinstance(video_prompt, dict):
                        f.write(f"[VIDEO PROMPT]\n{video_prompt.get('video_prompt', '')}\n\n")
                    
                    # Multi-angle camera prompt - Subject Focus
                    multi_angle_subject = prompt_data.get("multi_angle_camera_prompt_subject", "")
                    if multi_angle_subject:
                        f.write(f"[MULTI-ANGLE CAMERA - SUBJECT FOCUS]\n{multi_angle_subject}\n\n")
                    
                    # Multi-angle camera prompt - Environment Focus
                    multi_angle_env = prompt_data.get("multi_angle_camera_prompt_environment", "")
                    if multi_angle_env:
                        f.write(f"[MULTI-ANGLE CAMERA - ENVIRONMENT FOCUS]\n{multi_angle_env}\n")
            
            # Log summary
            self.log(f"    📝 Saved {len(image_prompts)} image prompt files (2 prompts each)")
            self.log(f"    🎬 Saved {len(image_prompts)} video prompt files")
            
        except Exception as e:
            self.log(f"    [!] Failed to save text files: {e}")

    def get_prompt_preview(self, index: int) -> ScenePromptData | None:
        """Get preview of specific prompt"""
        if 0 <= index < len(self.image_prompts):
            return self.image_prompts[index]
        return None
