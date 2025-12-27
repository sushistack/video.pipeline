
import json
from pathlib import Path

template_path = Path(r"d:\video.pipeline\materials\templates\capcut.draft.template.json")

with open(template_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print("Top Level Keys:", list(data.keys()))

if "materials" in data:
    print("Materials Keys:", list(data["materials"].keys()))
    if "videos" in data["materials"] and len(data["materials"]["videos"]) > 0:
        print("Video Material Sample:", json.dumps(data["materials"]["videos"][0], indent=2))
    if "audios" in data["materials"] and len(data["materials"]["audios"]) > 0:
        print("Audio Material Sample:", json.dumps(data["materials"]["audios"][0], indent=2))
    if "texts" in data["materials"] and len(data["materials"]["texts"]) > 0:
        print("Text Material Sample:", json.dumps(data["materials"]["texts"][0], indent=2))
else:
    print("No 'materials' key found!")

if "tracks" in data:
    print("Tracks Count:", len(data["tracks"]))
    for track in data["tracks"]:
        print(f"Track Type: {track.get('type')}")
        if track.get('type') == 'video':
             print("Video Track Sample:", json.dumps(track, indent=2))
        if track.get('type') == 'audio':
             print("Audio Track Sample:", json.dumps(track, indent=2))
        
