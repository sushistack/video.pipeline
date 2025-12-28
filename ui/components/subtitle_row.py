"""Subtitle Row Component"""
import reflex as rx
import sys
from pathlib import Path

UI_DIR = Path(__file__).parent.parent
if str(UI_DIR) not in sys.path:
    sys.path.insert(0, str(UI_DIR))

from states.review_state import ReviewState


def subtitle_row(row: dict) -> rx.Component:
    """
    Display a single subtitle row with editable fields.
    Shows collapsed "Deleted" view when marked as deleted.
    
    Args:
        row: Subtitle data dict with id, start, end, speaker, text_ja, text_ko, text_en
        
    Returns:
        Card component - full or collapsed based on deleted state
    """
    row_id = row["id"]
    is_deleted = ReviewState.deleted_rows.contains(row_id)
    
    return rx.cond(
        is_deleted,
        # DELETED VIEW - Collapsed 50px with Restore + Permanent Delete
        rx.card(
            rx.hstack(
                rx.text(f"🔥 Row #{row['id']} Deleted", color="red", weight="bold"),
                rx.hstack(
                    rx.button(
                        "↩️ Restore",
                        size="2",
                        variant="soft",
                        color_scheme="green",
                        on_click=ReviewState.restore_row(row_id),
                    ),
                    rx.button(
                        "💀 Delete Forever",
                        size="2",
                        variant="soft",
                        color_scheme="red",
                        on_click=ReviewState.permanent_delete(row_id),
                    ),
                    spacing="2",
                ),
                justify="between",
                width="100%",
                align="center",
            ),
            size="1",
            width="100%",
            height="50px",
            background_color="rgba(255, 0, 0, 0.1)",
        ),
        # NORMAL VIEW - Full height
        rx.card(
            rx.vstack(
                # Header: Row Info + Action Buttons
                rx.hstack(
                    # Row Info (Left)
                    rx.hstack(
                        rx.badge(row["id"], color_scheme="gray", size="1"),
                        rx.text(f"{row['start']} → {row['end']}", size="2", color="gray"),
                        spacing="2",
                    ),
                    
                    # Action Buttons (Right)
                    rx.hstack(
                        rx.button(
                            "➕",
                            size="1",
                            variant="soft",
                            color_scheme="blue",
                            on_click=ReviewState.insert_row_after(row_id),
                        ),
                        rx.button(
                            "🔥",
                            size="1",
                            variant="soft",
                            color_scheme="red",
                            on_click=ReviewState.mark_as_deleted(row_id),
                        ),
                        spacing="2",
                    ),
                    
                    justify="between",
                    width="100%",
                ),
                
                # Speaker Input
                rx.input(
                    value=row["speaker"],
                    placeholder="Speaker...",
                    on_change=lambda val: ReviewState.update_row(row_id, "speaker", val),
                    size="2",
                    width="100%",
                ),
                
                # Language Text Areas - Conditional display based on checkboxes
                rx.grid(
                    # Japanese (conditional)
                    rx.cond(
                        ReviewState.show_ja,
                        rx.vstack(
                            rx.text("🇯🇵 Japanese", size="2", weight="bold"),
                                rx.text_area(
                                    value=row["text_ja"],
                                    on_change=lambda val: ReviewState.update_row(row_id, "text_ja", val),
                                    width="100%",
                                    min_height="80px",
                                    size="3",
                                ),
                            spacing="1",
                            align="start",
                            width="100%",
                        ),
                        rx.box(),  # Empty placeholder when hidden
                    ),
                    
                    # Korean (always shown)
                    rx.vstack(
                        rx.text("🇰🇷 Korean", size="2", weight="bold"),
                        rx.text_area(
                            value=row["text_ko"],
                            on_change=lambda val: ReviewState.update_row(row_id, "text_ko", val),
                            width="100%",
                            min_height="80px",
                            size="3",
                        ),
                        spacing="1",
                        align="start",
                        width="100%",
                    ),
                    
                    # English (conditional)
                    rx.cond(
                        ReviewState.show_en,
                        rx.vstack(
                            rx.text("🇺🇸 English", size="2", weight="bold"),
                            rx.text_area(
                                value=row["text_en"],
                                on_change=lambda val: ReviewState.update_row(row_id, "text_en", val),
                                width="100%",
                                min_height="80px",
                                size="3",
                            ),
                            spacing="1",
                            align="start",
                            width="100%",
                        ),
                        rx.box(),  # Empty placeholder when hidden
                    ),
                    
                    columns="3",
                    spacing="4",
                    width="100%",
                ),
                
                spacing="3",
                width="100%",
            ),
            size="2",
            width="100%",
        ),
    )
