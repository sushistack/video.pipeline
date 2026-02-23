"""Image Prompter Page - Generate AI Image Prompts from Scripts"""
import reflex as rx
import sys
from pathlib import Path

UI_DIR = Path(__file__).parent.parent
if str(UI_DIR) not in sys.path:
    sys.path.insert(0, str(UI_DIR))

from states.image_prompter_state import ImagePrompterState, SubSceneData, ScenePromptData, VideoPromptData, ShotWithPrompt
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
            rx.badge(
                shot_data.shot.mood,
                color_scheme="amber",
                variant="soft",
                style={"whiteSpace": "normal", "wordBreak": "break-word", "overflowWrap": "break-word", "maxWidth": "100%"},
            ),
            rx.badge(
                shot_data.shot.motion,
                color_scheme="gray",
                variant="outline",
                style={"whiteSpace": "normal", "wordBreak": "break-word", "overflowWrap": "break-word", "maxWidth": "100%"},
            ),
            spacing="2",
            flex_wrap="wrap",
        ),
        # Subject
        rx.vstack(
            rx.text("Subject", size="1", color_scheme="gray", weight="bold"),
            rx.box(
                rx.text(
                    shot_data.shot.subject,
                    size="2",
                    line_height="1.6",
                ),
                width="100%",
                style={"wordBreak": "break-word", "whiteSpace": "pre-wrap", "overflowWrap": "break-word"},
            ),
            spacing="1",
            width="100%",
        ),
        # Lighting
        rx.vstack(
            rx.text("Lighting", size="1", color_scheme="gray", weight="bold"),
            rx.box(
                rx.text(
                    shot_data.shot.lighting,
                    size="2",
                ),
                width="100%",
                style={"wordBreak": "break-word", "whiteSpace": "pre-wrap", "overflowWrap": "break-word"},
            ),
            spacing="1",
            width="100%",
        ),
        # Image prompt
        rx.vstack(
            rx.hstack(
                rx.text("Image Prompt", weight="bold", size="2"),
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
            rx.box(
                rx.text(
                    shot_data.image_prompt.prompt,
                    size="2",
                    color_scheme="gray",
                    line_height="1.8",
                ),
                width="100%",
                style={"wordBreak": "break-word", "whiteSpace": "pre-wrap", "overflowWrap": "break-word"},
            ),
            width="100%",
            spacing="2",
            padding="12px",
            background_color="rgba(35, 35, 35, 0.9)",
            border_radius="8px",
            border_left="4px solid var(--gray-7)",
        ),
        width="100%",
        spacing="3",
        padding="16px",
        background_color="rgba(28, 28, 28, 0.8)",
        border_radius="10px",
        border="1px solid rgba(255, 255, 255, 0.06)",
    )


def video_prompt_card(vp: VideoPromptData) -> rx.Component:
    """Render video prompt with camera directions"""
    return rx.cond(
        vp.video_prompt != "",
        rx.vstack(
            rx.hstack(
                rx.icon("video", size=14, color="var(--purple-9)"),
                rx.text("Video Prompt", weight="bold", size="2", color_scheme="gray"),
                rx.icon_button(
                    rx.icon("copy", size=14),
                    variant="ghost",
                    size="1",
                    color_scheme="gray",
                    on_click=rx.set_clipboard(vp.video_prompt),
                    tooltip="Copy video prompt",
                ),
                justify="between",
                align_items="center",
                width="100%",
            ),
            rx.text(
                vp.video_prompt,
                size="2",
                color_scheme="gray",
                line_height="1.8",
                style={"wordBreak": "break-word", "whiteSpace": "pre-wrap", "overflowWrap": "break-word"},
            ),
            rx.cond(
                rx.cond(vp.camera_directions, True, False),
                rx.hstack(
                    rx.foreach(
                        vp.camera_directions,
                        lambda d: rx.badge(d, color_scheme="cyan", variant="outline", size="1"),
                    ),
                    flex_wrap="wrap",
                    spacing="1",
                    margin_top="4px",
                ),
            ),
            width="100%",
            spacing="2",
            padding="12px",
            background_color="rgba(35, 35, 40, 0.95)",
            border_radius="8px",
            border_left="4px solid var(--gray-7)",
        ),
    )


