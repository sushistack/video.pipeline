"""Image Generator Page - Generate images using Janus-Pro-7B via SiliconFlow API"""
import reflex as rx
import sys
from pathlib import Path

UI_DIR = Path(__file__).parent.parent
if str(UI_DIR) not in sys.path:
    sys.path.insert(0, str(UI_DIR))

from states.image_generator_state import ImageGeneratorState, ImagePromptItem
from components.layout import page_container, page_header
from components.file_selector import project_selector
from components.log_viewer import log_viewer


def settings_panel() -> rx.Component:
    """Settings panel for image generation"""
    return rx.card(
        rx.vstack(
            rx.heading("⚙️ Generation Settings", size="4"),
            rx.grid(
                # Guidance Scale
                rx.vstack(
                    rx.hstack(
                        rx.text("Guidance Scale", weight="bold", size="2"),
                        rx.badge(
                            f"{ImageGeneratorState.guidance_scale:.1f}",
                            color_scheme="blue",
                        ),
                    ),
                    rx.slider(
                        value=[ImageGeneratorState.guidance_scale],
                        min=1,
                        max=20,
                        step=0.5,
                        on_change=ImageGeneratorState.set_guidance_scale,
                        disabled=ImageGeneratorState.is_generating,
                        width="100%",
                    ),
                    rx.text("Higher = more faithful to prompt", size="1", color="gray"),
                    align_items="start",
                    width="100%",
                ),
                # Inference Steps
                rx.vstack(
                    rx.hstack(
                        rx.text("Inference Steps", weight="bold", size="2"),
                        rx.badge(
                            f"{ImageGeneratorState.num_inference_steps}",
                            color_scheme="blue",
                        ),
                    ),
                    rx.slider(
                        value=[ImageGeneratorState.num_inference_steps],
                        min=10,
                        max=100,
                        step=5,
                        on_change=ImageGeneratorState.set_num_inference_steps,
                        disabled=ImageGeneratorState.is_generating,
                        width="100%",
                    ),
                    rx.text("More steps = better quality, slower", size="1", color="gray"),
                    align_items="start",
                    width="100%",
                ),
                # Resolution
                rx.vstack(
                    rx.hstack(
                        rx.text("Resolution", weight="bold", size="2"),
                        rx.badge(
                            f"{ImageGeneratorState.image_width}×{ImageGeneratorState.image_height}",
                            color_scheme="blue",
                            size="1",
                        ),
                        align_items="center",
                        spacing="2",
                    ),
                    rx.hstack(
                        rx.select(
                            ["384", "512", "720", "768", "1024", "1280"],
                            value=ImageGeneratorState.image_width,
                            on_change=lambda v: ImageGeneratorState.set_image_width(v),
                            disabled=ImageGeneratorState.is_generating,
                            width="100%",
                        ),
                        rx.text("×", weight="bold", size="2"),
                        rx.select(
                            ["219", "288", "309", "329", "384", "405", "432", "439", "512", "540", "576", "720", "768", "1024", "1280"],
                            value=ImageGeneratorState.image_height,
                            on_change=lambda v: ImageGeneratorState.set_image_height(v),
                            disabled=ImageGeneratorState.is_generating,
                            width="100%",
                        ),
                        width="100%",
                    ),
                    # Aspect Ratio Presets
                    rx.hstack(
                        rx.button(
                            "1:1",
                            variant="outline",
                            size="1",
                            on_click=lambda: ImageGeneratorState.set_preset_ratio("1:1"),
                            disabled=ImageGeneratorState.is_generating,
                        ),
                        rx.button(
                            "16:9",
                            variant="outline",
                            size="1",
                            on_click=lambda: ImageGeneratorState.set_preset_ratio("16:9"),
                            disabled=ImageGeneratorState.is_generating,
                        ),
                        rx.button(
                            "9:16",
                            variant="outline",
                            size="1",
                            on_click=lambda: ImageGeneratorState.set_preset_ratio("9:16"),
                            disabled=ImageGeneratorState.is_generating,
                        ),
                        rx.button(
                            "4:3",
                            variant="outline",
                            size="1",
                            on_click=lambda: ImageGeneratorState.set_preset_ratio("4:3"),
                            disabled=ImageGeneratorState.is_generating,
                        ),
                        rx.button(
                            "21:9",
                            variant="outline",
                            size="1",
                            on_click=lambda: ImageGeneratorState.set_preset_ratio("21:9"),
                            disabled=ImageGeneratorState.is_generating,
                        ),
                        spacing="2",
                        wrap="wrap",
                    ),
                    rx.text("Janus-Pro-7B: any resolution (higher resolution = slower)", size="1", color="gray"),
                    align_items="start",
                    width="100%",
                ),
                # Seed
                rx.vstack(
                    rx.hstack(
                        rx.text("Seed", weight="bold", size="2"),
                        rx.badge(
                            rx.cond(
                                ImageGeneratorState.use_random_seed,
                                "Random",
                                f"{ImageGeneratorState.seed}"
                            ),
                            color_scheme="purple",
                            size="1",
                        ),
                        align_items="center",
                        spacing="2",
                    ),
                    rx.hstack(
                        rx.checkbox(
                            checked=ImageGeneratorState.use_random_seed,
                            on_change=ImageGeneratorState.set_use_random_seed,
                            disabled=ImageGeneratorState.is_generating,
                            size="2",
                        ),
                        rx.text(
                            "Use random seed for each image",
                            size="2",
                            color_scheme="gray",
                        ),
                        align_items="center",
                        spacing="2",
                        width="100%",
                    ),
                    rx.cond(
                        ~ImageGeneratorState.use_random_seed,
                        rx.vstack(
                            rx.slider(
                                value=[ImageGeneratorState.seed],
                                min=0,
                                max=2**31 - 1,
                                step=1,
                                on_change=ImageGeneratorState.set_seed,
                                disabled=ImageGeneratorState.is_generating,
                                width="100%",
                            ),
                            rx.text("Same seed = same result", size="1", color="gray"),
                            width="100%",
                        ),
                    ),
                    align_items="start",
                    width="100%",
                ),
                columns="1",
                spacing="5",
                width="100%",
            ),
            spacing="4",
            width="100%",
            align_items="start",
        ),
        width="100%",
    )


