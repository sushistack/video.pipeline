from pathlib import Path
from .utils import run_cmd

# Model URLs (Direct links or HuggingFace mirrors)
MODELS = {
    # V2 Base (Consolidated to v2/)
    "v2/s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt": "https://huggingface.co/lj1995/GPT-SoVITS/resolve/main/s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt",
    "v2/s2G488k.pth": "https://huggingface.co/lj1995/GPT-SoVITS/resolve/main/s2G488k.pth",
    "v2/s2D488k.pth": "https://huggingface.co/lj1995/GPT-SoVITS/resolve/main/s2D488k.pth",

    # NLP Models (BERT -> bert/)
    "bert/config.json": "https://huggingface.co/hfl/chinese-roberta-wwm-ext-large/resolve/main/config.json",
    "bert/pytorch_model.bin": "https://huggingface.co/hfl/chinese-roberta-wwm-ext-large/resolve/main/pytorch_model.bin",
    "bert/tokenizer.json": "https://huggingface.co/hfl/chinese-roberta-wwm-ext-large/resolve/main/tokenizer.json",

    # NLP Models (Hubert -> hubert/)
    "hubert/config.json": "https://huggingface.co/TencentGameMate/chinese-hubert-base/resolve/main/config.json",
    "hubert/pytorch_model.bin": "https://huggingface.co/TencentGameMate/chinese-hubert-base/resolve/main/pytorch_model.bin",
    "hubert/preprocessor_config.json": "https://huggingface.co/TencentGameMate/chinese-hubert-base/resolve/main/preprocessor_config.json",
    
    # Speaker Verification (SV -> sv/)
    # Note: Using likely path based on repo structure. If fail, will need correction.
    "sv/pretrained_eres2netv2w24s4ep4.ckpt": "https://huggingface.co/lj1995/GPT-SoVITS/resolve/main/pretrained_models/sv/pretrained_eres2netv2w24s4ep4.ckpt",

    # V2Pro
    "v2Pro/s2Gv2Pro.pth": "https://huggingface.co/lj1995/GPT-SoVITS/resolve/main/v2Pro/s2Gv2Pro.pth",
    "v2Pro/s2Gv2ProPlus.pth": "https://huggingface.co/lj1995/GPT-SoVITS/resolve/main/v2Pro/s2Gv2ProPlus.pth",
    
    # V4
    "s1v3.ckpt": "https://huggingface.co/lj1995/GPT-SoVITS/resolve/main/s1v3.ckpt",
    "gsv-v4-pretrained/s2Gv4.pth": "https://huggingface.co/lj1995/GPT-SoVITS/resolve/main/gsv-v4-pretrained/s2Gv4.pth",
    "gsv-v4-pretrained/vocoder.pth": "https://huggingface.co/lj1995/GPT-SoVITS/resolve/main/gsv-v4-pretrained/vocoder.pth",
}

def download_models(vendor_dir: Path):
    """
    Downloads required pretrained models to project_root/models/pretrained.
    """
    print("[*] Verifying Pretrained Models (Consolidated)...")
    project_root = vendor_dir.parent.parent
    models_dir = project_root / "models" / "pretrained"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    for rel_path, url in MODELS.items():
        target_path = models_dir / rel_path
        
        if not target_path.exists():
            print(f"    Downloading {rel_path}...")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            run_cmd(f"curl -L -o '{str(target_path)}' '{url}'")
        else:
            print(f"    OK: {rel_path}")
