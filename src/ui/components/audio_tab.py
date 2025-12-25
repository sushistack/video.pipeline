import streamlit as st

import json
import yaml
import sys
import re
import logging
import threading
import time
import queue
from pathlib import Path
from datetime import datetime
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
from worker.gpt_sovits_adapter import GPTSoVITSAdapter

logger = logging.getLogger("AudioTab")
logger.setLevel(logging.INFO)

def resolve_speaker_config(spk_tag: str, spk_map: dict, base_dir: Path, speakers_cfg: dict):
    """
    Resolves the reference audio path, text, and language for a given speaker tag.
    Returns: (ref_audio_path, ref_text, ref_lang)
    """
    # 1. Resolve Voice Config from Map
    map_data = {}
    
    # Try exact match first
    if spk_tag in spk_map:
        map_data = spk_map[spk_tag]
    else:
        # Try normalized match
        norm_tag = spk_tag.lower().replace(" ", "")
        for k, v in spk_map.items():
            if k.lower().replace(" ", "") == norm_tag:
                map_data = v
                break
                
    map_lang = map_data.get("lang")
    map_file = map_data.get("file")
    
    voice_key = None
    ref_audio_path = None
    
    # Case A: Map exists and valid
    if map_lang and map_file:
        possible_path = base_dir / "materials/audios/inputs" / map_lang / map_file
        if possible_path.exists():
            ref_audio_path = possible_path
            voice_key = possible_path.stem
    
    # Case B: Fallback (Map missing or invalid)
    if not ref_audio_path:
        # Default to sato-aoi
        voice_key = "sato-aoi"
        def_lang = speakers_cfg.get(voice_key, {}).get("ref_lang", "ja")
        def_type = speakers_cfg.get(voice_key, {}).get("audio_type", "wav")
        
        fallback_path = base_dir / "materials/audios/inputs" / def_lang / f"{voice_key}.{def_type}"
        if fallback_path.exists():
                ref_audio_path = fallback_path
        else:
                # Final safety: Find any wav in 'ja'
                scan_dir = base_dir / "materials/audios/inputs/ja"
                if scan_dir.exists():
                    fs = list(scan_dir.glob("*.wav"))
                    if fs:
                        ref_audio_path = fs[0]
                        voice_key = ref_audio_path.stem
    
    if not ref_audio_path:
        return None, "", "ja"

    # 2. Config Lookup for Ref Text
    ref_text = speakers_cfg.get(voice_key, {}).get("ref_text", "")
    ref_lang = speakers_cfg.get(voice_key, {}).get("ref_lang", "ja")
    
    return ref_audio_path, ref_text, ref_lang

# --- Helper Functions (Module Level) ---

def update_log_container(container, logs):
    """
    Renders the list of log messages into the Streamlit container 
    using a reversed flex-direction for auto-scrolling to bottom.
    """
    if not container: return
    
    # Construct CSS-based HTML
    rev_logs = logs[::-1]
    
    def escape_html(text):
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    inner_html = "\n".join([f"<div>{escape_html(l)}</div>" for l in rev_logs])
    
    container_id = "process_log_container"
    log_html = f"""
    <div id="{container_id}" style="
        height: 400px; 
        overflow-y: auto; 
        display: flex; 
        flex-direction: column-reverse;
        background-color: #0e1117; 
        color: #fafafa; 
        padding: 1rem; 
        border: 1px solid #31333f; 
        border-radius: 0.5rem; 
        font-family: 'Source Code Pro', monospace; 
        font-size: 14px; 
        line-height: 1.5;">
{inner_html}
    </div>
    """
    container.markdown(log_html, unsafe_allow_html=True)


