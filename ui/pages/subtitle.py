"""Subtitle Preview Page"""
import reflex as rx
import sys
from pathlib import Path

UI_DIR = Path(__file__).parent.parent
if str(UI_DIR) not in sys.path:
    sys.path.insert(0, str(UI_DIR))

from states.audio_state import SubtitleState, SubtitleLangData
from components.layout import page_container, page_header
from components.file_selector import project_selector


def render_lang_card(data: SubtitleLangData):
    """Render a card for a specific language using SubtitleLangData"""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.text(data.emoji, font_size="1.5em"),
                rx.text(f"Mapping for {data.lang}", font_weight="bold"),
                rx.spacer(),
                rx.badge(
                    f"Audio: {data.audio_count} / SRT Blocks: {data.srt_count}",
                    color_scheme=rx.cond(data.valid, "green", "red"),
                    variant="soft"
                ),
                width="100%",
                align="center",
            ),
            rx.divider(),
            rx.hstack(
                # Audio Files Column
                rx.vstack(
                    rx.text(f"Audio Files ({data.audio_count})", font_size="sm", color="gray"),
                    rx.scroll_area(
                        rx.vstack(
                            rx.foreach(
                                data.audios,
                                lambda f: rx.text(f, font_size="xs")
                            ),
                            align="start",
                        ),
                        type="always",
                        scrollbars="vertical",
                        style={"height": "150px"}
                    ),
                    width="40%",
                    align="start"
                ),
                # SRT Content Column
                rx.vstack(
                    rx.text(f"SRT Content ({data.srt_count} blocks)", font_size="sm", color="gray"),
                    rx.text_area(
                        value=data.srt_content,
                        is_read_only=True,
                        height="150px",
                        width="100%",
                        font_family="monospace",
                        font_size="xs"
                    ),
                    width="60%",
                    align="start"
                ),
                width="100%",
                spacing="4"
            ),
            width="100%"
        ),
        width="100%",
    )


def page() -> rx.Component:
    """Subtitle Tab - Preview and Generation"""
    return page_container([
        page_header("📝 Subtitle Generation", "Generate synced subtitles JSON"),
        
        # Project Selection
        project_selector(
            projects=SubtitleState.available_projects,
            current_project=SubtitleState.selected_project,
            on_change_callback=SubtitleState.set_selected_project,
            on_reload_callback=SubtitleState.on_load,
        ),
        
        rx.divider(),
        
        # Language Cards (Iterate over object list)
        rx.vstack(
            rx.foreach(
                SubtitleState.lang_list,
                render_lang_card
            ),
            width="100%",
            spacing="4"
        ),
        
        rx.divider(),
        
        # Generate Section with Confirmation
        rx.box(
            rx.alert_dialog.root(
                rx.alert_dialog.trigger(
                    rx.button(
                        "🎬 Generate Subtitles",
                        on_click=SubtitleState.open_confirm_dialog,
                        size="4",
                        width="100%",
                        variant="solid",
                        color_scheme="blue",
                    ),
                ),
                rx.alert_dialog.content(
                    rx.alert_dialog.title("Confirm Generation"),
                    rx.alert_dialog.description(
                        "The following languages are ready and will be processed:",
                        size="2",
                    ),
                    
                    # List All Languages with Status
                    rx.vstack(
                        rx.foreach(
                            SubtitleState.lang_list,
                            lambda data: rx.hstack(
                                rx.text(data.emoji, font_size="1.5em"),
                                rx.text(data.lang, weight="bold", color="var(--gray-12)"),
                                rx.spacer(),
                                rx.cond(
                                    data.valid,
                                    rx.badge("Ready", color_scheme="green", variant="solid"),
                                    rx.badge("Not Ready", color_scheme="gray", variant="soft"),
                                ),
                                width="100%",
                                align_items="center",
                                padding="3",
                                border_radius="md",
                                background="var(--gray-3)",
                                opacity=rx.cond(data.valid, "1", "0.5"), # Dim invalid items
                            )
                        ),
                        width="100%",
                        spacing="3", # Increased spacing
                        margin_y="4",
                        max_height="300px", # Increased max height
                        overflow_y="auto",
                    ),
                    
                    rx.text("Are you sure you want to proceed?", size="2", color="gray"),

                    rx.flex(
                        rx.alert_dialog.cancel(
                            rx.button("Cancel", variant="soft", color_scheme="gray", on_click=SubtitleState.close_confirm_dialog),
                        ),
                        rx.alert_dialog.action(
                            rx.button(
                                "Confirm", 
                                on_click=[SubtitleState.close_confirm_dialog, SubtitleState.generate_subtitles],
                                variant="solid", 
                                color_scheme="blue"
                            ),
                        ),
                        spacing="3",
                        margin_top="4",
                        justify="end",
                    ),
                ),
                open=SubtitleState.confirm_dialog_open,
                on_open_change=SubtitleState.set_confirm_dialog_open,
            ),
            width="100%",
            padding_y="4"
        )
        
    ], max_width="1000px")
