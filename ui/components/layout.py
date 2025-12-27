"""Common Layout Components"""
import reflex as rx



def navbar() -> rx.Component:
    """Navigation Bar - Dark Mode & Premium Design"""
    
    link_style = {
        "color": "#A0A0A0",
        "text_decoration": "none",
        "_hover": {"color": "white", "text_decoration": "none"},
        "transition": "color 0.2s ease",
        "font_weight": "medium",
        "size": "2",
    }
    
    return rx.box(
        rx.hstack(
            # Logo Section
            rx.link(
                rx.hstack(
                    rx.icon("clapperboard", color="white", size=20),
                    rx.heading("Video Pipeline", size="4", color="white", letter_spacing="-0.5px"),
                    align_items="center",
                    spacing="3",
                ),
                href="/",
                underline="none"
            ),
            
            rx.spacer(),
            
            # Application Links
            rx.hstack(
                rx.link(rx.text("📺 Extract", **link_style), href="/extract", underline="none"),
                rx.link(rx.text("📝 Review", **link_style), href="/review", underline="none"),
                rx.link(rx.text("🎬 Scenario", **link_style), href="/scenario", underline="none"),
                rx.link(rx.text("🎙️ Audio", **link_style), href="/audio", underline="none"),
                rx.link(rx.text("📝 Subtitle", **link_style), href="/subtitle", underline="none"),
                rx.link(rx.text("🎥 Project", **link_style), href="/project", underline="none"),
                spacing="6",
            ),
            
            rx.spacer(),

            align_items="center",
            width="100%",
            max_width="100%",
            padding="20px"
        ),
        # Glassmorphism container style
        border_bottom="1px solid rgba(255, 255, 255, 0.08)",
        width="100%",
        background_color="rgba(18, 18, 18, 0.8)",
        backdrop_filter="blur(16px)",
        position="sticky",
        top="0",
        z_index="999",
        box_shadow="0 4px 30px rgba(0, 0, 0, 0.1)",
    )


def page_container(children: list, max_width: str = "1400px") -> rx.Component:
    """
    Standard page container with consistent spacing.
    
    Args:
        children: Child components
        max_width: Maximum container width
        
    Returns:
        Container component
    """
    return rx.box(
        navbar(),
        rx.container(
            rx.vstack(
                *children,
                spacing="5",
                # Ensure vstack fills container
                width="100%", 
            ),
            # Container Styling
            max_width=max_width,
            width="100%",
            padding_x="4",
            padding_y="6",
            margin_x="auto", # Explicit centering
        ),
        width="100%",
        min_height="100vh",
    )


def page_header(title: str, subtitle: str = "") -> rx.Component:
    """
    Standard page header with title and optional subtitle.
    
    Args:
        title: Page title
        subtitle: Optional subtitle text
        
    Returns:
        Header component
    """
    components = [
        rx.heading(title, size="8"),
        rx.divider(),
    ]
    
    if subtitle:
        components.insert(1, rx.text(subtitle, color_scheme="gray", size="3"))
    
    return rx.vstack(*components, spacing="3", width="100%")
