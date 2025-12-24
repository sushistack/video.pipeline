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
        
        # Global Warning for Missing Maps (Selected Targets)
        base_missing = []
        for l in selected_langs:
             if not (sel_proj_sc_root / f"speaker_map-{l}.json").exists():
                  base_missing.append(l.upper())
        
        if base_missing:
             st.error(f"⚠️ Configuration needed for: {', '.join(base_missing)}")

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

            # Fixed list of languages to show mapping for
            MAPPING_LANGS = ["en", "ko", "ja"]
            
            for lang_code in MAPPING_LANGS:
                map_file = sel_proj_sc_root / f"speaker_map-{lang_code}.json"
                cur_map = {}
                map_exists = map_file.exists()
                
                if map_exists:
                    try: cur_map = json.load(open(map_file))
                    except: pass

                # --- Status & Header Logic ---
                is_selected_target = lang_code in selected_langs
                
                if not is_selected_target:
                     # Inactive State
                     header_title = f"⚪ Mapping for {lang_code.upper()} (Disabled)"
                     is_expanded = False
                     
                     with st.expander(header_title, expanded=is_expanded):
                          st.caption(f"Select '{lang_code.upper()}' in Target Languages above to configure this mapping.")
                
                else:
                    # Active State
                    # "If map exists -> Collapsed, else -> Open"
                    is_expanded = not map_exists
                    
                    # Header Title Decoration
                    status_icon = "✅" if map_exists else "⚠️"
                    title_color = "green" if map_exists else "red"
                    header_title = f"{status_icon} Mapping for {lang_code.upper()}"
                    if not map_exists:
                        header_title += " (Not Configured)"

                    with st.expander(header_title, expanded=is_expanded):
                        to_save = {}
                        
                        # Columns for Header: Speaker | Voice Lang | Voice File
                        c_h1, c_h2, c_h3 = st.columns([1,1,3])
                        c_h1.caption("Speaker")
                        c_h2.caption("Voice Lang")
                        c_h3.caption("Voice File")
                        
                        for spk in unique_speakers:
                            rc1, rc2, rc3 = st.columns([1,1,3])
                            rc1.markdown(f"**{spk}**")
                            
                            # Strict Match Logic
                            curr_data = cur_map.get(spk, {})
                            
                            # 1. Voice Language
                            saved_lang = curr_data.get("lang")
                            
                            default_lang_idx = 0
                            
                            if saved_lang and saved_lang in avail_voice_langs:
                                 default_lang_idx = avail_voice_langs.index(saved_lang)
                            elif lang_code in avail_voice_langs:
                                 default_lang_idx = avail_voice_langs.index(lang_code)
                            
                            sel_vl = rc2.selectbox(
                                "Voice Lang", 
                                avail_voice_langs, 
                                key=f"vl_{sel_proj_sc_root.name}_{lang_code}_{spk}", 
                                index=default_lang_idx,
                                label_visibility="collapsed"
                            )
                            
                            # 2. Voice File
                            v_dir = inputs_root / sel_vl
                            v_files = sorted([f.name for f in v_dir.glob("*.*")]) if v_dir.exists() else []
                            v_files.insert(0, "- Select -") # Add unselected option
                            
                            saved_file = curr_data.get("file")
                            
                            def_file_idx = 0
                            if saved_file and saved_file in v_files:
                                 def_file_idx = v_files.index(saved_file)
                            
                            # Visual validation for File selection
                            sel_vf = rc3.selectbox(
                                "Voice File", 
                                v_files, 
                                key=f"vf_{sel_proj_sc_root.name}_{lang_code}_{spk}",
                                index=def_file_idx, 
                                label_visibility="collapsed"
                            )
                            
                            # If "Select" is chosen, show warning text below
                            if sel_vf == "- Select -":
                                 rc3.caption(f":red[⚠️ Please select a voice file]")
                                 to_save[spk] = {"lang": sel_vl, "file": None}
                            else:
                                 to_save[spk] = {"lang": sel_vl, "file": sel_vf}

                        if st.button(f"💾 Save {lang_code.upper()} Mapping", key=f"btn_save_{lang_code}"):
                            # Validate before save
                            valid_save = True
                            for k, v in to_save.items():
                                 if v["file"] is None:
                                      valid_save = False
                                      break
                            
                            if valid_save:
                                 # Clean up "None" just in case before saving (though logic above handles it)
                                 final_save = {k: {"lang": v["lang"], "file": v["file"]} for k,v in to_save.items()}
                                 with open(map_file, "w") as f: json.dump(final_save, f, indent=2, ensure_ascii=False)
                                 st.toast(f"Saved {map_file.name}", icon="✅")
                                 st.rerun()
                            else:
                                 st.error("Please select a voice file for all speakers.")
                        
                        # Nested Raw JSON (Only if exists)
                        if map_exists:
                            st.write("---")
                            with st.expander("View Raw JSON", expanded=False):
                                st.json(json.load(open(map_file)))

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
        # Filter files based on selected_langs
        sc_files = sorted([
            f for f in sel_proj_sc_root.glob("senario-*.xml")
            if f.stem.replace("senario-", "") in selected_langs
        ])
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
