"""Scene Change Detector Page - Detect angle changes in multi-angle videos"""
import reflex as rx
import sys
from pathlib import Path

UI_DIR = Path(__file__).parent.parent
if str(UI_DIR) not in sys.path:
    sys.path.insert(0, str(UI_DIR))

from states.scene_detector_state import SceneDetectorState
from components.layout import page_container, page_header
from components.file_selector import project_selector


def video_selector() -> rx.Component:
    """Video file selector from workspace"""
    return rx.vstack(
        rx.hstack(
            rx.heading("🎬 Select Video", size="4"),
            rx.spacer(),
            rx.button(
                rx.icon("refresh-cw", size=14),
                "Refresh",
                on_click=SceneDetectorState.load_video_files,
                size="1",
                variant="ghost",
                disabled=SceneDetectorState.is_detecting,
            ),
            align="center",
            width="100%",
        ),
        rx.text(
            SceneDetectorState.source_dir_path,
            size="1",
            color="gray",
            font_family="monospace",
        ),
        rx.cond(
            SceneDetectorState.has_video_files,
            rx.vstack(
                rx.select(
                    SceneDetectorState.video_names,
                    placeholder="Select video file...",
                    value=SceneDetectorState.selected_video,
                    on_change=SceneDetectorState.set_selected_video,
                    width="100%",
                    disabled=SceneDetectorState.is_detecting,
                ),
                rx.cond(
                    SceneDetectorState.has_video_selected,
                    rx.card(
                        rx.hstack(
                            rx.icon("film", size=24, color="var(--blue-9)"),
                            rx.vstack(
                                rx.text(SceneDetectorState.selected_video, weight="bold"),
                                rx.text(SceneDetectorState.video_info_str, size="1", color="gray"),
                                align_items="start",
                                spacing="1",
                            ),
                            align="center",
                            width="100%",
                        ),
                        width="100%",
                    ),
                ),
                spacing="3",
                width="100%",
            ),
            rx.callout(
                f"Place video files in {SceneDetectorState.source_dir_path} folder.",
                icon="info",
                color_scheme="blue",
            ),
        ),
        spacing="3",
        width="100%",
    )


def detection_settings() -> rx.Component:
    """Detection settings panel"""
    return rx.card(
        rx.vstack(
            rx.heading("⚙️ Detection Settings", size="4"),
            rx.grid(
                # Threshold
                rx.vstack(
                    rx.hstack(
                        rx.text("Sensitivity (Threshold)", weight="bold", size="2"),
                        rx.badge(
                            SceneDetectorState.threshold,
                            color_scheme="blue",
                        ),
                    ),
                    rx.slider(
                        value=[SceneDetectorState.threshold],
                        min=10,
                        max=80,
                        step=1,
                        on_change=SceneDetectorState.set_threshold,
                        width="100%",
                        disabled=SceneDetectorState.is_detecting,
                    ),
                    rx.text("Lower = more sensitive (detects more cuts)", size="1", color="gray"),
                    align_items="start",
                    width="100%",
                ),
                # Algorithm
                rx.vstack(
                    rx.text("Detection Algorithm", weight="bold", size="2"),
                    rx.select(
                        SceneDetectorState.algorithm_options,
                        value=SceneDetectorState.algorithm,
                        on_change=SceneDetectorState.set_algorithm,
                        width="100%",
                        disabled=SceneDetectorState.is_detecting,
                    ),
                    rx.text(
                        rx.match(
                            SceneDetectorState.algorithm,
                            ("content", "Frame content change (recommended)"),
                            ("threshold", "Brightness threshold based"),
                            ("adaptive", "Adaptive detection"),
                            "Frame content change",
                        ),
                        size="1",
                        color="gray"
                    ),
                    align_items="start",
                    width="100%",
                ),
                columns="2",
                spacing="5",
                width="100%",
            ),
            rx.divider(),
            rx.text("Output Settings", weight="bold", size="3"),
            rx.grid(
                # Output format
                rx.vstack(
                    rx.text("Output Format", weight="bold", size="2"),
                    rx.select(
                        SceneDetectorState.format_options,
                        value=SceneDetectorState.output_format,
                        on_change=SceneDetectorState.set_output_format,
                        width="100%",
                    ),
                    align_items="start",
                    width="100%",
                ),
                # Quality
                rx.vstack(
                    rx.hstack(
                        rx.text("JPG Quality", weight="bold", size="2"),
                        rx.badge(
                            SceneDetectorState.output_quality,
                            color_scheme=rx.cond(
                                SceneDetectorState.quality_disabled,
                                "gray",
                                "blue"
                            ),
                        ),
                    ),
                    rx.slider(
                        value=[SceneDetectorState.output_quality],
                        min=50,
                        max=100,
                        step=5,
                        on_change=SceneDetectorState.set_output_quality,
                        width="100%",
                        disabled=SceneDetectorState.quality_disabled,
                    ),
                    rx.text(
                        rx.cond(
                            SceneDetectorState.quality_disabled,
                            "PNG is lossless",
                            "Higher = better quality"
                        ),
                        size="1",
                        color="gray"
                    ),
                    align_items="start",
                    width="100%",
                ),
                columns="2",
                spacing="5",
                width="100%",
            ),
            spacing="4",
            width="100%",
            align_items="start",
        ),
        width="100%",
    )


