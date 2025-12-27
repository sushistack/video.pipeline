"""Extract Tab State Management"""
import reflex as rx
from pathlib import Path
import sys
import asyncio
import io
import contextlib

# Add parent project to path
PARENT_DIR = Path(__file__).resolve().parent.parent.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

# Add ui_reflex to path  
UI_DIR = Path(__file__).parent.parent
if str(UI_DIR) not in sys.path:
    sys.path.insert(0, str(UI_DIR))

# Force UTF-8 encoding for stdout/stderr to prevent cp949 errors on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from core.gen_caption import CaptionGenerator


class ExtractState(rx.State):
    """State management for Extract Tab"""
    
    # File selection
    available_files: list[str] = []
    selected_file: str = ""
    
    # Parameters
    model_options: list[str] = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-3-flash-preview"]
    selected_model: str = "gemini-2.5-flash"
    speaker_options: list[str] = ["1", "2", "3", "4", "5+"]
    selected_speakers: str = "2"
    
    # Fixed parameters
    target_langs: list[str] = ["ja", "en", "ko"]
    
    # Extraction status
    is_extracting: bool = False
    extraction_logs: list[str] = []
    should_stop: bool = False  # Flag for graceful stop
    
    # Computed properties
    @rx.var
    def can_extract(self) -> bool:
        """Can start extraction"""
        return bool(self.selected_file) and not self.is_extracting
    
    @rx.var
    def speaker_count(self) -> int:
        """Parse speaker count"""
        return 5 if self.selected_speakers == "5+" else int(self.selected_speakers)
    
    # Explicit setters
    def set_selected_file(self, value: str):
        """Set selected file"""
        self.selected_file = value
    
    def set_selected_model(self, value: str):
        """Set selected model"""
        self.selected_model = value
    
    def set_selected_speakers(self, value: str):
        """Set selected speakers"""
        self.selected_speakers = value
    
    def on_load(self):
        """Called when page loads"""
        self.load_files()
    
    def load_files(self):
        """Scan for available video/audio files"""
        video_input_dir = PARENT_DIR / "assets" / "videos"
        
        if video_input_dir.exists():
            files = []
            for f in video_input_dir.glob("*.*"):
                if f.suffix.lower() in ['.mp4', '.mkv', '.avi', '.mov', '.mp3', '.wav', '.m4a']:
                    files.append(f.name)
            
            self.available_files = sorted(files)
        else:
            self.available_files = []
    
    def log(self, message: str):
        """Add log message (mirrors console)"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}"
        self.extraction_logs.append(formatted)
        try:
            print(formatted)  # Console mirror
        except UnicodeEncodeError:
            # Fallback for Windows console encoding issues
            print(formatted.encode("utf-8", "ignore").decode("utf-8"))
    
    def stop_extraction(self):
        """Request extraction to stop"""
        self.should_stop = True
        self.log("⚠️ Stop requested by user...")
    
    async def start_extraction(self):
        """Start caption extraction process"""
        if not self.can_extract:
            yield rx.toast.error("Please select a file first!")
            return
        
        # Initialize state
        self.is_extracting = True
        self.should_stop = False
        self.extraction_logs = []  # Clear logs only on start
        yield  # Force UI update
        
        try:
            self.log("=" * 50)
            self.log(f"🎬 Starting extraction for: {self.selected_file}")
            self.log(f"🤖 Model: {self.selected_model}")
            self.log(f"👥 Speaker count: {self.speaker_count}")
            self.log(f"🌐 Languages: {', '.join(self.target_langs)}")
            self.log("=" * 50)
            yield  # Update UI
            
            # Get file path
            audio_path = PARENT_DIR / "assets" / "videos" / self.selected_file
            
            if not audio_path.exists():
                self.log(f"❌ ERROR: File not found: {audio_path}")
                yield rx.toast.error(f"File not found!")
                return
            
            output_root = PARENT_DIR / "workspace"
            
            # Initialize CaptionGenerator
            self.log("⚙️ Initializing CaptionGenerator...")
            yield
            cg = CaptionGenerator(model_name=self.selected_model)
            self.log(f"✅ CaptionGenerator ready with {cg.model_name}")
            yield
            
            # Check for stop before starting
            if self.should_stop:
                self.log("🛑 Stopped before extraction started")
                return
            
            # Run extraction with stdout capture
            self.log("🚀 Running extraction... (this may take several minutes)")
            self.log("📝 Processing audio and generating subtitles...")
            yield
            
            # Capture stdout/stderr
            import subprocess
            from threading import Thread
            
            def run_extraction():
                """Run in thread to capture output"""
                import sys
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                
                try:
                    # Redirect to capture
                    sys.stdout = io.StringIO()
                    sys.stderr = io.StringIO()
                    
                    cg.generate(
                        audio_path=audio_path,
                        output_dir=output_root,
                        target_languages=self.target_langs,
                        generate_json=False,
                        speaker_count=self.speaker_count
                    )
                    
                finally:
                    # Restore
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
            
            await asyncio.to_thread(run_extraction)
            
            # Check if stopped
            if self.should_stop:
                self.log("🛑 Extraction stopped by user")
                yield rx.toast.warning("Extraction stopped")
            else:
                self.log("=" * 50)
                self.log("🎉 Extraction Complete!")
                self.log(f"📁 Output saved to: workspace/{audio_path.stem}/subtitles/")
                self.log("=" * 50)
                yield rx.toast.success("Extraction Complete! 🚀")
            
        except Exception as e:
            self.log(f"❌ ERROR: {str(e)}")
            import traceback
            error_trace = traceback.format_exc()
            for line in error_trace.split('\n')[:5]:  # First 5 lines of trace
                if line.strip():
                    self.log(f"   {line}")
            yield rx.toast.error(f"Extraction Failed: {e}")
        
        finally:
            self.is_extracting = False
            self.should_stop = False
            yield  # Final UI update
