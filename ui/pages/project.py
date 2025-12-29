
import reflex as rx
from components.layout import page_container, page_header
from states.project_state import ProjectState
from components.file_selector import project_selector

def page() -> rx.Component:
    return page_container(
        [
            page_header("Capcut Project Generation", "Generate CapCut draft projects from processed assets."),
            
            # Project Selection Section
            rx.vstack(
                rx.text("Select Project", weight="bold"),
                project_selector(
                    projects=ProjectState.available_projects,
                    current_project=ProjectState.selected_project,
                    on_change_callback=ProjectState.set_selected_project,
                    on_reload_callback=ProjectState.load_projects,
                ),
                
                # Validation UI (Stats)
                rx.cond(
                    ProjectState.selected_project,
                    rx.hstack(
                        rx.card(
                            rx.vstack(
                                rx.text("Audio Files", size="1", weight="medium"),
                                rx.text(ProjectState.audio_count, size="5", weight="bold"),
                            ),
                            size="1",
                            width="100%"
                        ),
                        rx.card(
                            rx.vstack(
                                rx.text("Subtitles", size="1", weight="medium"),
                                rx.text(ProjectState.subtitle_count, size="5", weight="bold"),
                            ),
                            size="1",
                            width="100%"
                        ),
                        rx.card(
                            rx.vstack(
                                rx.text("Video Files", size="1", weight="medium"),
                                rx.text(ProjectState.video_count, size="5", weight="bold"),
                            ),
                            size="1",
                            width="100%"
                        ),
                        width="100%",
                        spacing="4",
                    ),
                ),

                rx.divider(),
                
                # Generate Button
                rx.button(
                    rx.hstack(
                        rx.icon("clapperboard"),
                        rx.text("Generate Project Layout"),
                    ),
                    on_click=ProjectState.generate_project,
                    disabled=~ProjectState.is_valid,
                    loading=ProjectState.is_generating,
                    size="4",
                    width="100%",
                    color_scheme="blue",
                    margin_top="6",
                ),
                
                spacing="4",
                width="100%",
                max_width="600px",
            ),
            
            # Bottom Validation Status Bar (matches logic)
            rx.cond(
                ProjectState.selected_project,
                rx.box(
                     rx.cond(
                         ProjectState.is_valid,
                         rx.callout(
                            "Audio Matches Subtitles: Project assets are synced and ready for generation.",
                            icon="check",
                            color_scheme="green",
                            variant="surface",
                            width="100%",
                         ),
                         rx.callout(
                            f"Mismatch Detected: {ProjectState.validation_message}",
                            icon="info",
                            color_scheme="red",
                            variant="surface",
                            width="100%",
                         ),
                    ),
                    width="100%",
                    max_width="600px",
                    padding_top="4",
                )
            ),
        ]
    )
