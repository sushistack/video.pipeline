import re
import datetime
from pathlib import Path

# Optional import for Sudachi
try:
    from sudachipy import Dictionary, SplitMode
    SUDACHI_AVAILABLE = True
except ImportError:
    SUDACHI_AVAILABLE = False

def parse_srt(file_path: Path):
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

def get_kanjis(text: str):
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
            
            # 1. Strip matching trailing Kana (Okurigana)
            # Checks if surface and reading end with the same Hiragana character
            while surf and hira and surf[-1] == hira[-1] and not ('\u4e00' <= surf[-1] <= '\u9fff'):
                surf = surf[:-1]
                hira = hira[:-1]

            # 2. Strip matching leading Kana (Prefixes)
            while surf and hira and surf[0] == hira[0] and not ('\u4e00' <= surf[0] <= '\u9fff'):
                surf = surf[1:]
                hira = hira[1:]
            
            # Only add if valid Kanji remains
            if surf and any('\u4e00' <= c <= '\u9fff' for c in surf):
                results.append({
                    "kanji": surf,
                    "yomigana": hira
                })
            
    return results

def srt_to_ms(time_str: str) -> int:
    """Converts SRT timestamp 'HH:MM:SS,mmm' to milliseconds."""
    hours, minutes, seconds = time_str.split(':')
    seconds, milliseconds = seconds.split(',')
    
    total_ms = (int(hours) * 3600000) + \
               (int(minutes) * 60000) + \
               (int(seconds) * 1000) + \
               int(milliseconds)
    return total_ms

def ms_to_srt(total_ms: int) -> str:
    """Converts milliseconds to SRT timestamp 'HH:MM:SS,mmm'."""
    hours = total_ms // 3600000
    total_ms %= 3600000
    minutes = total_ms // 60000
    total_ms %= 60000
    seconds = total_ms // 1000
    milliseconds = total_ms % 1000
    
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02},{int(milliseconds):03}"

def format_timestamp_json(ms_total: int) -> str:
    """Formats milliseconds to JSON format MM:SS:fff (e.g. 02:23:408)"""
    # Note: User sample '00:02:232' (2s 232ms) -> MM:SS:mmm
    seconds = ms_total // 1000
    ms = ms_total % 1000
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02}:{secs:02}:{ms:03}"
