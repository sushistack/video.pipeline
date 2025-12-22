import sys
from pathlib import Path

# Ensure root is in path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from worker.caption_gen import CaptionGenerator

def test_caption():
    print("[-] Initializing Caption Test...")
    
    base_dir = Path(__file__).resolve().parent.parent
    test_audio = base_dir / "materials/audios/inputs/ja/kato-kaede.mp3"
    output_dir = base_dir / "outputs/subtitles"
    
    if not test_audio.exists():
        print(f"[!] Test audio not found: {test_audio}")
        return

    cg = CaptionGenerator()
    try:
        cg.generate(test_audio, output_dir)
        print("[+] Caption generation test successful!")
    except Exception as e:
        print(f"[!] Info: {e}")

if __name__ == "__main__":
    test_caption()
