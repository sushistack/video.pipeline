"""Image Preprocessor State - Image optimization for video generation models"""
import reflex as rx
from pathlib import Path
from PIL import Image
import io
import zipfile
import base64
import sys
from typing import List, Dict, Any

# Add paths
PARENT_DIR = Path(__file__).resolve().parent.parent.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))


class ImagePreprocessorState(rx.State):
    """State for Image Preprocessor page"""

    # Project selection
    available_projects: List[str] = []
    selected_project: str = ""

    # Source files from workspace/{project}/images/original
    source_files: List[Dict[str, Any]] = []
    processed_files: List[Dict[str, Any]] = []
    is_processing: bool = False

    # Settings
    target_resolution: str = "1280"
    output_format: str = "jpg"
    quality: int = 85
    add_suffix: bool = False
    suffix_text: str = "_processed"

    # Resolution options
    resolution_options: List[str] = ["720", "1024", "1280", "1920", "original"]
    format_options: List[str] = ["jpg", "webp", "png"]

    # Supported formats
    SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}

    def on_load(self):
        """Initialize state on page load"""
        self.load_projects()
        self.source_files = []
        self.processed_files = []
        self.is_processing = False

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
                self.load_source_files()

    def set_selected_project(self, project: str):
        """Set selected project and load source files"""
        self.selected_project = project
        self.source_files = []
        self.processed_files = []
        self.load_source_files()

    def load_source_files(self):
        """Load images from workspace/{project}/images/original"""
        if not self.selected_project:
            return

        source_dir = PARENT_DIR / "workspace" / self.selected_project / "images" / "original"

        # Ensure directory exists
        source_dir.mkdir(parents=True, exist_ok=True)

        files = []
        for ext in self.SUPPORTED_FORMATS:
            files.extend(source_dir.glob(f"*{ext}"))
            files.extend(source_dir.glob(f"*{ext.upper()}"))

        # Remove duplicates and sort
        files = sorted(set(files), key=lambda x: x.name.lower())

        self.source_files = []
        for file_path in files:
            try:
                img = Image.open(file_path)
                width, height = img.size
                size_kb = file_path.stat().st_size / 1024

                # Create preview (base64)
                preview_img = img.copy()
                preview_img.thumbnail((150, 150))
                preview_buffer = io.BytesIO()
                preview_format = "PNG" if img.mode == "RGBA" else "JPEG"
                preview_img.save(preview_buffer, format=preview_format)
                preview_base64 = base64.b64encode(preview_buffer.getvalue()).decode()

                self.source_files = self.source_files + [{
                    "id": file_path.stem,
                    "name": file_path.name,
                    "path": str(file_path),
                    "width": width,
                    "height": height,
                    "size_kb": round(size_kb, 1),
                    "preview": f"data:image/{preview_format.lower()};base64,{preview_base64}",
                }]
                img.close()
            except Exception as e:
                print(f"Error loading {file_path}: {e}")

    def set_target_resolution(self, value: str):
        """Set target resolution"""
        self.target_resolution = value

    def set_output_format(self, value: str):
        """Set output format"""
        self.output_format = value

    def set_quality(self, value: list[float]):
        """Set compression quality from slider"""
        if value:
            self.quality = int(value[0])

    def set_add_suffix(self, value: bool):
        """Toggle suffix addition"""
        self.add_suffix = value

    def set_suffix_text(self, value: str):
        """Set suffix text"""
        self.suffix_text = value

    @rx.var
    def quality_disabled(self) -> bool:
        """Disable quality slider for PNG (lossless)"""
        return self.output_format == "png"

    @rx.var
    def has_sources(self) -> bool:
        """Check if there are source files"""
        return len(self.source_files) > 0

    @rx.var
    def has_processed(self) -> bool:
        """Check if there are processed files"""
        return len(self.processed_files) > 0

    @rx.var
    def source_count(self) -> int:
        """Get source file count"""
        return len(self.source_files)

    @rx.var
    def processed_count(self) -> int:
        """Get processed count"""
        return len(self.processed_files)

    @rx.var
    def source_dir_path(self) -> str:
        """Get source directory path for display"""
        if not self.selected_project:
            return ""
        return f"workspace/{self.selected_project}/images/original"

    @rx.var
    def output_dir_path(self) -> str:
        """Get output directory path for display"""
        if not self.selected_project:
            return ""
        return f"workspace/{self.selected_project}/images/processed"

    async def process_images(self):
        """Process all source images and save to output directory"""
        if not self.source_files:
            yield rx.toast.error("No images to process")
            return

        if not self.selected_project:
            yield rx.toast.error("Please select a project")
            return

        self.is_processing = True
        self.processed_files = []
        yield

        # Create output directory
        output_dir = PARENT_DIR / "workspace" / self.selected_project / "images" / "processed"
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            for file_info in self.source_files:
                # Load image from path
                img = Image.open(file_info["path"])

                # Convert RGBA to RGB for JPG
                if self.output_format == "jpg" and img.mode == "RGBA":
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background
                elif self.output_format == "jpg" and img.mode != "RGB":
                    img = img.convert("RGB")

                # Resize if needed
                original_width, original_height = img.size
                new_width, new_height = original_width, original_height

                if self.target_resolution != "original":
                    target_size = int(self.target_resolution)
                    long_edge = max(original_width, original_height)

                    if long_edge > target_size:
                        scale = target_size / long_edge
                        new_width = int(original_width * scale)
                        new_height = int(original_height * scale)
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                # Generate new filename
                original_name = Path(file_info["name"]).stem
                suffix = self.suffix_text if self.add_suffix else ""
                new_filename = f"{original_name}{suffix}.{self.output_format}"
                output_path = output_dir / new_filename

                # Save to file
                save_format = self.output_format.upper()
                if save_format == "JPG":
                    save_format = "JPEG"

                save_kwargs = {}
                if self.output_format in ["jpg", "webp"]:
                    save_kwargs["quality"] = self.quality
                if self.output_format == "webp":
                    save_kwargs["method"] = 6  # Best compression

                img.save(output_path, format=save_format, **save_kwargs)
                new_size_kb = output_path.stat().st_size / 1024

                # Create preview
                preview_img = img.copy()
                preview_img.thumbnail((150, 150))
                preview_buffer = io.BytesIO()
                preview_format = "PNG" if img.mode == "RGBA" else "JPEG"
                preview_img.save(preview_buffer, format=preview_format)
                preview_base64 = base64.b64encode(preview_buffer.getvalue()).decode()

                self.processed_files = self.processed_files + [{
                    "id": file_info["id"],
                    "original_name": file_info["name"],
                    "name": new_filename,
                    "path": str(output_path),
                    "original_width": file_info["width"],
                    "original_height": file_info["height"],
                    "width": new_width,
                    "height": new_height,
                    "original_size_kb": file_info["size_kb"],
                    "size_kb": round(new_size_kb, 1),
                    "preview": f"data:image/{preview_format.lower()};base64,{preview_base64}",
                }]
                img.close()
                yield

            yield rx.toast.success(f"{len(self.processed_files)} images processed → {self.output_dir_path}")

        except Exception as e:
            yield rx.toast.error(f"Processing failed: {str(e)}")
        finally:
            self.is_processing = False

    def download_single(self, file_id: str):
        """Download single processed file"""
        for f in self.processed_files:
            if f["id"] == file_id:
                file_path = Path(f["path"])
                if file_path.exists():
                    data = file_path.read_bytes()
                    return rx.download(data=data, filename=f["name"])
        return rx.toast.error("File not found")

    def download_all_zip(self):
        """Download all processed files as ZIP"""
        if not self.processed_files:
            return rx.toast.error("No processed files")

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in self.processed_files:
                file_path = Path(f["path"])
                if file_path.exists():
                    zf.write(file_path, f["name"])

        zip_data = zip_buffer.getvalue()
        return rx.download(data=zip_data, filename="processed_images.zip")