def run_generation_sync(base_dir, selected_project, target_langs, gpt_path, sovits_path, speed_factor, speakers_cfg, log_container, prog_bar):
    """
    Synchronous generation worker.
    Updates UI directly via Streamlit placeholders (log_container, prog_bar).
    """
    # Init State
    st.session_state["audio_logs"] = []
    
    def log(msg):
        # Handle Progress Signals (explicit - kept just in case)
        if msg.startswith("PROGRESS:"):
            return

        # Normal Logs
        ts = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{ts}] {msg}"
        print(formatted_msg, flush=True) # Console Log
        
        # Smart Text Handling (for tqdm flicker reduction)
        is_progress = "it/s]" in msg or "%|" in msg
        logs = st.session_state["audio_logs"]
        
        if is_progress and logs:
             last_line = logs[-1]
             if "it/s]" in last_line or "%|" in last_line:
                 logs[-1] = formatted_msg
             else:
                 logs.append(formatted_msg)
        else:
             logs.append(formatted_msg)
        
        # Update UI Immediately
        update_log_container(log_container, logs)

    try:
        log("Initializing TTS Engine...")
        try:
             tts_engine = GPTSoVITSAdapter(base_dir=base_dir, python_exec=sys.executable)
        except Exception as e:
             log(f"Failed to init TTS: {e}")
             return

        gen_count = 0
        
        log("=============== Params (Global) ==================")
        log(f"GPT: {gpt_path}")
        log(f"SoVITS: {sovits_path}")
        log(f"speed_factor: {speed_factor}")
        log("=========================================")

        # --- Pre-calculate Total Tasks for Progress Bar ---
        total_tasks = 0
        task_list = [] # List of (lang, index, match_tuple)
        
        for lang in target_langs:
            xml_path = selected_project / f"senario-{lang}.xml"
            if not xml_path.exists(): continue
            try:
                content = xml_path.read_text(encoding="utf-8")
                pattern = re.compile(r"<([^>]+)>(.*?)</\1>")
                matches = pattern.findall(content)
                if matches:
                    total_tasks += len(matches)
                    task_list.append((lang, matches, xml_path))
            except: pass
            
        current_progress = 0
        
        # Initialize Progress Bar
        if total_tasks > 0:
             prog_bar.progress(0.0, text=f"Starting... 0% (0/{total_tasks})")
        else:
             prog_bar.progress(0.0, text="No tasks found.")

        for (lang, matches, xml_path) in task_list:
            if st.session_state.get("audio_gen_stop", False): break
            
            # Load Map
            map_path = selected_project / f"speaker_map-{lang}.json"
            spk_map = {}
            if map_path.exists():
                try: spk_map = json.load(open(map_path))
                except: pass
            
            # --- Speaker Config Summary ---
            speaker_cache = {}
            unique_speakers = sorted(list(set(m[0] for m in matches)))
            
            log(f"")
            log(f"--- Speaker Config Summary [{lang}] ---")
            for sp in unique_speakers:
                r_audio, r_text, r_lang = resolve_speaker_config(sp, spk_map, base_dir, speakers_cfg)
                speaker_cache[sp] = (r_audio, r_text, r_lang)
                status = "OK" if r_audio else "MISSING"
                audio_name = r_audio.name if r_audio else "None"
                disp_text = r_text[:30] + "..." if len(r_text) > 30 else r_text
                log(f"Speaker '{sp}': Audio={audio_name} [{status}], Text={disp_text}, Lang={r_lang}")
            log("------------------------------")
            log(f"")

            out_audio_dir = selected_project / "audios" / lang
            out_audio_dir.mkdir(parents=True, exist_ok=True)

            for i, (spk_tag, text) in enumerate(matches):
                if st.session_state.get("audio_gen_stop", False):
                    break

                text = text.strip()
                if not text: 
                    current_progress += 1
                    continue
                
                ref_audio_path, ref_text, ref_lang = speaker_cache.get(spk_tag, (None, "", "ja"))
                
                if not ref_audio_path:
                    log(f"Skipping {spk_tag}: Ref Audio unavailable.")
                    current_progress += 1
                    continue
                
                out_wav = out_audio_dir / f"{i:03d}_{spk_tag}.mp3"
                
                if out_wav.exists(): out_wav.unlink()

                log(f"Generating {i+1}/{len(matches)} [{lang}]: {spk_tag}...")
                
                try:
                    tts_engine.generate_voice(
                           gpt_model_path=Path(gpt_path),
                           sovits_model_path=Path(sovits_path),
                           ref_audio_path=Path(ref_audio_path),
                           ref_text=ref_text,
                           ref_language=ref_lang,
                           target_text=text,
                           target_language=lang,
                           output_path=out_wav,
                           speed_factor=speed_factor,
                           callback=log
                    )
                    gen_count += 1
                except Exception as e:
                     log(f"Error {lang}/{spk_tag}: {e}")
                
                # Update Progress (Count Based)
                current_progress += 1
                if total_tasks > 0:
                    p_val = min(current_progress / total_tasks, 1.0)
                    prog_bar.progress(p_val, text=f"Processing... {int(p_val*100)}% ({current_progress}/{total_tasks})")
        
        if st.session_state.get("audio_gen_stop", False):
             log("🛑 Stopped.")
        else:
             log(f"🎉 Completed! Generated {gen_count} audio files.")
             prog_bar.progress(1.0, text="Completed!")
             
    except Exception as e:
        log(f"Critical Error: {e}")
        import traceback
        traceback.print_exc()



