import os
import json
import yaml
import time
import typing_extensions as typing
import google.generativeai as genai
from pathlib import Path
from dotenv import load_dotenv

# Optional import for Sudachi (lazy load in method if needed)
try:
    from sudachipy import tokenizer, dictionary
    SUDACHI_AVAILABLE = True
except ImportError:
    SUDACHI_AVAILABLE = False

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

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
    def __init__(self, config_path="config.yaml"):
        base_dir = Path(__file__).resolve().parent.parent
        self.config_file = base_dir / config_path
        
        # Load Config
        if self.config_file.exists():
            with open(self.config_file, "r") as f:
                self.config = yaml.safe_load(f)
                self.model_name = self.config.get("gemini", {}).get("model_id", "gemini-2.0-flash-exp")
        else:
            self.model_name = "gemini-2.0-flash-exp"

        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found.")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
        
        # Initialize Sudachi if available
        if SUDACHI_AVAILABLE:
            self.tokenizer = dictionary.Dictionary(dict="core").create()
            self.mode = tokenizer.Tokenizer.SplitMode.C
            print("[*] SudachiPy initialized for Yomigana extraction.")
        else:
            print("[!] SudachiPy not found. Yomigana extraction will be skipped.")
            self.tokenizer = None

        print(f"[*] CaptionGenerator initialized with {self.model_name}")

    def generate(self, audio_path: Path, output_dir: Path, target_languages: list[str] = ["ja", "en", "ko"], generate_json: bool = True, speaker_count: typing.Optional[int] = None):
        output_dir.mkdir(parents=True, exist_ok=True)
        base_name = audio_path.stem

        # STEP 1: Generate Base Japanese Captions (Audio -> Text)
        print("[-] Step 1: Generating Base Japanese Captions...")
        captions = self._generate_base_captions(audio_path, speaker_count)
        
        # Save JA SRT immediately
        if "ja" in target_languages:
            self._save_srt(captions, output_dir / f"{base_name}.ja.srt", "ja")

        # STEP 2: Translation (Text -> Text)
        if "en" in target_languages or "ko" in target_languages:
            print("[-] Step 2: Translating Captions...")
            captions = self._translate_captions(captions, target_languages)
            
            # Save Translated SRTs
            if "en" in target_languages:
                self._save_srt(captions, output_dir / f"{base_name}.en.srt", "en")
            if "ko" in target_languages:
                self._save_srt(captions, output_dir / f"{base_name}.ko.srt", "ko")

        # STEP 3: Yomigana Extraction (Text -> Meta)
        # Only if JA is requested AND Json is generating
        if "ja" in target_languages and generate_json:
            print("[-] Step 3: Extracting Yomigana (SudachiPy)...")
            captions = self._add_yomigana(captions)
            
            # Save Master JSON
            master_json_path = output_dir / f"{base_name}.json"
            with open(master_json_path, "w", encoding="utf-8") as f:
                json.dump(captions, f, indent=2, ensure_ascii=False)
            print(f"[+] Saved Master JSON: {master_json_path}")
            return master_json_path
        
        return None
    def _generate_base_captions(self, audio_path: Path, speaker_count: typing.Optional[int] = None) -> list[CaptionItem]:
        # Upload
        myfile = genai.upload_file(audio_path)
        while myfile.state.name == "PROCESSING":
            time.sleep(1)
            myfile = genai.get_file(myfile.name)
            
        speaker_hint = f"There are exactly {speaker_count} speakers." if speaker_count else "Identify different speakers if possible (e.g., 'Speaker 1', 'Speaker 2')."

        prompt = f"""
        Listen to the audio and transcribe the original Japanese text.
        {speaker_hint}
        
        Output a JSON array of objects with these fields:
        - start (HH:MM:SS,mmm)
        - end (HH:MM:SS,mmm)
        - speaker (string, e.g. "Speaker 1")
        - text_ja (transcription)
        
        Output ONLY the raw JSON.
        """
        response = self.model.generate_content([myfile, prompt])
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
        response = self.model.generate_content(prompt)
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

if __name__ == "__main__":
    import sys
    # ... test stub ...
