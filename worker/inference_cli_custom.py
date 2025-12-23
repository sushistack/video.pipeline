import sys
import os
import argparse
import shutil
import torchaudio
import torch
import soundfile as sf
import numpy as np

# Force soundfile backend to avoid torchcodec issues
try:
    torchaudio.set_audio_backend("soundfile")
except Exception:
    pass

# Monkey patch torchaudio.load because torchcodec is broken in this env (MPS/MacOS specific fix)
def my_torchaudio_load(filepath, **kwargs):
    # data: (samples, channels) or (samples,)
    data, sr = sf.read(filepath)
    if data.ndim == 1:
        data = data[..., np.newaxis] # (samples, 1)
    # torchaudio expects (channels, samples)
    data = data.T # (channels, samples)
    return torch.from_numpy(data).float(), sr

torchaudio.load = my_torchaudio_load

from pathlib import Path
from typing import Optional, List, Any

# 1. Dependency Path Configuration
# Assumes this script is in worker/inference_cli_custom.py
CURRENT_DIR = Path(__file__).resolve().parent
WORKER_ROOT = CURRENT_DIR
VENDOR_ROOT = WORKER_ROOT / "vendor" / "GPT-SoVITS"

# Add GPT-SoVITS modules to sys.path
if str(VENDOR_ROOT) not in sys.path:
    sys.path.append(str(VENDOR_ROOT))

# Add inner modules (text, AR, etc.)
GPT_SOVITS_INNER = VENDOR_ROOT / "GPT_SoVITS"
if str(GPT_SOVITS_INNER) not in sys.path:
    sys.path.append(str(GPT_SOVITS_INNER))

# Add eres2net for sv.py relative imports
ERES2NET_DIR = GPT_SOVITS_INNER / "eres2net"
if str(ERES2NET_DIR) not in sys.path:
    sys.path.append(str(ERES2NET_DIR))

# 2. Import GPT-SoVITS modules
try:
    # Model Absolute Paths for env injection (inference_webui dependencies)
    # Point to the models inside vendor/GPT-SoVITS since we haven't moved them centrally yet
    bert_path = VENDOR_ROOT / "GPT_SoVITS" / "pretrained_models" / "chinese-roberta-wwm-ext-large"
    cnhubert_path = VENDOR_ROOT / "GPT_SoVITS" / "pretrained_models" / "chinese-hubert-base"
    sv_model_path = VENDOR_ROOT / "GPT_SoVITS" / "pretrained_models" / "sv" / "pretrained_eres2netv2w24s4ep4.ckpt"
    
    os.environ["bert_path"] = str(bert_path)
    os.environ["cnhubert_base_path"] = str(cnhubert_path)
    os.environ["sv_model_path"] = str(sv_model_path)
    
    # Default Paths to prevent init errors
    # Use the files we found in vendor/GPT-SoVITS/pretrained_models
    default_gpt_path = VENDOR_ROOT / "GPT_SoVITS" / "pretrained_models" / "s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt"
    default_sovits_path = VENDOR_ROOT / "GPT_SoVITS" / "pretrained_models" / "s2G488k.pth"
    
    os.environ["gpt_path"] = str(default_gpt_path)
    os.environ["sovits_path"] = str(default_sovits_path)
    
    from tools.i18n.i18n import I18nAuto
    from GPT_SoVITS.inference_webui import change_gpt_weights, change_sovits_weights, get_tts_wav
except ImportError as e:
    import traceback
    traceback.print_exc(file=sys.stderr)
    print(f"Error importing GPT-SoVITS modules: {e}", file=sys.stderr)
    print(f"Make sure the submodule is initialized and '{VENDOR_ROOT}' is correct.", file=sys.stderr)
    print(f"Sys Path: {sys.path}", file=sys.stderr)
    sys.exit(1)

i18n = I18nAuto()

