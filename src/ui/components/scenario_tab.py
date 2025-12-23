import streamlit as st
import json
from pathlib import Path
from worker.caption_gen import CaptionGenerator
from .utils import parse_srt

def render_scenario_tab(output_root: Path, base_dir: Path):
    st.header("🎬 Scenario Generation")
    
    # 1. Project Selector logic
    avail_projs_sc = []
    if output_root.exists():
        for proj_dir in output_root.iterdir():
            if proj_dir.is_dir() and (proj_dir / "subtitles" / "ja.srt").exists():
                avail_projs_sc.append(proj_dir)
    avail_projs_sc = sorted(avail_projs_sc, key=lambda p: p.name)
    
    # Sync Logic
    curr_proj_sc_idx = 0
    if "selected_audio_project" in st.session_state and st.session_state["selected_audio_project"]: 
         # Ensure selected_audio_project is a Path and has a name
         # Logic from original: 
         matches = [i for i,p in enumerate(avail_projs_sc) if p.name == st.session_state["selected_audio_project"].name]
         if matches: curr_proj_sc_idx = matches[0]

    if avail_projs_sc:
        sel_proj_sc_root = st.selectbox("📁 Select Project", avail_projs_sc, format_func=lambda x: x.name, index=curr_proj_sc_idx, key="scen_proj_sel")
        sel_proj_sc_sub = sel_proj_sc_root / "subtitles"
        
        # Checkboxes for Language Selection
        st.write("### Target Languages")
        c_l1, c_l2, c_l3 = st.columns(3)
        with c_l1: do_en = st.checkbox("English", value=False, key="scen_gen_en")
        with c_l2: do_ko = st.checkbox("Korean", value=False, key="scen_gen_ko")
        with c_l3: do_ja = st.checkbox("Japanese", value=True, key="scen_gen_ja")
        
        selected_langs = []
        if do_en: selected_langs.append("en")
        if do_ko: selected_langs.append("ko")
        if do_ja: selected_langs.append("ja")

        st.divider()

        # 1. Speaker Mapping (Per selected language)
        st.subheader("🗣️ Speaker Voice Mapping")
        
        # Get speakers from any available SRT (Priority: JA -> EN -> KO)
        ref_srt_path = sel_proj_sc_sub / "ja.srt"
        if not ref_srt_path.exists(): ref_srt_path = sel_proj_sc_sub / "en.srt"
        if not ref_srt_path.exists(): ref_srt_path = sel_proj_sc_sub / "ko.srt"
        
        unique_speakers = []
        if ref_srt_path.exists():
            items = parse_srt(ref_srt_path)
            s_set = set()
            for x in items:
                tx = x.get("text", "") # Safety use get
                if tx.startswith("[") and "]" in tx:
                    s_set.add(tx[1:tx.find("]")])
            unique_speakers = sorted(list(s_set))
            
        if not unique_speakers:
            st.info("No speakers found in SRT files. Use Story Review to add tags.")
        else:
            inputs_root = base_dir / "materials/audios/inputs"
            avail_voice_langs = sorted([d.name for d in inputs_root.iterdir() if d.is_dir()]) if inputs_root.exists() else ["ja"]

            if not selected_langs:
                st.info("Select a language above to configure mapping.")
            
            # Loop through selected languages for mapping
            for lang_code in selected_langs:
                with st.expander(f"Mapping for {lang_code.upper()}", expanded=True):
                    map_file = sel_proj_sc_root / f"speaker_map-{lang_code}.json"
                    
                    cur_map = {}
                    if map_file.exists():
                        try: cur_map = json.load(open(map_file))
                        except: pass
                    
                    to_save = {}
                    
                    # UI Header
                    c_h1, c_h2, c_h3 = st.columns([1,1,3])
                    c_h1.caption("Speaker")
                    c_h2.caption("Voice Lang")
                    c_h3.caption("Voice File")
                    
                    for spk in unique_speakers:
                        rc1, rc2, rc3 = st.columns([1,1,3])
                        rc1.markdown(f"**{spk}**")
                        
                        # Def values
                        d_v_l = cur_map.get(spk, {}).get("lang", "ja")
                        if d_v_l not in avail_voice_langs and avail_voice_langs: d_v_l = avail_voice_langs[0]
                        
                        sel_vl = rc2.selectbox("Voice Language", avail_voice_langs, key=f"vl_{lang_code}_{spk}", 
                                             index=avail_voice_langs.index(d_v_l) if d_v_l in avail_voice_langs else 0,
                                             label_visibility="collapsed")
                        
                        # Files
                        v_dir = inputs_root / sel_vl
                        v_files = sorted([f.name for f in v_dir.glob("*.*")]) if v_dir.exists() else []
                        
                        d_v_f = cur_map.get(spk, {}).get("file", "")
                        idx_f = v_files.index(d_v_f) if d_v_f in v_files else 0
                        
                        sel_vf = rc3.selectbox("Voice File", v_files, key=f"vf_{lang_code}_{spk}",
                                             index=idx_f, label_visibility="collapsed")
                                             
                        to_save[spk] = {"lang": sel_vl, "file": sel_vf}
                        
                    if st.button(f"🔄 Update", key=f"btn_save_{lang_code}"):
                        with open(map_file, "w") as f: json.dump(to_save, f, indent=2, ensure_ascii=False)
                        st.toast(f"Updated {map_file.name}", icon="✅")
                        st.rerun()
                    
                    if map_file.exists():
                        st.caption(f"Current Mapping ({map_file.name}):")
                        st.json(json.load(open(map_file)), expanded=True)

        st.divider()
        
        # 2. Make Scenario (Batch)
        st.subheader("📜 Create Scenario")
        
        # Validation: Check if mapping files exist for selected languages
        missing_maps = []
        for l in selected_langs:
            if not (sel_proj_sc_root / f"speaker_map-{l}.json").exists():
                missing_maps.append(l)
        
        can_generate_scen = (len(missing_maps) == 0) and (len(selected_langs) > 0)
        
        if not can_generate_scen and selected_langs:
            st.warning(f"Missing speaker mapping for: {', '.join(missing_maps)}. Please save mapping above.")
        
        # State Management for Loading Button
        if "scen_gen_running" not in st.session_state:
            st.session_state["scen_gen_running"] = False
            
        def on_gen_click():
            st.session_state["scen_gen_running"] = True
            
        if st.session_state["scen_gen_running"]:
            # 1. Show Disabled Loading Button
            st.button("⏳ Generating Scenarios...", disabled=True, type="primary")
            
            # 2. Run Logic
            try:
                my_bar = st.progress(0, text="Initializing Gemini...")
                
                cg_engine = CaptionGenerator()
                valid_count = 0
                
                for idx, lang_code in enumerate(selected_langs):
                    target_srt = sel_proj_sc_sub / f"{lang_code}.srt"
                    if not target_srt.exists(): continue
                    
                    try:
                        my_bar.progress((idx) / len(selected_langs), text=f"Generating {lang_code.upper()}...")
                        raw = parse_srt(target_srt)
                        xml_content = cg_engine.generate_xml_scenario(raw, lang_code)
                        out_xml = sel_proj_sc_root / f"senario-{lang_code}.xml"
                        out_xml.write_text(xml_content, encoding="utf-8")
                        valid_count += 1
                    except Exception as e:
                        st.error(f"Error generating {lang_code}: {e}")
                    
                    my_bar.progress((idx + 1) / len(selected_langs), text=f"Finished {lang_code.upper()}")
                
                my_bar.empty()
                if valid_count > 0:
                    st.toast(f"Generated {valid_count} scenario files!", icon="🎉")
                    
            except Exception as e:
                st.error(f"Critical Error: {e}")
                
            # 3. Reset and Rerun
            st.session_state["scen_gen_running"] = False
            st.rerun()

        else:
            # Normal Button
            st.button("🚀 Generate Scenarios", disabled=not can_generate_scen, type="primary", on_click=on_gen_click)

        # 3. Viewer
        st.subheader("👁️ Scenario Viewer")
        sc_files = sorted(list(sel_proj_sc_root.glob("senario-*.xml")))
        if sc_files:
            # Use Tabs for better UX
            sc_tabs = st.tabs([f.name for f in sc_files])
            
            for t, f in zip(sc_tabs, sc_files):
                with t:
                    st.text_area("XML Content", f.read_text(encoding="utf-8"), height=500, key=f"area_{f.name}")
        else:
            st.info("No scenarios generated yet.")
    else:
        st.info("No projects with SRT available.")