def sub_scene_card(sub_scene: SubSceneData) -> rx.Component:
    """Render a single sub-scene with collapsible sections"""
    return rx.accordion.item(
        header=rx.hstack(
            rx.badge(
                (sub_scene.sub_scene_index + 1).to_string(),
                color_scheme="gray",
                variant="solid",
                size="1",
            ),
            rx.text(
                sub_scene.key_point,
                size="2",
                color_scheme="gray",
                font_style="italic",
                line_height="1.6",
                flex_grow="1",
                style={"wordBreak": "break-word", "whiteSpace": "normal", "overflowWrap": "break-word"},
            ),
            align_items="center",
            spacing="2",
            width="100%",
        ),
        content=rx.vstack(
            # Opening Shot (collapsible) - Gray with subtle green accent
            rx.accordion.root(
                rx.accordion.item(
                    header=rx.hstack(
                        rx.icon("play", size=12, color="var(--green-9)"),
                        rx.text("Opening Shot", weight="bold", size="1", color_scheme="gray"),
                        align_items="center",
                        spacing="1",
                    ),
                    content=rx.vstack(
                        shot_item(sub_scene.opening_shot),
                        width="100%",
                        spacing="2",
                    ),
                    value="sub_" + sub_scene.sub_scene_index.to_string() + "_opening",
                    style={"background": "rgba(35, 35, 40, 0.6)", "border_radius": "8px", "border_left": "3px solid var(--gray-7)", "padding": "12px"},
                ),
                collapsible=True,
                type="single",
                width="100%",
            ),
            # Video Prompt (collapsible) - Gray with subtle purple accent
            rx.accordion.root(
                rx.accordion.item(
                    header=rx.hstack(
                        rx.icon("video", size=12, color="var(--purple-9)"),
                        rx.text("Video Prompt", weight="bold", size="1", color_scheme="gray"),
                        align_items="center",
                        spacing="1",
                    ),
                    content=rx.vstack(
                        video_prompt_card(sub_scene.video_prompt),
                        width="100%",
                        spacing="2",
                    ),
                    value="sub_" + sub_scene.sub_scene_index.to_string() + "_video",
                    style={"background": "rgba(38, 38, 42, 0.6)", "border_radius": "8px", "border_left": "3px solid var(--gray-5)", "padding": "12px"},
                ),
                collapsible=True,
                type="single",
                width="100%",
            ),
            width="100%",
            spacing="3",
        ),
        value="sub_scene_" + sub_scene.sub_scene_index.to_string(),
    )


