"""Story-to-Script Tab State Management"""
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

from core.gen_story_script import StoryToScriptGenerator


class StoryScriptState(rx.State):
    """State management for Story-to-Script Tab"""

    # Input fields
    story_title: str = ""
    story_context: str = ""
    project_name: str = ""  # User-defined project name

    # Model selection
    gemini_model_options: list[str] = ["gemini-2.5-flash", "gemini-3-flash-preview", "gemini-3-pro-preview"]
    selected_gemini_model: str = "gemini-3-pro-preview"

    # Pipeline status
    is_running: bool = False
    current_step: int = 0
    total_steps: int = 7
    progress: float = 0.0

    # Logs
    pipeline_logs: list[str] = []

    # Project info
    project_id: str = ""
    project_dir: str = ""

    # Generated files
    generated_content_path: str = ""
    generated_scripts: list[str] = []
    generated_subtitle_path: str = ""

    # Script content for preview
    current_script_content: str = ""
    script_sections: list[dict] = []

    # Computed properties
    @rx.var
    def can_start(self) -> bool:
        """Can start pipeline"""
        return bool(self.story_title.strip()) and not self.is_running
    
    @rx.var
    def progress_percentage(self) -> int:
        """Progress percentage"""
        return int((self.current_step / self.total_steps) * 100)
    
    @rx.var
    def status_text(self) -> str:
        """Current status text"""
        step_names = {
            0: "Ready",
            1: "Generating Content Research",
            2: "Creating Narration Script",
            3: "Improving with DeepSeek (Logic)",
            4: "Improving with Qwen (Polish)",
            5: "Improving with Gemini (Final)",
            6: "Generating Subtitles",
            7: "Complete"
        }
        return step_names.get(self.current_step, "Processing...")
    
    # Setters
    def set_story_title(self, value: str):
        """Set story title"""
        self.story_title = value

    def set_story_context(self, value: str):
        """Set story context"""
        self.story_context = value

    def set_project_name(self, value: str):
        """Set project name"""
        self.project_name = value

    def set_selected_gemini_model(self, value: str):
        """Set selected Gemini model"""
        self.selected_gemini_model = value

    def log(self, message: str):
        """Add log message"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}"
        self.pipeline_logs.append(formatted)
        print(formatted)
    
    async def run_pipeline(self):
        """Run the complete story-to-script pipeline"""
        if not self.can_start:
            yield rx.toast.error("Please enter a story title!")
            return
        
        # Initialize state
        self.is_running = True
        self.current_step = 0
        self.pipeline_logs = []
        self.generated_scripts = []
        self.generated_content_path = ""
        self.generated_subtitle_path = ""
        self.current_script_content = ""
        self.script_sections = []
        yield  # Force UI update
        
        try:
            self.log("=" * 60)
            self.log(f"🎬 Starting Story-to-Script Pipeline")
            self.log(f"   Title: {self.story_title}")
            self.log(f"   Model: {self.selected_gemini_model}")
            self.log("=" * 60)
            yield
            
            # Initialize generator
            workspace_dir = PARENT_DIR / "workspace"

            # Use user-defined project name or auto-generate
            import re
            if self.project_name.strip():
                # Slugify user input
                project_id = re.sub(r'[^a-zA-Z0-9가-힣_-]', '', self.project_name.strip())
                project_id = project_id.replace(' ', '_').replace('-', '_')
            else:
                # Auto-generate with timestamp
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                project_id = f"project_{timestamp}"

            generator = StoryToScriptGenerator(
                workspace_dir=workspace_dir,
                project_id=project_id
            )

            # Store project info
            self.project_id = generator.project_id
            self.project_dir = str(generator.project_dir)

            # Override model if different from default
            generator.gemini_model = self.selected_gemini_model
            
            # Define log callback
            def log_callback(message: str):
                self.log(message)
            
            # Step 1: Generate content
            self.current_step = 1
            yield
            content_path = await generator.generate_content(
                topic=self.story_title,
                context=self.story_context,
                log_callback=log_callback
            )
            self.generated_content_path = str(content_path)
            self.log(f"✅ Content generated: {content_path.name}")
            yield
            await asyncio.sleep(0.5)
            
            # Step 2: Generate narration script
            self.current_step = 2
            yield
            narration_path = await generator.generate_narration_script(log_callback=log_callback)
            self.generated_scripts.append(str(narration_path))
            self.log(f"✅ Narration script generated: {narration_path.name}")
            yield
            await asyncio.sleep(0.5)
            
            # Step 3: Improve with DeepSeek (Logic & Reasoning)
            self.current_step = 3
            yield
            deepseek_path = await generator.improve_script_step2(log_callback=log_callback)
            self.generated_scripts.append(str(deepseek_path))
            self.log(f"✅ DeepSeek improvement complete (Logic): {deepseek_path.name}")
            yield
            await asyncio.sleep(0.5)

            # Step 4: Improve with Qwen (Polish & Tone)
            self.current_step = 4
            yield
            qwen_path = await generator.improve_script_step3(log_callback=log_callback)
            self.generated_scripts.append(str(qwen_path))
            self.log(f"✅ Qwen improvement complete (Polish): {qwen_path.name}")
            yield
            await asyncio.sleep(0.5)

            # Step 5: Improve with Gemini (Final Review)
            self.current_step = 5
            yield
            gemini_path = await generator.improve_script_step1(log_callback=log_callback)
            self.generated_scripts.append(str(gemini_path))
            self.log(f"✅ Gemini improvement complete (Final): {gemini_path.name}")

            # Load final script for preview
            try:
                with open(gemini_path, "r", encoding="utf-8") as f:
                    final_script = json.load(f)
                    self.script_sections = final_script
                    self.current_script_content = json.dumps(final_script, indent=2, ensure_ascii=False)
            except Exception as e:
                self.log(f"[!] Warning: Could not load script preview: {e}")

            yield
            await asyncio.sleep(0.5)
            
            # Step 6: Generate subtitle
            self.current_step = 6
            yield
            subtitle_path = await generator.generate_subtitle(log_callback=log_callback)
            self.generated_subtitle_path = str(subtitle_path)
            self.log(f"✅ Subtitle generated: {subtitle_path.name}")
            yield
            
            # Complete
            self.current_step = 7
            self.log("=" * 60)
            self.log("🎉 Pipeline Complete!")
            self.log(f"📁 Project ID: {self.project_id}")
            self.log(f"📁 Project Path: {self.project_dir}")
            self.log(f"📄 Content: {self.generated_content_path}")
            self.log(f"📜 Scripts: {len(self.generated_scripts)} versions saved")
            self.log(f"📝 Subtitle: {self.generated_subtitle_path}")
            self.log("=" * 60)
            yield rx.toast.success("Story-to-Script Complete! 🚀")
            
        except Exception as e:
            self.log(f"❌ ERROR: {str(e)}")
            import traceback
            error_trace = traceback.format_exc()
            for line in error_trace.split('\n')[:5]:
                if line.strip():
                    self.log(f"   {line}")
            yield rx.toast.error(f"Pipeline Failed: {e}")
            
        finally:
            self.is_running = False
            yield  # Final UI update
    
    def load_script_preview(self, script_index: int = -1):
        """Load script preview from file"""
        if not self.generated_scripts:
            return
        
        try:
            # Use specified index or last script
            idx = script_index if script_index >= 0 else len(self.generated_scripts) - 1
            if idx >= len(self.generated_scripts):
                idx = len(self.generated_scripts) - 1
            
            script_path = Path(self.generated_scripts[idx])
            if script_path.exists():
                with open(script_path, "r", encoding="utf-8") as f:
                    script_data = json.load(f)
                    self.script_sections = script_data
                    self.current_script_content = json.dumps(script_data, indent=2, ensure_ascii=False)
                self.log(f"📄 Loaded preview: {script_path.name}")
        except Exception as e:
            self.log(f"[!] Failed to load script preview: {e}")
    
    def get_script_count(self) -> int:
        """Get number of generated scripts"""
        return len(self.generated_scripts)
