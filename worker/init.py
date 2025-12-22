#!/usr/bin/env python3
"""
worker/init.py - Modular Bootstrapper
=====================================
Orchestrates the setup using modules in `worker/bootstrap/`.
Automatically handles Python 3.10 environment isolation.
"""
import argparse
from pathlib import Path
import sys

# Ensure bootstrapping path
worker_dir = Path(__file__).parent
sys.path.append(str(worker_dir))

try:
    from bootstrap.env_setup import ensure_python_environment
    from bootstrap.checks import check_python_version, detect_platform
    from bootstrap.git_utils import init_submodule
    from bootstrap.dependencies import install_system_dependencies
    from bootstrap.models import download_models
except ImportError:
    # If running directly not as module, path append above handles it.
    from bootstrap.env_setup import ensure_python_environment
    from bootstrap.checks import check_python_version, detect_platform
    from bootstrap.git_utils import init_submodule
    from bootstrap.dependencies import install_system_dependencies
    from bootstrap.models import download_models

def main():
    parser = argparse.ArgumentParser(description="Initialize GPT-SoVITS worker")
    parser.add_argument("--force-cpu", action="store_true", help="Force CPU installation")
    # Only verify arguments, don't execute logic yet if we are in wrong python
    # But actually we want to run logic. args parsing is fine in any python.
    args, unknown = parser.parse_known_args()

    # 0. Auto-Environment Handling
    # This will exit and restart the process if python != 3.10
    ensure_python_environment(worker_dir)
    
    print("[-] Environment Verified (Python 3.10)")

    # 1. Hardware Detection
    platform_mode = "cpu"
    if not args.force_cpu:
        platform_mode = detect_platform()
    
    # 2. Submodule Setup
    vendor_dir = worker_dir / "vendor"
    init_submodule(vendor_dir)

    # 3. Dependency Injection
    install_system_dependencies(platform_mode, vendor_dir)

    # 4. Model Fetching
    download_models(vendor_dir)

    print("\n[+] Initialization Complete!")
    print(f"    To run adapter manually: {worker_dir}/.venv/bin/python worker/gpt_sovits_adapter.py")

if __name__ == "__main__":
    main()
