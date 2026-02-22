"""Home page - Landing page with overview"""
import reflex as rx
from ..components.layout import page_container, page_header


def page() -> rx.Component:
    """Dashboard - Index Page"""
    return page_container([
        page_header("🎞️ Video Pipeline UI"),

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
                "Qwen3-TTS generation",
                "/audio",
                "purple"
            ),
            _feature_card(
                "🎨 Prompter",
                "AI image prompt generation",
                "/image-prompter",
                "pink"
            ),
            _feature_card(
                "🖼️ Image",
                "Janus-Pro-7B image generation",
                "/image-generator",
                "violet"
            ),
            _feature_card(
                "🎬 Scene",
                "Scene detection",
                "/scene-detect",
                "teal"
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