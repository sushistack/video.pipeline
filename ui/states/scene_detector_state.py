"""Scene Change Detector State - Detect angle changes in multi-angle videos"""
import reflex as rx
from pathlib import Path
from typing import List, Dict, Any
import base64
import io
import zipfile
import sys

# Add paths
PARENT_DIR = Path(__file__).resolve().parent.parent.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))


class SceneDetectorState(rx.State):
    """State for Scene Change Detector page"""

    # Project selection
    available_projects: List[str] = []
    selected_project: str = ""

    # Video files from workspace/{project}/videos/original
    video_files: List[Dict[str, Any]] = []
    selected_video: str = ""
    video_info: Dict[str, Any] = {}

    # Detection state
    is_detecting: bool = False
    detection_progress: int = 0
    progress_text: str = ""

    # Settings
    threshold: int = 27
    algorithm: str = "content"
    output_format: str = "jpg"
    output_quality: int = 90

    # Algorithm options
    algorithm_options: List[str] = ["content", "threshold", "adaptive"]
    format_options: List[str] = ["jpg", "png"]

    # Results
    detected_scenes: List[Dict[str, Any]] = []
    selected_scenes: List[str] = []  # List of scene IDs

    # Supported video formats
    SUPPORTED_FORMATS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

    def on_load(self):
        """Initialize state on page load"""
        self.load_projects()
        self.video_files = []
        self.selected_video = ""
        self.video_info = {}
        self.detected_scenes = []
        self.selected_scenes = []
        self.is_detecting = False
        self.detection_progress = 0

    def load_projects(self):
        """Scan workspace for projects"""
        output_root = PARENT_DIR / "workspace"
        if output_root.exists():
            projects = [
                p.name
                for p in output_root.iterdir()
                if p.is_dir()
            ]
            self.available_projects = sorted(projects)

            # Auto-select first project
            if self.available_projects and not self.selected_project:
                self.selected_project = self.available_projects[0]
                self.load_video_files()

    def set_selected_project(self, project: str):
        """Set selected project and load video files"""
        self.selected_project = project
        self.video_files = []
        self.selected_video = ""
        self.video_info = {}
        self.detected_scenes = []
        self.selected_scenes = []
        self.load_video_files()

    def load_video_files(self):
        """Load videos from workspace/{project}/videos/original"""
        if not self.selected_project:
            return

        source_dir = PARENT_DIR / "workspace" / self.selected_project / "videos" / "original"

        # Ensure directory exists
        source_dir.mkdir(parents=True, exist_ok=True)

        files = []
        for ext in self.SUPPORTED_FORMATS:
            files.extend(source_dir.glob(f"*{ext}"))
            files.extend(source_dir.glob(f"*{ext.upper()}"))

        # Remove duplicates and sort
        files = sorted(set(files), key=lambda x: x.name.lower())

        self.video_files = []
        for file_path in files:
            size_mb = file_path.stat().st_size / (1024 * 1024)
            self.video_files = self.video_files + [{
                "name": file_path.name,
                "path": str(file_path),
                "size_mb": round(size_mb, 1),
            }]

    def set_selected_video(self, video_name: str):
        """Select a video file and load its info"""
        self.selected_video = video_name
        self.detected_scenes = []
        self.selected_scenes = []

        # Find video path
        video_path = None
        for v in self.video_files:
            if v["name"] == video_name:
                video_path = v["path"]
                break

        if not video_path:
            return

        try:
            import cv2
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0
            cap.release()

            self.video_info = {
                "name": video_name,
                "path": video_path,
                "fps": fps,
                "frame_count": frame_count,
                "width": width,
                "height": height,
                "duration": duration,
            }
        except Exception as e:
            print(f"Error loading video info: {e}")
            self.video_info = {}

    def set_threshold(self, value: list[float]):
        """Set detection threshold from slider"""
        if value:
            self.threshold = int(value[0])

    def set_algorithm(self, value: str):
        """Set detection algorithm"""
        self.algorithm = value

    def set_output_format(self, value: str):
        """Set output format"""
        self.output_format = value

    def set_output_quality(self, value: list[float]):
        """Set output quality from slider"""
        if value:
            self.output_quality = int(value[0])

    @rx.var
    def scene_count(self) -> int:
        """Get detected scene count"""
        return len(self.detected_scenes)

    @rx.var
    def selected_count(self) -> int:
        """Get selected scene count"""
        return len(self.selected_scenes)

    @rx.var
    def has_results(self) -> bool:
        """Check if there are detection results"""
        return len(self.detected_scenes) > 0

    @rx.var
    def has_selection(self) -> bool:
        """Check if any scenes are selected"""
        return len(self.selected_scenes) > 0

    @rx.var
    def quality_disabled(self) -> bool:
        """Disable quality for PNG"""
        return self.output_format == "png"

    @rx.var
    def has_video_files(self) -> bool:
        """Check if there are video files"""
        return len(self.video_files) > 0

    @rx.var
    def has_video_selected(self) -> bool:
        """Check if a video is selected"""
        return bool(self.selected_video) and bool(self.video_info)

    @rx.var
    def video_info_str(self) -> str:
        """Get video info string"""
        if not self.video_info:
            return ""
        duration = self.video_info.get("duration", 0)
        fps = self.video_info.get("fps", 0)
        width = self.video_info.get("width", 0)
        height = self.video_info.get("height", 0)
        mins = int(duration // 60)
        secs = int(duration % 60)
        return f"{width}x{height} • {mins}:{secs:02d} • {fps:.1f}fps"

    @rx.var
    def source_dir_path(self) -> str:
        """Get source directory path for display"""
        if not self.selected_project:
            return ""
        return f"workspace/{self.selected_project}/videos/original"

    @rx.var
    def output_dir_path(self) -> str:
        """Get output directory path for display"""
        if not self.selected_project:
            return ""
        return f"workspace/{self.selected_project}/images/detected-cuts"

    @rx.var
    def video_names(self) -> List[str]:
        """Get list of video names for select"""
        return [v["name"] for v in self.video_files]

    async def detect_scenes(self):
        """Detect scene changes in video and save to output directory"""
        if not self.has_video_selected:
            yield rx.toast.error("Please select a video first")
            return

        if not self.selected_project:
            yield rx.toast.error("Please select a project")
            return

        self.is_detecting = True
        self.detection_progress = 0
        self.progress_text = "Preparing analysis..."
        self.detected_scenes = []
        self.selected_scenes = []
        yield

        # Create output directory
        output_dir = PARENT_DIR / "workspace" / self.selected_project / "images" / "detected-cuts"
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            import cv2
            from scenedetect import open_video, SceneManager
            from scenedetect.detectors import ContentDetector, ThresholdDetector, AdaptiveDetector
            from PIL import Image

            video_path = self.video_info["path"]
            threshold = self.threshold
            algorithm = self.algorithm

            # Open video with scenedetect
            video = open_video(video_path)
            scene_manager = SceneManager()

            # Add detector based on algorithm
            if algorithm == "content":
                scene_manager.add_detector(ContentDetector(threshold=threshold))
            elif algorithm == "threshold":
                scene_manager.add_detector(ThresholdDetector(threshold=threshold))
            else:  # adaptive
                scene_manager.add_detector(AdaptiveDetector(adaptive_threshold=threshold / 10))

            self.progress_text = "Detecting scenes..."
            yield

            # Detect scenes
            scene_manager.detect_scenes(video)
            scene_list = scene_manager.get_scene_list()

            # Always include first frame + detected scene changes
            frames_to_extract = [(0, 0.0)]  # (frame_number, timestamp)
            for scene in scene_list:
                start_frame = scene[0].get_frames()
                start_time = scene[0].get_seconds()
                if start_frame > 0:  # Avoid duplicate first frame
                    frames_to_extract.append((start_frame, start_time))

            self.progress_text = f"{len(frames_to_extract)} frames to extract (1 initial + {len(scene_list)} cuts)..."
            self.detection_progress = 50
            yield

            # Extract frames
            cap = cv2.VideoCapture(video_path)
            scenes = []

            for i, (start_frame, start_time) in enumerate(frames_to_extract):
                # Seek to frame
                cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
                ret, frame = cap.read()

                if ret:
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    height, width = frame_rgb.shape[:2]

                    # Create thumbnail (for preview)
                    max_dim = 200
                    scale = max_dim / max(height, width)
                    thumb_size = (int(width * scale), int(height * scale))
                    thumbnail = cv2.resize(frame_rgb, thumb_size)

                    # Encode thumbnail as base64
                    thumb_img = Image.fromarray(thumbnail)
                    thumb_buffer = io.BytesIO()
                    thumb_img.save(thumb_buffer, format="JPEG", quality=80)
                    thumb_base64 = base64.b64encode(thumb_buffer.getvalue()).decode()

                    # Save full frame to output directory
                    full_img = Image.fromarray(frame_rgb)

                    # Determine output format and filename
                    ext = self.output_format
                    filename = f"frame_{start_frame:06d}.{ext}"
                    output_path = output_dir / filename

                    save_format = ext.upper()
                    if save_format == "JPG":
                        save_format = "JPEG"
                        if full_img.mode == "RGBA":
                            full_img = full_img.convert("RGB")

                    save_kwargs = {}
                    if ext == "jpg":
                        save_kwargs["quality"] = self.output_quality

                    full_img.save(output_path, format=save_format, **save_kwargs)

                    # Format timestamp
                    mins = int(start_time // 60)
                    secs = int(start_time % 60)
                    frames = int((start_time % 1) * 30)

                    scene_id = f"scene_{i:03d}"
                    scenes.append({
                        "id": scene_id,
                        "index": i + 1,
                        "frame_number": start_frame,
                        "timestamp": start_time,
                        "timestamp_str": f"{mins:02d}:{secs:02d}:{frames:02d}",
                        "preview": f"data:image/jpeg;base64,{thumb_base64}",
                        "filename": filename,
                        "path": str(output_path),
                        "width": width,
                        "height": height,
                        "selected": True,
                    })

                # Update progress
                if len(frames_to_extract) > 0:
                    progress = 50 + int((i + 1) / len(frames_to_extract) * 50)
                    self.detection_progress = progress
                    yield

            cap.release()

            self.detected_scenes = scenes
            self.selected_scenes = [s["id"] for s in scenes]
            self.progress_text = f"Complete! {len(scenes)} angle changes detected"
            self.detection_progress = 100
            self.is_detecting = False
            yield

            yield rx.toast.success(f"{len(scenes)} frames saved → {self.output_dir_path}")

        except ImportError as e:
            self.is_detecting = False
            yield rx.toast.error(f"Required library missing: {str(e)}")
        except Exception as e:
            self.is_detecting = False
            yield rx.toast.error(f"Detection failed: {str(e)}")

    def toggle_scene_selection(self, scene_id: str):
        """Toggle selection of a scene"""
        if scene_id in self.selected_scenes:
            self.selected_scenes = [s for s in self.selected_scenes if s != scene_id]
        else:
            self.selected_scenes = self.selected_scenes + [scene_id]

    def select_all_scenes(self):
        """Select all scenes"""
        self.selected_scenes = [s["id"] for s in self.detected_scenes]

    def deselect_all_scenes(self):
        """Deselect all scenes"""
        self.selected_scenes = []

    def download_single(self, scene_id: str):
        """Download single frame"""
        for scene in self.detected_scenes:
            if scene["id"] == scene_id:
                file_path = Path(scene["path"])
                if file_path.exists():
                    data = file_path.read_bytes()
                    return rx.download(data=data, filename=scene["filename"])
        return rx.toast.error("Frame not found")

    def download_selected_zip(self):
        """Download selected frames as ZIP"""
        if not self.selected_scenes:
            return rx.toast.error("No frames selected")

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for scene in self.detected_scenes:
                if scene["id"] in self.selected_scenes:
                    file_path = Path(scene["path"])
                    if file_path.exists():
                        zf.write(file_path, scene["filename"])

        return rx.download(data=zip_buffer.getvalue(), filename="detected_cuts.zip")
