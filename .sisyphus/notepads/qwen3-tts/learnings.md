## Qwen3-TTS Emotion Tag Extraction
- Implemented emotion tag extraction from text in `Qwen3TTSProvider`.
- Format: `(Emotion) Text`
- The extracted emotion is passed as `instruct` to the model, and the tag is removed from the text.
- Supported in `CustomVoice` model.
Modified tests/test_qwen3_generation.py to prevent deletion of generated audio files and made output paths unique for each test case.
Replaced sox dependency with numpy-based normalization in external/Qwen3-TTS/qwen_tts/core/tokenizer_25hz/vq/speech_vq.py to avoid binary dependency issues.
