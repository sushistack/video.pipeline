import streamlit as st
from pathlib import Path
from worker.caption_gen import CaptionGenerator
from .utils import parse_srt

def render_review_tab(output_root: Path):
    st.header("📝 Story Review")
    
    # 1. Scan for Available Projects (SRT based)
    available_projects = []
    if output_root.exists():
        for proj_dir in output_root.iterdir():
            if proj_dir.is_dir() and (proj_dir / "subtitles" / "ja.srt").exists():
                available_projects.append(proj_dir)
    
    available_projects = sorted(available_projects, key=lambda p: p.name)

    # 2. Determine Default Index from Session State
    current_video = st.session_state.get("current_project_file")
    default_index = 0
    if current_video and available_projects:
        # Match project directory name with video stem
        matches = [i for i, p in enumerate(available_projects) if p.name == current_video.stem]
        if matches:
            default_index = matches[0]

    # 3. Project Selector
    if available_projects:
        selected_project_root = st.selectbox(
            "📁 Select Project to Review", 
            available_projects, 
            format_func=lambda x: x.name,
            index=default_index,
            key="tab1_project_selector"
        )
        selected_project_dir = selected_project_root / "subtitles"
        project_name = selected_project_root.name
    else:
        st.info("No projects with SRT files found. Please extract SRT first.")
        selected_project_dir = None
        project_name = None

    # 4. Editor Logic
    if selected_project_dir:
        st.caption(f"Editing: **{project_name}** (SRT Mode)")
        
        # Visibility Toggles
        c_tog1, c_tog2 = st.columns([1, 13])
        with c_tog1: show_en = st.checkbox("English", value=True, key="story_review_en")
        with c_tog2: show_ja = st.checkbox("Japanese", value=True, key="story_review_ja")
        
        # Load SRT data
        ja_items = parse_srt(selected_project_dir / "ja.srt")
        ko_items = parse_srt(selected_project_dir / "ko.srt")
        en_items = parse_srt(selected_project_dir / "en.srt")
        
        # Merge by index
        combined_data = []
        max_len = max(len(ja_items), len(ko_items), len(en_items))
        
        for i in range(max_len):
            ja_item = ja_items[i] if i < len(ja_items) else {"start": "", "end": "", "text": ""}
            ko_item = ko_items[i] if i < len(ko_items) else {"start": "", "end": "", "text": ""}
            en_item = en_items[i] if i < len(en_items) else {"start": "", "end": "", "text": ""}
            
            # Timestamp (prefer JA, then EN, then KO)
            start = ja_item.get("start") or en_item.get("start") or ko_item.get("start")
            end = ja_item.get("end") or en_item.get("end") or ko_item.get("end")
            
            # Raw Texts
            text_ja = ja_item.get("text", "")
            text_ko = ko_item.get("text", "")
            text_en = en_item.get("text", "")
            speaker = ""
            
            # Helper: extract speaker from text
            def extract_and_clean(txt):
                spk = None
                clean_txt = txt
                if txt.startswith("[") and "]" in txt:
                    idx = txt.find("]")
                    possible = txt[1:idx]
                    if len(possible) < 30:
                        spk = possible
                        rem = txt[idx+1:].strip()
                        if rem.startswith(":"): rem = rem[1:].strip()
                        clean_txt = rem
                return spk, clean_txt

            # 1. Determine Speaker (Priority: JA -> EN -> KO)
            s_ja, _ = extract_and_clean(text_ja)
            if s_ja: 
                speaker = s_ja
            else:
                s_en, _ = extract_and_clean(text_en)
                if s_en:
                    speaker = s_en
                else:
                    s_ko, _ = extract_and_clean(text_ko)
                    if s_ko: speaker = s_ko

            # 2. Clean all texts of speaker tags
            _, text_ja = extract_and_clean(text_ja)
            _, text_en = extract_and_clean(text_en)
            _, text_ko = extract_and_clean(text_ko)

            combined_data.append({
                "start": start,
                "end": end,
                "speaker": speaker,
                "text_ja": text_ja,
                "text_ko": text_ko,
                "text_en": text_en
            })

        # Helper to Save (Write back to SRTs)
        def save_srts(proj_dir, items):
            cg = CaptionGenerator() 
            ja_save, ko_save, en_save = [], [], []
            
            for item in items:
                spk_pre = f"[{item['speaker']}] " if item['speaker'] else ""
                
                ja_save.append({"start": item["start"], "end": item["end"], "text_ja": f"{spk_pre}{item['text_ja']}" if item['speaker'] else item['text_ja']})
                ko_save.append({"start": item["start"], "end": item["end"], "text_ko": f"{spk_pre}{item['text_ko']}" if item['speaker'] else item['text_ko']})
                en_save.append({"start": item["start"], "end": item["end"], "text_en": f"{spk_pre}{item['text_en']}" if item['speaker'] else item['text_en']})
                
            cg._save_srt(ja_save, proj_dir / "ja.srt", "ja")
            cg._save_srt(ko_save, proj_dir / "ko.srt", "ko")
            cg._save_srt(en_save, proj_dir / "en.srt", "en")
            
            st.toast("Saved changes to EN/JA/KO SRTs! 💾", icon="✅")

        file_key = project_name

        with st.form("editor_form"):
            updated_data = []
            
            for idx, item in enumerate(combined_data):
                # Header
                c_info, c_spk = st.columns([1, 4])
                c_info.markdown(f"**#{idx+1}**\n{item['start']} \n⬇\n {item['end']}")
                
                # Speaker Input
                speaker_val = c_spk.text_input("Speaker", item["speaker"], key=f"{file_key}_spk_{idx}")
                
                # Determine active columns
                active_langs = []
                if show_en: active_langs.append("en")
                active_langs.append("ko") # Always show KO
                if show_ja: active_langs.append("ja")
                
                cols = st.columns(len(active_langs))
                new_vals = {}
                
                for i_col, lang in enumerate(active_langs):
                    with cols[i_col]:
                        if lang == "en":
                            st.caption("🇺🇸 English")
                            new_vals["en"] = st.text_area("en", item["text_en"], key=f"{file_key}_en_{idx}", height=100, label_visibility="collapsed")
                        elif lang == "ko":
                            st.caption("🇰🇷 Korean")
                            new_vals["ko"] = st.text_area("ko", item["text_ko"], key=f"{file_key}_ko_{idx}", height=100, label_visibility="collapsed")
                        elif lang == "ja":
                            st.caption("🇯🇵 Japanese")
                            new_vals["ja"] = st.text_area("ja", item["text_ja"], key=f"{file_key}_ja_{idx}", height=100, label_visibility="collapsed")
                
                updated_data.append({
                    "start": item["start"],
                    "end": item["end"],
                    "speaker": speaker_val,
                    "text_ja": new_vals.get("ja", item["text_ja"]),
                    "text_ko": new_vals.get("ko", item["text_ko"]),
                    "text_en": new_vals.get("en", item["text_en"])
                })
                st.divider()

            if st.form_submit_button("💾 Save Changes to SRT"):
                save_srts(selected_project_dir, updated_data)
                st.rerun()
