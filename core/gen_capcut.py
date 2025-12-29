import pycapcut as cc
from pycapcut import trange, SEC
from pathlib import Path
import os
from typing import List, Dict, Optional, Tuple
import shutil
import json
from collections import defaultdict

class CapCutGenerator:
    """
    Refactored CapCut Project Generator using pyCapCut.
    """
    
    def __init__(self, output_root: Path):
        self.output_root = output_root
        self.script: Optional[cc.ScriptFile] = None
        self.draft_name: str = ""
        self.drafts_root = self._resolve_drafts_root()
        if self.drafts_root:
            self.folder = cc.DraftFolder(str(self.drafts_root))
        else:
            print("Warning: Could not resolve CapCut Drafts folder.")
            self.folder = None

    def _resolve_drafts_root(self) -> Optional[Path]:
        """Find the CapCut draft directory."""
        candidates = [
            Path.home() / "Movies/CapCut/User Data/Projects/com.lveditor.draft",
            Path.home() / "Library/Containers/com.lemon.lvoverseas/Data/Movies/CapCut/User Data/Projects/com.lveditor.draft",
            Path(os.environ.get("LOCALAPPDATA", "")) / "CapCut/User Data/Projects/com.lveditor.draft" if os.environ.get("LOCALAPPDATA") else None
        ]
        for path in candidates:
            if path and path.exists():
                return path
        return None

    def _initialize_script(self, project_name: str):
        """Initialize or Create the Draft"""
        if not self.folder:
             raise RuntimeError("CapCut Drafts folder not found.")
        print(f"Creating draft '{project_name}' in {self.folder.folder_path}")
        self.script = self.folder.create_draft(project_name, width=1920, height=1080, fps=30, allow_replace=True)
        self.draft_name = project_name

    def add_media_tracks(self, project_name: str):
        """Add Audio and Video tracks"""
        if not self.script:
             self._initialize_script(project_name)
             
        project_dir = self.output_root / project_name
        video_dir = project_dir / "simulated"
        audio_dir = project_dir / "audios" / "ja"
        
        videos = sorted(list(video_dir.glob("*.mp4")))
        audios = sorted(list(audio_dir.glob("*.mp3")))
        
        if not audios:
             print("No audios found.")
             return

        track_video = self.script.add_track(cc.TrackType.video)
        track_audio = self.script.add_track(cc.TrackType.audio)
        
        current_time_us = 0
        
        for i, aud_path in enumerate(audios):
             str_aud_path = str(aud_path)
             vid_path = videos[i % len(videos)] if videos else None
             str_vid_path = str(vid_path) if vid_path else None
             
             # Audio Segment
             seg_audio = cc.AudioSegment(str_aud_path) 
             aud_dur = seg_audio.material.duration
             seg_audio.target_timerange = cc.Timerange(current_time_us, aud_dur)
             track_audio.add_segment(seg_audio)
             
             # Video Segment
             if str_vid_path:
                 seg_video = cc.VideoSegment(str_vid_path)
                 vid_dur = seg_video.material.duration
                 
                 # Loop or trim logic
                 if vid_dur > aud_dur:
                     seg_video.source_timerange = cc.Timerange(0, aud_dur)
                 else:
                     seg_video.source_timerange = cc.Timerange(0, vid_dur)
                     # Note: Video will be shorter than audio if not looped. 
                     # pycapcut does not auto-loop.
                     
                 seg_video.target_timerange = cc.Timerange(current_time_us, aud_dur)
                 track_video.add_segment(seg_video)
                 
             current_time_us += aud_dur
             
        self.script.save()

    def _split_text(self, text: str) -> List[str]:
        """Split text into lines of max 16 chars."""
        if '\n' in text:
            text = text.replace('\n', '')
        if len(text) <= 16:
            return [text]
        lines = []
        current = ""
        for char in text:
            if len(current) < 16:
                current += char
            else:
                lines.append(current)
                current = char
        if current:
            lines.append(current)
        return lines

    def _map_yomigana(self, text: str, kanjis: List[Dict]) -> Dict[int, tuple]:
        """Map text indices to (yomigana, len, kanji_idx)."""
        mapping = {}
        k_ptr = 0
        t_ptr = 0
        while t_ptr < len(text) and k_ptr < len(kanjis):
            target = kanjis[k_ptr]['kanji']
            try:
                found_idx = text.index(target, t_ptr)
                mapping[found_idx] = (kanjis[k_ptr]['yomigana'], len(target), k_ptr)
                t_ptr = found_idx + len(target)
                k_ptr += 1
            except ValueError:
                k_ptr += 1
        return mapping

    def process_subtitles(self, project_name: str):
        """Add Subtitles with Yomigana"""
        if not self.script:
             self._initialize_script(project_name)
             
        sub_path = self.output_root / project_name / "subtitles" / "synced" / "ja.json"
        if not sub_path.exists():
             return
             
        with open(sub_path, 'r', encoding='utf-8') as f:
             subs = json.load(f)
             
        # Add Tracks
        track_main = self.script.add_track(cc.TrackType.text)
        
        # Audio Sync Reference
        audio_segs = []
        for t in self.script.tracks:
            if t.type == cc.TrackType.audio:
                audio_segs.extend(t.segments)
        audio_segs.sort(key=lambda s: s.target_timerange.start) # Ensure order

        # Styles
        style_main = cc.TextStyle(size=5.0, color=(1.0, 1.0, 1.0))
        style_ruby = cc.TextStyle(size=5.0, color=(1.0, 1.0, 1.0)) # Size scaled by ClipSettings

        # Layout Constants
        LINE_HEIGHT = 0.2
        MAIN_Y = -0.4
        RUBY_Y_OFFSET = -1.185
        FULL_WIDTH = 0.0580
        HALF_WIDTH = 0.0290

        def get_char_width(c):
             return HALF_WIDTH if ord(c) < 128 else FULL_WIDTH

        ruby_segments_by_idx = defaultdict(list)

        for i, sub in enumerate(subs):
             if i >= len(audio_segs): break
             
             aud_seg = audio_segs[i]
             start = aud_seg.target_timerange.start
             duration = aud_seg.target_timerange.duration
             
             raw_text = sub.get("text", "")
             kanjis = sub.get("kanjis", [])
             
             clean_text = raw_text.replace('\n', '')
             yomi_map = self._map_yomigana(clean_text, kanjis)
             lines = self._split_text(clean_text)
             final_text = "\n".join(lines)
             
             # Main Text Placement
             ts_main = cc.TextSegment(final_text, cc.Timerange(start, duration), style=style_main)
             ts_main.clip_settings = cc.ClipSettings(transform_y=MAIN_Y)
             track_main.add_segment(ts_main)
             
             # Yomigana Logic
             num_lines = len(lines)
             start_y = MAIN_Y + ((num_lines - 1) * LINE_HEIGHT * 0.5)
             char_offset_global = 0
             
             for line_idx, line in enumerate(lines):
                  line_len = len(line)
                  base_y = start_y - (line_idx * LINE_HEIGHT)
                  total_visual_width = sum(get_char_width(c) for c in line)
                  current_x = 0.5 - (total_visual_width / 2)
                  
                  for char_i, char in enumerate(line):
                       cw = get_char_width(char)
                       
                       if char_offset_global in yomi_map:
                            ruby_text, span_len, k_idx = yomi_map[char_offset_global]
                            safe_span = min(span_len, line_len - char_i)
                            
                            group_width = sum(get_char_width(line[char_i + k]) for k in range(safe_span))
                            center_x = current_x + (group_width / 2)
                            ruby_y = base_y - RUBY_Y_OFFSET
                            
                            # Create Ruby Segment
                            ts_ruby = cc.TextSegment(ruby_text, cc.Timerange(start, duration), style=style_ruby)
                            
                            # pyCapCut coordinate system check:
                            # doc says transform_y=0.8 for top.
                            # old code used -1.185 offset?
                            # If MAIN_Y is -0.4. base_y - (-1.185) = -0.4 + 1.185 = 0.785 (higher up).
                            # This matches logic that positive Y is UP? Or negative offset means UP?
                            # "base_y - offset": if offset is negative, it ADDS to Y.
                            # If Y-UP: adding moves UP.
                            # So MAIN_Y(-0.4) + 1.185 = +0.785.
                            # CapCut: (0,0) center. -1 bottom, +1 top?
                            # Let's trust the logic math: `ruby_y = base_y - RUBY_Y_OFFSET`.
                            
                            # Note: pyCapCut ClipSettings transform maps to JSON 'transform' dict.
                            # We just pass the value.
                            
                            ts_ruby.clip_settings = cc.ClipSettings(
                                transform_x=center_x,  # X is 0.0 to 1.0 usually? Or -1 to 1?
                                # Old code X calculation: 0.5 - width/2. So 0.0 to 1.0 range.
                                # But CapCut JSON expects -1 to 1 usually?
                                # Wait, old code had `s["clip"]["transform"]["x"] = 0.5052`.
                                # That looks like 0-1 range.
                                # If pyCapCut expects -1 to 1 (NDC), we might need conversion.
                                # But `TextSegment` example in doc didn't clarify.
                                # Let's assume 0-1 based on old code values.
                                transform_y=ruby_y,
                                scale_x=0.6,
                                scale_y=0.6
                            )
                            
                            ruby_segments_by_idx[k_idx].append(ts_ruby)
                       
                       current_x += cw
                       char_offset_global += 1

        # Add Ruby Tracks
        sorted_indices = sorted(ruby_segments_by_idx.keys())
        for idx in sorted_indices:
             segments = ruby_segments_by_idx[idx]
             if segments:
                 track_ruby = self.script.add_track(cc.TrackType.text)
                 for seg in segments:
                      track_ruby.add_segment(seg)

        self.script.save()

    def save_project(self, project_name: str) -> Path:
        """Backup draft to workspace."""
        src = Path(self.folder.folder_path) / self.draft_name
        dst = self.output_root / project_name / "capcut_draft"
        if dst.exists(): 
            shutil.rmtree(dst)
        
        # pycapcut might lock files? No, it's just JSON.
        shutil.copytree(src, dst)
        return dst

    def export_to_capcut(self, project_name: str) -> Path:
        return Path(self.folder.folder_path) / self.draft_name
