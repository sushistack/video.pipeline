import asyncio
import os
import time
from pathlib import Path
from watchfiles import awatch, Change
from .transcriber import Transcriber

class Watcher:
    def __init__(self, input_dir: Path, output_dir: Path):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.transcriber = Transcriber() # Initialize Gemini Transcriber
        
        # Supported extensions
        self.extensions = {'.mp4', '.mkv', '.mov', '.mp3', '.wav', '.flac'}
        
        print(f"[*] Watcher initialized for: {self.input_dir}")
        print(f"[*] Output directory: {self.output_dir}")

    async def start(self):
        print("[-] Waiting for new files...")
        async for changes in awatch(self.input_dir):
            for change, file_path in changes:
                if change == Change.added:
                    path = Path(file_path)
                    if path.suffix.lower() in self.extensions:
                         print(f"[!] New file detected: {path.name}")
                         await self.process_file_with_debounce(path)

    async def process_file_with_debounce(self, path: Path):
        """
        Wait until file size is stable (upload/copy complete) before processing.
        """
        print(f"[-] Checking stability for: {path.name}...")
        
        # Simple stability check: wait 1s, check size, repeat until stable
        last_size = -1
        stable_count = 0
        
        while stable_count < 3: # Wait for 3 consecutive stable checks (3 seconds)
            try:
                current_size = path.stat().st_size
            except FileNotFoundError:
                print(f"[!] File disappeared: {path.name}")
                return

            if current_size == last_size and current_size > 0:
                stable_count += 1
            else:
                stable_count = 0
                last_size = current_size
            
            await asyncio.sleep(1.0)
            
        print(f"[-] File is stable: {path.name}. Starting breakdown...")
        
        try:
            # Run blocking transcription in a thread to keep watcher responsive
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.transcriber.transcribe, path, self.output_dir)
            print(f"[+] Processing done for: {path.name}")
            
        except Exception as e:
            print(f"[!] Error processing {path.name}: {e}")

if __name__ == "__main__":
    # Test runner
    BASE_DIR = Path(__file__).resolve().parent.parent
    IN_DIR = BASE_DIR / "materials/videos"
    OUT_DIR = BASE_DIR / "materials/scripts"
    
    IN_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    watcher = Watcher(IN_DIR, OUT_DIR)
    
    try:
        asyncio.run(watcher.start())
    except KeyboardInterrupt:
        print("[*] Watcher stopped.")
