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

    # Define Model Paths (Updated to verified works V3+V4)
    models_dir = BASE_DIR / "models" / "pretrained"
    gpt_model = models_dir / "s1v3.ckpt"
    sovits_model = models_dir / "gsv-v4-pretrained/s2Gv4.pth"
    
    # User provided Ref (Dynamic search)
    # Start with user-provided path, fallback to search
    ref_audio = BASE_DIR / "materials/audios/inputs/ko/male/guwon.mp3"
    
    if not ref_audio.exists():
         print(f"[!] Default ref audio not found: {ref_audio}")
         try:
            found_audios = list((BASE_DIR / "materials").rglob("*.mp3"))
            if found_audios:
                ref_audio = found_audios[0]
                print(f"[*] Switching to available audio: {ref_audio}")
         except Exception:
             pass 

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
            ref_text="오늘이라는 커다란 열매를 맺은 우리, 우리 역사에 대한 자긍심은 국가미래 발전에 원동력입니다.",
            ref_language="ko",
            target_text="안녕하세요. 이것은 테스트 음성입니다. 잘 들리시나요?", 
            target_language="ko",
            output_path=ADAPTER_TEST_OUT
        )
        print(f"[+] Success! Generated: {output}")

    except Exception as e:
        print(f"[!] Test Failed: {e}")

if __name__ == "__main__":
    main()
