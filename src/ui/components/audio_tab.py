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

def generation_worker(base_dir, selected_project, target_langs, gpt_path, sovits_path, speed_factor, speakers_cfg, _ignored_map, log_list):
    """Background worker for audio generation"""
    
    def log(msg):
        logger.info(msg)
        ts = datetime.now().strftime("%H:%M:%S")
        log_list.append(f"[{ts}] {msg}")

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

        for idx, lang in enumerate(target_langs):
            if st.session_state.get("audio_gen_stop", False):
                break

            xml_path = selected_project / f"senario-{lang}.xml"
            map_path = selected_project / f"speaker_map-{lang}.json"
            out_audio_dir = selected_project / "audios" / lang
            out_audio_dir.mkdir(parents=True, exist_ok=True)
            
            if not xml_path.exists():
                continue

            # Load Map
            spk_map = {}
            if map_path.exists():
                try: spk_map = json.load(open(map_path))
                except: pass

            try:
                content = xml_path.read_text(encoding="utf-8")
                pattern = re.compile(r"<([^>]+)>(.*?)</\1>")
                matches = pattern.findall(content)
            except: matches = []
            
            if not matches:
                log(f"No matches found in {xml_path.name}")
                continue
            
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
                # Truncate long text
                disp_text = r_text[:30] + "..." if len(r_text) > 30 else r_text
                log(f"Speaker '{sp}': Audio={audio_name} [{status}], Text={disp_text}, Lang={r_lang}")
            log("------------------------------")
            log(f"")

            for i, (spk_tag, text) in enumerate(matches):
                if st.session_state.get("audio_gen_stop", False):
                    break

                text = text.strip()
                if not text: continue
                
                ref_audio_path, ref_text, ref_lang = speaker_cache.get(spk_tag, (None, "", "ja"))
                
                if not ref_audio_path:
                    log(f"Skipping {spk_tag}: Ref Audio unavailable.")
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
                           callback=lambda msg: log_list.append(msg)
                    )
                    gen_count += 1
                except Exception as e:
                     log(f"Error {lang}/{spk_tag}: {e}")
        
        if st.session_state.get("audio_gen_stop", False):
             log("🛑 Stopped.")
        else:
             log(f"🎉 Completed! Generated {gen_count} audio files.")
             
    except Exception as e:
        log(f"Critical Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        st.session_state["audio_gen_running"] = False
        st.session_state["audio_gen_stop"] = False


def render_audio_tab(output_root: Path, base_dir: Path):
    st.header("🎙️ Text-to-Speech Generation")

    # Init Session State
    if "audio_gen_running" not in st.session_state: st.session_state["audio_gen_running"] = False
    if "audio_gen_stop" not in st.session_state: st.session_state["audio_gen_stop"] = False
    if "audio_logs" not in st.session_state: st.session_state["audio_logs"] = []

    is_running = st.session_state["audio_gen_running"]
    
    # File Selection (Same Logic)
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

    # Default latest logic
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
    
    # Selection from session state
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
        disabled=is_running # Disabled when running
    )
    
    if selected_project and selected_project.exists():
        st.caption(f"Generating Audio for: **{selected_project.name}**")
        
        # 1. Configuration (Model & Target)
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
                disabled=is_running
            )
            
            # Consolidated Paths
            models_root = base_dir / "models/pretrained"

            if model_version == "V4":
                # V4 uses s1v3 (GPT) + s2Gv4 (SoVITS)
                gpt_path = models_root / "s1v3.ckpt" 
                sovits_path = models_root / "gsv-v4-pretrained/s2Gv4.pth"
            elif model_version == "V2Pro":
                # V2 models consolidated in 'v2' and 'v2Pro'
                gpt_path = models_root / "s1v3.ckpt" 
                sovits_path = models_root / "v2Pro/s2Gv2Pro.pth"
            elif model_version == "V2ProPlus":
                gpt_path = models_root / "s1v3.ckpt" 
                sovits_path = models_root / "v2Pro/s2Gv2ProPlus.pth"
            
            g_ok = "✅" if gpt_path.exists() else "❌"
            s_ok = "✅" if sovits_path.exists() else "❌"
            
            # Show truncated names
            g_name = gpt_path.name[-15:] if len(gpt_path.name) > 15 else gpt_path.name
            s_name = sovits_path.name[-15:] if len(sovits_path.name) > 15 else sovits_path.name
            
            st.caption(f"{g_ok} GPT: ...{g_name} | {s_ok} SoVITS: ...{s_name}")

        with cfg_col2:
            st.caption("Target Languages")
            c_l1, c_l2, c_l3 = st.columns(3)
            with c_l1: gen_en = st.checkbox("English", value=False, key="aud_en", disabled=is_running)
            with c_l2: gen_ko = st.checkbox("Korean", value=False, key="aud_ko", disabled=is_running)
            with c_l3: gen_ja = st.checkbox("Japanese", value=True, key="aud_ja", disabled=is_running)

            st.caption("Speech Speed")
            speed_factor = st.slider("Speed Factor", 0.5, 2.0, 1.1, 0.1, key="aud_speed", disabled=is_running)

        target_langs = []
        if gen_en: target_langs.append("en")
        if gen_ko: target_langs.append("ko")
        if gen_ja: target_langs.append("ja")

        st.divider()

        # 2. Generation Logic
        st.subheader("🎧 Generation")
        
        # Load Config (Needed for worker kwargs)
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
        


        # 3. Control Buttons Area
        st.subheader("🎧 Generation Control")
        
        if is_running:
            c1, c2 = st.columns([1, 4])
            with c1:
                if st.button("🚫 Force Stop", type="primary"):
                     st.session_state["audio_gen_stop"] = True
            with c2:
                st.info("Generating Audio... Please wait.")
            
            # Polling mechanism
            time.sleep(1)
            st.rerun()
            
        else:
            def start_thread():
                st.session_state["audio_gen_running"] = True
                st.session_state["audio_logs"] = []
                st.session_state["audio_gen_stop"] = False
                
                # Capture current context explicitly
                ctx = get_script_run_ctx()
                
                # Pass the list OBJECT directly
                log_list = st.session_state["audio_logs"]
                
                t = threading.Thread(
                    target=generation_worker, 
                    args=(base_dir, selected_project, target_langs, gpt_path, sovits_path, speed_factor, speakers_cfg, {}, log_list)
                )
                add_script_run_ctx(t, ctx)
                t.start()
                
            st.button("🎙️ Generate Audio Tracks", type="primary", disabled=not target_langs, on_click=start_thread)

        st.divider()

        # Log Area
        st.markdown("### Process Logs (Newest First)")
        log_box = st.container(height=400)
        with log_box:
            # Render logs in REVERSE order (Newest at top) to ensure visibility of latest
            rev_logs = list(reversed(st.session_state["audio_logs"]))
            log_text = "\n".join(rev_logs)
            st.code(log_text, language="text")
