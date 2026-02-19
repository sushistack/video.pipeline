"""Image Preprocessor Page - Optimize images for video generation models"""
import reflex as rx
import sys
from pathlib import Path

UI_DIR = Path(__file__).parent.parent
if str(UI_DIR) not in sys.path:
    sys.path.insert(0, str(UI_DIR))

from states.image_preprocessor_state import ImagePreprocessorState
from components.layout import page_container, page_header
from components.file_selector import project_selector


def settings_panel() -> rx.Component:
    """Settings panel for image processing options"""
    return rx.card(
        rx.vstack(
            rx.heading("⚙️ Processing Settings", size="4"),
            rx.grid(
                # Resolution
                rx.vstack(
                    rx.text("Target Resolution (Long Edge)", weight="bold", size="2"),
                    rx.select(
                        ImagePreprocessorState.resolution_options,
                        value=ImagePreprocessorState.target_resolution,
                        on_change=ImagePreprocessorState.set_target_resolution,
                        disabled=ImagePreprocessorState.is_processing,
                        width="100%",
                    ),
                    rx.text("Maintains aspect ratio", size="1", color="gray"),
                    align_items="start",
                    width="100%",
                ),
                # Format
                rx.vstack(
                    rx.text("Output Format", weight="bold", size="2"),
                    rx.select(
                        ImagePreprocessorState.format_options,
                        value=ImagePreprocessorState.output_format,
                        on_change=ImagePreprocessorState.set_output_format,
                        disabled=ImagePreprocessorState.is_processing,
                        width="100%",
                    ),
                    rx.text("JPG/WebP: Lossy compression", size="1", color="gray"),
                    align_items="start",
                    width="100%",
                ),
                # Quality
                rx.vstack(
                    rx.hstack(
                        rx.text("Compression Quality", weight="bold", size="2"),
                        rx.badge(
                            f"{ImagePreprocessorState.quality}",
                            color_scheme=rx.cond(
                                ImagePreprocessorState.quality_disabled,
                                "gray",
                                "blue"
                            ),
                        ),
                    ),
                    rx.slider(
                        value=[ImagePreprocessorState.quality],
                        min=1,
                        max=100,
                        step=1,
                        on_change=ImagePreprocessorState.set_quality,
                        disabled=rx.cond(
                            ImagePreprocessorState.is_processing,
                            True,
                            ImagePreprocessorState.quality_disabled
                        ),
                        width="100%",
                    ),
                    rx.text(
                        rx.cond(
                            ImagePreprocessorState.quality_disabled,
                            "PNG is lossless (quality N/A)",
                            "Lower = smaller file size"
                        ),
                        size="1",
                        color="gray"
                    ),
                    align_items="start",
                    width="100%",
                ),
                columns="3",
                spacing="5",
                width="100%",
            ),
            # Suffix option
            rx.hstack(
                rx.checkbox(
                    "Add filename suffix",
                    checked=ImagePreprocessorState.add_suffix,
                    on_change=ImagePreprocessorState.set_add_suffix,
                    disabled=ImagePreprocessorState.is_processing,
                ),
                rx.cond(
                    ImagePreprocessorState.add_suffix,
                    rx.input(
                        value=ImagePreprocessorState.suffix_text,
                        on_change=ImagePreprocessorState.set_suffix_text,
                        placeholder="_processed",
                        width="150px",
                        size="1",
                        disabled=ImagePreprocessorState.is_processing,
                    ),
                ),
                align="center",
                spacing="3",
            ),
            spacing="4",
            width="100%",
            align_items="start",
        ),
        width="100%",
    )


def source_files_list() -> rx.Component:
    """List of source files from workspace"""
    return rx.vstack(
        rx.hstack(
            rx.heading("📁 Source Images", size="4"),
            rx.badge(
                ImagePreprocessorState.source_count,
                color_scheme="blue",
            ),
            rx.spacer(),
            rx.button(
                rx.icon("refresh-cw", size=14),
                "Refresh",
                on_click=ImagePreprocessorState.load_source_files,
                size="1",
                variant="ghost",
                disabled=ImagePreprocessorState.is_processing,
            ),
            align="center",
            width="100%",
        ),
        rx.text(
            ImagePreprocessorState.source_dir_path,
            size="1",
            color="gray",
            font_family="monospace",
        ),
        rx.cond(
            ImagePreprocessorState.has_sources,
            rx.scroll_area(
                rx.vstack(
                    rx.foreach(
                        ImagePreprocessorState.source_files,
                        lambda f: rx.card(
                            rx.hstack(
                                rx.image(
                                    src=f["preview"],
                                    width="60px",
                                    height="60px",
                                    object_fit="cover",
                                    border_radius="8px",
                                ),
                                rx.vstack(
                                    rx.text(f["name"], weight="bold", size="2"),
                                    rx.text(
                                        f"{f['width']}x{f['height']} • {f['size_kb']}KB",
                                        size="1",
                                        color="gray"
                                    ),
                                    align_items="start",
                                    spacing="1",
                                ),
                                align="center",
                                width="100%",
                            ),
                            size="1",
                            width="100%",
                        ),
                    ),
                    spacing="2",
                    width="100%",
                ),
                type="auto",
                scrollbars="vertical",
                style={"maxHeight": "300px"},
            ),
            rx.callout(
                f"Place image files in {ImagePreprocessorState.source_dir_path} folder.",
                icon="info",
                color_scheme="blue",
            ),
        ),
        spacing="3",
        width="100%",
    )


