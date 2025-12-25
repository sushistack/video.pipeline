import streamlit as st
import sys
from pathlib import Path
import importlib
import warnings

# Suppress Google API Core version warning
warnings.filterwarnings("ignore", message=".*Python version.*google.api_core.*", category=FutureWarning)

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_ROOT = BASE_DIR / "outputs"
VIDEO_INPUT_DIR = BASE_DIR / "materials/videos"

# Add Root to Path (for worker module)
sys.path.append(str(BASE_DIR))

# Add src/ui to Path (for components)
sys.path.append(str(Path(__file__).parent))

# Component Imports
# We use local imports assuming they are in src/ui/components
from components import extract_tab, review_tab, scenario_tab, audio_tab, subtitle_tab

# Force reload to avoid caching issues
importlib.reload(extract_tab)
importlib.reload(review_tab)
importlib.reload(scenario_tab)
importlib.reload(audio_tab)
importlib.reload(subtitle_tab)

from components.extract_tab import render_extract_tab
from components.review_tab import render_review_tab
from components.scenario_tab import render_scenario_tab
from components.audio_tab import render_audio_tab
from components.subtitle_tab import render_subtitle_tab

# Page Config
st.set_page_config(layout="wide", page_title="Video Pipeline")
st.title("🎞️ Video Pipeline Dashboard")

# Ensure Output Dir
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

# Tabs
t0, t1, t2, t3, t4 = st.tabs(["📺 Extract SRT", "📝 Story Review", "🎬 Scenario Gen", "🎙️ Audio Gen", "📝 Subtitle Gen"])

with t0:
    render_extract_tab(VIDEO_INPUT_DIR, OUTPUT_ROOT)

with t1:
    render_review_tab(OUTPUT_ROOT)

with t2:
    render_scenario_tab(OUTPUT_ROOT, BASE_DIR)

with t3:
    render_audio_tab(OUTPUT_ROOT, BASE_DIR)

with t4:
    render_subtitle_tab(OUTPUT_ROOT)