def render_audio_tab(output_root: Path, base_dir: Path):
    st.header("🎙️ Text-to-Speech Generation")

    # Init State
    if "audio_generating" not in st.session_state:
        st.session_state["audio_generating"] = False
        
    is_generating = st.session_state["audio_generating"]

    # File Selection
    all_projects = []
    if output_root.exists():
        for proj_dir in output_root.iterdir():
            if proj_dir.is_dir():
                has_any_sc = any(proj_dir.glob("senario-*.xml"))
                if has_any_sc:
                    all_projects.append(proj_dir)
    
    all_projects = sorted(all_projects, key=lambda p: p.name)
    
    if not all_projects:
        st.info("No projects with 'senario-*.xml' found. Please generate a scenario first.")
        return

    # Default logic
    if "selected_audio_project" not in st.session_state:
         if all_projects:
              latest = max(all_projects, key=lambda p: (p / "subtitles" / "ja.srt").stat().st_mtime if (p / "subtitles" / "ja.srt").exists() else p.stat().st_mtime)
              st.session_state["selected_audio_project"] = latest
    
    # Sync from Tab 0
    current_video = st.session_state.get("current_project_file")
    if current_video:
         matches = [p for p in all_projects if p.name == current_video.stem]
         if matches:
              st.session_state["selected_audio_project"] = matches[0]

    def on_audio_project_change():
        st.session_state["selected_audio_project"] = st.session_state["project_selector_audio"]
    
    try:
        current_index_audio = all_projects.index(st.session_state["selected_audio_project"])
    except ValueError:
        current_index_audio = 0
        st.session_state["selected_audio_project"] = all_projects[0]

    selected_project = st.selectbox(
        "📁 Select Project", 
        all_projects, 
        format_func=lambda x: x.name,
        index=current_index_audio,
        key="project_selector_audio",
        on_change=on_audio_project_change,
        disabled=is_generating
    )
    
    if selected_project and selected_project.exists():
        st.caption(f"Generating Audio for: **{selected_project.name}**")
        
        # 1. Configuration 
        st.subheader("⚙️ Configuration")
        cfg_col1, cfg_col2 = st.columns(2)
        
        with cfg_col1:
            st.caption("Model Version")
            model_version = st.selectbox(
                "Select Version", 
                ["V4", "V2Pro", "V2ProPlus"], 
                index=0, 
                label_visibility="collapsed", 
                key="model_ver_sel",
                disabled=is_generating
            )
            
            # Consolidated Paths
            models_root = base_dir / "models/pretrained"

            if model_version == "V4":
                gpt_path = models_root / "s1v3.ckpt" 
                sovits_path = models_root / "gsv-v4-pretrained/s2Gv4.pth"
            elif model_version == "V2Pro":
                gpt_path = models_root / "s1v3.ckpt" 
                sovits_path = models_root / "v2Pro/s2Gv2Pro.pth"
            elif model_version == "V2ProPlus":
                gpt_path = models_root / "s1v3.ckpt" 
                sovits_path = models_root / "v2Pro/s2Gv2ProPlus.pth"
            
            g_ok = "✅" if gpt_path.exists() else "❌"
            s_ok = "✅" if sovits_path.exists() else "❌"
            
            st.caption(f"{g_ok} GPT: ...{gpt_path.name[-15:]} | {s_ok} SoVITS: ...{sovits_path.name[-15:]}")

        with cfg_col2:
            st.caption("Target Languages")
            c_l1, c_l2, c_l3 = st.columns(3)
            with c_l1: gen_en = st.checkbox("English", value=False, key="aud_en", disabled=is_generating)
            with c_l2: gen_ko = st.checkbox("Korean", value=False, key="aud_ko", disabled=is_generating)
            with c_l3: gen_ja = st.checkbox("Japanese", value=True, key="aud_ja", disabled=is_generating)

            st.caption("Speech Speed")
            speed_factor = st.slider("Speed Factor", 0.5, 2.0, 1.1, 0.1, key="aud_speed", disabled=is_generating)

        target_langs = []
        if gen_en: target_langs.append("en")
        if gen_ko: target_langs.append("ko")
        if gen_ja: target_langs.append("ja")

        st.divider()

        # 2. Controls
        c_gen, _ = st.columns([1, 2])
        gen_placeholder = c_gen.empty()
        
        # Handler for Start Button
        def on_start_click():
            st.session_state["audio_generating"] = True
            
        if not is_generating:
            with gen_placeholder:
                 st.button("🎙️ Generate Audio Tracks", type="primary", 
                           disabled=not target_langs, 
                           use_container_width=True,
                           on_click=on_start_click)
        else:
             # Show Running State
             with gen_placeholder:
                 st.button("🚫 Generating... (Please Wait)", type="secondary", disabled=True, use_container_width=True)

        # Progress Bar Placeholder
        prog_bar = st.progress(0.0, text="")
        
        st.divider()

        # 3. Log Area
        st.markdown("### Process Logs")
        log_container = st.empty()
        
        # Restore logs if they exist
        if "audio_logs" in st.session_state and st.session_state["audio_logs"]:
            update_log_container(log_container, st.session_state["audio_logs"])
        
        # Load Config
        try:
            config_path = base_dir / "config.yaml"
            if config_path.exists():
               try:
                    app_config = yaml.safe_load(config_path.read_text())
                    speakers_cfg = app_config.get("speakers", {})
               except: speakers_cfg = {}
            else:
                speakers_cfg = {}
        except: speakers_cfg = {}

        # Execution Logic
        if is_generating:
            # We run the logic, then reset the flag
            run_generation_sync(
                base_dir, selected_project, target_langs, gpt_path, sovits_path, 
                speed_factor, speakers_cfg, log_container, prog_bar
            )
            
            # Finished
            time.sleep(1)
            st.session_state["audio_generating"] = False
            st.rerun()
