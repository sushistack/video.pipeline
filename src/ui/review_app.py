import streamlit as st
import json
import os
import sys
import tempfile
from pathlib import Path

# Ensure worker modules are accessible
sys.path.append(str(Path(__file__).resolve().parent.parent))
from worker.caption_gen import CaptionGenerator
from worker.gpt_sovits_adapter import GPTSoVITSAdapter

st.set_page_config(layout="wide", page_title="Video Pipeline")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SUBTITLE_DIR = BASE_DIR / "outputs/subtitles"
AUDIO_INPUT_DIR = BASE_DIR / "materials/audios/inputs/ja"

st.title("🎞️ Video Pipeline Dashboard")

# Ensure output dir exists
SUBTITLE_DIR.mkdir(parents=True, exist_ok=True)

# === TABS (3 tabs now: Extract, Review, Audio Gen) ===
tab0, tab1, tab2 = st.tabs(["🎤 Extract SRT", "📝 Translation Review", "🎙️ Audio Gen"])

# --- TAB 0: Extract SRT ---
with tab0:
    st.header("🎤 Caption Extraction (STT)")
    st.caption("Upload or select an audio/video file to extract subtitles using Gemini.")
    
    # File Selection
    col1, col2 = st.columns([1, 1])
    with col1:
        input_mode = st.radio("Input Mode", ["Select Existing File", "Upload New File"], horizontal=True, index=1)
    
    audio_path = None
    
    if input_mode == "Select Existing File":
        existing_files = sorted(list(AUDIO_INPUT_DIR.glob("*.*"))) if AUDIO_INPUT_DIR.exists() else []
        if existing_files:
            audio_path = st.selectbox("Select Audio", existing_files, format_func=lambda x: x.name)
        else:
            st.warning("No audio files found in `materials/audios/inputs/ja`")
    else:
        uploaded = st.file_uploader("Upload Audio/Video", type=["mp3", "wav", "mp4", "m4a", "webm"])
        if uploaded:
            temp_dir = Path(tempfile.mkdtemp())
            audio_path = temp_dir / uploaded.name
            audio_path.write_bytes(uploaded.read())
            st.success(f"Uploaded: {uploaded.name}")
    
    # Parameters
    st.subheader("⚙️ Generation Parameters")
    p_col1, p_col2, p_col3 = st.columns(3)
    with p_col1:
        gen_ja = st.checkbox("Generate JA", value=True, disabled=True)
        gen_en = st.checkbox("Generate EN", value=False)
        gen_ko = st.checkbox("Generate KO", value=True)
    with p_col2:
        gen_json = st.checkbox("Generate JSON (with Yomigana)", value=False)
        speaker_options = ["-- Select Speaker Count --", "1", "2", "3", "4", "5+"]
        speaker_selection = st.selectbox("Speaker Count", speaker_options, index=0)
    
    # Validation
    speaker_selected = speaker_selection != "-- Select Speaker Count --"
    can_generate = (audio_path is not None) and speaker_selected
    
    # Generate Button
    if st.button("🚀 Start Caption Extraction", type="primary", disabled=(not can_generate)):
        target_langs = []
        if gen_ja: target_langs.append("ja")
        if gen_en: target_langs.append("en")
        if gen_ko: target_langs.append("ko")
        
        if not target_langs:
            st.error("Please select at least one language.")
        else:
            log_container = st.empty()
            logs = []
            
            def log(msg):
                logs.append(msg)
                log_container.code("\n".join(logs[-20:]), language="log")
            
            if speaker_selection == "5+":
                parsed_speaker_count = 5
            else:
                parsed_speaker_count = int(speaker_selection)
            
            log(f"[*] Starting extraction for: {audio_path.name}")
            log(f"[*] Target languages: {target_langs}")
            log(f"[*] Speaker count: {parsed_speaker_count}")
            
            try:
                cg = CaptionGenerator()
                log(f"[*] CaptionGenerator initialized with {cg.model_name}")
                
                result = cg.generate(
                    audio_path=audio_path,
                    output_dir=SUBTITLE_DIR,
                    target_languages=target_langs,
                    generate_json=gen_json,
                    speaker_count=parsed_speaker_count
                )
                
                if result:
                    log(f"[+] Done! Output: {result}")
                    st.success(f"Extraction Complete! → {result.name}")
                    st.balloons()
                else:
                    log("[!] No JSON generated (check parameters).")
                    st.warning("SRT files generated, but no JSON.")
                    
            except Exception as e:
                log(f"[!] Error: {e}")
                st.error(f"Extraction Failed: {e}")

