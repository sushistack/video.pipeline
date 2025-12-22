from pathlib import Path
from .utils import run_cmd

REPO_URL = "https://github.com/RVC-Boss/GPT-SoVITS"

def init_submodule(vendor_dir: Path):
    """
    Ensures GPT-SoVITS submodule is initialized.
    """
    print("[*] Checking Submodules...")
    target_dir = vendor_dir / "GPT-SoVITS"
    
    if not target_dir.exists():
        print("    Adding submodule...")
        # Ensure we are in a git repo
        try:
            run_cmd("git rev-parse --is-inside-work-tree", check=True)
        except SystemExit: # run_cmd calls sys.exit(1) on failure, but we want to catch it or handle differently.
             # Wait, run_cmd exits. We need a check that doesn't exit.
             pass
        
        # Better approach: check if .git exists in root
        # Assuming we are at project root (cwd)
        if not Path(".git").exists():
            print("    [!] Not a git repository. Initializing git...")
            run_cmd("git init")
        
        # Git prefers relative paths for submodules
        try:
            rel_target = target_dir.relative_to(Path.cwd())
        except ValueError:
            # Fallback if specific relationship fails, though unlikely in this structure
            rel_target = target_dir

        run_cmd(f"git submodule add {REPO_URL} {rel_target}")
    
    print("    Updating submodule...")
    run_cmd("git submodule update --init --recursive")
    
    # Apply custom patches
    from .patches import apply_patches
    apply_patches(vendor_dir)
