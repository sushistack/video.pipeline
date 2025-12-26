"""Pagination Controls Component"""
import reflex as rx


def pagination_controls(state_class) -> rx.Component:
    """
    Reusable pagination controls.
    
    Args:
        state_class: State class with pagination properties (current_page, total_pages, can_prev, can_next)
        
    Returns:
        Pagination component with prev/next buttons
    """
    return rx.cond(
        state_class.total_rows > 0,
        rx.hstack(
            rx.button(
                "⬅️ Previous",
                on_click=state_class.prev_page,
                disabled=~state_class.can_prev,
                variant="soft",
            ),
            rx.hstack(
                rx.text("Page", size="2"),
                rx.badge(state_class.current_page, size="2"),
                rx.text("/", size="2"),
                rx.badge(state_class.total_pages, size="2"),
                spacing="2",
            ),
            rx.button(
                "Next ➡️",
                on_click=state_class.next_page,
                disabled=~state_class.can_next,
                variant="soft",
            ),
            spacing="3",
            justify="between",
        ),
    )
