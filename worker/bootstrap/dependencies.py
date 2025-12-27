import sys
from pathlib import Path
from .utils import run_cmd

def install_system_dependencies(platform_mode, vendor_dir: Path):
    """
    Install PyTorch and other deps based on platform.
    """
    print(f"[*] Installing dependencies (Platform: {platform_mode})...")
    
    # Ensure pip is available
    try:
        import pip
    except ImportError:
        print("[!] 'pip' module not found. Bootstrapping with ensurepip...")
        try:
            run_cmd(f'"{sys.executable}" -m ensurepip --default-pip')
        except Exception as e:
            print(f"[!] ensurepip failed: {e}. Trying to proceed via uv if possible or failing.")
            # If ensurepip fails, we might rely on uv if we switched to uv pip. 
            # But let's stick to python pip for now as we set pip_base that way.
            
    # Use the current python executable to ensure we install into the active venv
    pip_base = f'"{sys.executable}" -m pip install'
    
    # 1. PyTorch Selection
    if platform_mode == "rocm":
        torch_cmd = f"{pip_base} torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.0"
        print(f"    [ROCm] {torch_cmd}")
        run_cmd(torch_cmd)
    elif platform_mode == "mps":
        print("    [macOS] Installing standard PyTorch (MPS supported)...")
        # Pinning to stable version to avoid torchcodec issues in newer/nightly builds
        run_cmd(f"{pip_base} torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1")
    else:
        print("    [Default] Installing standard PyTorch...")
        run_cmd(f"{pip_base} torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1")

    # 2. GPT-SoVITS Requirements
    req_path = vendor_dir / "GPT-SoVITS" / "requirements.txt"
    if req_path.exists():
        print("[*] Installing vendor requirements...")
        run_cmd(f"{pip_base} -r {req_path}")

    # Install API dependencies (fastapi uvicorn requests) and CLI deps (soundfile)
    print("    Installing adapter dependencies...")
    # Force numpy<2 to avoid compatibility issues with Numba/Librosa
    run_cmd(f'{pip_base} fastapi uvicorn requests soundfile "numpy<2" ffmpeg-python google-genai PyYAML sudachipy sudachidict_core streamlit reflex mutagen python-mecab-ko python-mecab-ko-dic')

    # Create eunjeon shim for g2pk2
    create_eunjeon_shim(vendor_dir.parent / ".venv" / "Lib" / "site-packages")

def create_eunjeon_shim(site_packages: Path):
    """
    Creates a 'eunjeon.py' shim in site-packages that redirects to python-mecab-ko.
    This resolves the dependency issue where g2pk2 expects 'eunjeon' module.
    """
    shim_path = site_packages / "eunjeon.py"
    if site_packages.exists() and not shim_path.exists():
        print(f"[*] Creating eunjeon shim for g2pk2 at {shim_path}...")
        try:
            with open(shim_path, "w", encoding="utf-8") as f:
                f.write("from mecab import MeCab as Mecab\n")
        except Exception as e:
            print(f"[!] Failed to create eunjeon shim: {e}")
