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
        # Check .venv first (standard poetry/modern convention)
        potential_venvs = [
            base_dir / ".venv" / "bin" / "python",       # Unix .venv
            base_dir / ".venv" / "Scripts" / "python.exe", # Win .venv
            base_dir / "venv" / "bin" / "python",        # Unix venv
            base_dir / "venv" / "Scripts" / "python.exe"   # Win venv
        ]
        
        for p in potential_venvs:
            if p.exists():
                print(f"[*] Using venv python: {p}")
                self.python_exe = str(p)
                break
        
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

    async def remove_silence(self, file_path: Path) -> typing.AsyncGenerator[str, None]:
        """Remove long silence from audio"""
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
                keep_silence=100  # Keep 100ms at edges to avoid clipping
            )
            
            if chunks:
                # Recombine with 200ms silence
                combined = AudioSegment.empty()
                silence_chunk = AudioSegment.silent(duration=200)
                
                for i, chunk in enumerate(chunks):
                    combined += chunk
                    if i < len(chunks) - 1:
                        combined += silence_chunk
                        
                combined.export(file_path, format=file_path.suffix.lstrip("."))
                yield f"[+] Silence optimized (trimmed long gaps)"
            else:
                yield f"[.] No long silences found."
                
        except Exception as e:
            yield f"[!] Silence removal failed: {e}"

    async def normalize_audio(self, file_path: Path) -> typing.AsyncGenerator[str, None]:
        """Normalize audio to EBU R128 (-14 LUFS)"""
        try:
            temp_out = file_path.with_suffix(".norm" + file_path.suffix)
            output_fmt = file_path.suffix.lstrip(".")
            codec = "libmp3lame" if output_fmt == "mp3" else "pcm_s16le"
            
            norm_cmd = [
                "ffmpeg-normalize",
                str(file_path),
                "-nt", "ebu",
                "-t", "-14",
                "-tp", "-1.0",
                "-o", str(temp_out),
                "-f", 
                "-c:a", codec
            ]
            
            process = await asyncio.create_subprocess_exec(
                *norm_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # Replace original with normalized
                if temp_out.exists():
                    temp_out.replace(file_path)
                yield f"[+] Normalization complete."
            else:
                yield f"[!] Normalization failed: {stderr.decode()}"
                
        except Exception as e:
            yield f"[!] Normalization error: {e}"

    async def optimize_audio(self, file_path: Path) -> typing.AsyncGenerator[str, None]:
        """
        Post-process audio:
        1. Trim long silences
        2. Normalize audio
        """
        yield f"[*] Optimizing: {file_path.name}"
        
        async for log in self.remove_silence(file_path):
            yield f"    {log}"
            
        async for log in self.normalize_audio(file_path):
            yield f"    {log}"
