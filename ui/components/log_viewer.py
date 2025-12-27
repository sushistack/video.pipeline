"""Log Viewer Component"""
import reflex as rx


def log_viewer(logs: list[str]) -> rx.Component:
    """
    Display logs with auto-scroll to bottom (Console mirror).
    Always visible, even when empty. Full width with 200px height.
    Auto-scrolls to show latest logs.
    
    Args:
        logs: List of log messages
        
    Returns:
        Log display component with console-style formatting
    """
    return rx.box(
        rx.cond(
            logs.length() > 0,
            # Show logs with auto-scroll (reversed flex direction)
            rx.box(
                rx.vstack(
                    rx.foreach(
                        logs,
                        lambda log: rx.text(
                            log,
                            font_family="'Fira Code', 'Courier New', monospace",
                            size="2",
                            white_space="pre", # No wrapping
                            color=rx.cond(
                                log.contains("ERROR") | log.contains("❌"),
                                "red",
                                rx.cond(
                                    log.contains("✅") | log.contains("🎉"),
                                    "green",
                                    rx.cond(
                                        log.contains("⚠️") | log.contains("🛑"),
                                        "orange",
                                        "gray"
                                    )
                                ),
                            ),
                        ),
                    ),
                    spacing="1",
                    align="start",
                    width="100%",
                ),
                display="flex",
                flex_direction="column-reverse",  # Auto-scroll to bottom
                height="100%",
                overflow_y="auto",
                overflow_x="auto",  # Enable horizontal scroll
                width="100%",
            ),
            # Empty state
            rx.text(
                "No logs yet. Start extraction to see console output here.",
                color="gray",
                size="2",
                font_style="italic",
            ),
        ),
        height="200px",
        overflow_y="auto",
        width="100%",
        padding="1em",
        background_color="#0a0a0a",
        border_radius="8px",
        border="1px solid #333",
    )