def synthesize(
    gpt_model_path: str,
    sovits_model_path: str,
    ref_audio_path: str,
    ref_text_path: str,
    ref_language: str,
    target_text_path: str,
    target_language: str,
    output_path: str,
    speed_factor: float = 1.0,
) -> None:
    """
    Synthesize audio using GPT-SoVITS.
    """

    # Read Reference Text
    try:
        with open(ref_text_path, "r", encoding="utf-8") as file:
            ref_text = file.read().strip()
    except Exception as e:
        print(f"Error reading reference text: {e}", file=sys.stderr)
        return

    # Read Target Text
    try:
        with open(target_text_path, "r", encoding="utf-8") as file:
            target_text = file.read().strip()
    except Exception as e:
        print(f"Error reading target text: {e}", file=sys.stderr)
        return

    print(f"Loading Models...\nGPT: {gpt_model_path}\nSoVITS: {sovits_model_path}")

    # Change Model Weights
    try:
        change_gpt_weights(gpt_path=gpt_model_path)
        
        # change_sovits_weights returns a generator in some versions, consume it.
        sovits_gen = change_sovits_weights(sovits_path=sovits_model_path)
        if hasattr(sovits_gen, '__iter__'):
             for _ in sovits_gen: pass 
            
    except Exception as e:
        print(f"Error loading models: {e}")

    print(f"Synthesizing... (Speed: {speed_factor})")
    
    try:
        synthesis_result = get_tts_wav(
            ref_wav_path=ref_audio_path,
            prompt_text=ref_text,
            prompt_language=i18n(ref_language),
            text=target_text,
            text_language=i18n(target_language),
            top_p=1,
            temperature=1,
            speed=speed_factor
        )
        
        result_list = list(synthesis_result)
        
        if result_list:
            last_sampling_rate, last_audio_data = result_list[-1]
            output_wav_path = os.path.join(output_path, "output.wav")
            
            # Create output dir
            os.makedirs(output_path, exist_ok=True)
            
            sf.write(output_wav_path, last_audio_data, last_sampling_rate)
            print(f"Audio saved to {output_wav_path}")
        else:
            print("No audio generated.")
            
    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stderr)
        print(f"Error during synthesis: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Custom GPT-SoVITS Inference CLI with Speed Control")
    parser.add_argument("--gpt_model", required=True, help="Path to the GPT model file")
    parser.add_argument("--sovits_model", required=True, help="Path to the SoVITS model file")
    parser.add_argument("--ref_audio", required=True, help="Path to the reference audio file")
    parser.add_argument("--ref_text", required=True, help="Path to the reference text file")
    parser.add_argument(
        "--ref_language", required=True, 
        choices=["中文", "英文", "日文", "韩文", "粤语", "zh", "en", "ja", "ko", "yue"], 
        help="Language of the reference audio"
    )
    parser.add_argument("--target_text", required=True, help="Path to the target text file")
    parser.add_argument(
        "--target_language",
        required=True,
        choices=["中文", "英文", "日文", "韩文", "粤语", "中英混合", "日英混合", "多语种混合", "zh", "en", "ja", "ko", "yue", "auto"],
        help="Language of the target text",
    )
    parser.add_argument("--output_path", required=True, help="Path to the output directory")
    parser.add_argument("--speed_factor", type=float, default=1.0, help="Speech speed factor (0.5 to 2.0 recommended)")

    args = parser.parse_args()

    # Language Map
    lang_map = {
        "zh": "中文", "en": "英文", "ja": "日文", "ko": "多语种混合", "yue": "粤语",
        "auto": "多语种混合"
    }
    
    ref_lang = lang_map.get(args.ref_language, args.ref_language)
    target_lang = lang_map.get(args.target_language, args.target_language)

    synthesize(
        gpt_model_path=args.gpt_model,
        sovits_model_path=args.sovits_model,
        ref_audio_path=args.ref_audio,
        ref_text_path=args.ref_text,
        ref_language=ref_lang,
        target_text_path=args.target_text,
        target_language=target_lang,
        output_path=args.output_path,
        speed_factor=args.speed_factor
    )

if __name__ == "__main__":
    main()
