"""Speaker Information Extraction"""


def extract_speaker(text: str) -> tuple[str, str]:
    """
    Extract speaker tag from text.
    
    Format: [Speaker]: Text → ("Speaker", "Text")
    
    Args:
        text: Input text potentially containing speaker tag
        
    Returns:
        Tuple of (speaker_name, clean_text)
    """
    if text.startswith("[") and "]" in text:
        end_idx = text.find("]")
        speaker = text[1:end_idx]
        remaining = text[end_idx+1:].strip()
        
        # Remove leading colon if present
        if remaining.startswith(":"):
            remaining = remaining[1:].strip()
        
        return speaker, remaining
    
    return "", text
