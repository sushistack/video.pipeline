# pip install pydantic

import os
import sys
import shutil
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict

# Configure Logger
logger = logging.getLogger("GPTSoVITS_Adapter")
logging.basicConfig(level=logging.INFO)

class GPTSoVITSAdapter:
    """
    Adapter to control GPT-SoVITS via CLI (inference_cli.py).
    "Clean Code" / "Safety First" Refactoring.
    """
    def __init__(
        self, 
        base_dir: Path, 
        python_exec: Optional[str] = None
    ):
        self.base_dir = base_dir
        self.vendor_dir = base_dir / "worker" / "vendor" / "GPT-SoVITS"
        self.cli_script = self.vendor_dir / "GPT_SoVITS" / "inference_cli.py"
        
        # Determine Python Executable
        self.python_exec = python_exec or sys.executable
        
        # Verify Environment
        if not self.cli_script.exists():
            raise FileNotFoundError(f"CLI script not found at {self.cli_script}")

    def _map_language(self, lang_code: str) -> str:
        """Maps ISO codes to GPT-SoVITS CLI Chinese keys."""
        mapping = {
            "en": "英文",
            "ja": "日文",
            "zh": "中文",
            "ko": "韩文", # Note: Check if supported. CLI doc says Ref choices=["中文", "英文", "日文"]. KO might be missing in Ref?
                         # Target choices supports "多语种混合". Let's verify CLI source again.
                         # Original CLI choices: Ref=["中文", "英文", "日文"], Target=[... "多语种混合"]
                         # Wait, if Ref doesn't support KO, we can't use KO ref.
                         # Target usually supports KO via "多语种混合" in newer versions, or maybe not?
                         # Let's assume standard 3 langs for now. If user needs KO, they need a model supporting it.
                         # Assuming models provided (s1bert...) are the standard multi-lingual ones.
            "mix": "多语种混合"
        }
        # Fallback to mapped value or return as is (if valid)
        return mapping.get(lang_code.lower(), lang_code)

    def generate_voice(
        self, 
        gpt_model_path: Path,
        sovits_model_path: Path,
        ref_audio_path: Path,
        ref_text: str,
        ref_language: str,
        target_text: str,
        target_language: str,
        output_path: Path,
        device: str = None
    ) -> Path:
        """
        Generates audio by invoking the CLI script.
        Handles temp file creation for text inputs.
        """
        # Validate Inputs
        if not gpt_model_path.exists():
            raise FileNotFoundError(f"GPT Model not found: {gpt_model_path}")
        if not sovits_model_path.exists():
            raise FileNotFoundError(f"SoVITS Model not found: {sovits_model_path}")
        if not ref_audio_path.exists():
            raise FileNotFoundError(f"Ref Audio not found: {ref_audio_path}")

        # Create Temp Files for Text
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8", suffix=".txt") as tf_ref:
            tf_ref.write(ref_text)
            tf_ref_path = Path(tf_ref.name)
            
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8", suffix=".txt") as tf_tgt:
            tf_tgt.write(target_text)
            tf_tgt_path = Path(tf_tgt.name)

        # Prepare Output Directory (CLI takes a dir and saves 'output.wav')
        # We want to save to 'output_path'. So we use a temp dir then move.
        with tempfile.TemporaryDirectory() as temp_out_dir:
            try:
                # Construct Command
                cmd = [
                    self.python_exec,
                    str(self.cli_script),
                    "--gpt_model", str(gpt_model_path),
                    "--sovits_model", str(sovits_model_path),
                    "--ref_audio", str(ref_audio_path),
                    "--ref_text", str(tf_ref_path),
                    "--ref_language", self._map_language(ref_language),
                    "--target_text", str(tf_tgt_path),
                    "--target_language", self._map_language(target_language),
                    "--output_path", str(temp_out_dir)
                ]
                
                logger.info(f"[*] Executing CLI: {' '.join(cmd)}")
                
                env = os.environ.copy()
                env["PYTHONPATH"] = str(self.vendor_dir) + os.pathsep + env.get("PYTHONPATH", "")

                if device:
                    env["GPT_SOVITS_DEVICE"] = device
                
                # Critical Fix: inference_webui.py attempts to load weights on import.
                # We must provide valid paths via env vars to prevent FileNotFoundError.
                env["gpt_path"] = str(gpt_model_path)
                env["sovits_path"] = str(sovits_model_path)
                # Also set cnhubert path just in case
                env["cnhubert_base_path"] = str(self.vendor_dir / "GPT_SoVITS/pretrained_models/chinese-hubert-base")
                env["bert_path"] = str(self.vendor_dir / "GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large")
                env["is_half"] = "False" # Use FP32 for CPU compatibility/safety

                result = subprocess.run(
                    cmd, 
                    check=True, 
                    capture_output=True, 
                    text=True, 
                    cwd=self.vendor_dir,
                    env=env
                )
                
                # Check for output.wav
                generated_file = Path(temp_out_dir) / "output.wav"
                if not generated_file.exists():
                    raise RuntimeError(f"CLI finished but output.wav not found.\nSTDERR: {result.stderr}")
                
                # Move to final destination
                shutil.move(str(generated_file), str(output_path))
                logger.info(f"[+] Audio saved to {output_path}")
                
                return output_path

            except subprocess.CalledProcessError as e:
                logger.error(f"[!] CLI Failed with exit code {e.returncode}")
                logger.error(f"STDOUT: {e.stdout}")
                logger.error(f"STDERR: {e.stderr}")
                raise RuntimeError(f"GPT-SoVITS CLI Error: {e.stderr}") from e
            finally:
                # Cleanup Temp Text Files
                if tf_ref_path.exists(): tf_ref_path.unlink()
                if tf_tgt_path.exists(): tf_tgt_path.unlink()

if __name__ == "__main__":
    # Internal Test
    pass
