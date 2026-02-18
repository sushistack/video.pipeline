## Qwen3-TTS Real Inference Test
- Created tests/test_qwen3_real_inference.py for real GPU inference.
- The script uses Qwen3TTSProvider and handles GPU status reporting (including ROCm for AMD).
- It targets the CustomVoice model with the Dylan preset for English speech generation.
- Successfully modified `tests/test_qwen3_real_inference.py` to test voice cloning using the "Base" model.
- The `VoiceConfig` correctly handles `ref_audio_path` and `use_preset_speaker` for cloning.
- Verified that `assets/outputs/real_qwen3_en.wav` exists and can be used as a reference for cloning.
