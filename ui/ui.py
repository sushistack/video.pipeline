"""Video Pipeline - Multi-Page Application"""
import reflex as rx
from .pages import index, audio, scenario, subtitle, extract, review, project


# Create the app
app = rx.App()

# Add all pages with on_load handlers where applicable to ensure state initialization
app.add_page(index.page, route="/", title="Video Pipeline | Home")
app.add_page(extract.page, route="/extract", title="Video Pipeline | Extract", on_load=extract.ExtractState.on_load)
app.add_page(review.page, route="/review", title="Video Pipeline | Review", on_load=review.ReviewState.on_load)
app.add_page(scenario.page, route="/scenario", title="Video Pipeline | Scenario", on_load=scenario.ScenarioState.on_load)
app.add_page(audio.page, route="/audio", title="Video Pipeline | Audio", on_load=audio.AudioState.on_load)
app.add_page(subtitle.page, route="/subtitle", title="Video Pipeline | Subtitle", on_load=subtitle.SubtitleState.on_load)
app.add_page(project.page, route="/project", title="Video Pipeline | Project", on_load=project.ProjectState.on_load)
