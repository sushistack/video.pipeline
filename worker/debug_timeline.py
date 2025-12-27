
import json
from pathlib import Path

draft_path = Path(r"d:\video.pipeline\outputs\sample\capcut_draft\draft_content.json")

if not draft_path.exists():
    print("Draft file not found!")
    exit(1)

with open(draft_path, "r", encoding="utf-8") as f:
    data = json.load(f)

def print_track_info(track_type):
    print(f"\n--- {track_type} Track segments ---")
    tracks = [t for t in data["tracks"] if t["type"] == track_type]
    for t_idx, track in enumerate(tracks):
        print(f"Track {t_idx} (ID: {track['id']}):")
        segments = sorted(track["segments"], key=lambda x: x["target_timerange"]["start"])
        for i, seg in enumerate(segments):
            start = seg["target_timerange"]["start"]
            dur = seg["target_timerange"]["duration"]
            end = start + dur
            r_idx = seg.get("render_index", "N/A")
            print(f"  [{i}] Start: {start/1000000:.3f}s, End: {end/1000000:.3f}s, Dur: {dur/1000000:.3f}s, R_Idx: {r_idx}")

print_track_info("video")
print_track_info("audio")
print_track_info("text")