def prompt_card(item: ImagePromptItem, index: int) -> rx.Component:
    """Create a prompt card with preview"""
    # Status badge
    status_badge = rx.cond(
        item.status == "completed",
        rx.badge("✓", color_scheme="green", variant="solid"),
        rx.cond(
            item.status == "generating",
            rx.badge(rx.spinner(size="1"), color_scheme="blue", variant="solid"),
            rx.cond(
                item.status == "failed",
                rx.badge("✕", color_scheme="red", variant="solid"),
                rx.badge("○", color_scheme="gray", variant="solid"),
            ),
        ),
    )
    
    # Shot type badge
    shot_badge = rx.cond(
        item.shot_type == "first",
        rx.badge("Opening", color_scheme="green", variant="soft"),
        rx.badge("Closing", color_scheme="blue", variant="soft"),
    )
    
    # Truncated key point
    key_point_display = rx.cond(
        item.key_point.length() > 100,
        item.key_point[:100] + "...",
        item.key_point,
    )
    
    return rx.card(
        rx.hstack(
            # Left: Prompt info
            rx.vstack(
                rx.hstack(
                    rx.badge(f"#{index + 1}", color_scheme="gray", size="1"),
                    shot_badge,
                    status_badge,
                    rx.spacer(),
                    # Generate button for pending
                    rx.cond(
                        item.status == "pending",
                        rx.button(
                            rx.icon("wand-sparkles", size=14),
                            "Generate",
                            variant="solid",
                            size="1",
                            color_scheme="blue",
                            on_click=lambda: ImageGeneratorState.generate_single(item.id),
                            disabled=ImageGeneratorState.is_generating,
                        ),
                        # Retry button for completed/failed
                        rx.cond(
                            item.status == "completed",
                            rx.icon_button(
                                rx.icon("refresh-cw", size=14),
                                variant="ghost",
                                size="1",
                                color_scheme="gray",
                                on_click=lambda: ImageGeneratorState.retry_single(item.id),
                                tooltip="Regenerate",
                                disabled=ImageGeneratorState.is_generating,
                            ),
                            rx.cond(
                                item.status == "failed",
                                rx.icon_button(
                                    rx.icon("refresh-cw", size=14),
                                    variant="ghost",
                                    size="1",
                                    color_scheme="red",
                                    on_click=lambda: ImageGeneratorState.retry_single(item.id),
                                    tooltip="Retry",
                                    disabled=ImageGeneratorState.is_generating,
                                ),
                            ),
                        ),
                    ),
                    # Download button
                    rx.cond(
                        item.status == "completed",
                        rx.icon_button(
                            rx.icon("download", size=14),
                            variant="ghost",
                            size="1",
                            color_scheme="blue",
                            on_click=lambda: ImageGeneratorState.download_image(item.id),
                            tooltip="Download",
                        ),
                    ),
                    align_items="center",
                    width="100%",
                ),
                rx.text(item.scene_title, weight="bold", size="2"),
                rx.text(
                    key_point_display,
                    size="1",
                    color_scheme="gray",
                ),
                rx.box(
                    rx.text(
                        item.prompt,
                        size="1",
                        color_scheme="gray",
                        line_height="1.6",
                        style={"wordBreak": "break-word", "whiteSpace": "pre-wrap"},
                    ),
                    width="100%",
                    padding="8px",
                    background_color="rgba(35, 35, 35, 0.5)",
                    border_radius="6px",
                    border_left="3px solid var(--gray-7)",
                ),
                # Error message if failed
                rx.cond(
                    item.status == "failed",
                    rx.callout(
                        item.error,
                        icon="circle-x",
                        color_scheme="red",
                        size="1",
                    ),
                ),
                spacing="2",
                width="100%",
                flex="1",
            ),
            
            # Right: Image preview
            rx.cond(
                item.status == "completed",
                rx.vstack(
                    rx.image(
                        src=item.preview,
                        width="150px",
                        height="150px",
                        object_fit="cover",
                        border_radius="8px",
                        border="2px solid var(--green-9)",
                    ),
                    rx.text(
                        f"{item.width}x{item.height}",
                        size="1",
                        color_scheme="gray",
                    ),
                    align_items="center",
                    justify="center",
                    width="150px",
                    height="150px",
                    background_color="rgba(35, 35, 35, 0.5)",
                    border_radius="8px",
                ),
                rx.cond(
                    item.status == "generating",
                    rx.vstack(
                        rx.spinner(size="3", color_scheme="blue"),
                        rx.text("Generating...", size="1", color_scheme="gray"),
                        align_items="center",
                        justify="center",
                        width="150px",
                        height="150px",
                        background_color="rgba(35, 35, 35, 0.5)",
                        border_radius="8px",
                    ),
                    rx.vstack(
                        rx.icon("image", size=32, color="var(--gray-8)"),
                        rx.text("Pending", size="1", color_scheme="gray"),
                        align_items="center",
                        justify="center",
                        width="150px",
                        height="150px",
                        background_color="rgba(35, 35, 35, 0.3)",
                        border_radius="8px",
                        border="2px dashed var(--gray-7)",
                    ),
                ),
            ),
            
            align_items="start",
            spacing="4",
            width="100%",
        ),
        width="100%",
        size="2",
    )


