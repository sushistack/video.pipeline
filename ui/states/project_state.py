
import reflex as rx
from pathlib import Path
import sys

# Add paths
PARENT_DIR = Path(__file__).resolve().parent.parent.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

class ProjectState(rx.State):
    """State for Project Generation Tab"""
    
    available_projects: list[str] = []
    selected_project: str = ""
    is_generating: bool = False
    
    # Validation State
    audio_files: list[str] = []
    video_files: list[str] = []
    subtitle_count: int = 0
    audio_count: int = 0
    video_count: int = 0
    is_valid: bool = False
    validation_message: str = ""

    def on_load(self):
        """Load projects"""
        output_root = PARENT_DIR / "workspace"
        if output_root.exists():
            projects = [
                p.name for p in output_root.iterdir()
                if p.is_dir()
            ]
            self.available_projects = sorted(projects)

    def load_projects(self):
        """Reload project list (Alias for on_load)"""
        self.on_load()
    
    def set_selected_project(self, value: str):
        self.selected_project = value
        self.load_project_details()

    def load_project_details(self):
        """Load validation details for selected project"""
        if not self.selected_project:
            self.audio_files = []
            self.audio_count = 0
            self.video_files = []
            self.video_count = 0
            self.subtitle_count = 0
            self.is_valid = False
            self.validation_message = "No project selected."
            return

        project_dir = PARENT_DIR / "workspace" / self.selected_project
        
        # Scan Audios
        audio_dir = project_dir / "audios" / "ja"
        if audio_dir.exists():
            self.audio_files = sorted([f.name for f in audio_dir.glob("*.mp3")])
        else:
            self.audio_files = []
        self.audio_count = len(self.audio_files)

        # Scan Videos
        video_dir = project_dir / "simulated"
        if video_dir.exists():
            self.video_files = sorted([f.name for f in video_dir.glob("*.mp4")])
        else:
            self.video_files = []
        self.video_count = len(self.video_files)

        # Read Subtitle Count
        sub_path = project_dir / "subtitles" / "synced" / "ja.json"
        if sub_path.exists():
            try:
                import json
                with open(sub_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.subtitle_count = len(data)
            except:
                self.subtitle_count = 0
        else:
            self.subtitle_count = 0

        # Validate
        if self.audio_count == 0:
            self.is_valid = False
            self.validation_message = "No audio files found."
        elif self.subtitle_count == 0:
            self.is_valid = False
            self.validation_message = "No synonyms/subtitles found."
        elif self.audio_count != self.subtitle_count:
            self.is_valid = False
            self.validation_message = f"Mismatch: Audio ({self.audio_count}) != Subtitles ({self.subtitle_count})"
        else:
            self.is_valid = True
            self.validation_message = "Ready to generate."

    async def generate_project(self):
        """Generate CapCut Project Draft"""
        if not self.selected_project:
            yield rx.toast.error("Please select a project!")
            return
            
        self.is_generating = True
        yield
        
        try:
            # Import dynamically to ensure path is set
            from core.gen_capcut import CapCutGenerator
            
            output_root = PARENT_DIR / "workspace"
            generator = CapCutGenerator(output_root)
            
            yield rx.toast.info(f"Building timeline for {self.selected_project}...")
            generator.add_media_tracks(self.selected_project)
            
            yield rx.toast.info("Processing subtitles & Yomigana...")
            generator.process_subtitles(self.selected_project)
            
            # Use direct export to CapCut
            saved_path = generator.export_to_capcut(self.selected_project)
            
            yield rx.toast.success(f"Project exported to CapCut: {saved_path.name}")
            
        except Exception as e:
            yield rx.toast.error(f"Generation failed: {e}")
            print(f"Generation error: {e}")
        finally:
            self.is_generating = False
