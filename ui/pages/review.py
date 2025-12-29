"""Review Page - Subtitle Editing"""
import reflex as rx
import sys
from pathlib import Path

UI_DIR = Path(__file__).parent.parent
if str(UI_DIR) not in sys.path:
    sys.path.insert(0, str(UI_DIR))

from states.review_state import ReviewState
from components.layout import page_container, page_header
from components.file_selector import project_selector
from components.subtitle_row import subtitle_row


def page() -> rx.Component:
    """Review Tab - Subtitle Editing Page"""
    return page_container([
        page_header(
            "📝 Story Review",
            "Edit and review multilingual subtitles"
        ),
        
        # Project Selection
        project_selector(
            projects=ReviewState.available_projects,
            current_project=ReviewState.current_project,
            on_change_callback=ReviewState.load_project,
            on_reload_callback=ReviewState.load_projects,
        ),
        
        # Language Toggles
        rx.hstack(
            rx.checkbox("Show Japanese", checked=ReviewState.show_ja, on_change=ReviewState.set_show_ja),
            rx.checkbox("Show English", checked=ReviewState.show_en, on_change=ReviewState.set_show_en),
            spacing="4",
        ),
        
        rx.divider(),
        
        # Subtitle Rows - ALL AT ONCE (No Pagination)
        rx.vstack(
            rx.foreach(
                ReviewState.subtitles,
                subtitle_row
            ),
            spacing="3",
            width="100%",
        ),
        
        # Save Button
        rx.button(
            "💾 Save Changes",
            on_click=ReviewState.save_changes,
            size="4",
            color_scheme="green",
        ),
        
        # Floating Speaker Legend
        rx.card(
            rx.vstack(
                rx.text("Speakers", size="1", weight="bold", color="gray"),
                rx.foreach(
                    ReviewState.speaker_legend_items,
                    lambda item: rx.cond(
                         item["name"] != "",
                         rx.hstack(
                            rx.box(
                                width="12px", 
                                height="12px", 
                                border_radius="full", 
                                bg=item["color"]
                            ),
                            rx.text(item["name"], size="1", weight="medium"),
                            align="center",
                            spacing="2"
                        ),
                        rx.fragment()
                    )
                ),
                spacing="2",
                align="start"
            ),
            position="fixed",
            top="120px",  # Below header
            right="20px",
            z_index="100",
            size="1",
            max_width="200px",
            max_height="80vh",
            overflow_y="auto",
            variant="surface",
        ),
        
    ], max_width="1400px")
