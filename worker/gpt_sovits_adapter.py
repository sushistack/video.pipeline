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
logger = logging.getLogger("gpt_sovits_adapter")
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
        # Use our custom CLI for speed control & fixes
        self.cli_script = base_dir / "worker" / "inference_cli_custom.py"
        
        # Determine Python Executable
        self.python_exec = python_exec or sys.executable
        
        # Verify Environment
        if not self.cli_script.exists():
            raise FileNotFoundError(f"CLI script not found at {self.cli_script}")

    def _map_language(self, lang_code: str, is_target: bool = False) -> str:
        """Maps ISO codes to GPT-SoVITS CLI Chinese keys."""
        mapping = {
            "en": "英文",
            "ja": "日文",
            "zh": "中文",
            "yue": "粤语",
            "mix": "多语种混合"
        }
        
        normalized_lang = lang_code.lower()

        # Korean Special Handling
        if normalized_lang == "ko":
            if is_target:
                return "多语种混合" # Target Korean -> Multilingual Mix
            else:
                return "韩文"     # Reference Korean -> Korean

        # Fallback to mapped value or return as is (if valid)
        return mapping.get(normalized_lang, lang_code)

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
        device: str = None,
        speed_factor: float = 1.0,
        callback = None
    ) -> Path:
        """
        Generates audio by invoking the CLI script.
        Handles temp file creation for text inputs.
        """
        def log(msg):
            logger.info(msg)
            if callback: callback(msg)

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
                    "--ref_language", self._map_language(ref_language, is_target=False),
                    "--target_text", str(tf_tgt_path),
                    "--target_language", self._map_language(target_language, is_target=True),
                    "--output_path", str(temp_out_dir),
                    "--speed_factor", str(speed_factor)
                ]
                
                env = os.environ.copy()
                env["PYTHONPATH"] = str(self.vendor_dir) + os.pathsep + env.get("PYTHONPATH", "")

                if device:
                    env["GPT_SOVITS_DEVICE"] = device
                elif sys.platform == "darwin":
                    # Force CPU on macOS to avoid MPS channel limits (conv1d > 65536)
                    env["GPT_SOVITS_DEVICE"] = "cpu"
                
                # Critical Fix: Enable CPU fallback for MPS operations not implemented (e.g. huge conv1d)
                env["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
                
                # Critical Fix: inference_webui.py attempts to load weights on import.
                # We must provide valid paths via env vars to prevent FileNotFoundError.
                env["gpt_path"] = str(gpt_model_path)
                env["sovits_path"] = str(sovits_model_path)
                # Also set cnhubert path just in case
                env["cnhubert_base_path"] = str(self.vendor_dir / "GPT_SoVITS/pretrained_models/chinese-hubert-base")
                env["bert_path"] = str(self.vendor_dir / "GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large")
                env["is_half"] = "False" # Use FP32 for CPU compatibility/safety

                # Use Popen to capture stdout in real-time
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, # Merge stderr to stdout
                    text=True, 
                    cwd=self.vendor_dir,
                    env=env,
                    bufsize=1,            # Line buffered
                    universal_newlines=True
                )
                
                # Stream logs
                for line in process.stdout:
                    line = line.replace("\n", "")
                    if line.strip():
                        # Don't double log if our logger.info already goes to stdout
                        # But for UI callback we need it.
                        print(line) # Ensure it hits console
                        if callback: callback(line)
                
                process.wait()
                
                if process.returncode != 0:
                     raise subprocess.CalledProcessError(process.returncode, cmd)
                
                # Check for output.wav
                generated_file = Path(temp_out_dir) / "output.wav"
                if not generated_file.exists():
                    raise RuntimeError(f"CLI finished but output.wav not found.")
                
                # Move/Convert to final destination
                if output_path.suffix.lower() == ".mp3":
                    convert_cmd = [
                        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(generated_file),
                        "-codec:a", "libmp3lame", "-qscale:a", "2",
                        str(output_path)
                    ]
                    subprocess.run(convert_cmd, check=True)
                else:
                    shutil.move(str(generated_file), str(output_path))
                
                log("")
                log("============================================================================")
                log(f"[+] Audio saved to {output_path}")
                log("============================================================================")
                log("")
                
                return output_path

            except subprocess.CalledProcessError as e:
                log(f"[!] CLI Failed with exit code {e.returncode}")
                raise RuntimeError(f"GPT-SoVITS CLI Error (Exit Code {e.returncode})") from e
            finally:
                # Cleanup Temp Text Files
                if tf_ref_path.exists(): tf_ref_path.unlink()
                if tf_tgt_path.exists(): tf_tgt_path.unlink()

if __name__ == "__main__":
    # Internal Test
    pass
