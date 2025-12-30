"""Extract Page - STT Caption Extraction"""
import reflex as rx
import sys
from pathlib import Path

UI_DIR = Path(__file__).parent.parent
if str(UI_DIR) not in sys.path:
    sys.path.insert(0, str(UI_DIR))

from states.extract_state import ExtractState
from components.layout import page_container, page_header
from components.log_viewer import log_viewer


from components.file_selector import project_selector


def page() -> rx.Component:
    """Extract Tab - Caption Extraction Page"""
    return page_container([
        page_header(
            "🎤 Caption Extraction (STT)",
            "Select a video/audio file to generate multilingual subtitles"
        ),
        
        # Status Indicator
        rx.cond(
            ExtractState.is_extracting,
            rx.callout(
                "⏳ Extraction in progress... Please wait.",
                color_scheme="blue",
            ),
        ),
        
        # Row 1: File Selection (Full Width)
        rx.vstack(
            rx.text("Video/Audio File", weight="bold"),
            project_selector(
                projects=ExtractState.available_files,
                current_project=ExtractState.selected_file,
                on_change_callback=ExtractState.set_selected_file,
                on_reload_callback=ExtractState.load_files,
                placeholder="Select a file...",
                disabled=ExtractState.is_extracting,
            ),
             rx.text(
                f"Found {ExtractState.available_files.length()} files",
                size="1",
                color_scheme="gray"
            ),
            width="100%",
            align_items="start",
            max_width="600px",
        ),
        
        # Row 2: Model & Speaker Count (Two Columns)
        rx.grid(
            # Gemini Model
            rx.vstack(
                rx.text("Gemini Model", weight="bold"),
                rx.select(
                    ExtractState.model_options,
                    value=ExtractState.selected_model,
                    on_change=ExtractState.set_selected_model,
                    size="3",
                    width="100%",
                    disabled=ExtractState.is_extracting,
                ),
                width="100%",
                align_items="start",
            ),
            
            # Speaker Count
            rx.vstack(
                rx.text("Speakers", weight="bold"),
                rx.select(
                    ExtractState.speaker_options,
                    value=ExtractState.selected_speakers,
                    on_change=ExtractState.set_selected_speakers,
                    size="3",
                    width="100%",
                    disabled=ExtractState.is_extracting,
                ),
                width="100%",
                max_width="150px",
                align_items="start",
            ),
            
            columns="2",
            spacing="4",
            width="100%",
            max_width="600px",
            margin_top="15px"
        ),

        # Row 3: Target Languages
        rx.vstack(
            rx.text("Target Languages", weight="bold"),
            rx.hstack(
                rx.badge("🇯🇵 Japanese", color_scheme="blue", variant="solid", size="3"),
                rx.badge("🇺🇸 English", color_scheme="green", variant="solid", size="3"),
                rx.badge("🇰🇷 Korean", color_scheme="purple", variant="solid", size="3"),
                spacing="3",
            ),
            width="100%",
            align_items="start",
            max_width="600px",
            margin_top="15px",
            margin_bottom="10px",
        ),
        
        rx.divider(),
        
        # Action Buttons
        rx.hstack(
            rx.cond(
                ExtractState.is_extracting,
                # Stop button when running
                rx.button(
                    "🛑 Stop Extraction",
                    on_click=ExtractState.stop_extraction,
                    size="4",
                    color_scheme="red",
                    variant="soft",
                ),
                # Start button when idle
                rx.button(
                    "🚀 Start Caption Extraction",
                    on_click=ExtractState.start_extraction,
                    disabled=~ExtractState.can_extract,
                    size="4",
                    color_scheme="blue",
                ),
            ),
            spacing="3",
        ),
        
        # Log Viewer (Console Mirror) - Full Width
        rx.vstack(
            log_viewer(ExtractState.extraction_logs),
            width="100%",
            spacing="3",
        ),
        
        # Info
        rx.callout(
            "ℹ️ Extraction may take several minutes. Logs are mirrored from console output.",
            color_scheme="gray",
        ),
        
    ], max_width="1200px")
