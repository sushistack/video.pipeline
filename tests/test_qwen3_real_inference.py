import asyncio
import sys
import os
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

import torch
from core.tts.qwen3_tts import Qwen3TTSProvider
from core.tts.base import TTSConfig, VoiceConfig, ModelConfig


async def generate_audio(
    provider, model, text, lang, speaker, filename, ref_audio_path=None
):
    output_path = project_root / "assets" / "outputs" / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    config = TTSConfig(
        text=text,
        language=lang,
        output_path=output_path,
        voice=VoiceConfig(
            voice_id=speaker,
            use_preset_speaker=ref_audio_path is None,
            ref_audio_path=ref_audio_path,
        ),
    )

    print(f"\n[*] Starting generation for {lang}...")
    print(f"[*] Text: {config.text}")
    print(f"[*] Speaker: {speaker}")
    print(f"[*] Output: {config.output_path}")

    try:
        async for log in provider.generate(config, model):
            print(log)

        if output_path.exists():
            print(f"[SUCCESS] Audio generated and saved to {output_path}")
            print(f"File size: {output_path.stat().st_size} bytes")
        else:
            print(f"[FAILURE] Audio file {filename} was not created.")

    except Exception as e:
        print(f"[CRITICAL] Generation failed for {lang} with error: {e}")
        import traceback

        traceback.print_exc()


async def main():
    print("=== Qwen3-TTS Real Inference Test (Voice Cloning) ===")

    # GPU Status
    print(f"Python version: {sys.version}")
    print(f"PyTorch version: {torch.__version__}")
    cuda_available = torch.cuda.is_available()
    print(f"CUDA available: {cuda_available}")

    if cuda_available:
        print(f"GPU Device: {torch.cuda.get_device_name(0)}")
        # ROCm check (AMD GPU)
        if hasattr(torch.version, "hip") and torch.version.hip is not None:
            print(f"ROCm version: {torch.version.hip}")
    else:
        print("WARNING: CUDA not available. Running on CPU.")

    # Initialize Provider
    provider = Qwen3TTSProvider(project_root)

    # Get Base model config
    models = provider.get_available_models()
    base_model = next((m for m in models if m.name == "Base"), None)

    if not base_model:
        print("Error: Base model config not found.")
        return

    ref_audio_path = project_root / "assets" / "outputs" / "real_qwen3_en.wav"
    if not ref_audio_path.exists():
        print(f"Error: Reference audio not found at {ref_audio_path}")
        return

    # 1. English
    await generate_audio(
        provider,
        base_model,
        "Hello, this is a voice cloning test using the Base model.",
        "en",
        "ClonedVoice",
        "cloned_qwen3_en.wav",
        ref_audio_path=ref_audio_path,
    )

    # 2. Japanese
    await generate_audio(
        provider,
        base_model,
        "こんにちは、これはベースモデルを使用したボ이스クローニングのテストです。",
        "ja",
        "ClonedVoice",
        "cloned_qwen3_ja.wav",
        ref_audio_path=ref_audio_path,
    )

    # 3. Korean
    await generate_audio(
        provider,
        base_model,
        "안녕하세요, 이것은 베이스 모델을 사용한 보이스 클로닝 테스트입니다.",
        "ko",
        "ClonedVoice",
        "cloned_qwen3_ko.wav",
        ref_audio_path=ref_audio_path,
    )


if __name__ == "__main__":
    asyncio.run(main())
