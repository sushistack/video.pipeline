"""Image Generator State - Generate images using Janus-Pro-7B via SiliconFlow API"""
import reflex as rx
from pathlib import Path
import sys
import json
import random
from typing import List, Optional
from pydantic import BaseModel

# Add paths
PARENT_DIR = Path(__file__).resolve().parent.parent.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

UI_DIR = Path(__file__).parent.parent
if str(UI_DIR) not in sys.path:
    sys.path.insert(0, str(UI_DIR))

from core.gen_janus_api import JanusAPIGenerator


class ImagePromptItem(BaseModel):
    """Single image prompt item"""
    id: str = ""
    scene_index: int = 0
    sub_scene_index: int = 0
    shot_type: str = "first"  # "first" or "last"
    scene_title: str = ""
    key_point: str = ""
    prompt: str = ""
    image_path: Optional[str] = None
    preview: Optional[str] = None
    width: int = 0
    height: int = 0
    status: str = "pending"  # "pending", "generating", "completed", "failed"
    error: Optional[str] = None


class ImageGeneratorState(rx.State):
    """State for Image Generator page"""

    # Project selection
    available_projects: List[str] = []
    selected_project: str = ""

    # Prompts from file
    prompt_items: List[ImagePromptItem] = []

    # Generation status
    is_generating: bool = False
    current_index: int = 0
    total_items: int = 0
    completed_count: int = 0
    failed_count: int = 0

    # Logs
    generation_logs: List[str] = []

    # Settings
    guidance_scale: float = 5.0
    num_inference_steps: int = 30
    image_width: str = "1024"
    image_height: str = "576"
    seed: int = 42
    use_random_seed: bool = False

    # Generator instance
    _generator: Optional[JanusAPIGenerator] = None

    def on_load(self):
        """Initialize state on page load"""
        self.load_projects()
        self.generation_logs = []
        self.is_generating = False

    def load_projects(self):
        """Scan workspace for projects with image prompts"""
        workspace_dir = PARENT_DIR / "workspace"

        if workspace_dir.exists():
            projects = []
            for project_dir in workspace_dir.iterdir():
                if project_dir.is_dir() and not project_dir.name.startswith("."):
                    # Check if it has 05_image_prompts.json or scripts folder
                    prompts_file = project_dir / "scripts" / "05_image_prompts.json"
                    scripts_dir = project_dir / "scripts"
                    if prompts_file.exists() or scripts_dir.exists():
                        projects.append(project_dir.name)

            self.available_projects = sorted(projects, reverse=True)

            # Auto-select first project
            if self.available_projects and not self.selected_project:
                self.selected_project = self.available_projects[0]
                self.load_prompts()
        else:
            self.available_projects = []

    def set_selected_project(self, project: str):
        """Set selected project and load prompts"""
        self.selected_project = project
        self.prompt_items = []
        self.load_prompts()

    def load_prompts(self):
        """Load image prompts from workspace/{project}/scripts/05_image_prompts.json"""
        if not self.selected_project:
            return

        prompts_file = PARENT_DIR / "workspace" / self.selected_project / "scripts" / "05_image_prompts.json"
        if not prompts_file.exists():
            self.prompt_items = []
            return

        try:
            with open(prompts_file, "r", encoding="utf-8") as f:
                prompts_data = json.load(f)

            items = []
            item_id = 0

            for scene_idx, scene in enumerate(prompts_data):
                scene_title = scene.get("scene_title", f"Scene {scene_idx + 1}")
                sub_scenes = scene.get("sub_scenes", [])

                for sub_idx, sub_scene in enumerate(sub_scenes):
                    key_point = sub_scene.get("key_point", "")

                    # Opening shot (new schema)
                    opening_shot = sub_scene.get("opening_shot", {})
                    opening_prompt_data = opening_shot.get("image_prompt", {})
                    if isinstance(opening_prompt_data, dict) and opening_prompt_data.get("prompt"):
                        # Check if image already exists
                        image_path = PARENT_DIR / "workspace" / self.selected_project / "images" / "generated" / f"scene{scene_idx + 1}_sub{sub_idx + 1}_opening.png"
                        preview = None
                        status = "pending"

                        if image_path.exists():
                            import base64
                            from PIL import Image
                            import io

                            img = Image.open(image_path)
                            preview_buffer = io.BytesIO()
                            img.thumbnail((512, 512))
                            img.save(preview_buffer, format="PNG")
                            preview = f"data:image/png;base64,{base64.b64encode(preview_buffer.getvalue()).decode()}"
                            status = "completed"
                            img.close()

                        items.append(ImagePromptItem(
                            id=f"scene{scene_idx + 1}_sub{sub_idx + 1}_opening",
                            scene_index=scene_idx,
                            sub_scene_index=sub_idx,
                            shot_type="opening",
                            scene_title=scene_title,
                            key_point=key_point,
                            prompt=opening_prompt_data["prompt"],
                            image_path=str(image_path) if image_path.exists() else None,
                            preview=preview,
                            width=opening_shot.get("image_prompt", {}).get("width", 1024),
                            height=opening_shot.get("image_prompt", {}).get("height", 1024),
                            status=status,
                        ))
                        item_id += 1

            self.prompt_items = items
            self.total_items = len(items)
            self.completed_count = sum(1 for item in items if item.status == "completed")

        except Exception as e:
            print(f"Failed to load prompts: {e}")
            self.prompt_items = []

    def log(self, message: str):
        """Add log message"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}"
        self.generation_logs.append(formatted)
        print(formatted)

    @rx.var
    def progress_percentage(self) -> int:
        """Progress percentage"""
        if self.total_items == 0:
            return 0
        return int((self.current_index / self.total_items) * 100)

    @rx.var
    def status_text(self) -> str:
        """Current status text"""
        if not self.is_generating:
            return "Ready"
        return f"Generating {self.current_index}/{self.total_items}"

    @rx.var
    def can_generate(self) -> bool:
        """Check if can start generation"""
        return bool(self.selected_project) and not self.is_generating

    @rx.var
    def has_pending_items(self) -> bool:
        """Check if there are pending items"""
        return any(item.status == "pending" or item.status == "failed" for item in self.prompt_items)

    def get_generator(self) -> JanusAPIGenerator:
        """Get or create generator instance"""
        if self._generator is None:
            workspace_dir = PARENT_DIR / "workspace"
            self._generator = JanusAPIGenerator(workspace_dir=workspace_dir)
        return self._generator

    async def generate_single(self, item_id: str):
        """Generate single image"""
        # Find the item
        item_index = -1
        for i, item in enumerate(self.prompt_items):
            if item.id == item_id:
                item_index = i
                break

        if item_index == -1:
            yield rx.toast.error("Item not found")
            return

        item = self.prompt_items[item_index]

        # Check if image already exists - skip generation if it does
        output_path = PARENT_DIR / "workspace" / self.selected_project / "images" / "generated" / f"{item_id}.png"
        if output_path.exists():
            # Refresh the item status and return early
            self.load_prompts()
            yield rx.toast.info(f"이미 생성된 이미지입니다: {item.scene_title} - {item.shot_type}")
            return

        # Update status to generating
        self.prompt_items[item_index].status = "generating"
        yield

        try:
            generator = self.get_generator()

            output_path = PARENT_DIR / "workspace" / self.selected_project / "images" / "generated" / f"{item_id}.png"

            def log_callback(msg: str):
                self.log(msg)

            # Determine seed to use
            current_seed = random.randint(0, 2**31 - 1) if self.use_random_seed else self.seed

            result = await generator.generate_image(
                prompt=item.prompt,
                output_path=output_path,
                width=int(self.image_width),
                height=int(self.image_height),
                cfg_weight=self.guidance_scale,
                num_inference_steps=self.num_inference_steps,
                seed=current_seed,
                log_callback=log_callback,
            )

            # Update item with result
            self.prompt_items[item_index].status = "completed"
            self.prompt_items[item_index].image_path = result["image_path"]
            self.prompt_items[item_index].preview = result["preview"]
            self.prompt_items[item_index].width = result["width"]
            self.prompt_items[item_index].height = result["height"]

            self.completed_count += 1

            yield rx.toast.success(f"Image generated: {item.scene_title} - {item.shot_type}")

        except Exception as e:
            self.prompt_items[item_index].status = "failed"
            self.prompt_items[item_index].error = str(e)
            self.failed_count += 1
            yield rx.toast.error(f"Generation failed: {e}")

    async def retry_single(self, item_id: str):
        """Retry single image - always regenerate even if image exists"""
        # Find the item
        item_index = -1
        for i, item in enumerate(self.prompt_items):
            if item.id == item_id:
                item_index = i
                break

        if item_index == -1:
            yield rx.toast.error("Item not found")
            return

        item = self.prompt_items[item_index]

        # Update status to generating (no check for existing image)
        self.prompt_items[item_index].status = "generating"
        yield

        try:
            generator = self.get_generator()

            output_path = PARENT_DIR / "workspace" / self.selected_project / "images" / "generated" / f"{item_id}.png"

            def log_callback(msg: str):
                self.log(msg)

            # Determine seed to use
            current_seed = random.randint(0, 2**31 - 1) if self.use_random_seed else self.seed

            result = await generator.generate_image(
                prompt=item.prompt,
                output_path=output_path,
                width=int(self.image_width),
                height=int(self.image_height),
                cfg_weight=self.guidance_scale,
                num_inference_steps=self.num_inference_steps,
                seed=current_seed,
                log_callback=log_callback,
            )

            # Update item with result
            self.prompt_items[item_index].status = "completed"
            self.prompt_items[item_index].image_path = result["image_path"]
            self.prompt_items[item_index].preview = result["preview"]
            self.prompt_items[item_index].width = result["width"]
            self.prompt_items[item_index].height = result["height"]

            self.completed_count += 1

            yield rx.toast.success(f"이미지 재생성 완료: {item.scene_title} - {item.shot_type}")

        except Exception as e:
            self.prompt_items[item_index].status = "failed"
            self.prompt_items[item_index].error = str(e)
            self.failed_count += 1
            yield rx.toast.error(f"재생성 실패: {e}")

    async def generate_all(self):
        """Generate all pending images"""
        if not self.can_generate:
            yield rx.toast.error("Please select a project first!")
            return

        # Refresh prompt items to check for existing images
        self.load_prompts()
        yield

        pending_items = [i for i, item in enumerate(self.prompt_items) if item.status == "pending" or item.status == "failed"]

        if not pending_items:
            yield rx.toast.info("No pending images to generate")
            return

        self.is_generating = True
        self.current_index = 0
        self.total_items = len(pending_items)
        self.failed_count = 0

        self.log("=" * 60)
        self.log(f"🎨 Starting Image Generation (Tongyi-MAI/Z-Image-Turbo via SiliconFlow)")
        self.log(f"📁 Project: {self.selected_project}")
        self.log(f"📊 Total images to generate: {len(pending_items)}")
        self.log(f"✅ Already completed: {self.completed_count}")
        self.log("=" * 60)

        yield

        try:
            generator = self.get_generator()

            def log_callback(msg: str):
                self.log(msg)

            generator.load_model(log_callback)
            yield

            for idx, item_index in enumerate(pending_items):
                self.current_index = idx + 1
                item = self.prompt_items[item_index]

                self.log(f"[*] [{self.current_index}/{self.total_items}] {item.scene_title} - {item.shot_type}")
                yield

                # Update status
                self.prompt_items[item_index].status = "generating"
                yield

                try:
                    output_path = PARENT_DIR / "workspace" / self.selected_project / "images" / "generated" / f"{item.id}.png"

                    # Different seed for each image in batch
                    current_seed = random.randint(0, 2**31 - 1) if self.use_random_seed else (self.seed + idx)

                    result = await generator.generate_image(
                        prompt=item.prompt,
                        output_path=output_path,
                        width=int(self.image_width),
                        height=int(self.image_height),
                        cfg_weight=self.guidance_scale,
                        num_inference_steps=self.num_inference_steps,
                        seed=current_seed,
                        log_callback=log_callback,
                    )

                    # Update item
                    self.prompt_items[item_index].status = "completed"
                    self.prompt_items[item_index].image_path = result["image_path"]
                    self.prompt_items[item_index].preview = result["preview"]
                    self.prompt_items[item_index].width = result["width"]
                    self.prompt_items[item_index].height = result["height"]
                    self.completed_count += 1

                except Exception as e:
                    self.prompt_items[item_index].status = "failed"
                    self.prompt_items[item_index].error = str(e)
                    self.failed_count += 1
                    self.log(f"❌ Failed: {e}")

                yield

            self.log("=" * 60)
            self.log(f"🎉 Generation Complete!")
            self.log(f"✅ Completed: {self.completed_count}")
            self.log(f"❌ Failed: {self.failed_count}")
            self.log("=" * 60)

            yield rx.toast.success(f"Generation complete! {self.completed_count} images generated")

        except Exception as e:
            self.log(f"❌ ERROR: {e}")
            yield rx.toast.error(f"Generation failed: {e}")

        finally:
            self.is_generating = False
            yield

    def set_guidance_scale(self, value: list[float]):
        """Set guidance scale"""
        if value:
            self.guidance_scale = value[0]

    def set_num_inference_steps(self, value: list[float]):
        """Set number of inference steps"""
        if value:
            self.num_inference_steps = int(value[0])

    def set_image_width(self, value: str):
        """Set image width"""
        self.image_width = value

    def set_image_height(self, value: str):
        """Set image height"""
        self.image_height = value

    def set_preset_ratio(self, ratio: str):
        """Set resolution based on aspect ratio preset"""
        if ratio == "1:1":
            self.image_width = "1024"
            self.image_height = "1024"
        elif ratio == "16:9":
            self.image_width = "1024"
            self.image_height = "576"
        elif ratio == "9:16":
            self.image_width = "576"
            self.image_height = "1024"
        elif ratio == "4:3":
            self.image_width = "1024"
            self.image_height = "768"
        elif ratio == "21:9":
            self.image_width = "1280"
            self.image_height = "549"

    def set_seed(self, value: list[float]):
        """Set seed"""
        if value:
            self.seed = int(value[0])

    def set_use_random_seed(self, value: bool):
        """Toggle random seed"""
        self.use_random_seed = value

    def download_image(self, item_id: str):
        """Download single generated image"""
        for item in self.prompt_items:
            if item.id == item_id and item.image_path:
                from pathlib import Path
                img_path = Path(item.image_path)
                if img_path.exists():
                    data = img_path.read_bytes()
                    return rx.download(data=data, filename=f"{item_id}.png")
        return rx.toast.error("Image not found")

    def download_all_zip(self):
        """Download all generated images as ZIP"""
        import zipfile
        import io

        completed_items = [item for item in self.prompt_items if item.status == "completed" and item.image_path]

        if not completed_items:
            return rx.toast.error("No completed images to download")

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in completed_items:
                if item.image_path is None:
                    continue
                img_path = Path(item.image_path)
                if img_path.exists():
                    zf.write(img_path, f"{item.id}.png")

        zip_data = zip_buffer.getvalue()
        return rx.download(data=zip_data, filename="generated_images.zip")
