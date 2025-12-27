"""Scenario Generation Page"""
import reflex as rx
import sys
from pathlib import Path

UI_DIR = Path(__file__).parent.parent
if str(UI_DIR) not in sys.path:
    sys.path.insert(0, str(UI_DIR))

from states.audio_state import ScenarioState
from components.layout import page_container, page_header
from components.file_selector import project_selector


def voice_card(speaker_name: str, lang: str, flag: str) -> rx.Component:
    """Voice card with corrected padding structure (Direct VStack styling)"""
    
    # Using rx.vstack directly as the container to ensure padding works correctly
    return rx.vstack(
        # Row 1: Speaker Badge (Top Left)
        rx.hstack(
            rx.badge(
                speaker_name,
                size="3",
                color_scheme="blue",
                variant="solid",
                radius="full",
            ),
            # width="100%" removed to prevent overflow with margin
            margin="20px 20px 0 20px",
        ),
        
        # Row 2: Gender Selection (Buttons Only)
        rx.hstack(
            rx.button(
                "♀️ Female",
                size="1",
                variant=rx.cond(
                    ScenarioState.selected_voices[lang][speaker_name]["gender"] == "female",
                    "solid", 
                    "soft"
                ),
                color_scheme=rx.cond(
                    ScenarioState.selected_voices[lang][speaker_name]["gender"] == "female",
                    "pink", 
                    "gray"
                ),
                on_click=lambda: ScenarioState.set_speaker_gender(lang, speaker_name, "female"),
                radius="full",
                cursor="pointer",
                margin="0 0 0 20px"
            ),
            rx.button(
                "♂️ Male", 
                size="1",
                variant=rx.cond(
                    ScenarioState.selected_voices[lang][speaker_name]["gender"] == "male",
                    "solid", 
                    "soft"
                ),
                color_scheme=rx.cond(
                    ScenarioState.selected_voices[lang][speaker_name]["gender"] == "male",
                    "blue", 
                    "gray"
                ),
                on_click=lambda: ScenarioState.set_speaker_gender(lang, speaker_name, "male"),
                radius="full",
                cursor="pointer",
            ),
            width="100%",
            align="center",
            justify="start",
            spacing="2",
        ),

        rx.divider(margin_top="5px"),

        # Row 3: Selection Area
        rx.hstack(
            # Select Box (Left)
            rx.select(
                ScenarioState.available_voices[lang][
                    ScenarioState.selected_voices[lang][speaker_name]["gender"]
                ],
                placeholder="Select voice...",
                value=ScenarioState.selected_voices[lang][speaker_name]["voice"],
                on_change=lambda val: ScenarioState.set_speaker_voice(lang, speaker_name, val),
                size="3",
                flex="1", 
                radius="large",
                variant="soft"
            ),

            # Player Info (Right)
            rx.cond(
                ScenarioState.selected_voices[lang][speaker_name]["voice"] != "",
                rx.box(
                    rx.audio(
                        src="/audios/" + lang + "/" + ScenarioState.selected_voices[lang][speaker_name]["gender"] + "/" + ScenarioState.selected_voices[lang][speaker_name]["voice"],
                        width="100%",
                        height="40px",
                        controls=True,
                    ),
                    flex="1",
                    width="100%",
                ),
                # Empty State
                rx.center(
                    rx.text("Select voice to preview", size="1", color="var(--gray-9)"),
                    flex="1",
                    width="100%",
                    height="40px",
                    background="var(--gray-4)",
                    border_radius="full",
                    opacity="0.3",
                ),
            ),
            
            align="center",
            spacing="4",
            margin="5px 20px 20px 20px"
        ),
        
        
        # Container Styles applied directly to VStack
        width="100%", # Changed to 100% to fill grid cell
        min_width="auto", # Removed fixed min_width to allow grid resizing
        align="stretch", # Ensure children fill width naturally
        spacing="4",
        padding="5", # Generous padding
        border_radius="16px",
        border="1px solid var(--gray-6)",
        background="var(--gray-3)",
        box_shadow="0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
        transition="all 0.2s ease-in-out",
        _hover={
            "border_color": "var(--accent-8)",
            "box_shadow": "0 10px 15px -3px rgba(0, 0, 0, 0.1)",
            "transform": "translateY(-2px)",
        }
    )


def language_speaker_config(lang: str, lang_display: str, flag: str) -> rx.Component:
    """Speaker configuration for a specific language"""
    return rx.vstack(
        # Header
        rx.hstack(
            rx.heading(f"{flag} {lang_display}", size="5"),
            rx.cond(
                ScenarioState.speakers.length() > 0,
                rx.badge(
                    f"{ScenarioState.speakers.length()} speakers",
                    color_scheme="green",
                    variant="soft",
                ),
                rx.fragment(),
            ),
            spacing="3",
            align="center",
            padding_top="20px",
        ),
        
        # Info callout
        rx.cond(
            ScenarioState.speakers.length() > 0,
            rx.callout(
                f"Detected {ScenarioState.speakers.length()} speaker(s) from SRT file",
                color_scheme="green",
                size="1",
            ),
            rx.callout(
                "No speakers detected. Please select a project first.",
                color_scheme="orange",
                size="1",
            ),
        ),
        
        # Speaker cards in 2-column grid
        rx.grid(
            rx.foreach(
                ScenarioState.speakers,
                lambda speaker_name: voice_card(speaker_name, lang, flag),
            ),
            columns="2",
            spacing="4",
            width="100%",
        ),
        
        spacing="4",
        width="100%",
    )


def page() -> rx.Component:
    """Scenario Tab"""
    return page_container([
        page_header("🎬 Scenario Generation", "Configure voice files for each speaker"),
        
        project_selector(
            projects=ScenarioState.available_projects,
            current_project=ScenarioState.selected_project,
            on_change_callback=ScenarioState.set_selected_project,
            on_reload_callback=ScenarioState.on_load,
        ),
        
        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger("🇯🇵 Japanese", value="ja"),
                rx.tabs.trigger("🇰🇷 Korean", value="ko"),
                rx.tabs.trigger("🇺🇸 English", value="en"),
            ),
            
            rx.tabs.content(
                language_speaker_config("ja", "Japanese", "🇯🇵"),
                value="ja",
                padding_top="4",
            ),
            
            rx.tabs.content(
                language_speaker_config("ko", "Korean", "🇰🇷"),
                value="ko",
                padding_top="4",
            ),
            
            rx.tabs.content(
                language_speaker_config("en", "English", "🇺🇸"),
                value="en",
                padding_top="4",
            ),
            
            default_value="ja",
            width="100%",
        ),
        
        rx.divider(margin_top="4", margin_bottom="4"),
        
        # Generate button
        rx.cond(
            ScenarioState.is_generating,
            rx.button(
                "⏳ Generating...",
                loading=True,
                size="4",
                disabled=True,
                width="100%",
            ),
            rx.button(
                "🎬 Generate Scenario",
                on_click=ScenarioState.generate_scenario,
                disabled=~ScenarioState.can_generate,
                size="4",
                color_scheme="orange",
                width="100%",
            ),
        ),
        
        rx.callout(
            "ℹ️ All speakers must have voices selected for Japanese, Korean, and English.",
            color_scheme="blue",
            margin_top="3",
        ),
        
    ], max_width="1400px")
