"""Review Tab State Management"""
import reflex as rx
from pathlib import Path
import sys

# Add parent project to path (ui_reflex/states -> ui_reflex -> video.pipeline)
PARENT_DIR = Path(__file__).resolve().parent.parent.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

# Add ui_reflex to path
UI_DIR = Path(__file__).parent.parent
if str(UI_DIR) not in sys.path:
    sys.path.insert(0, str(UI_DIR))

from core.gen_caption import CaptionGenerator
from utils.srt_parser import parse_srt
from utils.speaker_extractor import extract_speaker


class ReviewState(rx.State):
    """State management for Review Tab"""
    
    # Data
    subtitles: list[dict] = []
    available_projects: list[str] = []
    current_project: str = ""
    deleted_rows: set[int] = set()  # Track deleted row IDs
    
    # UI toggles
    show_en: bool = True
    show_ja: bool = True
    
    # Setters for toggles
    def set_show_ja(self, value: bool):
        """Toggle Japanese display"""
        self.show_ja = value
    
    def set_show_en(self, value: bool):
        """Toggle English display"""
        self.show_en = value
    
    # Computed properties
    @rx.var
    def total_rows(self) -> int:
        """Total number of subtitle rows"""
        return len(self.subtitles)

    # Color Palette for Speakers
    COLORS: list[str] = [
        "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEEAD", 
        "#D4A5A5", "#9B59B6", "#3498DB", "#E67E22", "#2ECC71",
        "#F1C40F", "#1ABC9C", "#E74C3C", "#34495E", "#95A5A6"
    ]

    @rx.var
    def speaker_color_map(self) -> dict[str, str]:
        """Map each unique speaker to a color"""
        speakers = sorted(list(set(row["speaker"] for row in self.subtitles if row["speaker"])))
        mapping = {s: self.COLORS[i % len(self.COLORS)] for i, s in enumerate(speakers)}
        mapping[""] = "var(--gray-6)" # Default for empty
        return mapping

    @rx.var
    def speaker_legend_items(self) -> list[dict[str, str]]:
        """List of speaker items for the legend"""
        mapping = self.speaker_color_map
        return [{"name": k, "color": v} for k, v in mapping.items()]
    
    def on_load(self):
        """Called when page loads"""
        self.load_projects()
        # Auto-select most recent project
        if self.available_projects:
            # Find most recent by checking SRT modification time
            output_root = PARENT_DIR / "workspace"
            projects_with_time = []
            
            for proj_name in self.available_projects:
                srt_path = output_root / proj_name / "subtitles" / "ja.srt"
                if srt_path.exists():
                    mtime = srt_path.stat().st_mtime
                    projects_with_time.append((proj_name, mtime))
            
            if projects_with_time:
                # Sort by modification time (newest first)
                projects_with_time.sort(key=lambda x: x[1], reverse=True)
                most_recent = projects_with_time[0][0]
                self.load_project(most_recent)
        
    def load_projects(self):
        """Scan for available projects"""
        output_root = PARENT_DIR / "workspace"
        if output_root.exists():
            projects = [
                p.name for p in output_root.iterdir()
                if p.is_dir() and (p / "subtitles" / "ja.srt").exists()
            ]
            self.available_projects = sorted(projects)
            
    def _assign_colors(self):
        """Recalculate colors for all rows based on current speakers"""
        # compute map first
        speakers = sorted(list(set(row["speaker"] for row in self.subtitles if row.get("speaker"))))
        mapping = {s: self.COLORS[i % len(self.COLORS)] for i, s in enumerate(speakers)}
        mapping[""] = "var(--gray-6)"
        
        # update rows
        new_subtitles = []
        for row in self.subtitles:
            s = row.get("speaker", "")
            base_color = mapping.get(s, "var(--gray-6)")
            row["speaker_color"] = base_color
            
            # If base color is a hex, we can append opacity
            if base_color.startswith("#"):
                row["speaker_bg_color"] = base_color + "22"
            else:
                row["speaker_bg_color"] = "transparent"
                
            new_subtitles.append(row)
        self.subtitles = new_subtitles

    def load_project(self, project_name: str):
        """Load SRT files for selected project"""
        self.current_project = project_name
        project_path = PARENT_DIR / "workspace" / project_name / "subtitles"
        
        # Parse SRTs
        ja_items = parse_srt(project_path / "ja.srt")
        ko_items = parse_srt(project_path / "ko.srt")
        en_items = parse_srt(project_path / "en.srt")
        
        # Merge
        combined = []
        max_len = max(len(ja_items), len(ko_items), len(en_items))
        
        for i in range(max_len):
            ja = ja_items[i] if i < len(ja_items) else {"start": "", "end": "", "text": ""}
            ko = ko_items[i] if i < len(ko_items) else {"start": "", "end": "", "text": ""}
            en = en_items[i] if i < len(en_items) else {"start": "", "end": "", "text": ""}
            
            # Extract speaker from each language
            spk_ja, text_ja = extract_speaker(ja["text"])
            spk_en, text_en = extract_speaker(en["text"])
            spk_ko, text_ko = extract_speaker(ko["text"])
            
            # Priority: JA > EN > KO
            speaker = spk_ja or spk_en or spk_ko
            
            combined.append({
                "id": i,
                "start": ja["start"] or en["start"] or ko["start"],
                "end": ja["end"] or en["end"] or ko["end"],
                "speaker": speaker,
                "text_ja": text_ja,
                "text_ko": text_ko,
                "text_en": text_en,
            })
        
        self.subtitles = combined
        self._assign_colors()
    
    def update_row(self, row_id: int, field: str, value: str):
        """Update a specific field in a subtitle row"""
        need_recolor = False
        for row in self.subtitles:
            if row["id"] == row_id:
                row[field] = value
                if field == "speaker":
                    need_recolor = True
                break
        
        if need_recolor:
            self._assign_colors()
        else:
            # Force update for non-speaker fields since we modified list in place
            # Reflex needs reassignment to trigger update usually, but dict mutation inside list might be tracked if nested?
            # Safer to reassign logic or rely on Reflex's delta tracking.
            # To be safe:
            self.subtitles = self.subtitles 
    
    def insert_row_after(self, row_id: int):
        """Insert a new empty row after the specified row, splitting time in half"""
        print(f"[DEBUG] insert_row_after called with row_id: {row_id}")
        
        # Find index
        idx = next((i for i, row in enumerate(self.subtitles) if row["id"] == row_id), None)
        if idx is None:
            print(f"[DEBUG] Row {row_id} not found!")
            return
        
        current_row = self.subtitles[idx]
        
        # Parse time stamps to milliseconds
        def srt_to_ms(timestamp: str) -> int:
            if not timestamp or ',' not in timestamp: return 0
            time_part, ms_part = timestamp.split(',')
            h, m, s = map(int, time_part.split(':'))
            return (h * 3600 + m * 60 + s) * 1000 + int(ms_part)
        
        def ms_to_srt(ms: int) -> str:
            hours = ms // 3600000
            ms %= 3600000
            minutes = ms // 60000
            ms %= 60000
            seconds = ms // 1000
            milliseconds = ms % 1000
            return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
        
        # Calculate middle time
        start_ms = srt_to_ms(current_row["start"])
        end_ms = srt_to_ms(current_row["end"])
        middle_ms = (start_ms + end_ms) // 2
        
        # Save original end time
        original_end = ms_to_srt(end_ms)
        
        # Update current row's end time
        new_current_end = ms_to_srt(middle_ms)
        self.subtitles[idx]["end"] = new_current_end
        
        # Create new row
        new_id = max(row["id"] for row in self.subtitles) + 1 if self.subtitles else 0
        new_start = ms_to_srt(middle_ms)
        new_row = {
            "id": new_id,
            "start": new_start,
            "end": original_end,
            "speaker": current_row["speaker"],
            "text_ja": "",
            "text_ko": "",
            "text_en": "",
        }
        
        # Insert
        self.subtitles.insert(idx + 1, new_row)
        
        # Re-index
        for i, row in enumerate(self.subtitles):
            row["id"] = i
        
        self._assign_colors()
        
        yield rx.toast.success(f"Row split: {self.subtitles[idx]['start']} -> {new_row['end']}")
    
    def mark_as_deleted(self, row_id: int):
        """Mark row as deleted (soft delete)"""
        self.deleted_rows.add(row_id)
        yield rx.toast.warning(f"Row #{row_id} marked as deleted")
    
    def restore_row(self, row_id: int):
        """Restore a deleted row"""
        if row_id in self.deleted_rows:
            self.deleted_rows.remove(row_id)
            yield rx.toast.success(f"Row #{row_id} restored")
    
    def permanent_delete(self, row_id: int):
        """Permanently delete a row and merge its time with the previous row"""
        # Find the row to delete
        idx = next((i for i, row in enumerate(self.subtitles) if row["id"] == row_id), None)
        if idx is None:
            yield rx.toast.error("Row not found")
            return
        
        deleted_row = self.subtitles[idx]
        
        # If there's a previous row, merge time
        if idx > 0:
            previous_row = self.subtitles[idx - 1]
            # Extend previous row's end time to deleted row's end time
            previous_row["end"] = deleted_row["end"]
            yield rx.toast.info(f"Merged time: Row #{previous_row['id']} extended to {previous_row['end']}")
        
        # Remove from deleted_rows set if present
        self.deleted_rows.discard(row_id)
        
        # Remove the row permanently
        self.subtitles.pop(idx)
        
        # Re-index IDs
        for i, row in enumerate(self.subtitles):
            row["id"] = i
        
        self._assign_colors()
        
        yield rx.toast.warning(f"Row permanently deleted")
    
    def save_changes(self):
        """Save all changes back to SRT files (excluding deleted rows)"""
        if not self.current_project:
            return rx.toast.error("No project selected!")
        
        # Filter out deleted rows
        active_subtitles = [row for row in self.subtitles if row["id"] not in self.deleted_rows]
        
        project_path = PARENT_DIR / "workspace" / self.current_project / "subtitles"
        cg = CaptionGenerator()
        
        # Prepare data for saving
        for lang in ["ja", "ko", "en"]:
            srt_data = []
            for row in active_subtitles:
                text = row[f"text_{lang}"]
                if row["speaker"]:
                    text = f"[{row['speaker']}]: {text}"
                
                srt_data.append({
                    "start": row["start"],
                    "end": row["end"],
                    f"text_{lang}": text
                })
            
            cg._save_srt(srt_data, project_path / f"{lang}.srt", lang)
        
        return rx.toast.success(f"Saved {len(active_subtitles)} rows (excluded {len(self.deleted_rows)} deleted)!")
