from pathlib import Path

def apply_patches(vendor_dir: Path):
    """
    Apply necessary patches to vendor code.
    """
    print("[*] Applying patches...")
    _patch_inference_cli(vendor_dir)

def _patch_inference_cli(vendor_dir: Path):
    target_file = vendor_dir / "GPT-SoVITS/GPT_SoVITS/inference_cli.py"
    if not target_file.exists():
        print(f"    [!] Warning: {target_file} not found. Skipping patch.")
        return

    content = target_file.read_text(encoding="utf-8")
    
    # Check if already patched
    if "韩文" in content:
        print(f"    [OK] {target_file.name} is already patched.")
        return

    print(f"    [+] Patching {target_file.name} to support more languages...")
    
    # Simple string replacement to expand choices
    # Original choices in the file (based on observation)
    old_ref = 'choices=["中文", "英文", "日文"],'
    new_ref = 'choices=["中文", "英文", "日文", "粤语", "韩文"],'
    
    old_target = 'choices=["中文", "英文", "日文", "中英混合", "日英混合", "多语种混合"],'
    new_target = 'choices=["中文", "英文", "日文", "粤语", "韩文", "中英混合", "日英混合", "粤英混合", "韩英混合", "多语种混合", "多语种混合(粤语)"],'

    new_content = content.replace(old_ref, new_ref).replace(old_target, new_target)
    
    if new_content != content:
        target_file.write_text(new_content, encoding="utf-8")
        print("    [+] Patch applied successfully.")

def _patch_inference_webui(vendor_dir: Path):
    target_file = vendor_dir / "GPT-SoVITS/GPT_SoVITS/inference_webui.py"
    if not target_file.exists():
        return

    content = target_file.read_text(encoding="utf-8")
    
    # Check if already patched
    if "torch.backends.mps.is_available()" in content:
        print(f"    [OK] {target_file.name} is already MPS-enabled.")
        return

    print(f"    [+] Patching {target_file.name} for MacOS MPS support...")
    
    # Original device selection logic
    old_code = '''if torch.cuda.is_available():
    device = "cuda"
else:
    device = "cpu"'''
    
    # New logic: Check env var -> Check CUDA -> Check MPS -> Default CPU
    new_code = '''if os.environ.get("GPT_SOVITS_DEVICE"):
    device = os.environ["GPT_SOVITS_DEVICE"]
elif torch.cuda.is_available():
    device = "cuda"
elif torch.backends.mps.is_available():
    device = "mps"
else:
    device = "cpu"'''

    new_content = content.replace(old_code, new_code)
    
    if new_content != content:
        target_file.write_text(new_content, encoding="utf-8")
        print("    [+] MPS Patch applied successfully.")
    else:
        print("    [!] Warning: Could not find device selection code to patch.")

def apply_patches(vendor_dir: Path):
    """
    Apply necessary patches to vendor code.
    """
    print("[*] Applying patches...")
    _patch_inference_cli(vendor_dir)
    _patch_inference_webui(vendor_dir)

