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

            # SCP Selection (RAG-like)
            rx.vstack(
                rx.hstack(
                    rx.text("🔬 SCP Selection", weight="bold", size="2"),
                    rx.badge("RAG", color_scheme="purple", variant="soft", size="1"),
                    align_items="center",
                    spacing="2",
                ),
                rx.select(
                    StoryScriptState.scp_select_options,
                    value=StoryScriptState.scp_select_value,
                    on_change=StoryScriptState.handle_scp_select_change,
                    placeholder="Select an SCP entity...",
                    size="3",
                    width="100%",
                    disabled=StoryScriptState.is_running,
                ),
                rx.cond(
                    StoryScriptState.has_scp_facts,
                    rx.hstack(
                        rx.badge(
                            StoryScriptState.scp_facts.get("object_class", "Unknown"),
                            color_scheme="amber",
                            variant="soft",
                        ),
                        rx.text(
                            f"facts.json loaded • Visual elements ready for injection",
                            size="1",
                            color_scheme="green",
                        ),
                        spacing="2",
                    ),
                    rx.text(
                        "Select an SCP to auto-load facts for visual consistency",
                        size="1",
                        color_scheme="gray",
                    ),
                ),
                width="100%",
                spacing="2",
                padding="12px",
                background_color="rgba(139, 92, 246, 0.08)",
                border_radius="8px",
                border="1px solid rgba(139, 92, 246, 0.2)",
            ),

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
        
        # Step-by-Step File Previews
        rx.cond(
            StoryScriptState.current_step > 0,
            rx.vstack(
                rx.heading("📄 Generated Files Preview", size="5", margin_bottom="2"),
                
                rx.tabs.root(
                    rx.tabs.list(
                        rx.tabs.trigger("1. Research", value="research"),
                        rx.tabs.trigger("2. Structure", value="structure"),
                        rx.tabs.trigger("3. Writing", value="writing"),
                        rx.tabs.trigger("4. Review", value="review"),
                        rx.tabs.trigger("5. SRT", value="srt"),
                    ),
                    
                    # Research Tab - Markdown-like display
                    rx.tabs.content(
                        rx.scroll_area(
                            rx.vstack(
                                rx.foreach(
                                    StoryScriptState.research_lines,
                                    lambda line: rx.cond(
                                        line.startswith("#"),
                                        rx.heading(line, size="4", weight="bold", margin_bottom="1"),
                                        rx.cond(
                                            line.startswith("- ") | line.startswith("* "),
                                            rx.box(line, margin_left="1em", margin_bottom="0.5em"),
                                            rx.text(line, margin_bottom="0.5em", white_space="pre_wrap")
                                        )
                                    )
                                ),
                                width="100%",
                                spacing="1",
                            ),
                            type="always",
                            scrollbars="vertical",
                            height="400px",
                        ),
                        value="research",
                    ),
                    
                    # Structure Tab - JSON display
                    rx.tabs.content(
                        rx.scroll_area(
                            rx.vstack(
                                rx.foreach(
                                    StoryScriptState.structure_lines,
                                    lambda line: rx.text(
                                        line,
                                        white_space="pre",
                                        font_size="xs",
                                        font_family="monospace",
                                        line_height="1.4",
                                    )
                                ),
                                width="100%",
                                spacing="0",
                            ),
                            type="always",
                            scrollbars="vertical",
                            height="400px",
                        ),
                        value="structure",
                    ),
                    
                    # Writing Tab - JSON display
                    rx.tabs.content(
                        rx.scroll_area(
                            rx.vstack(
                                rx.foreach(
                                    StoryScriptState.writing_lines,
                                    lambda line: rx.text(
                                        line,
                                        white_space="pre",
                                        font_size="xs",
                                        font_family="monospace",
                                        line_height="1.4",
                                    )
                                ),
                                width="100%",
                                spacing="0",
                            ),
                            type="always",
                            scrollbars="vertical",
                            height="400px",
                        ),
                        value="writing",
                    ),
                    
                    # Review Tab - JSON display
                    rx.tabs.content(
                        rx.scroll_area(
                            rx.vstack(
                                rx.foreach(
                                    StoryScriptState.review_lines,
                                    lambda line: rx.text(
                                        line,
                                        white_space="pre",
                                        font_size="xs",
                                        font_family="monospace",
                                        line_height="1.4",
                                    )
                                ),
                                width="100%",
                                spacing="0",
                            ),
                            type="always",
                            scrollbars="vertical",
                            height="400px",
                        ),
                        value="review",
                    ),
                    
                    # SRT Tab - Preformatted text
                    rx.tabs.content(
                        rx.scroll_area(
                            rx.vstack(
                                rx.foreach(
                                    StoryScriptState.srt_lines,
                                    lambda line: rx.text(
                                        line,
                                        white_space="pre",
                                        font_size="sm",
                                        font_family="monospace",
                                        margin_bottom="0.25em",
                                    )
                                ),
                                width="100%",
                                spacing="0",
                            ),
                            type="always",
                            scrollbars="vertical",
                            height="400px",
                        ),
                        value="srt",
                    ),
                    
                    default_value="research",
                    width="100%",
                ),
                
                width="100%",
                max_width="900px",
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
            "ℹ️ The entire pipeline may take 3-5 minutes. The script is improved at each step (Research → Structure → Writing → Review), and a final subtitle file is generated.",
            color_scheme="gray",
        ),

        width="100%",
        spacing="6",
        margin_top="32px",
    )
