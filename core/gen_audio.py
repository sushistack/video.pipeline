import os
import sys
import asyncio
import subprocess
from pathlib import Path
import typing

class GenAudio:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.python_exe = sys.executable
        
        # Try to find venv python to ensure dependencies like pytorch_lightning are found
        venv_python = base_dir / "venv" / "Scripts" / "python.exe"
        if venv_python.exists():
            print(f"[*] Using venv python: {venv_python}")
            self.python_exe = str(venv_python)
        
        # Correct path to inference_cli.py based on file structure
        self.inference_script = base_dir / "external" / "GPT-SoVITS" / "GPT_SoVITS" / "inference_cli.py"
        
    async def async_generate_voice(
        self,
        gpt_model_path: Path,
        sovits_model_path: Path,
        ref_audio_path: Path,
        ref_text: str,
        ref_language: str,
        target_text: str,
        target_language: str,
        output_path: Path,
        speed_factor: float = 1.0,
    ) -> typing.AsyncGenerator[str, None]:
        """
        Run inference using GPT-SoVITS inference CLI.
        Yields stdout lines for real-time logging.
        """
        
        if not self.inference_script.exists():
             yield f"[!] Error: inference_cli.py not found at {self.inference_script}"
             return

        # Prepare Command
        cmd = [
            self.python_exe,
            str(self.inference_script),
            "--gpt_model", str(gpt_model_path),
            "--sovits_model", str(sovits_model_path),
            "--ref_audio", str(ref_audio_path),
            "--ref_text", ref_text,
            # Map common language codes to CLI expected codes if needed, 
            # but inference_cli.py seems to accept "en", "ja", "ko", "zh" directly.
            "--ref_language", ref_language,
            "--target_text", target_text,
            "--target_language", target_language,
            "--output_path", str(output_path),
            "--speed_factor", str(speed_factor),
            "--text_split_method", "cut5" 
        ]
        
        # Working directory should be the route of GPT-SoVITS to ensure imports work
        cwd = self.inference_script.parent.parent
        
        # Debug Log
        safe_cmd = ' '.join([str(c) for c in cmd])
        # Truncate long text for display
        display_cmd = safe_cmd[:200] + "..." if len(safe_cmd) > 200 else safe_cmd
        yield f"[*] Executing: {display_cmd}"
        
        try:
            # Force environment to use UTF-8
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(cwd),
                env=env
            )
            
            # Read output real-time
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                
                # specific handling for decoding on Windows might be needed if reconfigure isn't enough
                try:
                    line_str = line.decode('utf-8').strip()
                except UnicodeDecodeError:
                    try:
                        line_str = line.decode('cp949').strip()
                    except:
                        line_str = line.decode('utf-8', errors='ignore').strip()

                if line_str:
                    yield line_str
                
            await process.wait()
            
            if process.returncode == 0:
                yield f"[+] Saved: {output_path.name}"
            else:
                yield f"[!] Inference failed with exit code {process.returncode}"
                
        except Exception as e:
            yield f"[CRITICAL] Subprocess error: {str(e)}"
