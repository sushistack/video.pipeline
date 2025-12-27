"""Home page - Landing page with overview"""
import reflex as rx
from ..components.layout import page_container, page_header


def page() -> rx.Component:
    """Dashboard - Index Page"""
    return page_container([
        page_header("🎞️ Video Pipeline UI", "Reflex-based interface with zero-lag editing"),
        
        rx.text("Select a tab to get started:", size="4", weight="bold"),
        
        rx.grid(
            _feature_card(
                "📺 Extract",
                "STT subtitle extraction",
                "/extract",
                "blue"
            ),
            _feature_card(
                "📝 Review",
                "Edit multilingual subtitles",
                "/review",
                "green"
            ),
            _feature_card(
                "🎬 Scenario",
                "XML scenario generation",
                "/scenario",
                "orange"
            ),
            _feature_card(
                "🎙️ Audio",
                "GPT-SoVITS TTS generation",
                "/audio",
                "purple"
            ),
            _feature_card(
                "📝 Subtitle",
                "Subtitle preview",
                "/subtitle",
                "cyan"
            ),
            _feature_card(
                "🎥 Project",
                "CapCut project generation",
                "/project",
                "indigo"
            ),
            columns="3",
            spacing="4",
        ),
    ], max_width="1200px")


def _feature_card(title: str, description: str, href: str, color: str) -> rx.Component:
    """Helper: Feature card"""
    return rx.link(
        rx.card(
            rx.vstack(
                rx.heading(title, size="6"),
                rx.text(description, size="2", color_scheme="gray"),
                spacing="2",
            ),
            size="3",
            variant="surface",
        ),
        href=href,
    )