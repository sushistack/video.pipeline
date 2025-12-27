import os
import yaml
import subprocess
import sys
import tempfile
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
INFERENCE_SCRIPT = PROJECT_ROOT / "worker" / "inference_cli_custom.py"
PYTHON_EXE = PROJECT_ROOT / "worker" / ".venv" / "Scripts" / "python.exe"
OUTPUT_ROOT = PROJECT_ROOT / "outputs" / "comprehensive_test"

# Models
GPT_MODEL = PROJECT_ROOT / "models" / "pretrained" / "s1v3.ckpt"
SOVITS_MODELS = {
    "v4": PROJECT_ROOT / "models" / "pretrained" / "gsv-v4-pretrained" / "s2Gv4.pth",
    "v2Pro": PROJECT_ROOT / "models" / "pretrained" / "v2Pro" / "s2Gv2Pro.pth",
    "v2ProPlus": PROJECT_ROOT / "models" / "pretrained" / "v2Pro" / "s2Gv2ProPlus.pth"
}

# Target Texts for Generation
TARGET_TEXTS = {
    "ko": "안녕하세요? 이것은 한국어 음성 합성 테스트입니다. 잘 들리시나요?",
    "en": "Hello, this is a test of the English speech synthesis. Can you hear me clearly?",
    "ja": "こんにちは。これは日本語の音声合成テストです。聞こえますか？"
}

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def run_test(sovits_name, sovits_path, speaker_name, speaker_info, target_lang):
    print(f"\n[Test] Model: {sovits_name} | Speaker: {speaker_name} | Lang: {target_lang}")
    
    # Verify Model Path
    if not sovits_path.exists():
        print(f"  [Skipped] Model file not found: {sovits_path}")
        return

    # Prepare Paths
    ref_audio_path = PROJECT_ROOT / "materials" / "audios" / "inputs" / target_lang / speaker_info["gender"] / f"{speaker_name}.mp3"
    
    if not ref_audio_path.exists():
        print(f"  [Skipped] Reference audio not found: {ref_audio_path}")
        return

    # Use ref_text from config, fall back to temp file
    ref_text = speaker_info.get("ref_text", "")
    if not ref_text:
         print(f"  [Skipped] No ref_text in config for {speaker_name}")
         return
         
    # Create temp ref text file (CLI expects file)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, suffix=".txt") as f:
        f.write(ref_text)
        temp_ref_file = Path(f.name)
        
    # Create temp target text file
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False, suffix=".txt") as f:
        f.write(TARGET_TEXTS[target_lang])
        temp_target_file = Path(f.name)

    output_dir = OUTPUT_ROOT / sovits_name / target_lang
    output_dir.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        str(PYTHON_EXE),
        str(INFERENCE_SCRIPT),
        "--gpt_model", str(GPT_MODEL),
        "--sovits_model", str(sovits_path),
        "--ref_audio", str(ref_audio_path),
        "--ref_text", str(temp_ref_file),
        "--ref_lang", speaker_info["ref_lang"],
        "--target_text", str(temp_target_file),
        "--target_lang", target_lang,
        "--output_path", str(output_dir)
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("  [Success]")
        # print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("  [Failed]")
        print(e.stderr)
    finally:
        # Cleanup
        if temp_ref_file.exists(): temp_ref_file.unlink()
        if temp_target_file.exists(): temp_target_file.unlink()

def main():
    config = load_config()
    speakers = config.get("speakers", {})
    
    # Select representative speakers for each language
    # Adjust these names based on what actually exists in materials folder that matches config
    selected_speakers = {
        "ko": "guwon",        # config: guwon
        "en": "noah-williams",# config: noah-williams
        "ja": "suzuki-haruki" # config: suzuki-haruki
    }

    for sovits_name, sovits_path in SOVITS_MODELS.items():
        print(f"--- Testing SoVITS Model: {sovits_name} ---")
        for lang, speaker_key in selected_speakers.items():
            if speaker_key in speakers:
                run_test(sovits_name, sovits_path, speaker_key, speakers[speaker_key], lang)
            else:
                print(f"Speaker {speaker_key} not found in config.yaml")

if __name__ == "__main__":
    main()
