"""Reflex configuration file."""
import sys
import os

# SET EXCLUSIONS BEFORE EVERYTHING
os.environ["REFLEX_HOT_RELOAD_EXCLUDE_PATHS"] = "workspace:assets:external:core:.venv:tests"

# Suppress AMD GPU warnings (set to maximum level)
os.environ["HIP_LOG_LEVEL"] = "4"  # Only fatal errors
os.environ["AMD_LOG_LEVEL"] = "4"
os.environ["ROCM_LOG_LEVEL"] = "4"
os.environ["HSA_LOG_LEVEL"] = "4"
os.environ["PAL_LOG_LEVEL"] = "4"
os.environ["PYTHONWARNINGS"] = "ignore"

# Add current directory to Python path for absolute imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import reflex as rx

config = rx.Config(
    app_name="ui",
    api_url="http://localhost:8000",
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
)

