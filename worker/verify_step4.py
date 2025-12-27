
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

ruby_track_found = False
ruby_segments = 0

for track in tracks:
    t_type = track.get("type")
    # Identify ruby track? CapCut has no explicit "ruby" type, just text.
    # But our code creates it as the SECOND text track (or distinct one).
    # Let's count text tracks.
    if t_type == "text":
        segs = track.get("segments", [])
        print(f"Text Track found with {len(segs)} segments.")
        # Check if segments have 'scale' in clip (our ruby signature)
        if segs:
            first_clip = segs[0].get("clip", {})
            if "scale" in first_clip:
                print(" -> Identified as Ruby Track (scale present)")
                ruby_track_found = True
                ruby_segments = len(segs)
            else:
                 print(" -> Identified as Main Subtitle Track")

if ruby_track_found:
    print(f"SUCCESS: Ruby track found with {ruby_segments} segments.")
else:
    print("FAILURE: No Ruby track found.")
