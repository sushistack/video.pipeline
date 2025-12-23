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
