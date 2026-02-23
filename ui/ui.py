"""Video Pipeline - Multi-Page Application"""
import reflex as rx
from .pages import index, audio, scenario, extract, review, image_prompter, image_generator, scene_detector


# Create the app
app = rx.App()

# Add all pages with on_load handlers where applicable to ensure state initialization
app.add_page(index.page, route="/", title="Video Pipeline | Home")
app.add_page(extract.page, route="/extract", title="Video Pipeline | Extract", on_load=extract.ExtractState.on_load)
app.add_page(review.page, route="/review", title="Video Pipeline | Review", on_load=review.ReviewState.on_load)
app.add_page(scenario.page, route="/scenario", title="Video Pipeline | Scenario", on_load=scenario.ScenarioState.on_load)
app.add_page(audio.page, route="/audio", title="Video Pipeline | Audio", on_load=audio.AudioState.on_load)
app.add_page(image_prompter.page, route="/image-prompter", title="Video Pipeline | Image Prompter", on_load=image_prompter.ImagePrompterState.on_load)

# Mount workspace directory to serve generated audio files
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from .pages.image_generator import ImageGeneratorState
workspace_path = Path(__file__).parent.parent / "workspace"
workspace_path.mkdir(exist_ok=True) # Ensure it exists
app._api.mount("/workspace", StaticFiles(directory=str(workspace_path)), name="workspace")
app.add_page(image_generator.page, route="/image-generator", title="Video Pipeline | Image Generator", on_load=ImageGeneratorState.on_load)
app.add_page(scene_detector.page, route="/scene-detect", title="Video Pipeline | Scene Detector", on_load=scene_detector.SceneDetectorState.on_load)
