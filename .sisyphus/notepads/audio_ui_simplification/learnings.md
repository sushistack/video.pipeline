## Audio UI Simplification
- Added `show_model_version` property to `AudioState` to control visibility of model version selector.
- Wrapped Model Version selector in `ui/pages/audio.py` with `rx.cond(AudioState.show_model_version, ...)`.
- Confirmed `set_selected_provider` correctly sets `selected_model` to 'CustomVoice' for Qwen3-TTS.
