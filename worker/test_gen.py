import sys
from pathlib import Path
from gpt_sovits_adapter import GPTSoVITSAdapter

# Paths
BASE_DIR = Path(__file__).parent.parent
VENDOR_DIR = BASE_DIR / "worker" / "vendor"
ADAPTER_TEST_OUT = BASE_DIR / "output_test_tts.wav"

def main():
    print("[-] Initializing Adapter in Test Mode...")
    
    # Auto-detect venv python
    venv_python = BASE_DIR / "worker" / ".venv" / "bin" / "python3"
    if not venv_python.exists():
        # Fallback for Windows or system
        if sys.platform == "win32":
            venv_python = BASE_DIR / "worker" / ".venv" / "Scripts" / "python.exe"
    
    target_python = str(venv_python) if venv_python.exists() else sys.executable
    print(f"[-] Using Python: {target_python}")

    print(f"[-] Using Python: {target_python}")

    adapter = GPTSoVITSAdapter(base_dir=BASE_DIR, python_exec=target_python)

    # Define Model Paths (Default downloaded ones)
    gpt_model = VENDOR_DIR / "GPT-SoVITS/GPT_SoVITS/pretrained_models/s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt"
    sovits_model = VENDOR_DIR / "GPT-SoVITS/GPT_SoVITS/pretrained_models/s2G488k.pth"
    
    # User provided Ref
    ref_audio = BASE_DIR / "materials/audios/inputs/ja/kato-kaede.mp3" 

    try:
        if not ref_audio.exists():
            print(f"[!] Warning: Reference audio not found at {ref_audio}")
            # print("    Please place a 'ref.wav' in the project root to test generation.")
            return

        print("[-] Generating Voice via CLI...")
        output = adapter.generate_voice(
            gpt_model_path=gpt_model,
            sovits_model_path=sovits_model,
            ref_audio_path=ref_audio,
            ref_text="僕がそんなに子供じゃないって。私からしたら少年はまだまだ少年だぞ。うりうり。",
            ref_language="ja",
            target_text="こんにちは。これはテスト音声です。", # Use Japanese as V1 model (s2G488k) does not support Korean
            target_language="ja",
            output_path=ADAPTER_TEST_OUT
        )
        print(f"[+] Success! Generated: {output}")

    except Exception as e:
        print(f"[!] Test Failed: {e}")

if __name__ == "__main__":
    main()
