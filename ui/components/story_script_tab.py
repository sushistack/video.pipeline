"""Story-to-Script Tab UI Component"""
import reflex as rx
import sys
from pathlib import Path

UI_DIR = Path(__file__).parent.parent
if str(UI_DIR) not in sys.path:
    sys.path.insert(0, str(UI_DIR))

from states.story_script_state import StoryScriptState
from components.log_viewer import log_viewer


def story_script_tab() -> rx.Component:
    """Story-to-Script Tab Content"""
    return rx.vstack(
        # Input Section
        rx.vstack(
            rx.heading("1️⃣ Story & Project Input", size="5", margin_bottom="2"),

            # Project Name
            rx.vstack(
                rx.text("Project Name (Optional)", weight="bold", size="2"),
                rx.input(
                    placeholder="e.g., joseon_scientist, ai_future (auto-generated if empty)",
                    value=StoryScriptState.project_name,
                    on_change=StoryScriptState.set_project_name,
                    size="3",
                    width="100%",
                    disabled=StoryScriptState.is_running,
                ),
                rx.text(
                    "Project name will be auto-generated if left empty.",
                    size="1",
                    color_scheme="gray",
                ),
                width="100%",
                spacing="2",
            ),

            # Story Title
            rx.vstack(
                rx.text("Story Title / Topic", weight="bold", size="2"),
                rx.input(
                    placeholder="e.g., The Story of a Joseon-era Scientist, The Future of AI, etc.",
                    value=StoryScriptState.story_title,
                    on_change=StoryScriptState.set_story_title,
                    size="3",
                    width="100%",
                    disabled=StoryScriptState.is_running,
                ),
                width="100%",
                spacing="2",
            ),

            # Context (Optional)
            rx.vstack(
                rx.text("Additional Context (Optional)", weight="bold", size="2"),
                rx.text_area(
                    placeholder="Enter additional information about the story, content you want to emphasize, etc.",
                    value=StoryScriptState.story_context,
                    on_change=StoryScriptState.set_story_context,
                    size="3",
                    width="100%",
                    height="100px",
                    disabled=StoryScriptState.is_running,
                ),
                width="100%",
                spacing="2",
            ),

            # Model Selection
            rx.vstack(
                rx.text("Gemini Model", weight="bold", size="2"),
                rx.select(
                    StoryScriptState.gemini_model_options,
                    value=StoryScriptState.selected_gemini_model,
                    on_change=StoryScriptState.set_selected_gemini_model,
                    size="3",
                    width="100%",
                    disabled=StoryScriptState.is_running,
                ),
                width="100%",
                spacing="2",
            ),

            width="100%",
            max_width="800px",
            spacing="4",
            padding="20px",
            background_color="rgba(255, 255, 255, 0.02)",
            border_radius="12px",
            border="1px solid rgba(255, 255, 255, 0.08)",
        ),
        
        rx.divider(),
        
        # Progress Section
        rx.cond(
            StoryScriptState.is_running | (StoryScriptState.current_step > 0),
            rx.vstack(
                rx.heading("📊 Progress Status", size="5", margin_bottom="2"),
                
                # Status
                rx.hstack(
                    rx.cond(
                        StoryScriptState.is_running,
                        rx.spinner(size="3", color_scheme="blue"),
                        rx.icon("circle-check", color="green", size=20)
                    ),
                    rx.text(StoryScriptState.status_text, weight="bold"),
                    align_items="center",
                    spacing="3",
                ),
                
                # Progress Bar
                rx.progress(
                    value=StoryScriptState.progress_percentage.to(int),
                    color_scheme="blue",
                    size="3",
                    width="100%",
                ),
                
                rx.text(
                    f"Step {StoryScriptState.current_step}/{StoryScriptState.total_steps}",
                    size="2",
                    color_scheme="gray",
                ),
                
                width="100%",
                max_width="800px",
                spacing="3",
                padding="20px",
                background_color="rgba(255, 255, 255, 0.02)",
                border_radius="12px",
                border="1px solid rgba(255, 255, 255, 0.08)",
            ),
        ),
        
        rx.divider(),
        
        # Action Button
        rx.hstack(
            rx.cond(
                StoryScriptState.is_running,
                rx.button(
                    "⏳ Processing...",
                    size="4",
                    color_scheme="gray",
                    disabled=True,
                ),
                rx.button(
                    "🚀 Start Story → Script Generation",
                    on_click=StoryScriptState.run_pipeline,
                    disabled=~StoryScriptState.can_start,
                    size="4",
                    color_scheme="blue",
                ),
            ),
            spacing="3",
        ),
        
        # Generated Files Info
        rx.cond(
            StoryScriptState.project_id != "",
            rx.vstack(
                rx.heading("📁 Project Info", size="5", margin_bottom="2"),

                rx.hstack(
                    rx.icon("folder", color="blue", size=20),
                    rx.text("Project ID: ", weight="bold"),
                    rx.text(StoryScriptState.project_id, size="2", color_scheme="gray"),
                    align_items="center",
                    spacing="2",
                ),

                rx.hstack(
                    rx.icon("folder-open", color="blue", size=20),
                    rx.text("Path: ", weight="bold"),
                    rx.text(StoryScriptState.project_dir, size="2", color_scheme="gray"),
                    align_items="center",
                    spacing="2",
                ),

                rx.divider(),

                rx.heading("📄 Generated Files", size="4", margin_bottom="2"),

                rx.hstack(
                    rx.icon("file-text", color="blue", size=20),
                    rx.text("Content: ", weight="bold"),
                    rx.text(StoryScriptState.generated_content_path, size="2", color_scheme="gray"),
                    align_items="center",
                    spacing="2",
                ),

                rx.foreach(
                    StoryScriptState.generated_scripts,
                    lambda script: rx.hstack(
                        rx.icon("scroll", color="green", size=20),
                        rx.text("Script: ", weight="bold"),
                        rx.text(script, size="2", color_scheme="gray"),
                        align_items="center",
                        spacing="2",
                    ),
                ),

                rx.cond(
                    StoryScriptState.generated_subtitle_path != "",
                    rx.hstack(
                        rx.icon("captions", color="purple", size=20),
                        rx.text("Subtitle: ", weight="bold"),
                        rx.text(StoryScriptState.generated_subtitle_path, size="2", color_scheme="gray"),
                        align_items="center",
                        spacing="2",
                    ),
                ),

                width="100%",
                max_width="800px",
                spacing="3",
                padding="20px",
                background_color="rgba(255, 255, 255, 0.02)",
                border_radius="12px",
                border="1px solid rgba(255, 255, 255, 0.08)",
            ),
        ),
        
        # Script Preview
        rx.cond(
            StoryScriptState.script_sections.length() > 0,
            rx.vstack(
                rx.heading("📜 Script Preview", size="5", margin_bottom="2"),
                
                rx.accordion.root(
                    rx.foreach(
                        StoryScriptState.script_sections,
                        lambda section: rx.accordion.item(
                            header=rx.hstack(
                                rx.badge(section["section"], color_scheme="blue", variant="soft"),
                                rx.text(section["title"], weight="bold"),
                                rx.badge(
                                    section["estimated_duration"].to(str) + " sec",
                                    color_scheme="gray",
                                    variant="outline",
                                ),
                                align_items="center",
                                spacing="3",
                                width="100%",
                            ),
                            content=rx.text(
                                section["content"],
                                size="2",
                                line_height="1.8",
                            ),
                            value=section["section"],
                        ),
                    ),
                    collapsible=True,
                    type="multiple",
                    width="100%",
                ),
                
                width="100%",
                max_width="800px",
                spacing="3",
                padding="20px",
                background_color="rgba(255, 255, 255, 0.02)",
                border_radius="12px",
                border="1px solid rgba(255, 255, 255, 0.08)",
            ),
        ),
        
        # Log Viewer
        rx.vstack(
            rx.heading("📋 Logs", size="5", margin_bottom="2"),
            log_viewer(StoryScriptState.pipeline_logs),
            width="100%",
            spacing="3",
        ),
        
        # Info
        rx.callout(
            "ℹ️ The entire pipeline may take 3-5 minutes. The script is improved at each step, and a final subtitle file is generated.",
            color_scheme="gray",
        ),

        width="100%",
        spacing="6",
        margin_top="32px",
    )
