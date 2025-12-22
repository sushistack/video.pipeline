import sys
import os
import shutil
import subprocess
from pathlib import Path

def ensure_python_environment(worker_dir: Path):
    """
    Checks if current python is 3.10.
    If not, tries to create/find a .venv with 3.10 and re-executes the script.
    """
    # 1. Check Version
    major, minor = sys.version_info[:2]
    if major == 3 and minor == 10:
        print(f"[*] Python version {major}.{minor} is correct.")
        return # Continue execution

    print(f"[*] Current Python ({major}.{minor}) is not 3.10.")
    
    # 2. Define Venv Path
    venv_dir = worker_dir / ".venv"
    venv_python = venv_dir / "bin" / "python3"
    
    # Windows support
    if sys.platform == "win32":
         venv_python = venv_dir / "Scripts" / "python.exe"

    # 3. Create Venv if missing
    if not venv_python.exists():
        print("[*] Creating isolated Python 3.10 environment with `uv`...")
        uv = shutil.which("uv")
        if not uv:
            # Try default install location if not in PATH
            uv = os.path.expanduser("~/.local/bin/uv")
            if not os.path.exists(uv):
                 print("[!] Error: 'uv' not found. Please install uv or run in a python 3.10 environment.")
                 sys.exit(1)
        
        try:
            # uv venv .venv --python 3.10 --seed (creates pip/setuptools)
            subprocess.run([uv, "venv", str(venv_dir), "--python", "3.10", "--seed"], check=True)
            print("[+] Virtual environment created.")
        except subprocess.CalledProcessError:
            print("[!] Failed to create venv with uv. Do you have python 3.10 installed or managed by uv?")
            sys.exit(1)

    # 4. Re-execute script with new python
    print(f"[*] Switching to isolated environment: {venv_python}")
    
    # Pass all original arguments
    args = [str(venv_python)] + sys.argv
    
    # Reset environment variables to avoid conflicts (optional, but safer to keep system path usually)
    # forcing execution
    try:
        # Use subprocess instead of os.execv to keep it strictly controlled or just replace process
        if sys.platform == "win32":
            subprocess.run(args, check=True)
            sys.exit(0)
        else:
            os.execv(str(venv_python), args)
    except Exception as e:
        print(f"[!] Failed to re-execute: {e}")
        sys.exit(1)
