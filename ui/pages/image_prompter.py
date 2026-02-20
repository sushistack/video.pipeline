"""Image Prompter Page - Generate AI Image Prompts from Scripts"""
import reflex as rx
import sys
from pathlib import Path

UI_DIR = Path(__file__).parent.parent
if str(UI_DIR) not in sys.path:
    sys.path.insert(0, str(UI_DIR))

from states.image_prompter_state import ImagePrompterState, ShotWithPrompt, ScenePromptData
from components.layout import page_container, page_header
from components.log_viewer import log_viewer
from components.file_selector import project_selector


def shot_item(shot_data: ShotWithPrompt) -> rx.Component:
    """Render a single shot breakdown + image prompt"""
    return rx.vstack(
        # Shot header badges
        rx.hstack(
            rx.badge(
                rx.hstack(rx.icon("camera", size=12), shot_data.shot.camera_type, spacing="1"),
                color_scheme="blue",
                variant="soft",
            ),
            rx.badge(shot_data.shot.mood, color_scheme="amber", variant="soft"),
            rx.badge(shot_data.shot.motion, color_scheme="gray", variant="outline"),
            spacing="2",
            flex_wrap="wrap",
        ),
        # Subject
        rx.vstack(
            rx.text("피사체 (Subject)", size="1", color_scheme="gray", weight="bold"),
            rx.text(shot_data.shot.subject, size="2", line_height="1.6"),
            spacing="1",
            width="100%",
        ),
        # Lighting
        rx.vstack(
            rx.text("조명 (Lighting)", size="1", color_scheme="gray", weight="bold"),
            rx.text(shot_data.shot.lighting, size="2"),
            spacing="1",
            width="100%",
        ),
        # Image prompt
        rx.vstack(
            rx.hstack(
                rx.text("🎨 Image Prompt", weight="bold", size="2"),
                rx.icon_button(
                    rx.icon("copy", size=14),
                    variant="ghost",
                    size="1",
                    color_scheme="gray",
                    on_click=rx.set_clipboard(shot_data.image_prompt.prompt),
                    tooltip="Copy image prompt",
                ),
                justify="between",
                align_items="center",
                width="100%",
            ),
            rx.text(
                shot_data.image_prompt.prompt,
                size="2",
                color_scheme="gray",
                line_height="1.8",
            ),
            width="100%",
            spacing="2",
            padding="12px",
            background_color="rgba(35, 35, 35, 0.9)",
            border_radius="8px",
            border_left="4px solid var(--blue-7)",
        ),
        width="100%",
        spacing="3",
        padding="16px",
        background_color="rgba(28, 28, 28, 0.8)",
        border_radius="10px",
        border="1px solid rgba(255, 255, 255, 0.06)",
    )


def prompt_card(prompt_data: ScenePromptData, index: int) -> rx.Component:
    """Create a scene card showing all shots with breakdown + image prompts"""
    return rx.accordion.item(
        header=rx.hstack(
            rx.badge(f"#{index + 1}", color_scheme="gray", variant="solid"),
            rx.text(prompt_data.section_title, weight="bold"),
            rx.badge(
                prompt_data.section_type,
                color_scheme="amber",
                variant="soft",
            ),
            rx.badge(
                prompt_data.estimated_duration, " sec",
                color_scheme="gray",
                variant="outline",
            ),
            rx.badge(
                prompt_data.continuity_notes,
                color_scheme="blue",
                variant="soft",
                size="1",
            ),
            align_items="center",
            spacing="3",
            width="100%",
            flex_wrap="wrap",
        ),
        content=rx.vstack(
            # All shots (new pipeline: 2-4 shots per scene)
            rx.foreach(
                prompt_data.all_shots,
                shot_item,
            ),

            # Negative Prompt
            rx.cond(
                prompt_data.negative_prompt != "",
                rx.vstack(
                    rx.text("🚫 Negative Prompt", weight="bold", size="2"),
                    rx.text(
                        prompt_data.negative_prompt,
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

            # Scene Synopsis
            rx.vstack(
                rx.text("📜 Scene Synopsis", weight="bold", size="2"),
                rx.text(
                    prompt_data.narration_text,
                    size="2",
                    color_scheme="gray",
                    line_height="1.6",
                ),
                width="100%",
                spacing="2",
                margin_top="8px",
                padding="16px",
                background_color="rgba(45, 45, 45, 0.7)",
                border_radius="8px",
                border_left="4px solid var(--gray-6)",
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
                        rx.icon("circle-check", color="green", size=20)
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

        # Fixed Video Prompt (Independent Section)
        rx.vstack(
            rx.hstack(
                rx.icon("video", color="blue", size=24),
                rx.heading("🎬 Fixed Video Prompt", size="5"),
                align_items="center",
                spacing="3",
            ),
            rx.text(
                "A rapid series of sharp cuts between as many different camera angles and distances as possible: "
                "switching instantly between extreme close-up, wide shot, bird's-eye view, low angle, and side profile, "
                "with zero camera motion within each shot and instant transitions.",
                size="3",
                line_height="1.8",
                color_scheme="gray",
            ),
            rx.button(
                "📋 Copy Video Prompt",
                on_click=rx.set_clipboard(
                    "A rapid series of sharp cuts between as many different camera angles and distances as possible: "
                    "switching instantly between extreme close-up, wide shot, bird's-eye view, low angle, and side profile, "
                    "with zero camera motion within each shot and instant transitions."
                ),
                color_scheme="blue",
                variant="solid",
                size="3",
            ),
            width="100%",
            spacing="4",
            padding="24px",
            background_color="rgba(30, 40, 50, 0.9)",
            border_radius="12px",
            border="2px solid var(--blue-9)",
            margin_top="32px",
        ),

        # Aspect Ratio & Title Hint (Fixed Info Bar)
        rx.hstack(
            # Aspect Ratio Display
            rx.vstack(
                rx.hstack(
                    rx.icon("monitor", size=20, color="var(--blue-9)"),
                    rx.text("Aspect Ratio", weight="bold", size="2"),
                    align_items="center",
                    spacing="2",
                ),
                rx.badge(
                    "16:9",
                    color_scheme="blue",
                    variant="solid",
                    size="3",
                    padding="8px 16px",
                ),
                align_items="center",
                padding="16px",
                background_color="rgba(30, 40, 50, 0.8)",
                border_radius="8px",
                border="1px solid var(--blue-8)",
            ),

            # Title Hint
            rx.cond(
                ImagePrompterState.content_title != "",
                rx.vstack(
                    rx.hstack(
                        rx.icon("book-open", size=20, color="var(--gray-9)"),
                        rx.text("Content Title", weight="bold", size="2"),
                        align_items="center",
                        spacing="2",
                    ),
                    rx.text(
                        ImagePrompterState.content_title,
                        size="2",
                        color_scheme="gray",
                        line_height="1.6",
                        max_width="600px",
                    ),
                    align_items="start",
                    padding="16px",
                    background_color="rgba(40, 40, 40, 0.8)",
                    border_radius="8px",
                    border="1px solid var(--gray-7)",
                    flex_grow="1",
                ),
            ),

            width="100%",
            spacing="4",
            align_items="stretch",
            margin_top="24px",
            padding="16px",
            background_color="rgba(35, 35, 35, 0.9)",
            border_radius="12px",
            border="1px solid rgba(255, 255, 255, 0.05)",
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
