#!/usr/bin/env python3
"""
Download Qwen3-TTS models to ~/.qwen/models/

Usage:
    python scripts/download_qwen_models.py [--model CustomVoice|Base|VoiceDesign|all]
"""

import argparse
from pathlib import Path
from huggingface_hub import snapshot_download


def download_model(model_name: str, model_id: str):
    """Download model from HuggingFace to ~/.qwen/models/"""
    download_path = Path.home() / ".qwen" / "models" / model_name
    
    if download_path.exists():
        print(f"✓ Model already exists: {download_path}")
        print(f"  Path: {download_path}")
        return download_path
    
    print(f"[*] Downloading {model_name}...")
    print(f"    HuggingFace ID: {model_id}")
    print(f"    Download path: {download_path}")
    
    try:
        path = snapshot_download(
            repo_id=model_id,
            local_dir=str(download_path),
            local_dir_use_symlinks=False,
            resume_download=True
        )
        print(f"✓ Downloaded to: {path}")
        return download_path
    except Exception as e:
        print(f"✗ Download failed: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Download Qwen3-TTS models")
    parser.add_argument(
        "--model",
        choices=["CustomVoice", "Base", "VoiceDesign", "all"],
        default="all",
        help="Model to download (default: all)"
    )
    args = parser.parse_args()
    
    models = {
        "CustomVoice": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        "Base": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "VoiceDesign": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
    }
    
    if args.model == "all":
        for name, model_id in models.items():
            download_model(name, model_id)
            print()
    else:
        download_model(args.model, models[args.model])


if __name__ == "__main__":
    main()
