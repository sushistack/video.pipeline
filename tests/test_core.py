"""Unit tests for core package."""
import pytest
from pathlib import Path


def test_placeholder():
    """Placeholder test - TTS tests require model setup."""
    # Basic import test
    from core.tts import TTSProvider, TTSConfig, VoiceConfig, ModelConfig, TTSProviderType
    from core.gen_audio import GenAudio

    assert TTSProviderType.QWEN3_TTS.value == "qwen3_tts"


def test_gen_audio_providers():
    """Test GenAudio provider listing."""
    from core.gen_audio import GenAudio

    providers = GenAudio.get_available_providers()
    assert len(providers) == 1
    assert providers[0]["name"] == "Qwen3-TTS"
