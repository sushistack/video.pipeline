"""File/Project Selector Component"""
import reflex as rx


def project_selector(
    projects: list[str],
    current_project: str,
    on_change_callback,
    on_reload_callback,
    placeholder: str = "Select Project"
) -> rx.Component:
    """
    Reusable project selector with reload button.
    
    Args:
        projects: List of project names
        current_project: Currently selected project
        on_change_callback: Callback when selection changes
        on_reload_callback: Callback when reload button clicked
        placeholder: Placeholder text
        
    Returns:
        Selector component with reload button
    """
    return rx.hstack(
        rx.select(
            projects,
            placeholder=placeholder,
            on_change=on_change_callback,
            size="3",
            value=current_project,
        ),
        rx.button(
            "🔄 Reload",
            on_click=on_reload_callback,
            variant="soft",
        ),
        spacing="3",
    )
