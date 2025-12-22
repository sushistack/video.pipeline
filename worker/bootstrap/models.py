from pathlib import Path
from .utils import run_cmd

# Model URLs (Direct links or HuggingFace mirrors)
MODELS = {
    # Main Models
    "pretrained_models/s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt": "https://huggingface.co/lj1995/GPT-SoVITS/resolve/main/s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt",
    "pretrained_models/s2G488k.pth": "https://huggingface.co/lj1995/GPT-SoVITS/resolve/main/s2G488k.pth",
    "pretrained_models/s2D488k.pth": "https://huggingface.co/lj1995/GPT-SoVITS/resolve/main/s2D488k.pth",
    
    # NLP Models (Chinese-Roberta)
    "pretrained_models/chinese-roberta-wwm-ext-large/config.json": "https://huggingface.co/hfl/chinese-roberta-wwm-ext-large/resolve/main/config.json",
    "pretrained_models/chinese-roberta-wwm-ext-large/pytorch_model.bin": "https://huggingface.co/hfl/chinese-roberta-wwm-ext-large/resolve/main/pytorch_model.bin",
    "pretrained_models/chinese-roberta-wwm-ext-large/tokenizer.json": "https://huggingface.co/hfl/chinese-roberta-wwm-ext-large/resolve/main/tokenizer.json",

    # NLP Models (Chinese-Hubert-Base) - Required for GPT-SoVITS
    "pretrained_models/chinese-hubert-base/config.json": "https://huggingface.co/TencentGameMate/chinese-hubert-base/resolve/main/config.json",
    "pretrained_models/chinese-hubert-base/pytorch_model.bin": "https://huggingface.co/TencentGameMate/chinese-hubert-base/resolve/main/pytorch_model.bin",
    "pretrained_models/chinese-hubert-base/preprocessor_config.json": "https://huggingface.co/TencentGameMate/chinese-hubert-base/resolve/main/preprocessor_config.json",
}

def download_models(vendor_dir: Path):
    """
    Downloads required pretrained models if they don't exist.
    """
    print("[*] Verifying Pretrained Models...")
    gpt_sovits_root = vendor_dir / "GPT-SoVITS"
    
    # Ensure root exists inside vendor (should be done by git submodule)
    gpt_sovits_root.mkdir(parents=True, exist_ok=True)
    GPT_SOVITS_SUBDIR = gpt_sovits_root / "GPT_SoVITS" # Actual code dir usually has another layer or checks paths

    # NOTE: The repo structure puts pretrained_models under GPT_SoVITS/pretrained_models
    # Let's target the correct location relative to repo root
    
    for rel_path, url in MODELS.items():
        # Adjust path: The repo usually has them in GPT_SoVITS/pretrained_models
        # We need to check where the code expects them. 
        # User PRD check: `GPT_SoVITS/pretrained_models`
        
        target_path = gpt_sovits_root / "GPT_SoVITS" / rel_path
        
        if not target_path.exists():
            print(f"    Downloading {rel_path}...")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            # Use curl which is standard on macOS/Linux
            run_cmd(f"curl -L -o '{str(target_path)}' '{url}'")
        else:
            print(f"    OK: {rel_path}")
