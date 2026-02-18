"""Qwen3-TTS Provider implementation."""

import re
from pathlib import Path
from typing import AsyncGenerator, Optional
import asyncio

from .base import (
    TTSProvider,
    TTSProviderType,
    TTSConfig,
    ModelConfig,
    VoiceConfig,
)


class Qwen3TTSProvider(TTSProvider):
    """TTS Provider for Qwen3-TTS.

    Uses Python API directly for inference.
    Supports both preset speakers and voice cloning from reference audio.
    """

    # Available model configurations
    # Uses local models from assets/models/ if available, otherwise falls back to HuggingFace
    MODEL_CONFIGS = {
        "CustomVoice": {
            "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
            "local_path": Path(__file__).parent.parent.parent / "assets" / "models" / "Qwen3-TTS-12Hz-1.7B-CustomVoice",
            "type": "custom_voice",
        },
        "Base": {
            "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            "local_path": Path(__file__).parent.parent.parent / "assets" / "models" / "Qwen3-TTS-12Hz-1.7B-Base",
            "type": "base",
        },
        "VoiceDesign": {
            "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
            "local_path": Path(__file__).parent.parent.parent / "assets" / "models" / "Qwen3-TTS-12Hz-1.7B-VoiceDesign",
            "type": "voice_design",
        },
    }

    # Preset speakers available in CustomVoice model
    PRESET_SPEAKERS = [
        "Vivian",  # Chinese female
        "Serena",  # Chinese female
        "Uncle_Fu",  # Chinese male
        "Dylan",  # English male
        "Eric",  # English male
        "Ryan",  # English male
        "Aiden",  # English male
        "Ono_Anna",  # Japanese female
        "Sohee",  # Korean female
    ]

    # Language mapping from our codes to Qwen3-TTS expected format
    LANGUAGE_MAP = {
        "ja": "Japanese",
        "en": "English",
        "ko": "Korean",
        "zh": "Chinese",
    }

    def __init__(self, base_dir: Path):
        super().__init__(base_dir)
        self._model = None
        self._current_model_config: Optional[ModelConfig] = None

    @property
    def provider_type(self) -> TTSProviderType:
        return TTSProviderType.QWEN3_TTS

    @property
    def display_name(self) -> str:
        return "Qwen3-TTS"

    def get_available_models(self) -> list[ModelConfig]:
        """Return available Qwen3-TTS model configurations."""
        models = []
        for name, config in self.MODEL_CONFIGS.items():
            description = {
                "CustomVoice": "Pre-trained speakers with emotion control",
                "Base": "Voice cloning from reference audio",
                "VoiceDesign": "Natural language voice description",
            }.get(name, "")

            models.append(
                ModelConfig(
                    name=name,
                    display_name=f"Qwen3-TTS {name}",
                    model_paths={
                        "model_id": config["model_id"],
                        "local_path": config.get("local_path"),
                        "type": config["type"],
                    },
                    description=description,
                )
            )
        return models

    def get_preset_voices(self) -> list[str]:
        """Return list of preset speaker names."""
        return self.PRESET_SPEAKERS.copy()

    def supports_voice_cloning(self) -> bool:
        """Qwen3-TTS Base model supports voice cloning."""
        return True

    def is_model_available(self, model: ModelConfig) -> bool:
        """Check if model can be loaded (requires internet for first download)."""
        # Models are downloaded from HuggingFace on first use
        # We assume availability if the config exists
        return model.name in self.MODEL_CONFIGS

    def _get_language(self, lang_code: str) -> str:
        """Convert language code to Qwen3-TTS format."""
        return self.LANGUAGE_MAP.get(lang_code, "Auto")

    def validate_config(self, config: TTSConfig) -> list[str]:
        """Validate Qwen3-TTS specific configuration."""
        errors = super().validate_config(config)

        # Check if using preset speaker or voice cloning
        if config.voice.use_preset_speaker:
            if config.voice.voice_id not in self.PRESET_SPEAKERS:
                errors.append(
                    f"Unknown preset speaker: {config.voice.voice_id}. "
                    f"Available: {', '.join(self.PRESET_SPEAKERS)}"
                )
        else:
            # Voice cloning mode - requires reference audio
            if not config.voice.ref_audio_path:
                errors.append("Reference audio path is required for voice cloning")
            elif not config.voice.ref_audio_path.exists():
                errors.append(
                    f"Reference audio not found: {config.voice.ref_audio_path}"
                )

        return errors

    async def _load_model(self, model: ModelConfig) -> str:
        """Load Qwen3-TTS model (lazy loading).
        
        Returns:
            str: Log message about model loading status
        """
        if self._model is not None and self._current_model_config == model:
            return "[*] Model already loaded"

        # Import here to avoid loading heavy dependencies until needed
        try:
            import torch
            from qwen_tts import Qwen3TTSModel
        except ImportError as e:
            raise ImportError(
                f"Failed to import Qwen3-TTS. Install with: pip install qwen-tts. Error: {e}"
            )

        model_id = model.model_paths["model_id"]
        local_path = model.model_paths.get("local_path")

        # Use local model if available, otherwise use HuggingFace model_id
        model_path = None
        log_msg = ""
        cache_dir = self.base_dir / "assets" / "models" / ".cache"
        
        if local_path and local_path.exists():
            model_path = str(local_path)
            log_msg = f"[*] Using local model: {model_path}"
        else:
            model_path = model_id
            # Create cache directory for HuggingFace models
            cache_dir.mkdir(parents=True, exist_ok=True)
            log_msg = f"[*] Downloading/loading model from HuggingFace: {model_id} (cache: {cache_dir})"

        # Determine device and dtype
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32

        # Load model
        load_kwargs = {
            "device_map": device,
            "dtype": dtype,
            "cache_dir": str(cache_dir),
        }

        # Use flash attention only if the package is actually installed
        # Check by trying to import flash_attn
        flash_attn_available = False
        try:
            import flash_attn  # noqa: F401
            flash_attn_available = True
        except ImportError:
            pass

        if flash_attn_available and torch.cuda.is_available():
            load_kwargs["attn_implementation"] = "flash_attention_2"

        self._model = Qwen3TTSModel.from_pretrained(model_path, **load_kwargs)
        self._current_model_config = model
        
        return log_msg

    async def generate(
        self,
        config: TTSConfig,
        model: ModelConfig,
    ) -> AsyncGenerator[str, None]:
        """Generate speech using Qwen3-TTS.

        Yields log messages for real-time progress updates.
        """
        # Validate configuration
        errors = self.validate_config(config)
        if errors:
            for error in errors:
                yield f"[!] Validation Error: {error}"
            return

        yield f"[*] Loading Qwen3-TTS model: {model.display_name}..."

        try:
            # Load model (async wrapper for sync operation)
            log_msg = await self._load_model(model)
            yield log_msg
            yield "[+] Model loaded successfully"
        except Exception as e:
            yield f"[!] Failed to load model: {e}"
            return

        yield f"[*] Generating speech for: {config.text[:50]}..."

        try:
            import soundfile as sf
            import numpy as np

            model_type = model.model_paths.get("type", "custom_voice")
            language = self._get_language(config.language)

            wavs = None
            sr = None

            # Validate model type matches the requested operation
            if config.voice.use_preset_speaker:
                if model_type != "custom_voice":
                    yield f"[!] Error: Preset speakers require CustomVoice model, but {model.name} is {model_type}"
                    return

            if config.voice.use_preset_speaker and model_type == "custom_voice":
                # Use preset speaker (CustomVoice model)
                yield f"[*] Using preset speaker: {config.voice.voice_id}"

                # Get instruct from extra_options if provided
                instruct = config.extra_options.get("instruct", "")
                text = config.text

                # Extract emotion tag from text if present, e.g., "(Excited) Hello"
                emotion_match = re.match(r"^\((.*?)\)\s*(.*)$", text)
                if emotion_match:
                    instruct = emotion_match.group(1)
                    text = emotion_match.group(2)

                # Run generation in thread pool to avoid blocking
                wavs, sr = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._model.generate_custom_voice(
                        text=text,
                        speaker=config.voice.voice_id,
                        language=language,
                        instruct=instruct if instruct else None,
                    ),
                )

            elif model_type == "voice_design":
                # Use voice design (natural language description)
                instruct = config.extra_options.get("instruct", "")
                if not instruct:
                    instruct = "Natural speaking voice"

                yield f"[*] Using voice design with instruction: {instruct[:50]}..."

                wavs, sr = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._model.generate_voice_design(
                        text=config.text,
                        instruct=instruct,
                        language=language,
                    ),
                )

            else:
                # Voice cloning (Base model)
                yield f"[*] Using voice cloning from: {config.voice.ref_audio_path.name}"

                ref_audio_path = str(config.voice.ref_audio_path)
                ref_text = config.voice.ref_text

                # x_vector_only_mode: True = only speaker embedding, False = ICL mode (needs ref_text)
                x_vector_only = ref_text is None or ref_text.strip() == ""

                wavs, sr = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._model.generate_voice_clone(
                        text=config.text,
                        language=language,
                        ref_audio=ref_audio_path,
                        ref_text=ref_text if not x_vector_only else None,
                        x_vector_only_mode=x_vector_only,
                    ),
                )

            if wavs and len(wavs) > 0:
                # Save the generated audio
                output_path = config.output_path
                output_path.parent.mkdir(parents=True, exist_ok=True)

                wav_data = wavs[0]

                # Convert to appropriate format based on output extension
                if output_path.suffix.lower() == ".mp3":
                    # Save as WAV first, then convert
                    temp_wav = output_path.with_suffix(".temp.wav")
                    sf.write(str(temp_wav), wav_data, sr)

                    # Convert to MP3 using ffmpeg
                    import subprocess

                    try:
                        subprocess.run(
                            [
                                "ffmpeg",
                                "-y",
                                "-i",
                                str(temp_wav),
                                "-codec:a",
                                "libmp3lame",
                                "-qscale:a",
                                "2",
                                str(output_path),
                            ],
                            check=True,
                            capture_output=True,
                        )
                        temp_wav.unlink()  # Remove temp file
                    except subprocess.CalledProcessError as e:
                        yield f"[!] MP3 conversion failed, saving as WAV: {e}"
                        temp_wav.rename(output_path.with_suffix(".wav"))
                else:
                    sf.write(str(output_path), wav_data, sr)

                yield f"[+] Saved: {output_path.name}"
            else:
                yield "[!] No audio generated"

        except Exception as e:
            yield f"[CRITICAL] Generation error: {str(e)}"
            import traceback

            yield f"[DEBUG] {traceback.format_exc()}"
