"""GPT-SoVITS TTS Provider implementation."""

import os
import sys
import asyncio
from pathlib import Path
from typing import AsyncGenerator

from .base import (
    TTSProvider,
    TTSProviderType,
    TTSConfig,
    ModelConfig,
    VoiceConfig,
)


class GPTSoVITSProvider(TTSProvider):
    """TTS Provider for GPT-SoVITS.

    Uses subprocess to call the GPT-SoVITS inference CLI.
    Supports voice cloning from reference audio.
    """

    # Model configurations relative to pretrained_models directory
    MODEL_CONFIGS = {
        "V4": {
            "gpt": "s1v3.ckpt",
            "sovits": "gsv-v4-pretrained/s2Gv4.pth",
        },
        "V2Pro": {
            "gpt": "s1v3.ckpt",
            "sovits": "v2Pro/s2Gv2Pro.pth",
        },
        "V2ProPlus": {
            "gpt": "s1v3.ckpt",
            "sovits": "v2Pro/s2Gv2ProPlus.pth",
        },
    }

    def __init__(self, base_dir: Path):
        super().__init__(base_dir)
        self.python_exe = sys.executable

        # Try to find venv python
        potential_venvs = [
            base_dir / ".venv" / "bin" / "python",
            base_dir / ".venv" / "Scripts" / "python.exe",
            base_dir / "venv" / "bin" / "python",
            base_dir / "venv" / "Scripts" / "python.exe",
        ]

        for p in potential_venvs:
            if p.exists():
                self.python_exe = str(p)
                break

        self.inference_script = (
            base_dir / "external" / "GPT-SoVITS" / "GPT_SoVITS" / "inference_cli.py"
        )
        self.pretrained_models_dir = (
            base_dir / "external" / "GPT-SoVITS" / "GPT_SoVITS" / "pretrained_models"
        )

    @property
    def provider_type(self) -> TTSProviderType:
        return TTSProviderType.GPT_SOVITS

    @property
    def display_name(self) -> str:
        return "GPT-SoVITS"

    def get_available_models(self) -> list[ModelConfig]:
        """Return available GPT-SoVITS model configurations."""
        models = []
        for name, paths in self.MODEL_CONFIGS.items():
            models.append(
                ModelConfig(
                    name=name,
                    display_name=f"GPT-SoVITS {name}",
                    model_paths=paths,
                    description=f"GPT-SoVITS model version {name}",
                )
            )
        return models

    def get_preset_voices(self) -> list[str]:
        """GPT-SoVITS doesn't have preset voices - requires voice cloning."""
        return []

    def supports_voice_cloning(self) -> bool:
        return True

    def is_model_available(self, model: ModelConfig) -> bool:
        """Check if GPT and SoVITS model files exist."""
        gpt_path = self.pretrained_models_dir / model.model_paths.get("gpt", "")
        sovits_path = self.pretrained_models_dir / model.model_paths.get("sovits", "")
        return gpt_path.exists() and sovits_path.exists()

    def get_model_paths(self, model: ModelConfig) -> tuple[Path, Path]:
        """Get full paths to GPT and SoVITS model files."""
        gpt_path = self.pretrained_models_dir / model.model_paths["gpt"]
        sovits_path = self.pretrained_models_dir / model.model_paths["sovits"]
        return gpt_path, sovits_path

    def validate_config(self, config: TTSConfig) -> list[str]:
        """Validate GPT-SoVITS specific configuration."""
        errors = super().validate_config(config)

        # GPT-SoVITS requires reference audio and text for voice cloning
        if not config.voice.ref_audio_path:
            errors.append("Reference audio path is required for GPT-SoVITS")
        elif not config.voice.ref_audio_path.exists():
            errors.append(f"Reference audio not found: {config.voice.ref_audio_path}")

        if not config.voice.ref_text:
            errors.append("Reference text is required for GPT-SoVITS voice cloning")

        return errors

    async def generate(
        self,
        config: TTSConfig,
        model: ModelConfig,
    ) -> AsyncGenerator[str, None]:
        """Generate speech using GPT-SoVITS inference CLI.

        Yields log messages for real-time progress updates.
        """
        # Validate configuration
        errors = self.validate_config(config)
        if errors:
            for error in errors:
                yield f"[!] Validation Error: {error}"
            return

        if not self.inference_script.exists():
            yield f"[!] Error: inference_cli.py not found at {self.inference_script}"
            return

        # Get model paths
        gpt_path, sovits_path = self.get_model_paths(model)

        if not gpt_path.exists():
            yield f"[!] Error: GPT model not found at {gpt_path}"
            return

        if not sovits_path.exists():
            yield f"[!] Error: SoVITS model not found at {sovits_path}"
            return

        # Build command
        cmd = [
            self.python_exe,
            str(self.inference_script),
            "--gpt_model", str(gpt_path),
            "--sovits_model", str(sovits_path),
            "--ref_audio", str(config.voice.ref_audio_path),
            "--ref_text", config.voice.ref_text,
            "--ref_language", config.voice.ref_language,
            "--target_text", config.text,
            "--target_language", config.language,
            "--output_path", str(config.output_path),
            "--speed_factor", str(config.speed_factor),
            "--text_split_method", "cut5",
        ]

        # Working directory should be GPT-SoVITS root
        cwd = self.inference_script.parent.parent

        # Debug log
        safe_cmd = " ".join([str(c) for c in cmd])
        display_cmd = safe_cmd[:200] + "..." if len(safe_cmd) > 200 else safe_cmd
        yield f"[*] Executing: {display_cmd}"

        try:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(cwd),
                env=env,
            )

            while True:
                line = await process.stdout.readline()
                if not line:
                    break

                try:
                    line_str = line.decode("utf-8").strip()
                except UnicodeDecodeError:
                    try:
                        line_str = line.decode("cp949").strip()
                    except Exception:
                        line_str = line.decode("utf-8", errors="ignore").strip()

                if line_str:
                    yield line_str

            await process.wait()

            if process.returncode == 0:
                yield f"[+] Saved: {config.output_path.name}"
            else:
                yield f"[!] Inference failed with exit code {process.returncode}"

        except Exception as e:
            yield f"[CRITICAL] Subprocess error: {str(e)}"