def processed_results() -> rx.Component:
    """Processed files results table"""
    return rx.cond(
        ImagePreprocessorState.has_processed,
        rx.vstack(
            rx.hstack(
                rx.heading("✅ Results", size="4"),
                rx.badge(
                    ImagePreprocessorState.processed_count,
                    color_scheme="green",
                ),
                rx.spacer(),
                rx.text(
                    ImagePreprocessorState.output_dir_path,
                    size="1",
                    color="gray",
                    font_family="monospace",
                ),
                rx.button(
                    rx.icon("download", size=16),
                    "Download ZIP",
                    on_click=ImagePreprocessorState.download_all_zip,
                    color_scheme="blue",
                    size="2",
                ),
                align="center",
                width="100%",
            ),
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("#"),
                        rx.table.column_header_cell("Preview"),
                        rx.table.column_header_cell("Filename"),
                        rx.table.column_header_cell("Original"),
                        rx.table.column_header_cell("Processed"),
                        rx.table.column_header_cell(""),
                    ),
                ),
                rx.table.body(
                    rx.foreach(
                        ImagePreprocessorState.processed_files,
                        lambda f, idx: rx.table.row(
                            rx.table.cell(idx + 1),
                            rx.table.cell(
                                rx.image(
                                    src=f["preview"],
                                    width="50px",
                                    height="50px",
                                    object_fit="cover",
                                    border_radius="4px",
                                ),
                            ),
                            rx.table.cell(
                                rx.vstack(
                                    rx.text(f["name"], weight="bold", size="1"),
                                    rx.text(f["original_name"], size="1", color="gray"),
                                    align_items="start",
                                    spacing="0",
                                ),
                            ),
                            rx.table.cell(
                                rx.vstack(
                                    rx.text(f"{f['original_width']}x{f['original_height']}", size="1"),
                                    rx.text(f"{f['original_size_kb']}KB", size="1", color="gray"),
                                    align_items="start",
                                    spacing="0",
                                ),
                            ),
                            rx.table.cell(
                                rx.vstack(
                                    rx.text(f"{f['width']}x{f['height']}", size="1"),
                                    rx.badge(
                                        f"{f['size_kb']}KB",
                                        color_scheme="green",
                                        size="1",
                                    ),
                                    align_items="start",
                                    spacing="1",
                                ),
                            ),
                            rx.table.cell(
                                rx.icon_button(
                                    rx.icon("download"),
                                    on_click=lambda: ImagePreprocessorState.download_single(f["id"]),
                                    size="1",
                                    variant="ghost",
                                ),
                            ),
                        ),
                    ),
                ),
                width="100%",
            ),
            spacing="3",
            width="100%",
        ),
    )


def page() -> rx.Component:
    """Image Preprocessor Page"""
    return page_container([
        page_header(
            "🖼️ Image Preprocessor",
            "Optimize images for video generation models (resize, format conversion, compression)"
        ),

        # Project Selection
        project_selector(
            projects=ImagePreprocessorState.available_projects,
            current_project=ImagePreprocessorState.selected_project,
            on_change_callback=ImagePreprocessorState.set_selected_project,
            on_reload_callback=ImagePreprocessorState.load_projects,
            placeholder="Select Project...",
            disabled=ImagePreprocessorState.is_processing,
        ),

        # Source Files List
        source_files_list(),

        # Settings
        settings_panel(),

        # Process Button
        rx.cond(
            ImagePreprocessorState.has_sources,
            rx.hstack(
                rx.cond(
                    ImagePreprocessorState.is_processing,
                    rx.button(
                        rx.spinner(size="3"),
                        "Processing...",
                        disabled=True,
                        size="4",
                        color_scheme="blue",
                    ),
                    rx.button(
                        rx.icon("wand-sparkles", size=20),
                        "Start Processing",
                        on_click=ImagePreprocessorState.process_images,
                        size="4",
                        color_scheme="blue",
                    ),
                ),
                justify="center",
                width="100%",
                padding_y="4",
            ),
        ),

        # Processed Results
        processed_results(),

        # Info
        rx.callout(
            "💡 Images are resized based on long edge while maintaining aspect ratio. Results are saved to images/processed folder.",
            color_scheme="gray",
        ),

    ], max_width="1000px")
