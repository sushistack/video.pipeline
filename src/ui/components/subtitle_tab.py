import streamlit as st
import json
from pathlib import Path
from mutagen.mp3 import MP3
import re
import datetime
from .utils import parse_srt, get_kanjis

def format_timestamp(seconds: float) -> str:
    """Formats seconds to MM:SS:fff (e.g. 00:00:810)"""
    td = datetime.timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    ms = int(td.microseconds / 1000)
    
    minutes = total_seconds // 60
    secs = total_seconds % 60
    
    return f"{minutes:02}:{secs:02}:{ms:03}"

def format_timestamp_v2(ms_total: int) -> str:
    seconds = ms_total // 1000
    ms = ms_total % 1000
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02}:{secs:02}:{ms:03}"

def render_subtitle_tab(output_root: Path):
    st.header("📝 Subtitle Generation")
    
    # 1. Project Selector
    avail_projs = []
    if output_root.exists():
        for proj_dir in output_root.iterdir():
            # Check if 'audios' exists (prerequisite for subtitle gen)
            if proj_dir.is_dir() and (proj_dir / "audios").exists():
                avail_projs.append(proj_dir)
    avail_projs = sorted(avail_projs, key=lambda p: p.name)
    
    curr_proj_idx = 0
    if "selected_audio_project" in st.session_state and st.session_state["selected_audio_project"]:
         matches = [i for i,p in enumerate(avail_projs) if p.name == st.session_state["selected_audio_project"].name]
         if matches: curr_proj_idx = matches[0]

    if not avail_projs:
        st.info("No projects with generated audio found.")
        return

    sel_proj_root = st.selectbox("📁 Select Project", avail_projs, format_func=lambda x: x.name, index=curr_proj_idx, key="sub_proj_sel")
    st.session_state["selected_audio_project"] = sel_proj_root # Sync with other tabs
    
    # Paths
    audios_root = sel_proj_root / "audios"
    subtitles_root = sel_proj_root / "subtitles" # For reading SRT and saving JSON
    scenarios_root = sel_proj_root # For reading XML
    
    # 2. Language Checkboxes
    st.write("### Target Languages")
    
    langs = ["en", "ko", "ja"]
    lang_status = {}
    
    # Pre-check availability
    for l in langs:
        a_dir = audios_root / l
        has_audio = a_dir.exists() and any(a_dir.glob("*.mp3"))
        # CHANGED: Check SRT existence instead of XML
        has_srt = (subtitles_root / f"{l}.srt").exists()
        
        is_ready = has_audio and has_srt
        reason = []
        if not has_audio: reason.append("No Audio")
        if not has_srt: reason.append("No SRT")
        
        lang_status[l] = {
            "ready": is_ready,
            "desc": f"({', '.join(reason)})" if reason else ""
        }

    c_l1, c_l2, c_l3 = st.columns(3)
    
    # Defaults (Only if ready)
    def_en = False
    def_ko = False
    def_ja = True if lang_status["ja"]["ready"] else False

    with c_l1: 
        s = lang_status["en"]
        label = "English"
        if not s["ready"]: label += f" {s['desc']}"
        do_en = st.checkbox(label, value=def_en, key="sub_gen_en", disabled=not s["ready"])
        
    with c_l2: 
        s = lang_status["ko"]
        label = "Korean"
        if not s["ready"]: label += f" {s['desc']}"
        do_ko = st.checkbox(label, value=def_ko, key="sub_gen_ko", disabled=not s["ready"])
        
    with c_l3: 
        s = lang_status["ja"]
        label = "Japanese"
        if not s["ready"]: label += f" {s['desc']}"
        do_ja = st.checkbox(label, value=def_ja, key="sub_gen_ja", disabled=not s["ready"])
    
    selected_langs = []
    if do_en: selected_langs.append("en")
    if do_ko: selected_langs.append("ko")
    if do_ja: selected_langs.append("ja")
    
    st.divider()
    
    # 3. Per-Language Expanders
    lang_data_map = {} # Store data for generation: {lang: {audio: [], srt: []}}
    all_valid = True # Track overall validity
    
    for lang in selected_langs:
        # Paths
        audio_dir = audios_root / lang
        xml_file = scenarios_root / f"senario-{lang}.xml"
        srt_file = subtitles_root / f"{lang}.srt"
        
        # Load Data
        audio_files = sorted(list(audio_dir.glob("*.mp3"))) if audio_dir.exists() else []
        xml_content = xml_file.read_text(encoding="utf-8") if xml_file.exists() else ""
        srt_items = parse_srt(srt_file) if srt_file.exists() else []
        
        count_audio = len(audio_files)
        # CHANGED: Use SRT items count
        count_lines = len(srt_items)
        
        # Validation Logic (Audio Count vs SRT Count)
        is_valid = (count_audio == count_lines) and (count_audio > 0)
        if not is_valid:
             all_valid = False
             
        status_icon = "✅" if is_valid else "⚠️"
        
        # Header
        header_title = f"{status_icon} Mapping for {lang.upper()} (Audio: {count_audio} / SRT Blocks: {count_lines})"
        
        with st.expander(header_title, expanded=True):
            c1, c2 = st.columns([1, 1])
            
            with c1:
                st.caption(f"Audio Files ({len(audio_files)})")
                st.dataframe([f.name for f in audio_files], width="stretch", hide_index=True)
                
            with c2:
                # CHANGED: Show SRT Content
                st.caption(f"SRT Content ({count_lines} blocks)")
                srt_text_preview = srt_file.read_text(encoding="utf-8") if srt_file.exists() else "No SRT File"
                st.text_area("SRT", srt_text_preview, height=200, label_visibility="collapsed", key=f"srt_view_{lang}")
        
        # Store for generation
        lang_data_map[lang] = {
            "audios": audio_files,
            "srt": srt_items,
            "xml_path": xml_file
        }
    
    # 4. Generate Button
    st.divider()
    
    # Disable if no languages selected OR validation failed for any language
    btn_disabled = (not selected_langs) or (not all_valid)
    if st.button("🎬 Generate Subtitles", type="primary", disabled=btn_disabled):
        generated_count = 0
        
        for lang, data in lang_data_map.items():
            audios = data["audios"]
            srt_items = data["srt"]
            xml_path = data["xml_path"]
            
            if not audios or not srt_items:
                st.warning(f"Skipping {lang.upper()}: Missing audio or SRT files.")
                continue
            
            # Need strict matching? Or truncate?
            # We will zip, so it truncates to shortest
            
            # Parse XML for Speakers (Best effort)
            speakers = []
            if xml_path.exists():
                # Simple regex extraction to avoid XML parsing overhead/errors
                xml_txt = xml_path.read_text(encoding="utf-8")
                # pattern: speaker="Speaker 1"
                speakers = re.findall(r'speaker="([^"]+)"', xml_txt)
            
            json_output = []
            current_ms = 0
            GAP_MS = 0 # Sequential
            
            for idx, (audio_path, srt_item) in enumerate(zip(audios, srt_items)):
                try:
                    mp3 = MP3(audio_path)
                    duration_sec = mp3.info.length
                    duration_ms = int(duration_sec * 1000)
                    
                    start_str = format_timestamp_v2(current_ms)
                    end_ms = current_ms + duration_ms
                    end_str = format_timestamp_v2(end_ms)
                    
                    # Speaker: Try to get from XML list, else Default
                    spk = speakers[idx] if idx < len(speakers) else "Unknown"
                    
                    # Text: From SRT
                    raw_text = srt_item["text"]
                    
                    # Check for [speaker] pattern in text
                    # User feedback: "[speaker] processing needed"
                    # Pattern: [speaker_name] Text...
                    speaker_match = re.match(r"^\[(.*?)\]\s*(.*)", raw_text, re.DOTALL)
                    
                    if speaker_match:
                        spk_from_text = speaker_match.group(1)
                        clean_text = speaker_match.group(2)
                        
                        # Use extracted speaker if valid
                        spk = spk_from_text
                        text_content = clean_text
                    else:
                        text_content = raw_text
                    
                    entry = {
                        "start": start_str,
                        "end": end_str,
                        "speaker": spk,
                        "text": text_content
                    }
                    
                    # Add Kanji Analysis for Japanese
                    if lang == "ja":
                        entry["kanjis"] = get_kanjis(text_content)
                    
                    # Add language specific key if needed (User sample had text_ja, but instruction said separate files)
                    # "json text refers to {lang}.srt". 
                    # We'll use strict 'text' key unless user wants 'text_ja'. 
                    # Re-reading: "8. ...sample.json form. (However, separate by lang files)"
                    # Sample has "text_ja", "text_en".
                    # If separate files, maybe keep structure?
                    # Let's add 'text' AND 'text_{lang}' to be safe and helpful?
                    # User sample: "text_ja": "..."
                    # If I put "text": "...", it's safer for generic players.
                    # I'll put 'text' for now.
                    
                    json_output.append(entry)
                    
                    current_ms = end_ms + GAP_MS
                    
                except Exception as e:
                    st.error(f"Error processing {lang} item {idx}: {e}")
            
            # Save
            out_json = subtitles_root / f"{lang}.json"
            subtitles_root.mkdir(parents=True, exist_ok=True)
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(json_output, f, indent=2, ensure_ascii=False)
            
            generated_count += 1
            st.toast(f"Generated {lang.upper()} Subtitles: {out_json.name}", icon="✅")
            
        if generated_count > 0:
            st.success("Subtitle generation complete!")
