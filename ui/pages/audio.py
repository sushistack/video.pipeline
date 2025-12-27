"""Audio Generation Page - Simplified"""
import reflex as rx
import sys
from pathlib import Path

UI_DIR = Path(__file__).parent.parent
if str(UI_DIR) not in sys.path:
    sys.path.insert(0, str(UI_DIR))

from states.audio_state import AudioState
from components.layout import page_container, page_header
from components.log_viewer import log_viewer
from components.file_selector import project_selector


def page() -> rx.Component:
    """Audio Tab - TTS Generation"""
    return page_container([
        page_header("🎙️ Text-to-Speech Generation", "Generate audio tracks using GPT-SoVITS"),
        
        # Project Selection
        project_selector(
            projects=AudioState.available_projects,
            current_project=AudioState.selected_project,
            on_change_callback=AudioState.set_selected_project,
            on_reload_callback=AudioState.load_projects,
        ),
        
        # Configuration
        # Configuration
        rx.heading("⚙️ Configuration", size="5"),
        
        rx.grid(
            # Model Version & Validation
            rx.vstack(
                rx.text("Model Version", weight="bold"),
                rx.select(
                    AudioState.model_versions,
                    value=AudioState.selected_model,
                    on_change=AudioState.set_selected_model,
                    disabled=AudioState.is_generating,
                    width="250px",  # Fixed width
                ),
                # Validation Status
                rx.vstack(
                    rx.hstack(
                         rx.cond(AudioState.gpt_status["exists"], rx.icon("check", color="green", size=16), rx.icon("x", color="red", size=16)),
                         rx.text(AudioState.gpt_status["name"], size="1", color="gray"),
                         align="center",
                    ),
                    rx.hstack(
                         rx.cond(AudioState.sovits_status["exists"], rx.icon("check", color="green", size=16), rx.icon("x", color="red", size=16)),
                         rx.text(AudioState.sovits_status["name"], size="1", color="gray"),
                         align="center",
                    ),
                    spacing="1",
                    padding_top="2",
                ),
                align="start",
            ),
            
            # Speed Slider
            rx.vstack(
                rx.hstack(
                     rx.text("Speed:", weight="bold"),
                     rx.badge(f"{AudioState.speed_factor}x", color_scheme="blue"),
                ),
                rx.slider(
                    default_value=[1.1],
                    value=[AudioState.speed_factor],
                    min=0.5, 
                    max=2.0, 
                    step=0.1,
                    on_change=AudioState.set_speed_slider, # Use on_change for real-time update
                    width="100%",
                ),
                align="start",
                width="100%",
            ),
            
            columns="2",
            spacing="9", # Increased spacing
        ),
        
        # Language Selection (Toggle Buttons)
        rx.text("Target Languages", weight="bold", margin_top="1em"),
        rx.hstack(
            rx.button("🇺🇸 English", variant=rx.cond(AudioState.gen_en, "solid", "outline"), on_click=AudioState.set_gen_en( ~AudioState.gen_en )),
            rx.button("🇰🇷 Korean", variant=rx.cond(AudioState.gen_ko, "solid", "outline"), on_click=AudioState.set_gen_ko( ~AudioState.gen_ko )),
            rx.button("🇯🇵 Japanese", variant=rx.cond(AudioState.gen_ja, "solid", "outline"), on_click=AudioState.set_gen_ja( ~AudioState.gen_ja )),
            spacing="4",
        ),
        
        rx.divider(),
        
        # Generate Button
        # Generation Controls
        rx.hstack(
            # Progress Bar (Visible when generating)
            rx.cond(
                AudioState.is_generating,
                rx.vstack(
                    rx.progress(value=AudioState.progress, width="200px"),
                    rx.text(AudioState.progress_text, size="1", color="gray"),
                    align="center",
                    spacing="2",
                ),
            ),
            
            # Action Buttons
            rx.cond(
                AudioState.is_generating,
                rx.button(
                    "⏳ Generating...", 
                    loading=True, 
                    size="4", 
                    disabled=True,
                    color_scheme="purple",
                ),
                rx.button(
                    "🎙️ Generate Audio Tracks",
                    on_click=AudioState.start_generation,
                    disabled=~AudioState.can_generate,
                    size="4",
                    color_scheme="purple",
                ),
            ),
            spacing="4",
            align="center",
            width="100%",
            justify="end", # Align to right as requested (or left if preferred, but usually actions are right/center)
        ),
        
        # Logs
        log_viewer(AudioState.generation_logs),
        
    ], max_width="1200px")
