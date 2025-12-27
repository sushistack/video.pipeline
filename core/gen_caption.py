import os
import sys

import json
import yaml
import time
import typing_extensions as typing
import warnings

# Suppress Google Generative AI deprecation warning (though we are migrating)
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")
from google import genai
from google.genai import types
import shutil
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Optional import for Sudachi (lazy load in method if needed)
try:
    from sudachipy import tokenizer, dictionary
    SUDACHI_AVAILABLE = True
except ImportError:
    SUDACHI_AVAILABLE = False

# Robust .env loading
env_path = Path(__file__).resolve().parent.parent / ".env"
print(f"[*] Looking for .env at: {env_path}")
if env_path.exists():
    load_dotenv(env_path)
    print(f"[*] Loaded .env from specific path.")
else:
    print(f"[!] .env not found at specific path, trying default search...")
    load_dotenv()

class KanjiInfo(typing.TypedDict):
    kanji: str
    yomigana: str

class CaptionItem(typing.TypedDict):
    start: str
    end: str
    text_ja: str
    text_en: typing.Optional[str]
    text_ko: typing.Optional[str]
    speaker: typing.Optional[str]
    kanjis: list[KanjiInfo]

class CaptionGenerator:
    def __init__(self, config_path="config.yaml", model_name: typing.Optional[str] = None):
        base_dir = Path(__file__).resolve().parent.parent
        self.config_file = base_dir / config_path
        
        # Load Config
        if self.config_file.exists():
            with open(self.config_file, "r") as f:
                self.config = yaml.safe_load(f)
                config_model = self.config.get("gemini", {}).get("model_id", "gemini-2.5-flash")
        else:
            config_model = "gemini-2.5-flash"
            
        # Priority: Argument > Config > Default
        self.model_name = model_name if model_name else config_model

        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found.")
        
        genai_client = genai.Client(api_key=self.api_key)
        self.client = genai_client
        self.model_name = self.model_name # keeping attribute for reference
        
        # Initialize Sudachi if available
        if SUDACHI_AVAILABLE:
            self.tokenizer = dictionary.Dictionary(dict="core").create()
            self.mode = tokenizer.Tokenizer.SplitMode.C
            print("[*] SudachiPy initialized for Yomigana extraction.")
        else:
            print("[!] SudachiPy not found. Yomigana extraction will be skipped.")
            self.tokenizer = None

        print(f"[*] CaptionGenerator initialized with {self.model_name}")

        # Load Prompts
        self.prompts_dir = base_dir / "assets" / "prompts"
        self.prompts_dir.mkdir(parents=True, exist_ok=True)


    def generate(self, audio_path: Path, output_dir: Path, target_languages: list[str] = ["ja", "en", "ko"], generate_json: bool = True, speaker_count: typing.Optional[int] = None):
        base_name = audio_path.stem
        
        # New Structure: output_dir / {base_name} / subtitles / {lang}.srt
        project_dir = output_dir / base_name
        subtitle_dir = project_dir / "subtitles"
        subtitle_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"[*] Project Directory: {project_dir}")



        # STEP 0: Audio Preprocessing (FFmpeg + Demucs)
        print("[-] Step 0: Preprocessing Audio (Loudnorm + Vocal Isolation)...")
        try:
            processed_audio = self._preprocess_audio(audio_path, project_dir / "temp")
            print(f"[+] Used Processed Audio: {processed_audio}")
        except Exception as e:
            print(f"[!] Preprocessing failed: {e}")
            print("[!] Falling back to original audio.")
            processed_audio = audio_path

        # STEP 1: Generate Base Japanese Captions (Audio -> Text)
        print("[-] Step 1: Generating Base Japanese Captions...")
        captions = self._generate_base_captions(processed_audio, speaker_count)
        
        # Save JA SRT immediately
        if "ja" in target_languages:
            self._save_srt(captions, subtitle_dir / "ja.srt", "ja")

        # STEP 2: Translation (Text -> Text)
        if "en" in target_languages or "ko" in target_languages:
            print("[-] Step 2: Translating Captions...")
            captions = self._translate_captions(captions, target_languages)
            
            # Save Translated SRTs
            if "en" in target_languages:
                self._save_srt(captions, subtitle_dir / "en.srt", "en")
            if "ko" in target_languages:
                self._save_srt(captions, subtitle_dir / "ko.srt", "ko")

        # STEP 3: Yomigana Extraction (Text -> Meta)
        # Only if JA is requested AND Json is generating
        if "ja" in target_languages and generate_json:
            print("[-] Step 3: Extracting Yomigana (SudachiPy)...")
            captions = self._add_yomigana(captions)
            
            # Save Master JSON
            master_json_path = subtitle_dir / f"{base_name}.json"
            with open(master_json_path, "w", encoding="utf-8") as f:
                json.dump(captions, f, indent=2, ensure_ascii=False)
            print(f"[+] Saved Master JSON: {master_json_path}")
            return master_json_path
        
        return None
    def _generate_base_captions(self, audio_path: Path, speaker_count: typing.Optional[int] = None) -> list[CaptionItem]:
        # Upload using new Client
        print(f"    [*] Uploading {audio_path.name}...")
        myfile = self.client.files.upload(file=str(audio_path))
        
        # Wait for processing
        while myfile.state.name == "PROCESSING":
            time.sleep(1)
            myfile = self.client.files.get(name=myfile.name)
            
        print(f"    [+] File Ready: {myfile.name}")
            
        speaker_hint = f"There are exactly {speaker_count} speakers." if speaker_count else "Identify different speakers if possible (e.g., 'speaker1', 'speaker2')."

        prompt = f"""
        Listen to the audio and transcribe the original Japanese text.
        {speaker_hint}
        
        Output a JSON array of objects with these fields:
        - start: timestamp in SRT format (HH:MM:SS,mmm) e.g., "00:00:05,230"
        - end: timestamp in SRT format (HH:MM:SS,mmm) e.g., "00:00:08,450"
        - speaker: string (e.g., "speaker1")
        - text_ja: transcription
        
        IMPORTANT: Use standard SRT timestamp format with HOURS:MINUTES:SECONDS,MILLISECONDS
        Example: "00:01:23,456" means 1 minute, 23 seconds, and 456 milliseconds
        
        Output ONLY the raw JSON array.
        """
        
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=[myfile, prompt]
        )
        return self._parse_json_response(response.text)

    def _translate_captions(self, captions: list[CaptionItem], targets: list[str]) -> list[CaptionItem]:
        # We process in batches if too large, but for shorts, one batch is usually fine.
        # We send the JSON text and ask for augmentation.
        
        prompt = f"""
        Translate the following Japanese captions to {', '.join([t for t in targets if t!='ja'])}.
        Preserve the 'start', 'end', 'speaker', and 'text_ja' fields exactly.
        Add 'text_en' and 'text_ko' fields to each object as requested.
        
        Input JSON:
        ```json
        {json.dumps(captions, ensure_ascii=False)}
        ```
        
        Output ONLY the raw JSON with translations added.
        """
        
        # Use text input only (faster/cheaper)
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        return self._parse_json_response(response.text)

    def _add_yomigana(self, captions: list[CaptionItem]) -> list[CaptionItem]:
        if not self.tokenizer:
            return captions
            
        for item in captions:
            text = item.get("text_ja", "")
            if not text:
                item["kanjis"] = []
                continue
                
            kanji_list = []
            tokens = self.tokenizer.tokenize(text, self.mode)
            
            for token in tokens:
                surface = token.surface()
                reading = token.reading_form() # katakana normally
                
                # Simple heuristic: if surface contains Kanji, it needs reading
                if self._has_kanji(surface):
                    # Convert reading to hiragana
                    yomigana = self._katakana_to_hiragana(reading)
                    kanji_list.append({
                        "kanji": surface,
                        "yomigana": yomigana
                    })
            
            item["kanjis"] = kanji_list
            
        return captions

    def _has_kanji(self, text: str) -> bool:
        # Check unicode range for CJK Unified Ideographs
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return True
        return False

    def _katakana_to_hiragana(self, text: str) -> str:
        # Simple shift
        return "".join([chr(ord(c) - 96) if ('\u30a1' <= c <= '\u30f6') else c for c in text])

    def _parse_json_response(self, text: str) -> list[CaptionItem]:
        try:
            clean = text.strip()
            if clean.startswith("```json"): clean = clean[7:]
            if clean.startswith("```"): clean = clean[3:]
            if clean.endswith("```"): clean = clean[:-3]
            return json.loads(clean)
        except json.JSONDecodeError:
            print(f"[!] JSON Error. Raw: {text[:100]}...")
            return []

    def _save_srt(self, captions: list[CaptionItem], path: Path, lang: str):
        content = ""
        key = f"text_{lang}"
        for idx, item in enumerate(captions, 1):
            text = item.get(key, "")
            speaker = item.get("speaker", "")
            
            # Format: [Speaker]: Text (if speaker exists)
            display_text = f"[{speaker}] {text}" if speaker else text
            
            content += f"{idx}\n{item['start']} --> {item['end']}\n{display_text}\n\n"
        path.write_text(content, encoding="utf-8")
        print(f"[+] Saved SRT ({lang}): {path}")

    def generate_xml_scenario(self, captions: list[dict], target_lang: str) -> str:
        """
        Generates an XML scenario using Gemini with strict specific rules:
        1. Transliterate English/Numbers to target language pronunciation.
        2. Strictly NO other changes to content.
        3. Match strict XML structure: <script><speaker_tag>Content</speaker_tag>...</script>
        """
        
        # Helper to simplify input for prompt
        minified_input = []
        for c in captions:
            txt = c.get("text", "")
            spk = "unknown"
            content = txt
            if txt.startswith("[") and "]" in txt:
                idx = txt.find("]")
                spk_raw = txt[1:idx]
                spk = "".join(x for x in spk_raw if x.isalnum()).lower()
                content = txt[idx+1:].strip()
                if content.startswith(":"): content = content[1:].strip()
            minified_input.append({"tag": spk, "text": content})

        # Load prompt from assets/prompts
        prompt_file = self.prompts_dir / f"scenario_refine_{target_lang}.txt"
        if not prompt_file.exists():
            print(f"[!] Warning: Scenario prompt for {target_lang} not found. Using English fallback.")
            prompt_file = self.prompts_dir / "scenario_refine_en.txt"
        
        if not prompt_file.exists():
             raise FileNotFoundError(f"Scenario prompt file not found: {prompt_file}")

        prompt_template = prompt_file.read_text(encoding="utf-8")
        
        # Safe replacement to avoid format() issues with other braces
        prompt = prompt_template.replace("{input_json}", json.dumps(minified_input, ensure_ascii=False))

        # Retry logic
        for attempt in range(3):
            try:
                print(f"[-] Generating XML Scenario for {target_lang} (Attempt {attempt+1}/3)...")
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                
                # Cleanup
                result = response.text.strip()
                if result.startswith("```xml"): result = result[6:]
                if result.startswith("```"): result = result[3:]
                if result.endswith("```"): result = result[:-3]
                result = result.strip()
                
                # Simple validation check
                if result.startswith("<script>") and result.endswith("</script>"):
                    return result
                else:
                    print(f"[!] Invalid XML format in response. Retrying...")
            except Exception as e:
                print(f"[!] Error generating scenario: {e}")
                time.sleep(1)
        
        raise ValueError("Failed to generate valid XML scenario after 3 attempts.")

    def _preprocess_audio(self, input_path: Path, output_dir: Path) -> Path:
        """
        1. Normalize loudness (FFmpeg)
        2. Isolate vocals (Demucs)
        Returns path to the isolated vocals.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Normalize
        normalized_path = output_dir / "normalized.wav"
        if not normalized_path.exists():
            print("    [*] Normalizing loudness...")
            cmd_norm = [
                "ffmpeg", "-y", "-i", str(input_path),
                "-af", "loudnorm=I=-16:LRA=11:TP=-1.5",
                str(normalized_path)
            ]
            subprocess.run(cmd_norm, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # 2. Vocal Separation (Demucs)
        # Demucs output structure: {output_dir}/htdemucs/{track_name}/vocals.wav
        # We need to correctly identify the track name demucs uses (usually filename without extension)
        track_name = normalized_path.stem
        demucs_out = output_dir / "demucs"
        expected_vocals = demucs_out / "htdemucs" / track_name / "vocals.wav"
        
        if not expected_vocals.exists():
            print("    [*] Separating vocals (Demucs)... This may take time.")
            # Run demucs
            # demucs --two-stems=vocals -o {out_dir} {input}
            cmd_demucs = [
                "demucs", "--two-stems=vocals",
                "-d", "cpu",
                "-o", str(demucs_out),
                str(normalized_path)
            ]
            # Capture output to avoid cluttering logs too much, but print if error
            try:
                subprocess.run(cmd_demucs, check=True) # Let it print progress
            except FileNotFoundError:
                 # Try python -m demucs if direct command not found
                cmd_demucs_py = [
                    sys.executable, "-m", "demucs", 
                    "--two-stems=vocals",
                    "-d", "cpu",
                    "-o", str(demucs_out),
                    str(normalized_path)
                ]
                subprocess.run(cmd_demucs_py, check=True)

        if expected_vocals.exists():
            return expected_vocals
        else:
            raise FileNotFoundError(f"Demucs output not found at {expected_vocals}")

    def refine_script(self, captions: list[CaptionItem]) -> list[CaptionItem]:
        """
        Refines the Japanese script by removing filler and focusing on story relevance.
        Uses assets/prompts/refine_script_ja.txt
        """
        prompt_file = self.prompts_dir / "refine_script_ja.txt"
        if not prompt_file.exists():
            print(f"[!] Warning: Refine prompt not found at {prompt_file}. Using default.")
            prompt_text = "Refine the following Japanese script to remove filler and improved flow."
        else:
            prompt_text = prompt_file.read_text(encoding="utf-8")

        prompt = f"""
        {prompt_text}

        # Input Data:
        {json.dumps(captions, ensure_ascii=False)}
        """
        
        for attempt in range(3):
            try:
                print(f"[-] Refining script with {self.model_name} (Attempt {attempt+1}/3)...")
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                result = self._parse_json_response(response.text)
                if result:
                    return result
                print("[!] Empty or invalid JSON received. Retrying...")
            except Exception as e:
                print(f"[!] Error during refinement: {e}")
                time.sleep(1)
        
        print("[!] Refinement failed after 3 attempts.")
        raise ValueError("Failed to refine script after 3 attempts. Please check logs.")


    def translate_refined_script(self, captions: list[CaptionItem], targets: list[str]) -> list[CaptionItem]:
        """
        Translates the refined script to target languages.
        Uses assets/prompts/translate_script.txt
        """
        prompt_file = self.prompts_dir / "translate_script.txt"
        if not prompt_file.exists():
            print(f"[!] Warning: Translate prompt not found at {prompt_file}. Using default.")
            prompt_text = "Translate the script to English and Korean."
        else:
            prompt_text = prompt_file.read_text(encoding="utf-8")
            
        prompt = f"""
        {prompt_text}
        
        # Input Data:
        {json.dumps(captions, ensure_ascii=False)}
        
        # Targets: {', '.join(targets)}
        """
        
        for attempt in range(3):
            try:
                print(f"[-] Translating refined script (Attempt {attempt+1}/3)...")
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                result = self._parse_json_response(response.text)
                if result:
                    return result
                print("[!] Empty or invalid JSON received. Retrying...")
            except Exception as e:
                print(f"[!] Error during translation: {e}")
                time.sleep(1)

        print("[!] Translation failed after 3 attempts.")
        raise ValueError("Failed to translate script after 3 attempts. Please check logs.")



    def simple_transcribe(self, audio_path: Path, lang: str = "ja") -> str:
        """Transcribe audio for reference text using Gemini"""
        try:
            print(f"    [*] Uploading for transcription: {audio_path.name}")
            myfile = self.client.files.upload(file=str(audio_path))
            
            while myfile.state.name == "PROCESSING":
                time.sleep(1)
                myfile = self.client.files.get(name=myfile.name)
            
            prompt = f"Transcribe this audio in {lang}. Output ONLY the transcription text. Do not include timestamps or speaker labels."
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[myfile, prompt]
            )
            if response.text:
                return response.text.strip()
            return ""
        except Exception as e:
            print(f"[!] Error transcribing {audio_path}: {e}")
            return ""

if __name__ == "__main__":
    import sys
    # ... test stub ...