def scene_card(prompt_data: ScenePromptData) -> rx.Component:
    """Create a scene accordion card showing all sub-scenes"""
    return rx.accordion.item(
        header=rx.hstack(
            rx.badge("#1", color_scheme="gray", variant="solid"),
            rx.text(prompt_data.section_title, weight="bold"),
            rx.badge(
                prompt_data.section_type,
                color_scheme="amber",
                variant="soft",
            ),
            rx.badge(
                prompt_data.estimated_duration.to_string(), " sec",
                color_scheme="gray",
                variant="outline",
            ),
            rx.badge(
                prompt_data.sub_scenes.length().to_string(), " sub-scenes",
                color_scheme="gray",
                variant="soft",
                size="1",
            ),
            align_items="center",
            spacing="3",
            width="100%",
            flex_wrap="wrap",
        ),
        content=rx.vstack(
            # Sub-scenes
            rx.foreach(
                prompt_data.sub_scenes,
                lambda sub: sub_scene_card(sub),
            ),
            width="100%",
            spacing="4",
        ),
        value="scene",
        style={"background": "rgba(40, 40, 45, 0.7)", "border_radius": "10px", "border_left": "4px solid var(--gray-8)", "padding": "4px"},
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
            rx.hstack(
                rx.text(
                    rx.cond(
                        ImagePrompterState.available_projects.length() > 0,
                        f"Found {ImagePrompterState.available_projects.length()} projects with scripts",
                        "No projects found. Generate a script first in the Story->Script tab."
                    ),
                    size="1",
                    color_scheme="gray"
                ),
                rx.cond(
                    ImagePrompterState.has_scp_facts,
                    rx.badge(
                        "Frozen Descriptor Ready",
                        color_scheme="purple",
                        variant="soft",
                        size="1",
                    ),
                ),
                spacing="2",
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
                rx.heading("Progress", size="5", margin_bottom="2"),

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

        # Speed Mode Toggle
        rx.hstack(
            rx.switch(
                checked=ImagePrompterState.speed_mode,
                on_change=ImagePrompterState.set_speed_mode,
                color_scheme="green",
                size="2",
            ),
            rx.vstack(
                rx.text("⚡ Speed Mode", weight="bold", size="2"),
                rx.text(
                    rx.cond(
                        ImagePrompterState.speed_mode,
                        "Enabled: Skip Qwen review for 2x faster generation (recommended)",
                        "Disabled: Full quality with Qwen review (slower)"
                    ),
                    size="1",
                    color_scheme="gray"
                ),
                spacing="0",
            ),
            rx.spacer(),
            rx.cond(
                ImagePrompterState.speed_mode,
                rx.badge("≈50% faster", color_scheme="green", variant="soft"),
                rx.badge("Full quality", color_scheme="blue", variant="soft"),
            ),
            align_items="center",
            spacing="3",
            width="100%",
            padding="12px",
            background_color=rx.cond(
                ImagePrompterState.speed_mode,
                "rgba(34, 197, 94, 0.1)",
                "rgba(59, 130, 246, 0.1)"
            ),
            border_radius="8px",
            border=rx.cond(
                ImagePrompterState.speed_mode,
                "1px solid rgba(34, 197, 94, 0.3)",
                "1px solid rgba(59, 130, 246, 0.3)"
            ),
        ),

        rx.divider(),

        # Action Button
        rx.hstack(
            rx.cond(
                ImagePrompterState.is_generating,
                rx.button(
                    "Generating...",
                    size="4",
                    color_scheme="gray",
                    disabled=True,
                ),
                rx.button(
                    "Generate Image Prompts",
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
                rx.heading(f"Generated Prompts ({ImagePrompterState.image_prompts.length()} scenes)", size="5", margin_bottom="2"),

                rx.accordion.root(
                    rx.foreach(
                        ImagePrompterState.image_prompts,
                        lambda prompt: scene_card(prompt),
                    ),
                    collapsible=True,
                    type="multiple",
                    width="100%",
                ),

                width="100%",
                spacing="3",
            ),
        ),

        # Aspect Ratio & Title Hint (Fixed Info Bar)
        rx.hstack(
            # Aspect Ratio Display
            rx.vstack(
                rx.hstack(
                    rx.icon("monitor", size=20, color="var(--gray-9)"),
                    rx.text("Aspect Ratio", weight="bold", size="2"),
                    align_items="center",
                    spacing="2",
                ),
                rx.badge(
                    "16:9",
                    color_scheme="gray",
                    variant="solid",
                    size="3",
                    padding="8px 16px",
                ),
                align_items="center",
                padding="16px",
                background_color="rgba(35, 35, 40, 0.8)",
                border_radius="8px",
                border="1px solid var(--gray-8)",
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
            rx.heading("Logs", size="5", margin_bottom="2"),
            log_viewer(ImagePrompterState.generation_logs),
            width="100%",
            spacing="3",
        ),

        # Info
        rx.callout(
            "Image prompts are optimized for AI image generators (Midjourney, SD, DALL-E 3). "
            "Video prompts include dynamic camera directions for AI video generators (Runway, Pika, Sora). "
            "Each sub-scene maintains visual continuity across the entire video.",
            color_scheme="gray",
        ),

    ], max_width="1200px")