def page() -> rx.Component:
    """Image Generator Page"""
    return page_container([
        page_header(
            "🖼️ AI Image Generator",
            "Generate images from prompts using Janus-Pro-7B via SiliconFlow API"
        ),

        # Project Selection
        rx.vstack(
            rx.text("Select Project", weight="bold"),
            project_selector(
                projects=ImageGeneratorState.available_projects,
                current_project=ImageGeneratorState.selected_project,
                on_change_callback=ImageGeneratorState.set_selected_project,
                on_reload_callback=ImageGeneratorState.load_projects,
                placeholder="Select a project...",
                disabled=ImageGeneratorState.is_generating,
            ),
            rx.hstack(
                rx.cond(
                    ImageGeneratorState.available_projects.length() > 0,
                    rx.text(
                        f"Found {ImageGeneratorState.available_projects.length()} projects in workspace",
                        size="1",
                        color_scheme="gray"
                    ),
                    rx.text(
                        "No projects found in workspace/ folder.",
                        size="1",
                        color_scheme="gray"
                    ),
                ),
                rx.cond(
                    ImageGeneratorState.prompt_items.length() > 0,
                    rx.badge(
                        f"{ImageGeneratorState.prompt_items.length()} prompts",
                        color_scheme="blue",
                        variant="soft",
                    ),
                ),
                align_items="center",
                spacing="3",
            ),
            width="100%",
            align_items="start",
            max_width="600px",
            margin_top="32px",
        ),

        rx.divider(),

        # Settings Panel
        settings_panel(),

        rx.divider(),

        # Progress Section
        rx.cond(
            ImageGeneratorState.is_generating | (ImageGeneratorState.current_index > 0),
            rx.vstack(
                rx.heading("Progress", size="5", margin_bottom="2"),

                # Status
                rx.hstack(
                    rx.cond(
                        ImageGeneratorState.is_generating,
                        rx.spinner(size="3", color_scheme="blue"),
                        rx.icon("circle-check", color="green", size=20)
                    ),
                    rx.text(ImageGeneratorState.status_text, weight="bold"),
                    rx.spacer(),
                    rx.hstack(
                        rx.badge(
                            f"✓ {ImageGeneratorState.completed_count}",
                            color_scheme="green",
                            variant="soft",
                        ),
                        rx.cond(
                            ImageGeneratorState.failed_count > 0,
                            rx.badge(
                                f"✕ {ImageGeneratorState.failed_count}",
                                color_scheme="red",
                                variant="soft",
                            ),
                        ),
                        spacing="2",
                    ),
                    align_items="center",
                    spacing="3",
                    width="100%",
                ),

                # Progress Bar
                rx.progress(
                    value=ImageGeneratorState.progress_percentage,
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

        # Action Buttons
        rx.hstack(
            rx.cond(
                ImageGeneratorState.is_generating,
                rx.button(
                    rx.spinner(size="3"),
                    "Generating...",
                    disabled=True,
                    size="4",
                    color_scheme="blue",
                ),
                rx.button(
                    rx.icon("wand-sparkles", size=20),
                    "Generate All Images",
                    on_click=ImageGeneratorState.generate_all,
                    disabled=~ImageGeneratorState.can_generate,
                    size="4",
                    color_scheme="blue",
                    variant="solid",
                ),
            ),
            rx.cond(
                ImageGeneratorState.completed_count > 0,
                rx.button(
                    rx.icon("download", size=16),
                    "Download ZIP",
                    on_click=ImageGeneratorState.download_all_zip,
                    size="4",
                    variant="outline",
                ),
            ),
            spacing="3",
            width="100%",
            justify="center",
        ),

        # Log Viewer (Console)
        rx.vstack(
            rx.heading("📋 Generation Logs", size="5", margin_bottom="2"),
            log_viewer(ImageGeneratorState.generation_logs),
            width="100%",
            spacing="3",
        ),

        rx.divider(),

        # Prompt Cards List
        rx.cond(
            ImageGeneratorState.prompt_items.length() > 0,
            rx.vstack(
                rx.heading(
                    f"Image Prompts ({ImageGeneratorState.prompt_items.length()})",
                    size="5",
                    margin_bottom="2"
                ),
                rx.vstack(
                    rx.foreach(
                        ImageGeneratorState.prompt_items,
                        lambda item, idx: prompt_card(item, idx),
                    ),
                    spacing="3",
                    width="100%",
                ),
                width="100%",
                spacing="4",
            ),
            rx.callout(
                "Select a project to view image prompts. Generate image prompts first in the Prompter tab if none exist.",
                icon="info",
                color_scheme="blue",
            ),
        ),

        # Info
        rx.callout(
            "💡 Janus-Pro-7B is DeepSeek's multimodal model running via SiliconFlow cloud API. "
            "No local GPU required — images are generated on SiliconFlow's servers. "
            "Use the same seed value to reproduce identical results. "
            "API key is read from SILICONFLOW_API_KEY in your .env file.",
            color_scheme="gray",
        ),

    ], max_width="1200px")
