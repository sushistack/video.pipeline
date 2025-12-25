import streamlit as st
from pathlib import Path
from worker.caption_gen import CaptionGenerator

def render_extract_tab(video_input_dir: Path, output_root: Path):
    st.header("🎤 Caption Extraction (STT)")
    st.caption("Select a video file to generate subtitles (Japanese & Korean).")
    
    # Simplified Layout: 3 Columns
    col_file, col_model, col_spk = st.columns([1, 1, 1])
    
    with col_file:
        existing_files = sorted(list(video_input_dir.glob("*.*"))) if video_input_dir.exists() else []
        if existing_files:
            audio_path = st.selectbox(
                "Select Video/Audio", 
                existing_files, 
                format_func=lambda x: x.name,
                index=None,
                placeholder="Select a file...",
                key="tab0_selector"
            )
            # Sync to session state
            if audio_path:
                st.session_state["current_project_file"] = audio_path
        else:
            st.warning("No files found")
            audio_path = None

    with col_model:
        model_options = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-3-flash-preview"]
        selected_model = st.selectbox("Gemini Model", model_options, index=1)

    with col_spk:
        speaker_options = ["1", "2", "3", "4", "5+"]
        speaker_selection = st.selectbox("Speaker Count", speaker_options, index=1) # index 1 is "2"

    # Fixed Parameters (Hidden)
    target_langs = ["ja", "en", "ko"]
    gen_json = False 
    
    # Validation
    can_generate = (audio_path is not None)
    
    # Initialize session state for extraction status
    if "is_extracting" not in st.session_state:
        st.session_state.is_extracting = False

    def start_extraction():
        st.session_state.is_extracting = True

    # Generate Button or Loading State
    if st.session_state.is_extracting:
        st.button("⏳ Extracting Captions...", type="primary", disabled=True)
        
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
        log(f"[*] Model: {selected_model}")
        log(f"[*] Speaker count: {parsed_speaker_count}")
        
        try:
            with st.spinner("Extracting captions... This may take a while."):
                # Pass selected model here
                cg = CaptionGenerator(model_name=selected_model)
                log(f"[*] CaptionGenerator initialized with {cg.model_name}")
                
                # CaptionGenerator will create {OUTPUT_ROOT}/{base_name}/subtitles/
                cg.generate(
                    audio_path=audio_path,
                    output_dir=output_root,
                    target_languages=target_langs,
                    generate_json=gen_json,
                    speaker_count=parsed_speaker_count
                )
            
            # Success (SRT-only mode)
            log(f"[+] Extraction Done! (SRT Mode)")
            st.success(f"Extraction Complete! 🚀\nGo to 'Story Review' to edit.")
            st.balloons()
                
        except Exception as e:
            log(f"[{e}]") # Log plain error first
            st.error(f"Extraction Failed: {e}")
        finally:
            st.session_state.is_extracting = False
            st.rerun()

    else:
        st.button(
            "🚀 Start Caption Extraction", 
            type="primary", 
            disabled=(not can_generate),
            on_click=start_extraction
        )

    # -------------------------------------------------------------------------
    # Script Refinement Section
    # -------------------------------------------------------------------------
    st.divider()
    st.subheader("✨ Script Refinement & Translation")
    st.caption("Refine the extracted Japanese script (remove fillers, fix grammar) and generate natural translations.")

    if audio_path:
        base_name = audio_path.stem
        project_dir = output_root / base_name
        subtitle_dir = project_dir / "subtitles"
        ja_srt_path = subtitle_dir / "ja.srt"
        
        # Check if basic extraction exists
        if ja_srt_path.exists():
            st.success(f"Found existing captions for: {base_name}")
            
            # Helper to parse SRT if JSON missing
            def parse_srt(srt_path):
                import re
                content = srt_path.read_text(encoding="utf-8")
                items = []
                # Simple block regex
                blocks = re.split(r'\n\n+', content.strip())
                for block in blocks:
                    lines = block.strip().split('\n')
                    if len(lines) >= 3:
                        # 0: index, 1: time, 2+: text
                        times = lines[1].split(' --> ')
                        text = " ".join(lines[2:])
                        # Extract speaker if present [Speaker]: Text
                        speaker = None
                        spk_match = re.match(r'\[(.*?)\] (.*)', text)
                        if spk_match:
                            speaker = spk_match.group(1)
                            text = spk_match.group(2)
                        
                        items.append({
                            "start": times[0].strip(),
                            "end": times[1].strip() if len(times)>1 else times[0].strip(),
                            "text_ja": text,
                            "speaker": speaker
                        })
                return items

            if st.button("🧠 Refine Script & Generate Translations", type="secondary"):
                try:
                    with st.spinner("Refining and Translating..."):
                        cg = CaptionGenerator(model_name=selected_model)
                        
                        # Load Data
                        json_path = subtitle_dir / f"{base_name}.json"
                        if json_path.exists():
                            import json
                            raw_captions = json.loads(json_path.read_text(encoding="utf-8"))
                        else:
                            st.info("Master JSON not found, parsing SRT...")
                            raw_captions = parse_srt(ja_srt_path)
                            
                        # 1. Refine
                        refined_captions = cg.refine_script(raw_captions)
                        cg._save_srt(refined_captions, subtitle_dir / "ja_refined.srt", "ja")
                        
                        # 2. Translate
                        final_captions = cg.translate_refined_script(refined_captions, ["en", "ko"])
                        cg._save_srt(final_captions, subtitle_dir / "en_refined.srt", "en")
                        cg._save_srt(final_captions, subtitle_dir / "ko_refined.srt", "ko")
                        
                        st.success("Refinement & Translation Complete! Checked: ja_refined.srt, en_refined.srt, ko_refined.srt")
                except Exception as e:
                    st.error(f"Refinement Failed: {e}")
        else:
            st.info("Run extraction first to enable refinement.")
