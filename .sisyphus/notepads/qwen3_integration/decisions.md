# Qwen3-TTS Integration Test Decisions

- **Decision**: Use mocking for heavy dependencies (torch, qwen_tts, soundfile) in the integration test.
- **Rationale**: The environment might not have a GPU or enough disk space for the 1.7B model. Mocking allows us to verify the *logic* of the provider (how it handles configs, calls the model API, and saves files) without the overhead of real inference.