def detection_button() -> rx.Component:
    """Detection start button with progress"""
    return rx.cond(
        SceneDetectorState.has_video_selected,
        rx.vstack(
            rx.cond(
                SceneDetectorState.is_detecting,
                rx.vstack(
                    rx.hstack(
                        rx.spinner(size="3"),
                        rx.text(SceneDetectorState.progress_text, weight="medium"),
                        align="center",
                        spacing="3",
                    ),
                    rx.progress(
                        value=SceneDetectorState.detection_progress,
                        width="100%",
                        max_width="400px",
                    ),
                    align="center",
                    spacing="3",
                    width="100%",
                ),
                rx.button(
                    rx.icon("scan-search", size=20),
                    "Start Scene Detection",
                    on_click=SceneDetectorState.detect_scenes,
                    size="4",
                    color_scheme="blue",
                ),
            ),
            align="center",
            width="100%",
            padding_y="4",
        ),
    )


def results_section() -> rx.Component:
    """Detection results section"""
    return rx.cond(
        SceneDetectorState.has_results,
        rx.vstack(
            # Header
            rx.hstack(
                rx.heading("✅ Results", size="4"),
                rx.badge(
                    f"{SceneDetectorState.scene_count} cuts",
                    color_scheme="green",
                ),
                rx.spacer(),
                rx.text(
                    SceneDetectorState.output_dir_path,
                    size="1",
                    color="gray",
                    font_family="monospace",
                ),
                rx.hstack(
                    rx.button(
                        "Select All",
                        on_click=SceneDetectorState.select_all_scenes,
                        size="1",
                        variant="ghost",
                    ),
                    rx.button(
                        "Deselect All",
                        on_click=SceneDetectorState.deselect_all_scenes,
                        size="1",
                        variant="ghost",
                    ),
                    rx.button(
                        rx.icon("download", size=16),
                        f"ZIP ({SceneDetectorState.selected_count})",
                        on_click=SceneDetectorState.download_selected_zip,
                        color_scheme="blue",
                        size="2",
                        disabled=~SceneDetectorState.has_selection,
                    ),
                    spacing="2",
                ),
                align="center",
                width="100%",
            ),

            # Results table
            rx.scroll_area(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Select", width="50px"),
                            rx.table.column_header_cell("#"),
                            rx.table.column_header_cell("Time"),
                            rx.table.column_header_cell("Frame"),
                            rx.table.column_header_cell("Preview"),
                            rx.table.column_header_cell("Filename"),
                            rx.table.column_header_cell(""),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            SceneDetectorState.detected_scenes,
                            lambda scene: rx.table.row(
                                rx.table.cell(
                                    rx.checkbox(
                                        checked=SceneDetectorState.selected_scenes.contains(scene["id"]),
                                        on_change=lambda _: SceneDetectorState.toggle_scene_selection(scene["id"]),
                                    ),
                                ),
                                rx.table.cell(
                                    rx.text(scene["index"], weight="bold"),
                                ),
                                rx.table.cell(
                                    rx.badge(
                                        scene["timestamp_str"],
                                        color_scheme="blue",
                                        variant="soft",
                                    ),
                                ),
                                rx.table.cell(
                                    rx.text(scene["frame_number"], size="2", color="gray"),
                                ),
                                rx.table.cell(
                                    rx.image(
                                        src=scene["preview"],
                                        width="120px",
                                        height="68px",
                                        object_fit="cover",
                                        border_radius="4px",
                                    ),
                                ),
                                rx.table.cell(
                                    rx.text(scene["filename"], size="1", color="gray"),
                                ),
                                rx.table.cell(
                                    rx.icon_button(
                                        rx.icon("download"),
                                        on_click=lambda: SceneDetectorState.download_single(scene["id"]),
                                        size="1",
                                        variant="ghost",
                                    ),
                                ),
                            ),
                        ),
                    ),
                    width="100%",
                ),
                type="auto",
                scrollbars="vertical",
                style={"maxHeight": "500px"},
            ),

            spacing="4",
            width="100%",
        ),
    )


def page() -> rx.Component:
    """Scene Change Detector Page"""
    return page_container([
        page_header(
            "🎬 Scene Change Detector",
            "Automatically detect camera angle changes in multi-angle videos and extract keyframes"
        ),

        # Project Selection
        project_selector(
            projects=SceneDetectorState.available_projects,
            current_project=SceneDetectorState.selected_project,
            on_change_callback=SceneDetectorState.set_selected_project,
            on_reload_callback=SceneDetectorState.load_projects,
            placeholder="Select Project...",
            disabled=SceneDetectorState.is_detecting,
        ),

        # Video Selector
        video_selector(),

        # Settings
        detection_settings(),

        # Detection Button
        detection_button(),

        # Results
        results_section(),

        # Info
        rx.callout(
            "💡 Uses PySceneDetect to analyze frame content changes. Results are saved to images/detected-cuts folder.",
            color_scheme="gray",
        ),

    ], max_width="1000px")
