"""Abstract base class for TTS providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncGenerator, Optional
from enum import Enum


class TTSProviderType(str, Enum):
    """Supported TTS provider types."""
    QWEN3_TTS = "qwen3_tts"


@dataclass
class VoiceConfig:
    """Configuration for voice/speaker settings."""
    # Can be preset speaker name OR reference audio path
    voice_id: str

    # Reference audio path (optional for voice cloning)
    ref_audio_path: Optional[Path] = None

    # Reference text (optional for voice cloning)
    ref_text: Optional[str] = None

    # Reference language code (ja, en, ko, zh)
    ref_language: str = "ja"

    # For Qwen3-TTS: use preset speaker instead of voice cloning
    use_preset_speaker: bool = False


@dataclass
class TTSConfig:
    """Common configuration for TTS generation."""
    # Target text to synthesize
    text: str

    # Target language code (ja, en, ko, zh)
    language: str

    # Output file path
    output_path: Path

    # Voice configuration
    voice: VoiceConfig

    # Speech speed factor (1.0 = normal)
    speed_factor: float = 1.0

    # Provider-specific options
    extra_options: dict = field(default_factory=dict)


@dataclass
class ModelConfig:
    """Model configuration for a TTS provider."""
    name: str
    display_name: str
    # Provider-specific model paths or identifiers
    model_paths: dict = field(default_factory=dict)
    description: str = ""


class TTSProvider(ABC):
    """Abstract base class for TTS providers.

    All TTS engines should implement this interface.
    """

    def __init__(self, base_dir: Path):
        """Initialize the provider.

        Args:
            base_dir: Base directory of the project (for resolving relative paths)
        """
        self.base_dir = base_dir

    @property
    @abstractmethod
    def provider_type(self) -> TTSProviderType:
        """Return the provider type identifier."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for UI display."""
        pass

    @abstractmethod
    def get_available_models(self) -> list[ModelConfig]:
        """Return list of available models for this provider.

        Returns:
            List of ModelConfig objects describing available models
        """
        pass

    @abstractmethod
    def get_preset_voices(self) -> list[str]:
        """Return list of preset voice names (if supported).

        Returns:
            List of preset voice names, or empty list if not supported
        """
        pass

    @abstractmethod
    def supports_voice_cloning(self) -> bool:
        """Check if this provider supports voice cloning from reference audio."""
        pass

    @abstractmethod
    async def generate(
        self,
        config: TTSConfig,
        model: ModelConfig,
    ) -> AsyncGenerator[str, None]:
        """Generate speech from text.

        Args:
            config: TTS generation configuration
            model: Model configuration to use

        Yields:
            Log messages for real-time progress updates
        """
        pass

    @abstractmethod
    def is_model_available(self, model: ModelConfig) -> bool:
        """Check if the specified model files exist and are ready to use.

        Args:
            model: Model configuration to check

        Returns:
            True if model is available, False otherwise
        """
        pass

    def validate_config(self, config: TTSConfig) -> list[str]:
        """Validate TTS configuration before generation.

        Args:
            config: Configuration to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not config.text:
            errors.append("Text to synthesize is required")

        if not config.language:
            errors.append("Target language is required")

        if not config.output_path:
            errors.append("Output path is required")

        return errors
