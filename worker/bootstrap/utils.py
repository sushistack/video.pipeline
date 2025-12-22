import sys
import os
import subprocess
from pathlib import Path

def run_cmd(cmd, cwd=None, check=True, env=None):
    """Run a shell command with consistent logging."""
    print(f"[$] {cmd}")
    try:
        subprocess.run(
            cmd, 
            shell=True, 
            check=check, 
            cwd=cwd, 
            env=env or os.environ.copy()
        )
    except subprocess.CalledProcessError as e:
        print(f"[!] Command failed: {e}")
        sys.exit(1)
