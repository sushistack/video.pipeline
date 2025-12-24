from src.ui.components.utils import get_kanjis, SUDACHI_AVAILABLE
import traceback

print(f"SUDACHI_AVAILABLE: {SUDACHI_AVAILABLE}")

text = "どうして遅くまで起きてたの？"
try:
    result = get_kanjis(text)
    print(f"Result for '{text}': {result}")
except Exception:
    traceback.print_exc()

# Also try explicit init to see error
if SUDACHI_AVAILABLE:
    try:
        from sudachipy import Dictionary, SplitMode
        print("Import successful")
        tok = Dictionary(dict="core").create()
        print("Dictionary created")
        mode = SplitMode.C
        tokens = tok.tokenize(text, mode)
        print(f"Tokenized: {[t.surface() for t in tokens]}")
    except Exception:
        traceback.print_exc()
