
import json
from pathlib import Path

template_path = Path(r"d:\video.pipeline\materials\templates\capcut.draft.template.json")

with open(template_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print("--- Track Analysis ---")
for track in data["tracks"]:
    if track["type"] == "text":
        seg = track["segments"][0]
        clip = seg["clip"]
        scale = clip.get("scale", {})
        transform = clip.get("transform", {})
        mat_id = seg["material_id"]
        
        # Find material
        material = next((m for m in data["materials"]["texts"] if m["id"] == mat_id), None)
        
        print(f"\nTrack ID: {track['id']}")
        print(f"  Scale: x={scale.get('x')}, y={scale.get('y')}")
        print(f"  Pos: x={transform.get('x')}, y={transform.get('y')}")
        if material:
            print(f"  Material Content: {material.get('content')}")
