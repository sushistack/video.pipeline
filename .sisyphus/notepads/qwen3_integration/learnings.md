# Qwen3-TTS Integration Test Learnings

- Successfully verified Qwen3-TTS generation logic using a mock-based integration test.
- Confirmed that `instruct` (emotion tags) is correctly passed to `generate_custom_voice` when using the `CustomVoice` model.
- Verified that voice cloning correctly identifies and uses reference audio paths.
- The `Qwen3TTSProvider` correctly handles both preset speakers and custom voice cloning.
- Mocking heavy dependencies (torch, qwen_tts, soundfile) allows for fast and reliable testing of the provider logic without requiring a GPU or large model downloads.
Set Qwen3-TTS default model to 'Base' in ui/states/audio_state.py to support voice cloning by default.
