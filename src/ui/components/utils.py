import re
from pathlib import Path

# Optional import for Sudachi
try:
    from sudachipy import Dictionary, SplitMode
    SUDACHI_AVAILABLE = True
except ImportError:
    SUDACHI_AVAILABLE = False

def parse_srt(file_path):
    if not file_path.exists():
        return []
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    
    if not content:
        return []

    items = []
    blocks = content.split("\n\n")
    
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) >= 3:
            # Line 0: Index (ignore)
            # Line 1: Time
            # Line 2+: Text
            time_line = lines[1]
            if "-->" in time_line:
                start, end = time_line.split(" --> ")
                text = "\n".join(lines[2:])
                items.append({
                    "start": start.strip(),
                    "end": end.strip(),
                    "text": text
                })
    return items

def normalize_text_for_xml(text, tokenizer_obj, mode):
    """
    Converts text for better TTS:
    - English -> Katakana (reading)
    - Kanji -> Hiragana
    - Others -> Keep Surface
    """
    if not tokenizer_obj:
        return text
        
    try:
        tokens = tokenizer_obj.tokenize(text, mode)
    except Exception:
        return text

    out = ""
    for t in tokens:
        surf = t.surface()
        read = t.reading_form()
        
        # 1. English -> Katakana
        if re.search(r'[a-zA-Z]', surf):
            out += read
        # 2. Kanji -> Hiragana
        elif any('\u4e00' <= c <= '\u9fff' for c in surf):
            # Convert Katakana Reading to Hiragana
            hira = "".join([chr(ord(c) - 96) if ('\u30a1' <= c <= '\u30f6') else c for c in read])
            out += hira
        else:
            out += surf
    return out

def get_kanjis(text):
    """
    Extracts Kanji words and their Yomigana (Hiragana) from text.
    Returns list of {"kanji": "...", "yomigana": "..."}
    """
    if not SUDACHI_AVAILABLE:
        return []

    try:
        # Initialize lazily to avoid overhead if unused
        # Fixed API usage for SudachiPy 0.6+
        tok = Dictionary(dict="core").create()
        mode = SplitMode.C
        tokens = tok.tokenize(text, mode)
    except Exception as e:
        # print(f"Sudachi Error: {e}") # Debug if needed
        return []

    results = []
    for t in tokens:
        surf = t.surface()
        
        # Check if token contains Kanji
        if any('\u4e00' <= c <= '\u9fff' for c in surf):
            read = t.reading_form()
            # Convert Katakana Reading to Hiragana
            hira = "".join([chr(ord(c) - 96) if ('\u30a1' <= c <= '\u30f6') else c for c in read])
            
            results.append({
                "kanji": surf,
                "yomigana": hira
            })
            
    return results
