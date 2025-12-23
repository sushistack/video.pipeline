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

PROJECT_MODELS = {
    # V2Pro
    "v2Pro/s2Gv2Pro.pth": "https://huggingface.co/lj1995/GPT-SoVITS/resolve/main/v2Pro/s2Gv2Pro.pth",
    
    # V4
    "s1v3.ckpt": "https://huggingface.co/lj1995/GPT-SoVITS/resolve/main/s1v3.ckpt",
    "gsv-v4-pretrained/s2Gv4.pth": "https://huggingface.co/lj1995/GPT-SoVITS/resolve/main/gsv-v4-pretrained/s2Gv4.pth",
    "gsv-v4-pretrained/vocoder.pth": "https://huggingface.co/lj1995/GPT-SoVITS/resolve/main/gsv-v4-pretrained/vocoder.pth",
}

def download_models(vendor_dir: Path):
    """
    Downloads required pretrained models if they don't exist.
    """
    print("[*] Verifying Pretrained Models...")
    gpt_sovits_root = vendor_dir / "GPT-SoVITS"
    project_root = vendor_dir.parent.parent # worker/vendor -> worker -> root
    
    # Ensure root exists inside vendor (should be done by git submodule)
    gpt_sovits_root.mkdir(parents=True, exist_ok=True)
    
    # 1. Vendor Models (Original logic)
    for rel_path, url in MODELS.items():
        target_path = gpt_sovits_root / "GPT_SoVITS" / rel_path
        
        if not target_path.exists():
            print(f"    Downloading (Vendor) {rel_path}...")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            run_cmd(f"curl -L -o '{str(target_path)}' '{url}'")
        else:
            print(f"    OK (Vendor): {rel_path}")

    # 2. Project Models (New logic)
    models_dir = project_root / "models" / "pretrained"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    for rel_path, url in PROJECT_MODELS.items():
        target_path = models_dir / rel_path
        
        if not target_path.exists():
            print(f"    Downloading (Project) {rel_path}...")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            run_cmd(f"curl -L -o '{str(target_path)}' '{url}'")
        else:
            print(f"    OK (Project): {rel_path}")
