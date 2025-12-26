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
        
        # File Selection + Parameters
        rx.grid(
            # File Select
            rx.vstack(
                rx.text("Video/Audio File", weight="bold", size="3"),
                rx.cond(
                    ExtractState.available_files.length() > 0,
                    rx.select(
                        ExtractState.available_files,
                        placeholder="Select a file...",
                        value=ExtractState.selected_file,
                        on_change=ExtractState.set_selected_file,
                        size="3",
                        disabled=ExtractState.is_extracting,  # Disable during extraction
                    ),
                    rx.text("No files found in materials/videos/", color="red", size="2"),
                ),
                rx.button(
                    "🔄 Refresh Files",
                    on_click=ExtractState.load_files,
                    variant="soft",
                    size="2",
                    disabled=ExtractState.is_extracting,  # Disable during extraction
                ),
                rx.text(
                    f"Found {ExtractState.available_files.length()} files",
                    size="1",
                    color_scheme="gray"
                ),
                align="start",
            ),
            
            # Model Select
            rx.vstack(
                rx.text("Gemini Model", weight="bold", size="3"),
                rx.select(
                    ExtractState.model_options,
                    value=ExtractState.selected_model,
                    on_change=ExtractState.set_selected_model,
                    size="3",
                    disabled=ExtractState.is_extracting,  # Disable during extraction
                ),
                align="start",
            ),
            
            # Speaker Count
            rx.vstack(
                rx.text("Speaker Count", weight="bold", size="3"),
                rx.select(
                    ExtractState.speaker_options,
                    value=ExtractState.selected_speakers,
                    on_change=ExtractState.set_selected_speakers,
                    size="3",
                    disabled=ExtractState.is_extracting,  # Disable during extraction
                ),
                align="start",
            ),
            
            columns="3",
            spacing="4",
        ),
        
        # Target Languages (Display Only)
        rx.hstack(
            rx.text("Target Languages:", weight="bold"),
            rx.badge("🇯🇵 Japanese", color_scheme="blue"),
            rx.badge("🇺🇸 English", color_scheme="green"),
            rx.badge("🇰🇷 Korean", color_scheme="purple"),
            spacing="3",
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
            rx.heading("📜 Console Logs", size="5"),
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
