
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
                
                # Validation UI
                rx.cond(
                    ProjectState.selected_project,
                    rx.vstack(
                        # Stats Row
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
                                    rx.cond(
                                        ProjectState.is_valid,
                                        rx.text("Matches Audio", size="1", color="green"),
                                        rx.text("Mismatch", size="1", color="red"),
                                    ),
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
                        
                        # File Lists
                        rx.grid(
                            # Audio List
                            rx.vstack(
                                rx.text("Audio Files", weight="bold", size="2"),
                                rx.vstack(
                                    rx.foreach(
                                        ProjectState.audio_files,
                                        lambda f: rx.text(f, size="1", color="gray")
                                    ),
                                    height="150px",
                                    overflow_y="auto",
                                    border="1px solid #333",
                                    padding="2",
                                    width="100%",
                                    bg="rgba(255,255,255,0.02)"
                                ),
                                width="100%",
                            ),
                            # Video List
                            rx.vstack(
                                rx.text("Video Files", weight="bold", size="2"),
                                rx.vstack(
                                    rx.foreach(
                                        ProjectState.video_files,
                                        lambda f: rx.text(f, size="1", color="gray")
                                    ),
                                    height="150px",
                                    overflow_y="auto",
                                    border="1px solid #333",
                                    padding="2",
                                    width="100%",
                                    bg="rgba(255,255,255,0.02)"
                                ),
                                width="100%",
                            ),
                            columns="2",
                            spacing="4",
                            width="100%",
                        ),
                        
                        # Validation Message
                        rx.cond(
                            ProjectState.is_valid,
                            rx.callout(
                                ProjectState.validation_message,
                                icon="circle_check",
                                color_scheme="green",
                                width="100%"
                            ),
                            rx.callout(
                                ProjectState.validation_message,
                                icon="info",
                                color_scheme="red",
                                width="100%"
                            ),
                        ),
                        width="100%",
                        spacing="4"
                    )
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
                ),
                
                spacing="4",
                width="100%",
                max_width="600px",
            ),
        ]
    )
