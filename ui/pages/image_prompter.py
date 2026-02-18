"""Image Prompter Page - Generate AI Image Prompts from Scripts"""
import reflex as rx
import sys
from pathlib import Path

UI_DIR = Path(__file__).parent.parent
if str(UI_DIR) not in sys.path:
    sys.path.insert(0, str(UI_DIR))

from states.image_prompter_state import ImagePrompterState
from components.layout import page_container, page_header
from components.log_viewer import log_viewer
from components.file_selector import project_selector


def prompt_card(prompt_data: dict, index: int) -> rx.Component:
    """Create a card for a single image prompt"""
    return rx.accordion.item(
        header=rx.hstack(
            rx.badge(f"#{index + 1}", color_scheme="gray", variant="solid"),
            rx.text(prompt_data.get("section_title", "Unknown"), weight="bold"),
            rx.badge(
                prompt_data.get("section_type", "unknown"),
                color_scheme="gray",
                variant="soft",
            ),
            rx.badge(
                f"{prompt_data.get('estimated_duration', 0)} sec",
                color_scheme="gray",
                variant="outline",
            ),
            align_items="center",
            spacing="3",
            width="100%",
        ),
        content=rx.vstack(
            # Image Prompt 1
            rx.vstack(
                rx.hstack(
                    rx.text("🎨 Image Prompt 1 (Subject Focus)", weight="bold", size="2"),
                    rx.icon_button(
                        rx.icon("copy", size=16),
                        variant="ghost",
                        size="1",
                        color_scheme="gray",
                        on_click=lambda: rx.set_clipboard(prompt_data.get("image_prompt", "")),
                        tooltip="Copy image prompt 1",
                    ),
                    justify="between",
                    align_items="center",
                    width="100%",
                ),
                rx.text(
                    prompt_data.get("image_prompt", ""),
                    size="2",
                    line_height="1.8",
                    color_scheme="gray",
                ),
                width="100%",
                spacing="2",
                padding="16px",
                background_color="rgba(35, 35, 35, 0.9)",
                border_radius="8px",
                border_left="4px solid var(--gray-7)",
            ),

            # Image Prompt 2
            rx.vstack(
                rx.hstack(
                    rx.text("🎨 Image Prompt 2 (Environment Focus)", weight="bold", size="2"),
                    rx.icon_button(
                        rx.icon("copy", size=16),
                        variant="ghost",
                        size="1",
                        color_scheme="gray",
                        on_click=lambda: rx.set_clipboard(prompt_data.get("image_prompt_2", "")),
                        tooltip="Copy image prompt 2",
                    ),
                    justify="between",
                    align_items="center",
                    width="100%",
                ),
                rx.text(
                    prompt_data.get("image_prompt_2", ""),
                    size="2",
                    line_height="1.8",
                    color_scheme="gray",
                ),
                width="100%",
                spacing="2",
                padding="16px",
                background_color="rgba(35, 35, 35, 0.9)",
                border_radius="8px",
                border_left="4px solid var(--gray-6)",
            ),

            # Multi-Angle Camera Prompt (right after image prompt)
            rx.vstack(
                rx.hstack(
                    rx.text("🎥 Multi-Angle Camera Prompt", weight="bold", size="2"),
                    rx.icon_button(
                        rx.icon("copy", size=16),
                        variant="ghost",
                        size="1",
                        color_scheme="gray",
                        on_click=lambda: rx.set_clipboard(prompt_data.get("multi_angle_camera_prompt", "")),
                        tooltip="Copy camera prompt",
                    ),
                    justify="between",
                    align_items="center",
                    width="100%",
                ),
                rx.text(
                    prompt_data.get("multi_angle_camera_prompt", "Multi-angle camera prompt will be generated..."),
                    size="2",
                    line_height="1.6",
                    color_scheme="gray",
                    white_space="pre",
                ),
                width="100%",
                spacing="2",
                padding="16px",
                background_color="rgba(35, 45, 55, 0.9)",
                border_radius="8px",
                border_left="4px solid var(--blue-8)",
            ),

            # Negative Prompt
            rx.cond(
                prompt_data.get("negative_prompt", "") != "",
                rx.vstack(
                    rx.text("🚫 Negative Prompt", weight="bold", size="2"),
                    rx.text(
                        prompt_data.get("negative_prompt", ""),
                        size="2",
                        color_scheme="gray",
                    ),
                    width="100%",
                    spacing="2",
                    padding="16px",
                    background_color="rgba(50, 30, 30, 0.6)",
                    border_radius="8px",
                    border_left="3px solid var(--red-9)",
                ),
            ),

            # Settings Grid
            rx.grid(
                rx.vstack(
                    rx.text("Aspect Ratio", size="1", color_scheme="gray"),
                    rx.text(prompt_data.get("suggested_aspect_ratio", "N/A"), weight="bold"),
                    align_items="start",
                    padding="16px",
                    background_color="rgba(40, 40, 40, 0.6)",
                    border_radius="8px",
                ),
                rx.vstack(
                    rx.text("Camera", size="1", color_scheme="gray"),
                    rx.text(prompt_data.get("suggested_camera", "N/A"), weight="bold"),
                    align_items="start",
                    padding="16px",
                    background_color="rgba(40, 40, 40, 0.6)",
                    border_radius="8px",
                ),
                rx.vstack(
                    rx.text("Lighting", size="1", color_scheme="gray"),
                    rx.text(prompt_data.get("suggested_lighting", "N/A"), weight="bold"),
                    align_items="start",
                    padding="16px",
                    background_color="rgba(40, 40, 40, 0.6)",
                    border_radius="8px",
                ),
                columns="3",
                spacing="3",
                width="100%",
                margin_top="12px",
            ),

            # Priority Elements (display as comma-separated text)
            rx.vstack(
                rx.text("🎯 Priority Elements", weight="bold", size="2"),
                rx.text(
                    rx.Var.create(prompt_data.get("priority_elements", [])).to(list).join(", "),
                    size="2",
                    color_scheme="gray",
                ),
                width="100%",
                spacing="2",
                margin_top="12px",
                padding="16px",
                background_color="rgba(40, 40, 40, 0.6)",
                border_radius="8px",
            ),

            # Continuity Notes
            rx.cond(
                prompt_data.get("continuity_notes", "") != "",
                rx.vstack(
                    rx.text("🔗 Continuity Notes", weight="bold", size="2"),
                    rx.text(
                        prompt_data.get("continuity_notes", ""),
                        size="2",
                        color_scheme="gray",
                        font_style="italic",
                    ),
                    width="100%",
                    spacing="2",
                    margin_top="12px",
                    padding="16px",
                    background_color="rgba(40, 40, 40, 0.6)",
                    border_radius="8px",
                    border_left="3px solid var(--gray-6)",
                ),
            ),

            # Narration Text
            rx.vstack(
                rx.text("📜 Narration", weight="bold", size="2"),
                rx.text(
                    prompt_data.get("narration_text", ""),
                    size="2",
                    color_scheme="gray",
                ),
                width="100%",
                spacing="2",
                margin_top="12px",
                padding="16px",
                background_color="rgba(45, 45, 45, 0.7)",
                border_radius="8px",
                border_left="4px solid var(--gray-6)",
            ),

            # Video Prompt (if exists)
            rx.cond(
                rx.Var.create(prompt_data.get("video_prompt")).to(dict).get("video_prompt", "") != "",
                rx.vstack(
                    rx.hstack(
                        rx.icon("video", color="blue", size=20),
                        rx.text("🎬 Video Prompt", weight="bold", size="2"),
                        align_items="center",
                        spacing="2",
                    ),
                    rx.text(
                        rx.Var.create(prompt_data.get("video_prompt")).to(dict).get("video_prompt", ""),
                        size="2",
                        line_height="1.8",
                        color_scheme="gray",
                    ),
                    width="100%",
                    spacing="2",
                    margin_top="12px",
                    padding="16px",
                    background_color="rgba(30, 40, 50, 0.8)",
                    border_radius="8px",
                    border_left="4px solid var(--blue-9)",
                ),
            ),



            width="100%",
            spacing="4",
        ),
        value=f"prompt_{index}",
    )


