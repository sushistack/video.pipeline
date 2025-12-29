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
        rx.grid(
            # Left Column: Configuration & Controls
            rx.vstack(
                rx.heading("⚙️ Configuration", size="5"),
                
                # Model Version & Validation
                rx.vstack(
                    rx.text("Model Version", weight="bold"),
                    rx.select(
                        AudioState.model_versions,
                        value=AudioState.selected_model,
                        on_change=AudioState.set_selected_model,
                        disabled=AudioState.is_generating,
                        width="250px",
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
                        on_change=AudioState.set_speed_slider,
                        width="100%",
                        max_width="280px", 
                    ),
                    align="start",
                    width="100%",
                ),
                
                # Language Selection (Toggle Buttons)
                rx.vstack(
                    rx.text("Target Languages", weight="bold"),
                    rx.hstack(
                        rx.button("🇯🇵 Japanese", variant=rx.cond(AudioState.gen_ja, "solid", "outline"), on_click=AudioState.set_gen_ja( ~AudioState.gen_ja )),
                        rx.button("🇺🇸 English", variant=rx.cond(AudioState.gen_en, "solid", "outline"), on_click=AudioState.set_gen_en( ~AudioState.gen_en )),
                        rx.button("🇰🇷 Korean", variant=rx.cond(AudioState.gen_ko, "solid", "outline"), on_click=AudioState.set_gen_ko( ~AudioState.gen_ko )),
                        spacing="4",
                    ),
                    spacing="4",
                    align="start",
                ),
                

                width="100%",
                align_items="start",
                spacing="8",
            ),
            
            # Right Column: Generated Audio Files
            rx.vstack(
            rx.hstack(
                rx.heading("📂 Generated Artifacts", size="5"),
                rx.icon_button(
                    rx.icon("rotate-cw"),
                    size="2",
                    variant="ghost",
                    on_click=AudioState.load_generated_audios,
                    tooltip="Refresh List",
                ),
                justify="between",
                align="center",
                width="100%",
                margin_bottom="2",
            ),
                rx.tabs.root(
                    rx.tabs.list(
                        rx.tabs.trigger("🇯🇵 Japanese", value="ja"),
                        rx.tabs.trigger("🇺🇸 English", value="en"),
                        rx.tabs.trigger("🇰🇷 Korean", value="ko"),
                    ),
                    rx.tabs.content(
                        rx.scroll_area(
                            rx.vstack(
                                rx.cond(
                                    AudioState.generated_audios["ja"],
                                    rx.foreach(
                                        AudioState.generated_audios["ja"],
                                        lambda file: rx.card(
                                            rx.vstack(
                                                rx.hstack(
                                                    rx.text(file["name"], size="1", weight="bold"),
                                                    rx.cond(
                                                        file["confirm_delete"],
                                                        rx.hstack(
                                                            rx.icon_button(rx.icon("check"), on_click=AudioState.delete_audio(file["name"], "ja"), color_scheme="red", variant="soft", size="1"),
                                                            rx.icon_button(rx.icon("undo-2"), on_click=AudioState.toggle_delete_confirm(file["name"], "ja"), variant="soft", size="1"),
                                                            spacing="1",
                                                        ),
                                                        rx.icon_button(rx.icon("trash-2"), on_click=AudioState.toggle_delete_confirm(file["name"], "ja"), color_scheme="red", variant="ghost", size="1"),
                                                    ),
                                                    align="center",
                                                    width="100%",
                                                    justify="between",
                                                ),
                                                rx.audio(src=file["url"], controls=True, width="100%"),
                                                spacing="2",
                                            ),
                                            size="1"
                                        )
                                    ),
                                    rx.text("No audio files generated yet.", color="gray", font_style="italic")
                                ),
                                spacing="2",
                            ),
                            type="always",
                            scrollbars="vertical",
                            style={
                                "height": "400px", 
                                "padding": "20px", 
                                "backgroundColor": "var(--gray-2)", 
                                "borderRadius": "12px", 
                                "border": "1px solid var(--gray-6)"
                            }
                        ),
                        value="ja",
                    ),
                    rx.tabs.content(
                        rx.scroll_area(
                            rx.vstack(
                                rx.cond(
                                    AudioState.generated_audios["en"],
                                    rx.foreach(
                                        AudioState.generated_audios["en"],
                                        lambda file: rx.card(
                                            rx.vstack(
                                                rx.hstack(
                                                    rx.text(file["name"], size="1", weight="bold"),
                                                    rx.cond(
                                                        file["confirm_delete"],
                                                        rx.hstack(
                                                            rx.icon_button(rx.icon("check"), on_click=AudioState.delete_audio(file["name"], "en"), color_scheme="red", variant="soft", size="1"),
                                                            rx.icon_button(rx.icon("undo-2"), on_click=AudioState.toggle_delete_confirm(file["name"], "en"), variant="soft", size="1"),
                                                            spacing="1",
                                                        ),
                                                        rx.icon_button(rx.icon("trash-2"), on_click=AudioState.toggle_delete_confirm(file["name"], "en"), color_scheme="red", variant="ghost", size="1"),
                                                    ),
                                                    align="center",
                                                    width="100%",
                                                    justify="between",
                                                ),
                                                rx.audio(src=file["url"], controls=True, width="100%"),
                                                spacing="2",
                                            ),
                                            size="1"
                                        )
                                    ),
                                    rx.text("No audio files generated yet.", color="gray", font_style="italic")
                                ),
                                spacing="2",
                            ),
                            type="always",
                            scrollbars="vertical",
                            style={
                                "height": "400px", 
                                "padding": "20px", 
                                "backgroundColor": "var(--gray-2)", 
                                "borderRadius": "12px", 
                                "border": "1px solid var(--gray-6)"
                            }
                        ),
                        value="en",
                    ),
                    rx.tabs.content(
                         rx.scroll_area(
                            rx.vstack(
                                rx.cond(
                                    AudioState.generated_audios["ko"],
                                    rx.foreach(
                                        AudioState.generated_audios["ko"],
                                        lambda file: rx.card(
                                            rx.vstack(
                                                rx.hstack(
                                                    rx.text(file["name"], size="1", weight="bold"),
                                                    rx.cond(
                                                        file["confirm_delete"],
                                                        rx.hstack(
                                                            rx.icon_button(rx.icon("check"), on_click=AudioState.delete_audio(file["name"], "ko"), color_scheme="red", variant="soft", size="1"),
                                                            rx.icon_button(rx.icon("undo-2"), on_click=AudioState.toggle_delete_confirm(file["name"], "ko"), variant="soft", size="1"),
                                                            spacing="1",
                                                        ),
                                                        rx.icon_button(rx.icon("trash-2"), on_click=AudioState.toggle_delete_confirm(file["name"], "ko"), color_scheme="red", variant="ghost", size="1"),
                                                    ),
                                                    align="center",
                                                    width="100%",
                                                    justify="between",
                                                ),
                                                rx.audio(src=file["url"], controls=True, width="100%"),
                                                spacing="2",
                                            ),
                                            size="1"
                                        )
                                    ),
                                    rx.text("No audio files generated yet.", color="gray", font_style="italic")
                                ),
                                spacing="2",
                            ),
                            type="always",
                            scrollbars="vertical",
                            style={
                                "height": "400px", 
                                "padding": "20px", 
                                "backgroundColor": "var(--gray-2)", 
                                "borderRadius": "12px", 
                                "border": "1px solid var(--gray-6)"
                            }
                        ),
                        value="ko",
                    ),
                    default_value="ja",
                    width="100%",
                ),
                width="100%",
                align_items="start",
                padding_left="2em",
                border_left="1px solid #333",
            ),
            
            columns="2",
            spacing="5",
            width="100%",
        ),

        # Generation Controls (Moved to bottom)
        rx.hstack(
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
            spacing="4",
            align="center",
            width="100%",
            justify="start", 
            margin_y="4",
        ),
        
        # Logs
        log_viewer(AudioState.generation_logs),
        
    ], max_width="1200px")
