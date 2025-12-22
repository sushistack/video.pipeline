import sys
from pathlib import Path

# Ensure root is in path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from worker.transcriber import Transcriber

def test_stt():
    print("[-] Initializing Transcriber Test...")
    
    # Use existing audio content if available
    base_dir = Path(__file__).resolve().parent.parent
    test_audio = base_dir / "materials/audios/inputs/ja/kato-kaede.mp3"
    output_dir = base_dir / "materials/scripts"
    
    if not test_audio.exists():
        print(f"[!] Test audio not found at: {test_audio}")
        print("    Please ensure 'materials/audios/inputs/ja/kato-kaede.mp3' exists.")
        return

    transcriber = Transcriber() # Use default Gemini Flash
    
    try:
        print(f"[-] Transcribing {test_audio}...")
        result_path = transcriber.transcribe(test_audio, output_dir)
        print(f"[+] Success! Transcript saved to: {result_path}")
        print(f"[-] Content preview: {result_path.read_text(encoding='utf-8')[:100]}...")
    except Exception as e:
        print(f"[!] STT Output Failed: {e}")

if __name__ == "__main__":
    test_stt()
