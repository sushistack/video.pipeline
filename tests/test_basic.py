"""Basic test script to verify core package imports and initialization."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core import GenAudio
from core.tts import TTSProviderType, Qwen3TTSProvider


def main():
    """Run basic tests"""
    print("=" * 60)
    print("Qwen3-TTS Core Package - Basic Test")
    print("=" * 60)

    # Test 1: Import verification
    print("\n[Test 1] Import verification...")
    print("[OK] Successfully imported core modules")

    # Test 2: GenAudio initialization
    print("\n[Test 2] Initializing GenAudio...")
    gen_audio = GenAudio(base_dir=project_root)
    print("[OK] GenAudio initialized")

    # Test 3: Provider listing
    print("\n[Test 3] Listing available providers...")
    providers = GenAudio.get_available_providers()
    for p in providers:
        print(f"   - {p['name']}: {p['description']}")
    print("[OK] Providers listed")

    # Test 4: Provider type check
    print("\n[Test 4] Checking provider type...")
    assert TTSProviderType.QWEN3_TTS.value == "qwen3_tts"
    print("[OK] Provider type verified")

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
