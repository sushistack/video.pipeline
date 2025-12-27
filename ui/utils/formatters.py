"""Formatting Utilities"""


def srt_to_ms(timestamp: str) -> int:
    """
    Convert SRT timestamp to milliseconds.
    
    Args:
        timestamp: SRT format "00:00:10,500"
        
    Returns:
        Milliseconds (int)
    """
    parts = timestamp.replace(",", ".").split(":")
    if len(parts) == 3:
        h, m, s = parts
        total_seconds = int(h) * 3600 + int(m) * 60 + float(s)
        return int(total_seconds * 1000)
    return 0


def ms_to_srt(ms: int) -> str:
    """
    Convert milliseconds to SRT timestamp format.
    
    Args:
        ms: Milliseconds (int)
        
    Returns:
        SRT format "00:00:10,500"
    """
    seconds = ms / 1000
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")
