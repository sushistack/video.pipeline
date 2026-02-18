import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np
import os

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Mock heavy dependencies before importing provider
sys.modules["torch"] = MagicMock()
sys.modules["qwen_tts"] = MagicMock()
sys.modules["soundfile"] = MagicMock()

from core.tts.qwen3_tts import Qwen3TTSProvider
from core.tts.base import TTSConfig, VoiceConfig, ModelConfig


async def test_qwen3_generation():
    print("Starting Qwen3-TTS generation test...")

    # Setup paths
    base_dir = project_root
    assets_dir = base_dir / "assets" / "audios" / "ja"
    ref_audio_path = assets_dir / "test_speaker.wav"

    # Ensure output directory exists
    output_dir = base_dir / "assets" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Mock Qwen3TTSModel
    import qwen_tts

    mock_model = MagicMock()
    qwen_tts.Qwen3TTSModel.from_pretrained.return_value = mock_model

    # Mock soundfile.write to actually create the file
    import soundfile as sf

    def mock_sf_write(path, data, sr):
        with open(path, "wb") as f:
            f.write(b"dummy wav data")

    sf.write.side_effect = mock_sf_write

    # Mock torch.cuda.is_available
    import torch

    torch.cuda.is_available.return_value = False

    provider = Qwen3TTSProvider(base_dir)
    models = provider.get_available_models()

    # 1. Test Voice Cloning (Base model)
    print("\n--- Testing Voice Cloning (Base model) ---")
    output_path = output_dir / "test_qwen3_cloning.wav"
    voice_config = VoiceConfig(
        voice_id="test_speaker",
        ref_audio_path=ref_audio_path,
        ref_text="This is a test transcript for the dummy speaker.",
        use_preset_speaker=False,
    )

    config = TTSConfig(
        text="こんにちは、これはテスト입니다.",
        language="ja",
        output_path=output_path,
        voice=voice_config,
        extra_options={"instruct": "Happy"},
    )

    base_model = next(m for m in models if m.name == "Base")
    mock_model.generate_voice_clone.return_value = ([np.zeros(1000)], 24000)

    async for message in provider.generate(config, base_model):
        print(message)

    if output_path.exists():
        print(f"SUCCESS: Output file created at {output_path}")
        # os.remove(output_path)
    else:
        print("FAILURE: Output file not created")
        sys.exit(1)

    mock_model.generate_voice_clone.assert_called_once()
    print("SUCCESS: generate_voice_clone was called")

    # 2. Test CustomVoice with instruct
    print("\n--- Testing CustomVoice with instruct ---")
    output_path = output_dir / "test_qwen3_custom.wav"
    voice_config_preset = VoiceConfig(voice_id="Ono_Anna", use_preset_speaker=True)

    config_preset = TTSConfig(
        text="こんにちは、이것은 테스트입니다.",
        language="ja",
        output_path=output_path,
        voice=voice_config_preset,
        extra_options={"instruct": "Happy"},
    )

    custom_model = next(m for m in models if m.name == "CustomVoice")
    mock_model.generate_custom_voice.return_value = ([np.zeros(1000)], 24000)

    async for message in provider.generate(config_preset, custom_model):
        print(message)

    if output_path.exists():
        print(f"SUCCESS: Output file created at {output_path}")
        # os.remove(output_path)
    else:
        print("FAILURE: Output file not created")
        sys.exit(1)

    mock_model.generate_custom_voice.assert_called_once_with(
        text=config_preset.text,
        speaker="Ono_Anna",
        language="Japanese",
        instruct="Happy",
    )
    print("SUCCESS: generate_custom_voice was called with correct instruct")

    # 3. Test Japanese with emotion tag
    print("\n--- Testing Japanese with emotion tag ---")
    output_path = output_dir / "test_qwen3_ja_emotion.wav"
    mock_model.generate_custom_voice.reset_mock()

    config_ja_emotion = TTSConfig(
        text="(Excited) こんにちは",
        language="ja",
        output_path=output_path,
        voice=voice_config_preset,
    )

    async for message in provider.generate(config_ja_emotion, custom_model):
        print(message)

    if output_path.exists():
        print(f"SUCCESS: Output file created at {output_path}")
        # os.remove(output_path)

    mock_model.generate_custom_voice.assert_called_once_with(
        text="こんにちは",
        speaker="Ono_Anna",
        language="Japanese",
        instruct="Excited",
    )
    print("SUCCESS: Japanese emotion tag handled correctly")

    # 4. Test Korean with emotion tag
    print("\n--- Testing Korean with emotion tag ---")
    output_path = output_dir / "test_qwen3_ko_emotion.wav"
    mock_model.generate_custom_voice.reset_mock()

    config_ko_emotion = TTSConfig(
        text="(Sad) 안녕하세요",
        language="ko",
        output_path=output_path,
        voice=voice_config_preset,
    )

    async for message in provider.generate(config_ko_emotion, custom_model):
        print(message)

    if output_path.exists():
        print(f"SUCCESS: Output file created at {output_path}")
        # os.remove(output_path)

    mock_model.generate_custom_voice.assert_called_once_with(
        text="안녕하세요",
        speaker="Ono_Anna",
        language="Korean",
        instruct="Sad",
    )
    print("SUCCESS: Korean emotion tag handled correctly")


if __name__ == "__main__":
    asyncio.run(test_qwen3_generation())
