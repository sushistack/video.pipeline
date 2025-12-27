"""Unit tests for core package."""
import pytest
from pathlib import Path
from core import TTSRequest, TTSResponse, GPTSoVITSWrapper
from core.exceptions import ModelNotLoadedError, SubmoduleNotFoundError
from core.utils import validate_audio_file


def test_tts_request_validation():
    """Test TTSRequest validation"""
    # Valid request
    request = TTSRequest(
        text="Hello world", reference_audio=Path("test.wav")
    )
    assert request.text == "Hello world"
    assert request.reference_audio == Path("test.wav")

    # Invalid - empty text should fail
    with pytest.raises(ValueError):
        TTSRequest(text="", reference_audio=Path("test.wav"))


def test_tts_response_creation():
    """Test TTSResponse creation"""
    response = TTSResponse(
        success=True,
        output_path=Path("output.wav"),
        processing_time=1.5,
    )
    assert response.success is True
    assert response.output_path == Path("output.wav")
    assert response.processing_time == 1.5


def test_wrapper_initialization():
    """Test wrapper initialization"""
    wrapper = GPTSoVITSWrapper()
    assert wrapper.device in ["cuda", "cpu"]
    assert wrapper.model is None


def test_validate_audio_file():
    """Test audio file validation"""
    # Test with non-existent file
    assert validate_audio_file(Path("nonexistent.wav")) is False
    
    # Test with invalid extension
    # Note: This requires creating actual test files for full testing


def test_model_not_loaded_error():
    """Test that inference fails when model is not loaded"""
    wrapper = GPTSoVITSWrapper()
    
    request = TTSRequest(
        text="Test", reference_audio=Path("test.wav")
    )
    
    with pytest.raises(ModelNotLoadedError):
        wrapper.inference(request)


def test_model_loading():
    """Test model loading"""
    wrapper = GPTSoVITSWrapper()
    result = wrapper.load_model()
    assert result is True
    assert wrapper.model is not None
