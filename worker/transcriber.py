import os
import time
import yaml
import google.generativeai as genai
from pathlib import Path
from dotenv import load_dotenv

# Load env variables (API keys)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

class Transcriber:
    def __init__(self, config_path="config.yaml"):
        # Load Config
        base_dir = Path(__file__).resolve().parent.parent
        self.config_file = base_dir / config_path
        
        if self.config_file.exists():
            with open(self.config_file, "r") as f:
                self.config = yaml.safe_load(f)
                self.model_name = self.config.get("gemini", {}).get("model_id", "gemini-2.0-flash-exp")
                print(f"[*] Loaded config from {config_path}")
        else:
            self.model_name = os.getenv("GEMINI_MODEL_ID", "gemini-2.0-flash-exp")
            print(f"[!] Config file not found, using default/env: {self.model_name}")

        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables.")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
        print(f"[*] Transcriber initialized with Gemini Model: {self.model_name}")

    def transcribe(self, media_path: Path, output_dir: Path) -> Path:
        """
        Uploads file to Gemini, generates transcript, and saves to output_dir.
        """
        if not media_path.exists():
            raise FileNotFoundError(f"File not found: {media_path}")

        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"[-] Uploading to Gemini: {media_path.name}...")
        
        # Upload file
        myfile = genai.upload_file(media_path)
        
        # Wait for processing state
        while myfile.state.name == "PROCESSING":
            print("    Url processing...")
            time.sleep(2)
            myfile = genai.get_file(myfile.name)
            
        if myfile.state.name == "FAILED":
            raise RuntimeError("Gemini File Upload Failed.")

        print(f"[-] Generating transcript for: {media_path.name}")
        
        # Prompt for pure transcription
        prompt = "Please transcribe this audio file. Output ONLY the transcription text, no preamble or extra commentary. Ignore background noise."
        
        response = self.model.generate_content([myfile, prompt])
        
        # Save output
        text = response.text.strip()
        filename = media_path.stem + ".txt"
        output_path = output_dir / filename
        
        output_path.write_text(text, encoding="utf-8")
        print(f"[+] Saved transcript to: {output_path}")
        
        # Cleanup remote file (optional but good practice)
        # genai.delete_file(myfile.name) 
        
        return output_path

if __name__ == "__main__":
    import sys
    # Test stub
    if len(sys.argv) > 1:
        f = Path(sys.argv[1])
        t = Transcriber()
        t.transcribe(f, Path("materials/scripts"))
