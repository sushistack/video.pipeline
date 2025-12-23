import streamlit as st
import json
import yaml
import sys
import re
from pathlib import Path
from worker.gpt_sovits_adapter import GPTSoVITSAdapter

def render_audio_tab(output_root: Path, base_dir: Path):
    st.header("🎙️ Text-to-Speech Generation")
    
    # File Selection (Same Logic)
    all_projects = []
    if output_root.exists():
        for proj_dir in output_root.iterdir():
            if proj_dir.is_dir():
                # Check for any senario-*.xml
                has_any_sc = any(proj_dir.glob("senario-*.xml"))
                if has_any_sc:
                    all_projects.append(proj_dir)
    
    all_projects = sorted(all_projects, key=lambda p: p.name)
    
    if not all_projects:
        st.info("No projects with 'senario-*.xml' found. Please generate a scenario first.")
        return

    # Default latest
    if "selected_audio_project" not in st.session_state:
         if all_projects:
              # Sort by mtime of the ja.srt
              latest = max(all_projects, key=lambda p: (p / "subtitles" / "ja.srt").stat().st_mtime)
              st.session_state["selected_audio_project"] = latest

    # Check for sync from Tab 0
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
        on_change=on_audio_project_change
    )
    
    if selected_project and selected_project.exists():
        st.caption(f"Generating Audio for: **{selected_project.name}**")
        
        # 1. Configuration (Model & Target)
        st.subheader("⚙️ Configuration")
        cfg_col1, cfg_col2 = st.columns(2)
        
        with cfg_col1:
            st.caption("Model Version")
            model_version = st.selectbox("Select Version", ["V2Pro", "V4"], label_visibility="collapsed", key="model_ver_sel")
            
            if model_version == "V2Pro":
                gpt_path = base_dir / "worker/vendor/GPT-SoVITS/GPT_SoVITS/pretrained_models/s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt"
                sovits_path = base_dir / "models/pretrained/v2Pro/s2Gv2Pro.pth"
            else: 
                gpt_path = base_dir / "models/pretrained/s1v3.ckpt"
                sovits_path = base_dir / "models/pretrained/gsv-v4-pretrained/s2Gv4.pth"
            
            g_ok = "✅" if gpt_path.exists() else "❌"
            s_ok = "✅" if sovits_path.exists() else "❌"
            st.caption(f"{g_ok} GPT...{gpt_path.name[-10:]} | {s_ok} SoVITS...{sovits_path.name[-10:]}")

        with cfg_col2:
            st.caption("Target Languages")
            c_l1, c_l2, c_l3 = st.columns(3)
            with c_l1: gen_en = st.checkbox("English", value=False, key="aud_en")
            with c_l2: gen_ko = st.checkbox("Korean", value=False, key="aud_ko")
            with c_l3: gen_ja = st.checkbox("Japanese", value=True, key="aud_ja")

            st.caption("Speech Speed")
            speed_factor = st.slider("Speed Factor", 0.5, 2.0, 1.0, 0.1, key="aud_speed")

        target_langs = []
        if gen_en: target_langs.append("en")
        if gen_ko: target_langs.append("ko")
        if gen_ja: target_langs.append("ja")

        st.divider()

        # 2. Generation Logic
        st.subheader("🎧 Generation")
        
        if "audio_gen_running" not in st.session_state:
            st.session_state["audio_gen_running"] = False
            
        def on_audio_run():
            st.session_state["audio_gen_running"] = True
            
        if st.session_state["audio_gen_running"]:
            st.button("⏳ Generating Audio...", disabled=True, type="primary")
            
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

            # Initialize Adapter
            try:
                tts_engine = GPTSoVITSAdapter(base_dir=base_dir, python_exec=sys.executable)
            except Exception as e:
                st.error(f"Failed to init TTS: {e}")
                st.stop()
            
            prog_bar = st.progress(0, text="Initializing...")
            gen_count = 0
            
            for idx, lang in enumerate(target_langs):
                xml_path = selected_project / f"senario-{lang}.xml"
                map_path = selected_project / f"speaker_map-{lang}.json"
                out_audio_dir = selected_project / "audios" / lang
                out_audio_dir.mkdir(parents=True, exist_ok=True)
                
                if not xml_path.exists(): continue

                spk_map = {}
                if map_path.exists():
                    try: spk_map = json.load(open(map_path))
                    except: pass
                
                try:
                   content = xml_path.read_text(encoding="utf-8")
                   pattern = re.compile(r"<([^>]+)>(.*?)</\1>")
                   matches = pattern.findall(content)
                except: matches = []
                
                if not matches: continue
                
                for i, (spk_tag, text) in enumerate(matches):
                    text = text.strip()
                    if not text: continue
                    
                    prog_step = (idx + (i / len(matches))) / len(target_langs)
                    prog_bar.progress(prog_step, text=f"[{lang.upper()}] {i+1}/{len(matches)}: {spk_tag}")
                    
                    # 1. Resolve Voice Config from Map
                    # 1. Resolve Voice Config from Map
                    # Fuzzy match: "speaker1" vs "Speaker 1"
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
                                
                    map_lang = map_data.get("lang")           # e.g., "ja"
                    map_file = map_data.get("file")           # e.g., "sato-aoi.wav"
                    
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
                        print(f"Skipping {spk_tag}: Ref Audio unavailable.")
                        continue

                    # 2. Config Lookup for Ref Text
                    ref_text = speakers_cfg.get(voice_key, {}).get("ref_text", "")
                    ref_lang = speakers_cfg.get(voice_key, {}).get("ref_lang", "ja")
                    
                    out_wav = out_audio_dir / f"{i:03d}_{spk_tag}.mp3"
                    
                    try:
                        if out_wav.exists(): out_wav.unlink()
                        
                        tts_engine.generate_voice(
                               gpt_model_path=Path(gpt_path),
                               sovits_model_path=Path(sovits_path),
                               ref_audio_path=Path(ref_audio_path),
                               ref_text=ref_text,
                               ref_language=ref_lang,
                               target_text=text,
                               target_language=lang,
                               output_path=out_wav,
                               speed_factor=speed_factor
                        )
                        gen_count += 1
                    except Exception as e:
                        print(f"TTS Error {lang}: {e}")
                    
            prog_bar.empty()
            if gen_count > 0:
                st.toast(f"Generated {gen_count} audio files!", icon="🎉")
            
            st.session_state["audio_gen_running"] = False
            st.rerun()

        else:
            st.button("🎙️ Generate Audio Tracks", type="primary", disabled=not target_langs, on_click=on_audio_run)