# --- TAB 1: Translation Review (with file selection and Raw JSON inside) ---
with tab1:
    st.header("📝 Translation Review")
    
    # File Selection inside this tab
    all_files = sorted(list(SUBTITLE_DIR.glob("*.json")), key=lambda f: f.name)
    
    if not all_files:
        st.info("No JSON files yet. Use 'Extract SRT' tab first.")
    else:
        latest_file = max(all_files, key=lambda f: f.stat().st_mtime)
        
        if "selected_file_path" not in st.session_state:
            st.session_state["selected_file_path"] = latest_file
        
        def on_file_change():
            st.session_state["selected_file_path"] = st.session_state["file_selector_review"]
        
        try:
            current_index = all_files.index(st.session_state["selected_file_path"])
        except ValueError:
            current_index = 0
            st.session_state["selected_file_path"] = all_files[0]

        selected_file = st.selectbox(
            "📁 Select File to Edit", 
            all_files, 
            format_func=lambda x: x.name, 
            index=current_index,
            key="file_selector_review",
            on_change=on_file_change
        )
        
        if selected_file and selected_file.exists():
            with open(selected_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Helper to save
            def save_data(path, new_data, old_data):
                cg = CaptionGenerator()
                modified_items = []
                has_updates = False
                
                for new_item, old_item in zip(new_data, old_data):
                    if new_item["text_ja"] != old_item["text_ja"]:
                        temp_list = [new_item]
                        cg._add_yomigana(temp_list)
                        modified_items.append(temp_list[0])
                        has_updates = True
                    else:
                        modified_items.append(new_item)
                        
                if has_updates:
                    st.toast("Detected Japanese text changes. Updated Yomigana.", icon="🎌")
                
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(modified_items, f, indent=2, ensure_ascii=False)
                st.toast(f"Saved JSON to {path}", icon="✅")
                
                base_name = path.stem
                cg._save_srt(modified_items, path.parent / f"{base_name}.ja.srt", "ja")
                cg._save_srt(modified_items, path.parent / f"{base_name}.en.srt", "en")
                cg._save_srt(modified_items, path.parent / f"{base_name}.ko.srt", "ko")
                st.toast("Regenerated SRTs!", icon="🔄")
            
            # Language toggle
            c_mode, _ = st.columns([1, 4])
            with c_mode:
                right_lang = st.radio("Right Column", ["Japanese", "English"], horizontal=True, label_visibility="collapsed")
            
            tgt_label = "🇯🇵 Japanese" if right_lang == "Japanese" else "🇺🇸 English"
            file_key = selected_file.stem

            with st.form("editor_form"):
                updated_data = []
                
                for idx, item in enumerate(data):
                    st.markdown(f"**#{idx+1}** ({item['start']} --> {item['end']})")
                    
                    left_col, right_col = st.columns([1, 1])
                    
                    with left_col:
                        speaker_val = st.text_input("Speaker", item.get("speaker", ""), key=f"{file_key}_spk_{idx}")
                        new_ko = st.text_area("🇰🇷 Korean", item.get("text_ko", ""), key=f"{file_key}_ko_{idx}", height=100)
                        
                    with right_col:
                        if right_lang == "Japanese":
                            new_ja = st.text_area(tgt_label, item.get("text_ja", ""), key=f"{file_key}_ja_{idx}", height=100)
                            new_en = item.get("text_en", "")
                        else:
                            new_en = st.text_area(tgt_label, item.get("text_en", ""), key=f"{file_key}_en_{idx}", height=100)
                            new_ja = item.get("text_ja", "")

                    with st.expander("Show Kanjis / Metadata"):
                        kanjis = item.get("kanjis", [])
                        kanjis_json = st.text_area("Kanjis JSON", json.dumps(kanjis, ensure_ascii=False), key=f"{file_key}_kj_{idx}", height=70)

                    try:
                        parsed_kanjis = json.loads(kanjis_json)
                    except:
                        parsed_kanjis = kanjis

                    updated_data.append({
                        "start": item["start"],
                        "end": item["end"],
                        "speaker": speaker_val,
                        "text_ja": new_ja,
                        "text_en": new_en,
                        "text_ko": new_ko,
                        "kanjis": parsed_kanjis
                    })
                    st.divider()

                if st.form_submit_button("💾 Save All Changes (Auto-Update Yomigana)"):
                    save_data(selected_file, updated_data, data)
                    st.rerun()
            
            # Raw JSON inside Translation Review as expander
            with st.expander("🔧 View Raw JSON"):
                st.json(data)

# --- TAB 2: Audio Gen ---
with tab2:
    st.header("🎙️ Text-to-Speech Generation")
    
    # File Selection for Audio Gen
    all_files_audio = sorted(list(SUBTITLE_DIR.glob("*.json")), key=lambda f: f.name)
    
    if not all_files_audio:
        st.info("No JSON files yet. Use 'Extract SRT' tab first.")
    else:
        if "selected_file_path" not in st.session_state:
            st.session_state["selected_file_path"] = max(all_files_audio, key=lambda f: f.stat().st_mtime)
        
        def on_audio_file_change():
            st.session_state["selected_file_path"] = st.session_state["file_selector_audio"]
        
        try:
            current_index_audio = all_files_audio.index(st.session_state["selected_file_path"])
        except ValueError:
            current_index_audio = 0
            st.session_state["selected_file_path"] = all_files_audio[0]

        selected_file_audio = st.selectbox(
            "📁 Select Subtitle File", 
            all_files_audio, 
            format_func=lambda x: x.name, 
            index=current_index_audio,
            key="file_selector_audio",
            on_change=on_audio_file_change
        )
        
        if selected_file_audio and selected_file_audio.exists():
            with open(selected_file_audio, "r", encoding="utf-8") as f:
                data_audio = json.load(f)
            
            st.caption(f"Generating for: {selected_file_audio.name}")
            
            with st.expander("⚙️ Model & Reference Configuration", expanded=True):
                cols = st.columns(2)
                with cols[0]:
                    vendor_dir = BASE_DIR / "worker" / "vendor"
                    default_gpt = vendor_dir / "GPT-SoVITS/GPT_SoVITS/pretrained_models/s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt"
                    default_sovits = vendor_dir / "GPT-SoVITS/GPT_SoVITS/pretrained_models/s2G488k.pth"
                    
                    gpt_path = st.text_input("GPT Model Path", str(default_gpt))
                    sovits_path = st.text_input("SoVITS Model Path", str(default_sovits))
                    
                with cols[1]:
                    ref_dir = BASE_DIR / "materials/audios/inputs/ja"
                    ref_files = sorted(list(ref_dir.glob("*.*"))) if ref_dir.exists() else []
                    
                    ref_audio_path = st.selectbox(
                        "Reference Audio", 
                        ref_files, 
                        format_func=lambda x: x.name,
                        index=0 if ref_files else None
                    )
                    ref_text = st.text_input("Reference Text", "僕がそんなに子供じゃないって。私からしたら少年はまだまだ少年だぞ。うりうり。")
                    ref_lang = st.selectbox("Reference Language", ["ja", "en", "ko"], index=0)

            target_lang = st.radio("Target Audio Language", ["Japanese (ja)", "English (en)", "Korean (ko)"], horizontal=True)
            t_lang_code = target_lang.split("(")[1].strip(")")
            
            # Log Container
            tts_log_container = st.empty()
            tts_logs = []
            
            def tts_log(msg):
                tts_logs.append(msg)
                tts_log_container.code("\n".join(tts_logs[-15:]), language="log")
            
            if st.button("🚀 Generate Audio Tracks", type="primary"):
                if not ref_audio_path:
                    st.error("Please select a Reference Audio file.")
                else:
                    tts_log(f"[*] Initializing GPT-SoVITS Adapter...")
                    adapter = GPTSoVITSAdapter(base_dir=BASE_DIR, python_exec=sys.executable)
                    output_base = BASE_DIR / f"materials/audios/outputs/{t_lang_code}"
                    output_base.mkdir(parents=True, exist_ok=True)
                    
                    tts_log(f"[*] Output dir: {output_base}")
                    
                    progress_bar = st.progress(0)
                    total = len(data_audio)
                    
                    for i, item in enumerate(data_audio):
                        input_text = item.get(f"text_{t_lang_code}", "")
                        if not input_text:
                            tts_log(f"[{i+1}/{total}] Skipped (no text)")
                            continue
                            
                        out_filename = f"{selected_file_audio.stem}_{i+1:04d}.wav"
                        out_path = output_base / out_filename
                        
                        tts_log(f"[{i+1}/{total}] Generating: {input_text[:40]}...")
                        
                        try:
                            adapter.generate_voice(
                                gpt_model_path=Path(gpt_path),
                                sovits_model_path=Path(sovits_path),
                                ref_audio_path=Path(ref_audio_path),
                                ref_text=ref_text,
                                ref_language=ref_lang,
                                target_text=input_text,
                                target_language=t_lang_code,
                                output_path=out_path
                            )
                            tts_log(f"[{i+1}/{total}] ✅ Saved: {out_filename}")
                        except Exception as e:
                            tts_log(f"[{i+1}/{total}] ❌ Failed: {e}")
                            st.error(f"Failed at #{i+1}: {e}")
                            break
                            
                        progress_bar.progress((i + 1) / total)
                        
                    tts_log("[+] Generation Complete!")
                    st.toast("Audio Generation Complete!", icon="🎉")
            
            st.divider()
            st.subheader("🎧 Audio Preview")
            
            output_base_preview = BASE_DIR / f"materials/audios/outputs/{t_lang_code}"
            
            for i, item in enumerate(data_audio):
                out_filename = f"{selected_file_audio.stem}_{i+1:04d}.wav"
                audio_file = output_base_preview / out_filename
                
                c1, c2, c3 = st.columns([1, 4, 3])
                c1.markdown(f"**#{i+1}**")
                c2.text(item.get(f"text_{t_lang_code}", ""))
                if audio_file.exists():
                    c3.audio(str(audio_file))
                else:
                    c3.caption("No Audio")
                st.divider()
