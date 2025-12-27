
import json
from pathlib import Path

draft_path = Path(r"d:\video.pipeline\outputs\sample\capcut_draft\draft_content.json")

if not draft_path.exists():
    print("Draft file not found!")
    exit(1)

with open(draft_path, "r", encoding="utf-8") as f:
    data = json.load(f)

tracks = data.get("tracks", [])
print(f"Total Tracks: {len(tracks)}")

for track in tracks:
    t_type = track.get("type")
    seg_count = len(track.get("segments", []))
    print(f"Track Type: {t_type}, Segments: {seg_count}")

materials = data.get("materials", {})
print("Materials Count:")
for k, v in materials.items():
    print(f"  {k}: {len(v)}")
