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

# SCP Database path
SCP_DB_DIR = Path("/mnt/data/raw")


class StoryScriptState(rx.State):
    """State management for Story-to-Script Tab"""

    # SCP Selection (RAG-like injection)
    available_scps: list[dict] = []  # [{scp_id, title, rating}, ...]
    selected_scp_id: str = ""  # e.g., "SCP-049"
    scp_facts: dict = {}  # Loaded facts.json data

    # Model selection
    gemini_model_options: list[str] = ["gemini-2.5-flash", "gemini-3-flash-preview", "gemini-3-pro-preview"]
    selected_gemini_model: str = "gemini-3-pro-preview"

    # Pipeline status
    is_running: bool = False
    current_step: int = 0
    total_steps: int = 5
    progress: float = 0.0

    # Logs
    pipeline_logs: list[str] = []

    # Project info
    project_id: str = ""
    project_dir: str = ""
    scripts_dir: str = ""

    # Generated files
    generated_content_path: str = ""
    generated_scripts: list[str] = []
    generated_subtitle_path: str = ""

    # Script content for preview
    current_script_content: str = ""
    script_sections: list[dict] = []
    
    # Step-by-step file previews
    research_content: str = ""
    structure_content: str = ""
    writing_content: str = ""
    review_content: str = ""
    srt_content: str = ""

    # Computed properties
    @rx.var
    def can_start(self) -> bool:
        """Can start pipeline"""
        return bool(self.selected_scp_id) and not self.is_running

    @rx.var
    def progress_percentage(self) -> int:
        """Progress percentage"""
        return int((self.current_step / self.total_steps) * 100)

    @rx.var
    def status_text(self) -> str:
        """Current status text"""
        if self.current_step == 5:
            return "✅ Complete"

        step_names = {
            0: "Ready",
            1: "Step 1/5: Research",
            2: "Step 2/5: Structure",
            3: "Step 3/5: Writing",
            4: "Step 4/5: Review",
        }
        return step_names.get(self.current_step, "Processing...")
    
    @rx.var
    def structure_lines(self) -> list[str]:
        """Format structure JSON for display"""
        return self._format_json_lines(self.structure_content)
    
    @rx.var
    def writing_lines(self) -> list[str]:
        """Format writing JSON for display"""
        return self._format_json_lines(self.writing_content)
    
    @rx.var
    def review_lines(self) -> list[str]:
        """Format review JSON for display"""
        return self._format_json_lines(self.review_content)
    
    @rx.var
    def srt_lines(self) -> list[str]:
        """Format SRT content for display"""
        return self.srt_content.split("\n") if self.srt_content else []
    
    @rx.var
    def research_lines(self) -> list[str]:
        """Get research content lines for display"""
        return self.research_content.split("\n") if self.research_content else []
    
    def _format_json_lines(self, json_str: str) -> list[str]:
        """Helper to format JSON with proper indentation"""
        import json as json_module
        try:
            if not json_str:
                return ["No content"]
            data = json_module.loads(json_str)
            formatted = json_module.dumps(data, indent=2, ensure_ascii=False)
            return formatted.split("\n")
        except:
            return json_str.split("\n") if json_str else ["Invalid JSON"]

    def set_selected_gemini_model(self, value: str):
        """Set selected Gemini model"""
        self.selected_gemini_model = value

    # SCP Selection Methods
    def on_load(self):
        """Called when page loads - load available SCPs"""
        self.load_available_scps()

    def load_available_scps(self):
        """Scan /mnt/data/*/facts.json, sorted by rating (descending)"""
        if not SCP_DB_DIR.exists():
            self.available_scps = []
            return

        scps = []
        for scp_dir in SCP_DB_DIR.iterdir():
            if scp_dir.is_dir() and scp_dir.name.startswith("SCP-"):
                facts_file = scp_dir / "facts.json"
                if facts_file.exists():
                    try:
                        with open(facts_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            scps.append({
                                "scp_id": data.get("scp_id", scp_dir.name),
                                "title": data.get("title", "Unknown"),
                                "rating": data.get("rating", 0),
                            })
                    except Exception as e:
                        print(f"Failed to load {facts_file}: {e}")

        # Sort by rating (descending)
        scps.sort(key=lambda x: x["rating"], reverse=True)
        self.available_scps = scps

        # Auto-select first if none selected
        if scps and not self.selected_scp_id:
            self.set_selected_scp(scps[0]["scp_id"])

    def set_selected_scp(self, scp_id: str):
        """Select an SCP and load its facts.json"""
        self.selected_scp_id = scp_id

        if not scp_id:
            self.scp_facts = {}
            return

        facts_file = SCP_DB_DIR / scp_id / "facts.json"
        if facts_file.exists():
            try:
                with open(facts_file, "r", encoding="utf-8") as f:
                    self.scp_facts = json.load(f)
            except Exception as e:
                print(f"Failed to load SCP facts: {e}")
                self.scp_facts = {}
        else:
            self.scp_facts = {}

    @rx.var
    def scp_select_options(self) -> list[str]:
        """Format SCP options for select dropdown"""
        return [f"{s['scp_id']} - {s['title']} (★{s['rating']})" for s in self.available_scps]

    @rx.var
    def scp_select_value(self) -> str:
        """Get current SCP select value"""
        for s in self.available_scps:
            if s["scp_id"] == self.selected_scp_id:
                return f"{s['scp_id']} - {s['title']} (★{s['rating']})"
        return ""

    def handle_scp_select_change(self, value: str):
        """Handle SCP select dropdown change"""
        # Extract SCP ID from "SCP-049 - The Plague Doctor (★4500)"
        if value and " - " in value:
            scp_id = value.split(" - ")[0]
            self.set_selected_scp(scp_id)

    @rx.var
    def has_scp_facts(self) -> bool:
        """Check if SCP facts are loaded"""
        return bool(self.scp_facts)

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
            self.log(f"   SCP: {self.selected_scp_id}")
            self.log(f"   Model: {self.selected_gemini_model}")
            self.log("=" * 60)
            yield

            # Initialize generator
            workspace_dir = PARENT_DIR / "workspace"

            # Use SCP ID as project_id (e.g., "SCP-049" -> "SCP_049")
            project_id = self.selected_scp_id.replace('-', '_')

            generator = StoryToScriptGenerator(
                workspace_dir=workspace_dir,
                project_id=project_id
            )

            # Store project info
            self.project_id = generator.project_id
            self.project_dir = str(generator.project_dir)
            self.scripts_dir = str(generator.scripts_dir)

            # Override model if different from default
            generator.gemini_model = self.selected_gemini_model

            # Prepare SCP facts for RAG injection (convert to regular dict if needed)
            scp_facts_dict = dict(self.scp_facts) if self.scp_facts else None

            # Save SCP facts to project directory for image prompter
            if scp_facts_dict:
                scp_facts_path = generator.project_dir / "scp_facts.json"
                with open(scp_facts_path, "w", encoding="utf-8") as f:
                    json.dump(scp_facts_dict, f, indent=2, ensure_ascii=False)
                self.log(f"   [RAG] Saved SCP facts to: {scp_facts_path}")

            # Define log callback
            def log_callback(message: str):
                self.log(message)

            scripts_path = Path(self.scripts_dir) if self.scripts_dir else Path(generator.scripts_dir)
            subtitles_path = Path(generator.subtitles_dir)

            # Step 1: Research
            self.current_step = 1
            yield
            research_path = scripts_path / "01_research_packet.md"
            
            # Get topic from SCP facts
            topic = self.scp_facts.get("title", self.selected_scp_id)
            
            if research_path.exists():
                self.log(f"⏭️ Step 1/5: Research already exists, skipping...")
                from core.models.script_models import ResearchPacket
                research = ResearchPacket(
                    topic=topic,
                    raw_content=research_path.read_text(encoding="utf-8")
                )
                self.research_content = research.raw_content
            else:
                research = await generator.step1_research(
                    topic=topic,
                    scp_facts=scp_facts_dict,
                    log_callback=log_callback
                )
                self.research_content = research.raw_content
                # Save research content for preview
                with open(research_path, "w", encoding="utf-8") as f:
                    f.write(research.raw_content)
            self.generated_content_path = str(research_path)
            self.log(f"✅ Step 1/5: Research complete")
            yield
            await asyncio.sleep(0.5)

            # Step 2: Structure
            self.current_step = 2
            yield
            structure_path = scripts_path / "02_scene_structure.json"
            if structure_path.exists():
                self.log(f"⏭️ Step 2/5: Structure already exists, skipping...")
                from core.models.script_models import SceneStructure
                with open(structure_path, "r", encoding="utf-8") as f:
                    structure = SceneStructure.from_dict(json.load(f))
                self.structure_content = json.dumps(structure.to_dict(), indent=2, ensure_ascii=False)
            else:
                structure = await generator.step2_structure(
                    research=research,
                    target_duration_minutes=12,
                    scp_facts=scp_facts_dict,
                    log_callback=log_callback
                )
                self.structure_content = structure.to_json()
                # Save structure for preview
                with open(structure_path, "w", encoding="utf-8") as f:
                    json.dump(structure.to_dict(), f, indent=2, ensure_ascii=False)
            self.generated_scripts.append(str(structure_path))
            self.log(f"✅ Step 2/5: Structure complete")
            yield
            await asyncio.sleep(0.5)

            # Step 3: Writing
            self.current_step = 3
            yield
            draft_path = scripts_path / "03_narration_draft.json"
            if draft_path.exists():
                self.log(f"⏭️ Step 3/5: Writing already exists, skipping...")
                from core.models.script_models import NarrationScript
                with open(draft_path, "r", encoding="utf-8") as f:
                    script = NarrationScript.from_dict(json.load(f))
                self.writing_content = json.dumps(script.to_dict(), indent=2, ensure_ascii=False)
            else:
                script = await generator.step3_writing(
                    structure=structure,
                    log_callback=log_callback
                )
                self.writing_content = script.to_json()
                # Save draft for preview
                with open(draft_path, "w", encoding="utf-8") as f:
                    json.dump(script.to_dict(), f, indent=2, ensure_ascii=False)
            self.generated_scripts.append(str(draft_path))
            self.log(f"✅ Step 3/5: Writing complete")
            yield
            await asyncio.sleep(0.5)

            # Step 4: Review
            self.current_step = 4
            yield
            reviewed_path = scripts_path / "04_narration_reviewed.json"
            if reviewed_path.exists():
                self.log(f"⏭️ Step 4/5: Review already exists, skipping...")
                from core.models.script_models import NarrationScript
                with open(reviewed_path, "r", encoding="utf-8") as f:
                    reviewed = NarrationScript.from_dict(json.load(f))
                self.review_content = json.dumps(reviewed.to_dict(), indent=2, ensure_ascii=False)
            else:
                reviewed = await generator.step4_review(
                    script=script,
                    log_callback=log_callback
                )
                self.review_content = json.dumps(reviewed.to_dict(), indent=2, ensure_ascii=False)
                # Save reviewed script for preview
                with open(reviewed_path, "w", encoding="utf-8") as f:
                    json.dump(reviewed.to_dict(), f, indent=2, ensure_ascii=False)
            self.generated_scripts.append(str(reviewed_path))
            self.log(f"✅ Step 4/5: Review complete")
            yield
            await asyncio.sleep(0.5)

            # Step 5: SRT (directly from NarrationScript)
            self.current_step = 5
            yield
            srt_path = subtitles_path / "ko.srt"
            if srt_path.exists():
                self.log(f"⏭️ Step 5/5: SRT already exists, skipping...")
                self.srt_content = srt_path.read_text(encoding="utf-8")
            else:
                srt_path = await generator.step5_srt(
                    script=reviewed,
                    log_callback=log_callback
                )
                self.srt_content = srt_path.read_text(encoding="utf-8")
            self.generated_subtitle_path = str(srt_path)
            self.log(f"✅ Step 5/5: SRT complete")
            yield
            await asyncio.sleep(0.5)

            # Load final script for preview
            try:
                final_script_path = reviewed_path
                if final_script_path.exists():
                    with open(final_script_path, "r", encoding="utf-8") as f:
                        final_script = json.load(f)
                        # Extract lines array if the data is wrapped in a dict
                        if isinstance(final_script, dict) and 'lines' in final_script:
                            self.script_sections = final_script['lines']
                        else:
                            self.script_sections = final_script
                        # current_script_content is already set from review_content
                        self.current_script_content = self.review_content
            except Exception as e:
                self.log(f"[!] Warning: Could not load script preview: {e}")
            yield
            
            # Complete
            self.current_step = 5
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
                    # Extract lines array if the data is wrapped in a dict
                    if isinstance(script_data, dict) and 'lines' in script_data:
                        self.script_sections = script_data['lines']
                    else:
                        self.script_sections = script_data
                    self.current_script_content = json.dumps(script_data, indent=2, ensure_ascii=False)
                self.log(f"📄 Loaded preview: {script_path.name}")
        except Exception as e:
            self.log(f"[!] Failed to load script preview: {e}")
    
    def get_script_count(self) -> int:
        """Get number of generated scripts"""
        return len(self.generated_scripts)
