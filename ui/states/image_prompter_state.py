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

from core.gen_image_prompt import ImagePromptGenerator


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
    image_prompts: list[dict] = []
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
    def set_selected_project(self, value: str):
        """Set selected project"""
        self.selected_project = value
        self.extract_content_title()

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
                    # Check if it has scripts directory with narration file
                    script_file = project_dir / "scripts" / "04.narration_final.json"
                    if script_file.exists():
                        projects.append(project_dir.name)

            self.available_projects = sorted(projects, reverse=True)

            # Auto-select first project if none selected
            if self.available_projects and not self.selected_project:
                self.selected_project = self.available_projects[0]
                self.extract_content_title()
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

    def set_selected_project(self, value: str):
        """Set selected project"""
        self.selected_project = value
        self.extract_content_title()
        self.extract_content_title()

    async def generate_prompts(self):
        """Generate image prompts for selected project"""
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
            self.log(f"🎨 Starting Image Prompt Generation")
            self.log(f"📁 Project: {self.selected_project}")
            self.log("=" * 60)
            yield

            # Initialize generator
            workspace_dir = PARENT_DIR / "workspace"
            generator = ImagePromptGenerator(workspace_dir=workspace_dir)

            # Define log callback
            def log_callback(message: str):
                self.log_with_callback(message)

            # Load script first to get section count
            script_path = workspace_dir / self.selected_project / "scripts" / "04.narration_final.json"
            if not script_path.exists():
                self.log(f"❌ Script not found: {script_path}")
                yield rx.toast.error("Script file not found!")
                return

            with open(script_path, "r", encoding="utf-8") as f:
                script_data = json.load(f)

            self.total_sections = len(script_data)
            self.log(f"📄 Found {self.total_sections} sections in script")
            yield

            # Generate prompts using the generator method with progress tracking
            image_prompts = []
            previous_context = ""
            
            for idx, section in enumerate(script_data):
                self.current_section = idx + 1
                yield  # Update progress UI
                
                self.log(f"[-] Generating prompt for section {idx + 1}/{self.total_sections}: {section.get('title', 'Unknown')}")
                yield

                # Generate image prompt
                prompt_data = await generator._generate_section_prompt(
                    section=section,
                    section_index=idx,
                    total_sections=self.total_sections,
                    previous_context=previous_context,
                    log_callback=log_callback
                )
                yield

                # Generate video prompt
                self.log(f"    [-] Generating video prompt...")
                yield
                video_prompt = await generator._generate_video_prompt(
                    section=section,
                    image_prompt_data=prompt_data,
                    section_index=idx,
                    total_sections=self.total_sections,
                    previous_context=previous_context,
                    log_callback=log_callback
                )
                prompt_data["video_prompt"] = video_prompt
                yield

                # Generate multi-angle camera prompt for subject focus
                self.log(f"    [-] Generating multi-angle camera prompt (subject)...")
                yield
                multi_angle_subject = await generator._generate_multi_angle_camera_prompt(
                    section=section,
                    image_prompt_data=prompt_data,
                    section_index=idx,
                    total_sections=self.total_sections,
                    prompt_type="subject",
                    log_callback=log_callback
                )
                prompt_data["multi_angle_camera_prompt_subject"] = multi_angle_subject
                yield

                # Generate multi-angle camera prompt for environment focus
                self.log(f"    [-] Generating multi-angle camera prompt (environment)...")
                yield
                multi_angle_env = await generator._generate_multi_angle_camera_prompt(
                    section=section,
                    image_prompt_data=prompt_data,
                    section_index=idx,
                    total_sections=self.total_sections,
                    prompt_type="environment",
                    log_callback=log_callback
                )
                prompt_data["multi_angle_camera_prompt_environment"] = multi_angle_env
                yield

                image_prompts.append(prompt_data)

                # Update context for next section
                previous_context = generator._build_context(section, prompt_data)
                yield

                await asyncio.sleep(0.5)  # Rate limiting

            # Store results
            self.image_prompts = image_prompts
            self.prompts_file_path = str(workspace_dir / self.selected_project / "prompts" / "05.image_prompts.json")
            
            # Save files manually
            output_path = Path(self.prompts_file_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save JSON
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(image_prompts, f, indent=2, ensure_ascii=False)
            
            # Save text files
            self._save_prompt_text_files(output_path, image_prompts)

            # Complete
            self.log("=" * 60)
            self.log("🎉 Image Prompt Generation Complete!")
            self.log(f"📄 Generated {len(image_prompts)} prompts")
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

    def get_prompt_preview(self, index: int) -> dict:
        """Get preview of specific prompt"""
        if 0 <= index < len(self.image_prompts):
            return self.image_prompts[index]
        return {}
