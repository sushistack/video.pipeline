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
    
    def nav_link(text: str, url: str) -> rx.Component:
        is_active = rx.State.router.page.path == url
        return rx.link(
            rx.text(text, **link_style),
            href=url,
            underline="none",
            border_bottom=rx.cond(is_active, "2px solid var(--blue-9)", "2px solid transparent"),
            padding_bottom="2px",
            color=rx.cond(is_active, "white", "#A0A0A0"),
        )

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
            
            # Application Links - Absolutely Centered
            rx.hstack(
                nav_link("📺 Extract", "/extract"),
                nav_link("📝 Review", "/review"),
                nav_link("🎬 Scenario", "/scenario"),
                nav_link("🎙️ Audio", "/audio"),
                nav_link("📝 Subtitle", "/subtitle"),
                nav_link("🎥 Project", "/project"),
                spacing="6",
                position="absolute",
                left="50%",
                transform="translateX(-50%)",
            ),
            
            align_items="center",
            width="100%",
            max_width="100%",
            padding="20px",
            position="relative", # For absolute child
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


def footer() -> rx.Component:
    """Global Footer - Balanced Design"""
    
    def footer_heading(text: str):
        return rx.text(text, weight="bold", color="white", size="3", margin_bottom="2")
        
    def footer_link(text: str, url: str):
        return rx.link(
            text, 
            href=url, 
            color="var(--gray-9)", 
            size="2", 
            underline="none",
            _hover={"color": "white", "text_decoration": "underline"}
        )

    return rx.box(
        rx.container(
            rx.vstack(
                # Main Footer Content (Grid)
                rx.grid(
                    # Col 1: Brand
                    rx.vstack(
                        rx.hstack(
                            rx.icon("clapperboard", size=24, color="white"),
                            rx.heading("Video Pipeline", size="5", color="white", letter_spacing="-0.5px"),
                            align_items="center",
                            spacing="3",
                            margin_bottom="2"
                        ),
                        rx.text(
                            "Next-gen AI video automation platform.",
                            color="var(--gray-8)",
                            size="2",
                        ),
                        rx.hstack(
                            rx.icon_button(rx.icon("github"), variant="ghost", color_scheme="gray", size="2"),
                            rx.icon_button(rx.icon("twitter"), variant="ghost", color_scheme="gray", size="2"),
                            spacing="2",
                            margin_top="4"
                        ),
                        align_items="start",
                    ),
                    
                    # Col 2: Navigation
                    rx.vstack(
                        footer_heading("Platform"),
                        footer_link("Feature Extraction", "/extract"),
                        footer_link("Subtitle Review", "/review"),
                        footer_link("Scenario Editor", "/scenario"),
                        footer_link("Audio Generation", "/audio"),
                        align_items="start",
                        spacing="2",
                    ),

                    # Col 3: Tech & Info
                    rx.vstack(
                        footer_heading("Powered By"),
                        rx.hstack(
                             rx.badge("Reflex", color_scheme="violet", variant="soft", size="2"),
                             rx.badge("GPT-SoVITS", color_scheme="blue", variant="soft", size="2"),
                             spacing="2",
                        ),
                        rx.text("Version 1.2.0-beta", size="1", color="var(--gray-8)", margin_top="2"),
                        align_items="start",
                        spacing="2",
                    ),
                    
                    columns="3",
                    spacing="8",
                    width="100%",
                ),
                
                rx.spacer(),
                rx.divider(color_scheme="gray", opacity="0.2"),
                
                # Bottom Bar
                rx.hstack(
                    rx.text("© 2024 Video Pipeline Inc.", size="1", color="var(--gray-8)"),
                    rx.spacer(),
                    rx.hstack(
                        footer_link("Privacy", "#"),
                        footer_link("Terms", "#"),
                        spacing="4",
                    ),
                    width="100%",
                    padding_top="4",
                ),
                
                height="100%",
                width="100%",
                padding_y="40px", 
                justify="between",
            ),
            max_width="1400px",
            height="100%",
        ),
        width="100%",
        height="300px",
        background="linear-gradient(180deg, #111113 0%, #0A0A0C 100%)",
        border_top="1px solid rgba(255, 255, 255, 0.05)",
        margin_top="auto",
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
    return rx.vstack(
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
            flex="1", # Allow content to grow
        ),
        footer(),
        width="100%",
        min_height="100vh",
        spacing="0",
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
