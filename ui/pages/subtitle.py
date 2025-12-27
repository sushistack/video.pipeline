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
        
        # Generate Button
        rx.box(
            rx.button(
                "🎬 Generate Subtitles",
                on_click=SubtitleState.generate_subtitles,
                loading=SubtitleState.is_generating,
                size="4",
                width="100%",
                variant="solid",
                color_scheme="blue", # User requested specific style? 'classic' blue/primary
            ),
            width="100%",
            padding_y="4"
        )
        
    ], max_width="1000px")
