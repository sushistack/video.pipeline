"""Audio generation with Qwen3-TTS provider support."""

import asyncio
import sys
from pathlib import Path
import typing

from core.tts import (
    TTSProvider,
    TTSConfig,
    VoiceConfig,
    ModelConfig,
    TTSProviderType,
    Qwen3TTSProvider,
)


class GenAudio:
    """Audio generation orchestrator with Qwen3-TTS support.

    Supports:
    - Qwen3-TTS: Preset speakers and voice cloning via Python API
    """

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self._providers: dict[TTSProviderType, TTSProvider] = {}

    def get_provider(self, provider_type: TTSProviderType) -> TTSProvider:
        """Get or create a TTS provider instance."""
        if provider_type not in self._providers:
            if provider_type == TTSProviderType.QWEN3_TTS:
                self._providers[provider_type] = Qwen3TTSProvider(self.base_dir)
            else:
                raise ValueError(f"Unknown provider type: {provider_type}")
        return self._providers[provider_type]

    @staticmethod
    def get_available_providers() -> list[dict[str, str]]:
        """Return list of available TTS providers."""
        return [
            {
                "type": TTSProviderType.QWEN3_TTS.value,
                "name": "Qwen3-TTS",
                "description": "Fast TTS with preset speakers and voice cloning",
            },
        ]

    async def generate_voice(
        self,
        provider_type: TTSProviderType,
        model: ModelConfig,
        config: TTSConfig,
    ) -> typing.AsyncGenerator[str, None]:
        """Generate voice using specified provider and model.

        Args:
            provider_type: Which TTS provider to use
            model: Model configuration for the provider
            config: TTS generation configuration

        Yields:
            Log messages for real-time progress updates
        """
        provider = self.get_provider(provider_type)

        async for log_line in provider.generate(config, model):
            yield log_line

    async def remove_silence(self, file_path: Path) -> typing.AsyncGenerator[str, None]:
        """Remove long silence from audio."""
        try:
            from pydub import AudioSegment, silence

            if file_path.suffix.lower() == ".mp3":
                audio = AudioSegment.from_mp3(file_path)
            else:
                audio = AudioSegment.from_file(file_path)

            # Split on silence > 500ms, -45dB
            chunks = silence.split_on_silence(
                audio,
                min_silence_len=500,
                silence_thresh=-45,
                keep_silence=100,  # Keep 100ms at edges
            )

            if chunks:
                combined = AudioSegment.empty()
                silence_chunk = AudioSegment.silent(duration=200)

                for i, chunk in enumerate(chunks):
                    combined += chunk
                    if i < len(chunks) - 1:
                        combined += silence_chunk

                combined.export(file_path, format=file_path.suffix.lstrip("."))
                yield "[+] Silence optimized (trimmed long gaps)"
            else:
                yield "[.] No long silences found."

        except Exception as e:
            yield f"[!] Silence removal failed: {e}"

    async def normalize_audio(self, file_path: Path) -> typing.AsyncGenerator[str, None]:
        """Normalize audio to EBU R128 (-14 LUFS)."""
        try:
            import shutil
            import os

            # Get the venv bin directory path
            venv_bin = os.path.dirname(os.path.dirname(sys.executable))
            if os.name != "nt":  # Not Windows
                venv_bin = os.path.join(venv_bin, "bin")
            ffmpeg_normalize_path = os.path.join(venv_bin, "ffmpeg-normalize")

            # Check if ffmpeg-normalize exists in venv
            if os.path.exists(ffmpeg_normalize_path):
                ffmpeg_normalize_cmd = ffmpeg_normalize_path
            elif shutil.which("ffmpeg-normalize"):
                ffmpeg_normalize_cmd = "ffmpeg-normalize"
            else:
                # Fallback to ffmpeg loudnorm filter
                yield "[*] ffmpeg-normalize not found, using ffmpeg loudnorm filter..."
                temp_out = file_path.with_suffix(".norm" + file_path.suffix)
                output_fmt = file_path.suffix.lstrip(".")
                codec = "libmp3lame" if output_fmt == "mp3" else "pcm_s16le"

                # Two-pass loudnorm for better accuracy
                loudnorm_cmd = [
                    "ffmpeg",
                    "-y",
                    "-i", str(file_path),
                    "-af", "loudnorm=I=-14:TP=-1.0:LRA=11:print_format=summary",
                    "-c:a", codec,
                    str(temp_out),
                ]

                process = await asyncio.create_subprocess_exec(
                    *loudnorm_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout, stderr = await process.communicate()

                if process.returncode == 0:
                    if temp_out.exists():
                        temp_out.replace(file_path)
                    yield "[+] Normalization complete (using ffmpeg loudnorm)."
                else:
                    yield f"[!] Normalization failed: {stderr.decode()}"
                return

            # Use ffmpeg-normalize
            temp_out = file_path.with_suffix(".norm" + file_path.suffix)
            output_fmt = file_path.suffix.lstrip(".")
            codec = "libmp3lame" if output_fmt == "mp3" else "pcm_s16le"

            norm_cmd = [
                ffmpeg_normalize_cmd,
                str(file_path),
                "-nt", "ebu",
                "-t", "-14",
                "-tp", "-1.0",
                "-o", str(temp_out),
                "-f",
                "-c:a", codec,
            ]

            process = await asyncio.create_subprocess_exec(
                *norm_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                if temp_out.exists():
                    temp_out.replace(file_path)
                yield "[+] Normalization complete."
            else:
                yield f"[!] Normalization failed: {stderr.decode()}"

        except Exception as e:
            yield f"[!] Normalization error: {e}"

    async def optimize_audio(self, file_path: Path) -> typing.AsyncGenerator[str, None]:
        """Post-process audio: trim silences and normalize."""
        yield f"[*] Optimizing: {file_path.name}"

        async for log in self.remove_silence(file_path):
            yield f"    {log}"

        async for log in self.normalize_audio(file_path):
            yield f"    {log}"
