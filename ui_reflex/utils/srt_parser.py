"""SRT Parsing Utilities"""
from pathlib import Path
import re


def parse_srt(srt_path: Path) -> list[dict]:
    """
    Parse SRT file into structured data.
    
    Args:
        srt_path: Path to SRT file
        
    Returns:
        List of dicts with 'start', 'end', 'text' keys
    """
    if not srt_path.exists():
        return []
    
    content = srt_path.read_text(encoding="utf-8")
    items = []
    
    # Split by double newlines (SRT block separator)
    blocks = re.split(r'\n\n+', content.strip())
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            # Line 0: index
            # Line 1: timestamp (00:00:00,000 --> 00:00:01,000)
            # Line 2+: text
            times = lines[1].split(' --> ')
            text = " ".join(lines[2:])
            
            items.append({
                "start": times[0].strip(),
                "end": times[1].strip() if len(times) > 1 else times[0].strip(),
                "text": text
            })
    
    return items
