"""File/Project Selector Component"""
import reflex as rx


def project_selector(
    projects: list[str],
    current_project: str,
    on_change_callback,
    on_reload_callback,
    placeholder: str = "Select Project",
    disabled: bool = False,
) -> rx.Component:
    """
    Reusable project selector with reload button.
    
    Args:
        projects: List of project names
        current_project: Currently selected project
        on_change_callback: Callback when selection changes
        on_reload_callback: Callback when reload button clicked
        placeholder: Placeholder text
        disabled: Whether to disable inputs
        
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
            disabled=disabled,
            width="100%", # Ensure full width in flex
        ),
        rx.button(
            "🔄 Reload",
            on_click=on_reload_callback,
            variant="soft",
            disabled=disabled,
        ),

        spacing="3",
    )