def page() -> rx.Component:
    """Image Prompter Page"""
    return page_container([
        page_header(
            "🎨 AI Image & Video Prompt Generator",
            "Generate image prompts and dynamic video prompts with camera directions from narration scripts"
        ),

        # Project Selection
        rx.vstack(
            rx.text("Select Project", weight="bold"),
            project_selector(
                projects=ImagePrompterState.available_projects,
                current_project=ImagePrompterState.selected_project,
                on_change_callback=ImagePrompterState.set_selected_project,
                on_reload_callback=ImagePrompterState.load_projects,
                placeholder="Select a project...",
                disabled=ImagePrompterState.is_generating,
            ),
            rx.text(
                rx.cond(
                    ImagePrompterState.available_projects.length() > 0,
                    f"Found {ImagePrompterState.available_projects.length()} projects with scripts",
                    "No projects found. Generate a script first in the Story→Script tab."
                ),
                size="1",
                color_scheme="gray"
            ),
            width="100%",
            align_items="start",
            max_width="600px",
            margin_top="32px",
        ),

        rx.divider(),

        # Progress Section
        rx.cond(
            ImagePrompterState.is_generating | (ImagePrompterState.current_section > 0),
            rx.vstack(
                rx.heading("📊 Progress", size="5", margin_bottom="2"),

                # Status
                rx.hstack(
                    rx.cond(
                        ImagePrompterState.is_generating,
                        rx.spinner(size="3", color_scheme="gray"),
                        rx.icon("check-circle", color="green", size=20)
                    ),
                    rx.text(ImagePrompterState.status_text, weight="bold"),
                    align_items="center",
                    spacing="3",
                ),

                # Progress Bar
                rx.progress(
                    value=ImagePrompterState.progress_percentage,
                    color_scheme="blue",
                    size="3",
                    width="100%",
                ),

                width="100%",
                max_width="800px",
                spacing="3",
                padding="20px",
                background_color="rgba(35, 35, 35, 0.8)",
                border_radius="12px",
                border="1px solid rgba(255, 255, 255, 0.05)",
            ),
        ),

        rx.divider(),

        # Action Button
        rx.hstack(
            rx.cond(
                ImagePrompterState.is_generating,
                rx.button(
                    "⏳ Generating...",
                    size="4",
                    color_scheme="gray",
                    disabled=True,
                ),
                rx.button(
                    "🚀 Generate Image Prompts",
                    on_click=ImagePrompterState.generate_prompts,
                    disabled=~ImagePrompterState.can_generate,
                    size="4",
                    color_scheme="blue",
                    variant="solid",
                ),
            ),
            spacing="3",
        ),

        # Generated Prompts
        rx.cond(
            ImagePrompterState.image_prompts.length() > 0,
            rx.vstack(
                rx.heading(f"🎨 Generated Prompts ({ImagePrompterState.image_prompts.length()})", size="5", margin_bottom="2"),

                rx.accordion.root(
                    rx.foreach(
                        ImagePrompterState.image_prompts,
                        lambda prompt, idx: prompt_card(prompt, idx),
                    ),
                    collapsible=True,
                    type="multiple",
                    width="100%",
                ),

                width="100%",
                spacing="3",
            ),
        ),

        # Log Viewer
        rx.vstack(
            rx.heading("📋 Logs", size="5", margin_bottom="2"),
            log_viewer(ImagePrompterState.generation_logs),
            width="100%",
            spacing="3",
        ),

        # Info
        rx.callout(
            "ℹ️ Image prompts are optimized for AI image generators (Midjourney, SD, DALL-E 3). "
            "Video prompts include dynamic camera directions for AI video generators (Runway, Pika, Sora). "
            "Each prompt maintains visual continuity across scenes.",
            color_scheme="gray",
        ),

    ], max_width="1200px")
