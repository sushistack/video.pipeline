import sys
import shutil
from .utils import run_cmd

def check_python_version():
    """Ensure running on Python 3.10."""
    major, minor = sys.version_info[:2]
    print(f"[*] Checking Python version: {major}.{minor}")
    if major != 3 or minor != 10:
        print("[!] Error: GPT-SoVITS requires Python 3.10 exactly.")
        print(f"    Current version: {sys.version}")
        sys.exit(1)

def detect_platform():
    """
    Detects the hardware platform for torch optimization.
    Returns: 'rocm', 'mps', or 'cpu'
    """
    print("[*] Checking Hardware Acceleration...")
    
    # 1. macOS (MPS)
    if sys.platform == "darwin":
        print("    Detected macOS (Apple Silicon/Intel). Assuming MPS/CPU.")
        return "mps"

    # 2. AMD ROCm
    if shutil.which("rocm-smi"):
        print("    Found 'rocm-smi'. Assuming AMD GPU (ROCm) present.")
        return "rocm"
    
    # 3. CUDA Check (via PyTorch if available, else assuming CPU/CUDA)
    try:
        import torch
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            if "AMD" in device_name or "Radeon" in device_name:
                return "rocm"
            return "cuda" # Standard NVIDIA
    except ImportError:
        pass

    print("    No specific accelerator found in environment. Defaulting to CPU/Standard.")
    return "cpu"
