import sys
from pathlib import Path
import shutil
import asyncio

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

# Ensure pydub is installed (it should be per requirements)
try:
    from pydub import AudioSegment
except ImportError:
    print("pydub not installed. Please pip install pydub")
    sys.exit(1)

from core.gen_audio import GenAudio

async def main():
    base_dir = PROJECT_ROOT
    output_dir = base_dir / "tests" / "manual_audio_test"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    source_file = base_dir / "assets/audios/ko/male/guwon.mp3"
    
    if not source_file.exists():
        print(f"Source file not found: {source_file}")
        return

    print(f"[-] Source: {source_file}")
    print(f"[-] Output Dir: {output_dir}")

    # Load Source
    print("[-] Loading audio...")
    audio = AudioSegment.from_file(source_file)
    print(f"    Length: {len(audio)}ms, dBFS: {audio.dBFS}")
    
    # Instantiate GenAudio
    gen_audio = GenAudio(base_dir)

    # --- Test 1: Silence Trimming ---
    print("\n[Test 1] Silence Trimming")
    # Insert silence at Start and End (easier to verify)
    silence_2s = AudioSegment.silent(duration=2000)
    
    # Prepend and Append silence
    bad_audio = silence_2s + audio + silence_2s
    
    path_silence_added = output_dir / "silence_added.mp3"
    bad_audio.export(path_silence_added, format="mp3")
    print(f"    [+] Created: {path_silence_added.name} (Length: {len(bad_audio)}ms)")
    
    # Prepare target for optimization
    path_silence_removed = output_dir / "silence_removed.mp3"
    shutil.copy(path_silence_added, path_silence_removed)
    
    print(f"    [*] Running remove_silence on {path_silence_removed.name}...")
    # CALL GRANULAR METHOD
    async for log in gen_audio.remove_silence(path_silence_removed):
        print(f"      {log}")
        
    # Verify length reduction
    cleaned_audio = AudioSegment.from_file(path_silence_removed)
    print(f"    [=] Result Length: {len(cleaned_audio)}ms (Original Input Audio: {len(audio)}ms)")

    # --- Test 2: Normalization ---
    print("\n[Test 2] Normalization")
    
    # Amplified (+10dB)
    amplified_audio = audio + 10
    path_amplified = output_dir / "amplified.mp3"
    amplified_audio.export(path_amplified, format="mp3")
    print(f"    [+] Created: {path_amplified.name} (dBFS: {amplified_audio.dBFS:.2f})")
    
    path_norm_amp = output_dir / "normalized-foramplified.mp3"
    shutil.copy(path_amplified, path_norm_amp)
    
    print(f"    [*] Running normalize_audio on {path_norm_amp.name}...")
    # CALL GRANULAR METHOD
    async for log in gen_audio.normalize_audio(path_norm_amp):
        print(f"      {log}")
        
    norm_amp_audio = AudioSegment.from_file(path_norm_amp)
    print(f"    [=] Result dBFS: {norm_amp_audio.dBFS:.2f} (Target ~ -14 LUFS)")
    print(f"    [=] Result Length: {len(norm_amp_audio)}ms (Should match original: {len(audio)}ms)")


    # Reduced (-20dB)
    reduced_audio = audio - 20
    path_reduced = output_dir / "reduced.mp3"
    reduced_audio.export(path_reduced, format="mp3")
    print(f"    [+] Created: {path_reduced.name} (dBFS: {reduced_audio.dBFS:.2f})")
    
    path_norm_red = output_dir / "normalized-reduced.mp3"
    shutil.copy(path_reduced, path_norm_red)
    
    print(f"    [*] Running normalize_audio on {path_norm_red.name}...")
    # CALL GRANULAR METHOD
    async for log in gen_audio.normalize_audio(path_norm_red):
        print(f"      {log}")

    norm_red_audio = AudioSegment.from_file(path_norm_red)
    print(f"    [=] Result dBFS: {norm_red_audio.dBFS:.2f} (Target ~ -14 LUFS)")
    print(f"    [=] Result Length: {len(norm_red_audio)}ms (Should match original: {len(audio)}ms)")

    print("\n[Done] Check output directory for results.")

if __name__ == "__main__":
    asyncio.run(main())
