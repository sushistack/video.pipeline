"""Main Reflex App - Clean Entry Point"""
import reflex as rx
import sys
from pathlib import Path

# Ensure ui_reflex is in path
UI_DIR = Path(__file__).parent.parent
if str(UI_DIR) not in sys.path:
    sys.path.insert(0, str(UI_DIR))

from pages import index, review, extract, audio, scenario, subtitle, project
from states.review_state import ReviewState
from states.extract_state import ExtractState
from states.audio_state import AudioState, ScenarioState, SubtitleState
from states.project_state import ProjectState


# Create app
app = rx.App()

# Register all pages
app.add_page(index.page, route="/")
app.add_page(review.page, route="/review", on_load=ReviewState.on_load)
app.add_page(extract.page, route="/extract", on_load=ExtractState.on_load)
app.add_page(audio.page, route="/audio", on_load=AudioState.on_load)
app.add_page(scenario.page, route="/scenario", on_load=ScenarioState.on_load)
app.add_page(subtitle.page, route="/subtitle", on_load=SubtitleState.on_load)
app.add_page(project.project, route="/project", on_load=ProjectState.on_load)
