
import json
from pathlib import Path

template_path = Path(r"d:\video.pipeline\materials\templates\capcut.draft.template.json")

with open(template_path, "r", encoding="utf-8") as f:
    data = json.load(f)

if "texts" in data.get("materials", {}):
    texts = data["materials"]["texts"]
    if texts:
        print("--- Text Content Sample ---")
        print(texts[0].get("content"))
        print("---------------------------")
    else:
        print("No text materials found.")
else:
    print("Materials or texts key missing.")
