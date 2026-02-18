"""Audio Tab State Management - Multi-Provider Support"""

from __future__ import annotations

import reflex as rx
from pathlib import Path
import sys
import asyncio
import re
from datetime import datetime
from typing import Any, Optional, cast, AsyncGenerator

# Add paths
PARENT_DIR = Path(__file__).resolve().parent.parent.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

UI_DIR = Path(__file__).parent.parent
if str(UI_DIR) not in sys.path:
    sys.path.insert(0, str(UI_DIR))

from core.gen_audio import GenAudio
from core.gen_caption import CaptionGenerator
from core.tts.base import TTSProviderType


class AudioState(rx.State):
    """State management for Audio Tab with multi-provider support"""

    # Projects
    available_projects: list[str] = []
    selected_project: str = ""

    # Provider selection
    available_providers: list[str] = ["Qwen3-TTS", "GPT-SoVITS"]
    selected_provider: str = "Qwen3-TTS"

    # Model selection (dynamic based on provider)
    model_versions: list[str] = ["Base", "CustomVoice", "VoiceDesign"]
    selected_model: str = "Base"

    # GPT-SoVITS Model Mappings (Relative to pretrained_models)
    MODEL_MAPPINGS = {
        "V4": {"gpt": "s1v3.ckpt", "sovits": "gsv-v4-pretrained/s2Gv4.pth"},
        "V2Pro": {"gpt": "s1v3.ckpt", "sovits": "v2Pro/s2Gv2Pro.pth"},
        "V2ProPlus": {"gpt": "s1v3.ckpt", "sovits": "v2Pro/s2Gv2ProPlus.pth"},
    }

    # Qwen3-TTS Model Mappings
    QWEN3_MODEL_MAPPINGS = {
        "CustomVoice": {
            "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
            "type": "custom_voice",
            "description": "Pre-trained speakers with emotion control",
        },
        "Base": {
            "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            "type": "base",
            "description": "Voice cloning from reference audio",
        },
        "VoiceDesign": {
            "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
            "type": "voice_design",
            "description": "Natural language voice description",
        },
    }

    # Qwen3-TTS preset speakers
    QWEN3_PRESET_SPEAKERS: list[str] = [
        "Vivian",
        "Serena",
        "Uncle_Fu",
        "Dylan",
        "Eric",
        "Ryan",
        "Aiden",
        "Ono_Anna",
        "Sohee",
    ]
    selected_preset_speaker: str = "Vivian"
    use_preset_speaker: bool = False  # For Qwen3-TTS: use preset vs voice cloning

    # Language selection
    gen_en: bool = False
    gen_ko: bool = True
    gen_ja: bool = False

    # Speed factor
    speed_factor: float = 1.0

    # Generation status
    is_generating: bool = False
    generation_logs: list[str] = []
    progress: int = 0
    progress_text: str = ""

    cancel_requested: bool = False

    # Generated Audio Files
    # Store all files internally: {"ja": [...], ...}
    _all_audios: dict[str, list[dict[str, Any]]] = {"ja": [], "en": [], "ko": []}

    # Pagination State
    ITEMS_PER_PAGE: int = 10
    displayed_counts: dict[str, int] = {"ja": 10, "en": 10, "ko": 10}

    @rx.var
    def generated_audios(self) -> dict[str, list[dict[str, Any]]]:
        """Return sliced audio list for display"""
        return {
            lang: self._all_audios[lang][: self.displayed_counts[lang]]
            for lang in ["ja", "en", "ko"]
        }

    @rx.var
    def has_more(self) -> dict[str, bool]:
        """Check if more items exist"""
        return {
            lang: len(self._all_audios[lang]) > self.displayed_counts[lang]
            for lang in ["ja", "en", "ko"]
        }

    def load_more(self, lang: str):
        """Increase displayed count for language"""
        self.displayed_counts[lang] += self.ITEMS_PER_PAGE

    def load_generated_audios(self):
        """Scan workspace for generated audio files"""
        if not self.selected_project:
            return

        base_dir = PARENT_DIR / "workspace" / self.selected_project / "audios"
        new_audios = {"ja": [], "en": [], "ko": []}

        for lang in ["ja", "en", "ko"]:
            lang_dir = base_dir / lang
            files = []
            if lang_dir.exists():
                # Sort by creation time (newest first) or name? Usually name for ordered dialogue.
                # Let's sort by name for now as they are likely numbered.
                for f in sorted(
                    lang_dir.glob("*.wav")
                ):  # Wav is usually intermediate, but let's check
                    files.append(
                        {
                            "name": f.name,
                            "url": f"http://localhost:8000/workspace/{self.selected_project}/audios/{lang}/{f.name}",
                            "confirm_delete": False,
                        }
                    )
                # Check mp3 as well if we generate those
                for f in sorted(lang_dir.glob("*.mp3")):
                    files.append(
                        {
                            "name": f.name,
                            "url": f"http://localhost:8000/workspace/{self.selected_project}/audios/{lang}/{f.name}",
                            "confirm_delete": False,
                        }
                    )

            # Sort by primitive number if possible (e.g. 1_ja.mp3)
            def simple_sort(item):
                name = item["name"]
                match = re.search(r"(\d+)", name)
                return int(match.group(1)) if match else 999999

            files.sort(key=simple_sort)
            new_audios[lang] = files

        self._all_audios = new_audios
        # Reset counts on reload? Or keep? Reset seems safer for clean state.
        self.displayed_counts = {
            "ja": self.ITEMS_PER_PAGE,
            "en": self.ITEMS_PER_PAGE,
            "ko": self.ITEMS_PER_PAGE,
        }

    def toggle_delete_confirm(self, filename: str, lang: str):
        """Toggle delete confirmation for a file"""
        files = self._all_audios[lang]
        new_files = []
        for f in files:
            new_f = f.copy()
            if f["name"] == filename:
                new_f["confirm_delete"] = not f.get("confirm_delete", False)
            new_files.append(new_f)

        new_audios = self._all_audios.copy()
        new_audios[lang] = new_files
        self._all_audios = new_audios

    def delete_audio(self, filename: str, lang: str):
        """Hard delete audio file"""
        if not self.selected_project:
            return

        file_path = (
            PARENT_DIR
            / "workspace"
            / self.selected_project
            / "audios"
            / lang
            / filename
        )
        if file_path.exists():
            try:
                file_path.unlink()
                rx.toast.success(f"Deleted {filename}")
                self.load_generated_audios()
            except Exception as e:
                rx.toast.error(f"Failed to delete {filename}: {e}")

    def cancel_generation(self):
        """Request cancellation"""
        self.cancel_requested = True

    # Explicit setters
    def set_selected_project(self, value: str):
        self.selected_project = value
        if value:
            self.load_generated_audios()

    def set_selected_provider(self, value: str):
        """Set TTS provider and update available models"""
        self.selected_provider = value
        # Update model versions based on provider
        if value == "GPT-SoVITS":
            self.model_versions = ["V2Pro", "V2ProPlus", "V4"]
            self.selected_model = "V2ProPlus"
        elif value == "Qwen3-TTS":
            self.model_versions = ["Base", "CustomVoice", "VoiceDesign"]
            self.selected_model = "Base"

    def set_selected_model(self, value: str):
        self.selected_model = value

    def set_selected_preset_speaker(self, value: str):
        """Set preset speaker for Qwen3-TTS"""
        self.selected_preset_speaker = value

    def set_use_preset_speaker(self, value: bool):
        """Toggle preset speaker mode for Qwen3-TTS"""
        self.use_preset_speaker = value

    def set_gen_en(self, value: bool):
        self.gen_en = value

    def set_gen_ko(self, value: bool):
        self.gen_ko = value

    def set_gen_ja(self, value: bool):
        self.gen_ja = value

    def set_speed_factor(self, value: list[float]):
        """Slider returns list[float]"""
        if value:
            self.speed_factor = value[0]

    def set_speed_slider(self, value: list[int | float]):
        """Handle slider value"""
        if value:
            self.speed_factor = float(value[0])

    @rx.var
    def is_gpt_sovits(self) -> bool:
        """Check if GPT-SoVITS is selected"""
        return self.selected_provider == "GPT-SoVITS"

    @rx.var
    def is_qwen3_tts(self) -> bool:
        """Check if Qwen3-TTS is selected"""
        return self.selected_provider == "Qwen3-TTS"

    @rx.var
    def show_model_version(self) -> bool:
        """Show model version selector only for GPT-SoVITS"""
        return self.selected_provider == "GPT-SoVITS"

    @rx.var
    def show_preset_speaker(self) -> bool:
        """Show preset speaker selector for Qwen3-TTS CustomVoice model"""
        return False

    @rx.var
    def current_model_description(self) -> str:
        """Get description for current model"""
        if self.selected_provider == "Qwen3-TTS":
            return self.QWEN3_MODEL_MAPPINGS.get(self.selected_model, {}).get(
                "description", ""
            )
        return ""

    @rx.var
    def can_generate(self) -> bool:
        """Can start generation"""
        return (
            bool(self.selected_project)
            and not self.is_generating
            and (self.gen_en or self.gen_ko or self.gen_ja)
        )

    @rx.var
    def target_langs(self) -> list[str]:
        """Get target languages"""
        langs = []
        if self.gen_ja:
            langs.append("ja")
        if self.gen_en:
            langs.append("en")
        if self.gen_ko:
            langs.append("ko")
        return langs

    @rx.var
    def gpt_status(self) -> dict[str, str | bool]:
        """Check GPT model status"""
        rel_path = self.MODEL_MAPPINGS.get(self.selected_model, {}).get("gpt", "")
        if not rel_path:
            return {"exists": False, "name": "Configuration Error"}

        full_path = (
            PARENT_DIR / "external/GPT-SoVITS/GPT_SoVITS/pretrained_models" / rel_path
        )
        return {"exists": full_path.exists(), "name": rel_path}

    @rx.var
    def sovits_status(self) -> dict[str, str | bool]:
        """Check SoVITS model status"""
        rel_path = self.MODEL_MAPPINGS.get(self.selected_model, {}).get("sovits", "")
        if not rel_path:
            return {"exists": False, "name": "Configuration Error"}

        full_path = (
            PARENT_DIR / "external/GPT-SoVITS/GPT_SoVITS/pretrained_models" / rel_path
        )
        return {"exists": full_path.exists(), "name": rel_path}

    def on_load(self):
        """Called when page loads"""
        self.load_projects()

    def load_projects(self):
        """Scan for projects with scenario files"""
        output_root = PARENT_DIR / "workspace"
        if output_root.exists():
            projects = [
                p.name
                for p in output_root.iterdir()
                if p.is_dir() and any(p.glob("scenario_*.xml"))
            ]
            self.available_projects = sorted(projects)

            # Auto-select first project in AudioState
            if self.available_projects and not self.selected_project:
                self.set_selected_project(self.available_projects[0])

    def log(self, message: str):
        """Add log message with overwrite for progress bars"""
        # Handle carriage returns from tqdm: always take the latest update
        if "\r" in message:
            message = message.split("\r")[-1].strip()

        # Add timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        message = f"[{timestamp}] {message}"

        # Clean potential ANSI codes for detection
        clean_msg = re.sub(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", message)

        # Robust tqdm detection:
        # 1. Contains "it/s]" (end of tqdm)
        # 2. X%| (percentage bar)
        # 3. | X/Y [ (counter)
        is_progress = bool(
            "it/s]" in clean_msg
            or re.search(r"\d+%\|", clean_msg)
            or re.search(r"\|\s*\d+/\d+\s*\[", clean_msg)
        )

        if is_progress and self.generation_logs:
            last_msg = self.generation_logs[-1]
            clean_last = re.sub(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", last_msg)

            last_is_progress = bool(
                "it/s]" in clean_last
                or re.search(r"\d+%\|", clean_last)
                or re.search(r"\|\s*\d+/\d+\s*\[", clean_last)
            )

            if last_is_progress:
                # Replace the last item efficiently
                self.generation_logs[-1] = message
                return

        self.generation_logs.append(message)

    def _ensure_ref_text(self, audio_path: Path, lang: str = "ja") -> str:
        """Ensure reference text exists for audio"""
        txt_path = audio_path.with_suffix(".txt")
        if txt_path.exists():
            return txt_path.read_text(encoding="utf-8")

        # Transcribe
        self.log(
            f"[*] Transcribing reference audio due to missing text: {audio_path.name}"
        )
        try:
            gen = CaptionGenerator()
            text = gen.simple_transcribe(audio_path, lang)

            if text:
                txt_path.write_text(text, encoding="utf-8")
                self.log(f"    [+] Saved transcript: {txt_path.name}")
            return text
        except Exception as e:
            self.log(f"[!] Transcription failed: {e}")
            return ""

    async def start_generation(self):
        """Start TTS generation with multi-provider support"""
        if not self.can_generate:
            yield rx.toast.error("Please select project and languages!")
            return

        self.is_generating = True
        self.generation_logs = []
        self.progress = 0
        self.progress_text = "Initializing..."
        yield

        try:
            self.log("[*] Initializing TTS Engine...")
            self.log(f"[*] Provider: {self.selected_provider}")
            self.log(f"[*] Project: {self.selected_project}")
            self.log(f"[*] Model: {self.selected_model}")

            audio_generator = GenAudio(base_dir=PARENT_DIR)

            # Get provider type
            if self.selected_provider == "GPT-SoVITS":
                provider_type = TTSProviderType.GPT_SOVITS
            else:
                provider_type = TTSProviderType.QWEN3_TTS

            provider = audio_generator.get_provider(provider_type)

            # Get model config
            model = None
            for m in provider.get_available_models():
                if m.name == self.selected_model:
                    model = m
                    break

            if model is None:
                yield rx.toast.error(f"Model {self.selected_model} not found!")
                return

            # For GPT-SoVITS, check model files exist
            if provider_type == TTSProviderType.GPT_SOVITS:
                gpt_status = self.gpt_status
                sovits_status = self.sovits_status

                if not gpt_status["exists"] or not sovits_status["exists"]:
                    yield rx.toast.error(
                        "Invalid model configuration! Check model paths."
                    )
                    return

            output_root = PARENT_DIR / "workspace" / self.selected_project
            audio_output_dir = output_root / "audios"
            audio_output_dir.mkdir(parents=True, exist_ok=True)

            target_langs = self.target_langs

            # Calculate total work (Load scenarios first)
            scenarios = []
            total_lines = 0
            for lang in target_langs:
                sc_path = output_root / f"scenario_{lang}.xml"
                if sc_path.exists():
                    content = sc_path.read_text(encoding="utf-8")
                    matches = re.findall(r"<([^>]+)>([^<]+)</\1>", content)
                    if matches:
                        scenarios.append((lang, sc_path, matches))
                        total_lines += len(matches)

            if not scenarios:
                yield rx.toast.error("No scenario files found (scenario_*.xml)!")
                return

            self.log(
                f"[*] Found {len(scenarios)} scenarios with total {total_lines} lines."
            )
            processed_lines = 0

            # Cache all available voice files once for fuzzy matching
            input_root = PARENT_DIR / "assets/audios"
            all_voice_files = []
            if input_root.exists():
                for f in input_root.glob("**/*"):
                    if f.is_file() and f.suffix.lower() in [
                        ".mp3",
                        ".wav",
                        ".m4a",
                        ".flac",
                    ]:
                        all_voice_files.append(f)

            # Import TTS config classes
            from core.tts import TTSConfig, VoiceConfig

            for lang_code, sc_path, matches in scenarios:
                self.log(f"[-] Processing Scenario: {lang_code.upper()}")

                # Output dir for this language
                out_lang_dir = audio_output_dir / lang_code
                out_lang_dir.mkdir(exist_ok=True)

                for idx, (voice_name, text) in enumerate(matches):
                    # Emotion Extraction
                    instruct = ""
                    emotion_match = re.match(r"^\((.*?)\)\s*(.*)", text)
                    if emotion_match:
                        instruct = emotion_match.group(1)
                        text = emotion_match.group(2)
                        self.log(f"    [i] Emotion: {instruct}")

                    # Check Cancellation
                    if self.cancel_requested:
                        self.log("[!] Cancellation Requested.")
                        yield rx.toast.warning("Generation Cancelled.")
                        return

                    # Progress Check
                    self.progress = int((processed_lines / total_lines) * 100)
                    self.progress_text = f"Generating {lang_code.upper()}... ({processed_lines}/{total_lines})"
                    yield

                    # Output File
                    out_file = out_lang_dir / f"{idx + 1:03d}_{voice_name}.mp3"

                    if out_file.exists():
                        self.log(f"    Line {idx + 1}: {voice_name} (Skipped - Exists)")
                        processed_lines += 1
                        continue

                    self.log(f"    Line {idx + 1}: {voice_name}")

                    # Build voice config based on provider
                    voice_id = ""
                    ref_audio_path = None
                    ref_text = None
                    ref_lang = "ja"
                    use_preset = False

                    # Check if voice_name is a Qwen3-TTS preset speaker
                    qwen3_presets = [
                        "Vivian",
                        "Serena",
                        "Uncle_Fu",
                        "Dylan",
                        "Eric",
                        "Ryan",
                        "Aiden",
                        "Ono_Anna",
                        "Sohee",
                    ]

                    # 1. Check for Reference Audio File (Priority 1)
                    target_norm = re.sub(r"[^a-zA-Z0-9]", "", voice_name).lower()
                    candidate = None
                    for vf in all_voice_files:
                        vf_norm = re.sub(r"[^a-zA-Z0-9]", "", vf.stem).lower()
                        if vf_norm == target_norm:
                            candidate = vf
                            break

                    if (
                        provider_type == TTSProviderType.QWEN3_TTS
                        and voice_name in qwen3_presets
                    ):
                        # 2. Specific Preset Speaker (Priority 2)
                        use_preset = True
                        voice_id = voice_name

                    elif candidate:
                        # 1. Reference Audio Found -> Voice Cloning (Priority 1)
                        use_preset = False
                        ref_audio_path = candidate
                        voice_id = ref_audio_path.stem

                        # Determine Ref Language from path
                        for part in ref_audio_path.parts:
                            if part in ["ja", "ko", "en", "zh"]:
                                ref_lang = part
                                break

                        # Ensure Ref Text
                        ref_text = self._ensure_ref_text(ref_audio_path, ref_lang)
                        if not ref_text and provider_type == TTSProviderType.GPT_SOVITS:
                            self.log(
                                f"[!] Missing ref text for {voice_name}. Skipping line."
                            )
                            processed_lines += 1
                            continue

                    elif (
                        provider_type == TTSProviderType.QWEN3_TTS
                        and self.use_preset_speaker
                    ):
                        # 3. Global Preset Fallback (Priority 3)
                        use_preset = True
                        voice_id = self.selected_preset_speaker

                    else:
                        # 4. No candidate and no preset -> Fail or Skip
                        if not candidate:
                            self.log(
                                f"[!] Voice file not found: {voice_name} (Normalized: {target_norm})"
                            )
                            processed_lines += 1
                            continue

                    # Build TTS config
                    voice_config = VoiceConfig(
                        voice_id=voice_id
                        if use_preset
                        else (ref_audio_path.stem if ref_audio_path else ""),
                        ref_audio_path=ref_audio_path,
                        ref_text=ref_text,
                        ref_language=ref_lang,
                        use_preset_speaker=use_preset,
                    )

                    tts_config = TTSConfig(
                        text=text,
                        language=lang_code,
                        output_path=out_file,
                        voice=voice_config,
                        speed_factor=self.speed_factor,
                        extra_options={"instruct": instruct},
                    )

                    try:
                        # Use provider's generate method
                        async for log_line in cast(
                            AsyncGenerator[str, None],
                            provider.generate(tts_config, model),
                        ):
                            if log_line:
                                self.log(log_line)
                                yield

                            # Check Cancellation mid-stream
                            if self.cancel_requested:
                                break

                        if self.cancel_requested:
                            self.log("[!] Cancellation Requested.")
                            yield rx.toast.warning("Generation Cancelled.")
                            return

                    except Exception as e:
                        self.log(f"[!] Generation Error: {e}")

                    # Optimization Step
                    if not self.cancel_requested and out_file.exists():
                        try:
                            async for log_line in audio_generator.optimize_audio(
                                out_file
                            ):
                                if log_line:
                                    self.log(log_line)
                                    yield
                        except Exception as e:
                            self.log(f"[!] Optimization Error: {e}")

                    processed_lines += 1

            self.progress = 100
            self.progress_text = "Done!"
            yield rx.toast.success("Audio generation completed!")
            self.log("[+] All tasks finished.")
            self.load_generated_audios()

        except Exception as e:
            self.log(f"[CRITICAL] {str(e)}")
            yield rx.toast.error(f"Generation failed: {e}")

        finally:
            self.is_generating = False
            self.cancel_requested = False


class ScenarioState(rx.State):
    """State for Scenario Tab"""

    available_projects: list[str] = []
    selected_project: str = ""
    is_generating: bool = False

    # Detected speakers from SRT
    speakers: list[str] = []  # ["speaker1", "speaker2", ...]

    # Available SRT languages for current project
    has_ja_srt: bool = False
    has_en_srt: bool = False
    has_ko_srt: bool = False

    # Available voice files by language and gender
    # Structure: {lang: {gender: [filenames]}}
    available_voices: dict[str, dict[str, list[str]]] = {}

    # Selected voices per language per speaker
    # Structure: {lang: {speaker_name: {gender: str, voice: str}}}
    # Example: {"ja": {"speaker1": {"gender": "female", "voice": "voice1.mp3"}}}
    selected_voices: dict[str, dict[str, dict[str, str]]] = {}

    def _get_config_path(self) -> Optional[Path]:
        """Get path to speaker configuration file"""
        if not self.selected_project:
            return None
        return PARENT_DIR / "workspace" / self.selected_project / "speaker_map.json"

    def _load_config(self):
        """Load speaker configuration from JSON"""
        config_path = self._get_config_path()
        if not config_path or not config_path.exists():
            return

        try:
            import json

            data = json.loads(config_path.read_text(encoding="utf-8"))

            # Merge loaded data with current detected speakers
            for lang, speakers in data.items():
                if lang not in self.selected_voices:
                    self.selected_voices[lang] = {}

                for speaker, info in speakers.items():
                    # Only calculate match if speaker exists in detecting list
                    if speaker in self.speakers:
                        if speaker not in self.selected_voices[lang]:
                            self.selected_voices[lang][speaker] = {
                                "gender": "female",
                                "voice": "",
                            }

                        # Restore saved values
                        self.selected_voices[lang][speaker]["gender"] = info.get(
                            "gender", "female"
                        )
                        self.selected_voices[lang][speaker]["voice"] = info.get(
                            "voice", ""
                        )

        except Exception as e:
            print(f"Error loading config: {e}")

    def _save_config(self):
        """Save current configuration to JSON"""
        config_path = self._get_config_path()
        if not config_path:
            return

        try:
            import json

            config_path.write_text(
                json.dumps(self.selected_voices, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            print(f"Error saving config: {e}")

    def set_selected_project(self, value: str):
        """Set project and auto-detect speakers"""
        print(f"[DEBUG] set_selected_project called with: {value}")
        self.selected_project = value
        if value:
            self._detect_speakers()
            self._load_config()  # Load saved config after detection
            print(f"[DEBUG] Detected speakers: {self.speakers}")
        else:
            print("[DEBUG] No value provided")

    def _detect_speakers(self):
        """Parse SRT file and extract unique speakers"""
        if not self.selected_project:
            return

        project_path = PARENT_DIR / "workspace" / self.selected_project / "subtitles"
        
        # Check which SRT files exist
        self.has_ja_srt = (project_path / "ja.srt").exists()
        self.has_en_srt = (project_path / "en.srt").exists()
        self.has_ko_srt = (project_path / "ko.srt").exists()

        # Try to find any available SRT file (ko > en > ja priority)
        srt_path = project_path / "ko.srt"
        if not srt_path.exists():
            srt_path = project_path / "en.srt"
        if not srt_path.exists():
            srt_path = project_path / "ja.srt"
        
        if not srt_path.exists():
            return

        speakers_set = set()
        content = srt_path.read_text(encoding="utf-8")

        # Parse SRT format
        for line in content.split("\n"):
            line = line.strip()
            # Look for "[speaker]: text" or "[speaker] text" pattern
            match = re.match(r"^\[(.*?)\](?::)?\s*.*", line)
            if match:
                speaker = match.group(1).strip()
                speakers_set.add(speaker)

        # Sort and store
        self.speakers = sorted(speakers_set)

        # Initialize voice selections for detected speakers
        # IMPORTANT: Initialize FRESH to avoid stale data from other projects,
        # but _load_config will overwrite relevant parts
        self.selected_voices = {}
        for lang in ["ja", "ko", "en"]:
            self.selected_voices[lang] = {
                speaker: {"gender": "female", "voice": ""} for speaker in self.speakers
            }

    def set_speaker_gender(self, lang: str, speaker_name: str, gender: str):
        """Set gender for a speaker in a specific language.

        Gender options: female, male, preset_female, preset_male
        """
        if lang not in self.selected_voices:
            self.selected_voices[lang] = {}
        if speaker_name not in self.selected_voices[lang]:
            self.selected_voices[lang][speaker_name] = {"gender": "female", "voice": ""}

        self.selected_voices[lang][speaker_name]["gender"] = gender
        # Reset voice when gender changes
        self.selected_voices[lang][speaker_name]["voice"] = ""
        self._save_config()  # Save on change

    def set_speaker_voice(self, lang: str, speaker_name: str, voice: str):
        """Set voice file for a speaker in a specific language"""
        if lang not in self.selected_voices:
            self.selected_voices[lang] = {}
        if speaker_name not in self.selected_voices[lang]:
            self.selected_voices[lang][speaker_name] = {"gender": "female", "voice": ""}

        self.selected_voices[lang][speaker_name]["voice"] = voice
        self._save_config()  # Save on change

    def on_load(self):
        """Load projects and voice files"""
        print("[DEBUG] ScenarioState.on_load called")
        
        # Load projects - any SRT file is sufficient
        output_root = PARENT_DIR / "workspace"
        if output_root.exists():
            projects = [
                p.name
                for p in output_root.iterdir()
                if p.is_dir() and (
                    (p / "subtitles" / "ko.srt").exists() or
                    (p / "subtitles" / "en.srt").exists() or
                    (p / "subtitles" / "ja.srt").exists()
                )
            ]
            self.available_projects = sorted(projects)
            print(f"[DEBUG] Found projects: {self.available_projects}")

            # Auto-select first project in ScenarioState
            if self.available_projects and not self.selected_project:
                first_project = self.available_projects[0]
                print(f"[DEBUG] Auto-selecting project: {first_project}")
                self.selected_project = first_project
                self._detect_speakers()
                self._load_config()
                print(f"[DEBUG] After detect, speakers: {self.speakers}")

        # Load available voice files by language and gender
        audio_inputs = PARENT_DIR / "assets" / "audios"

        # Qwen3-TTS preset speakers (no audio files needed)
        qwen3_presets_female = ["Vivian", "Serena", "Ono_Anna", "Sohee"]
        qwen3_presets_male = ["Uncle_Fu", "Dylan", "Eric", "Ryan", "Aiden"]

        for lang in ["ja", "ko", "en"]:
            self.available_voices[lang] = {
                "female": [],
                "male": [],
                "preset_female": [],
                "preset_male": [],
            }
            lang_dir = audio_inputs / lang

            # Add Qwen3-TTS presets (available for all languages)
            self.available_voices[lang]["preset_female"] = qwen3_presets_female.copy()
            self.available_voices[lang]["preset_male"] = qwen3_presets_male.copy()

            if lang_dir.exists():
                for gender in ["female", "male"]:
                    gender_dir = lang_dir / gender
                    if gender_dir.exists():
                        files = sorted(
                            [
                                f.name
                                for f in gender_dir.glob("*.*")
                                if f.suffix.lower() in [".mp3", ".wav", ".m4a", ".flac"]
                            ]
                        )
                        self.available_voices[lang][gender] = files

    @rx.var
    def can_generate(self) -> bool:
        """Check if all speakers have voices selected for available languages"""
        if not self.selected_project or not self.speakers:
            return False

        # Determine which languages are available (based on SRT existence)
        project_path = PARENT_DIR / "workspace" / self.selected_project / "subtitles"
        available_langs = []
        if (project_path / "ja.srt").exists():
            available_langs.append("ja")
        if (project_path / "ko.srt").exists():
            available_langs.append("ko")
        if (project_path / "en.srt").exists():
            available_langs.append("en")

        # If no SRT files found, cannot generate
        if not available_langs:
            return False

        # Check all speakers have voices in available languages only
        for lang in available_langs:
            if lang not in self.selected_voices:
                return False

            for speaker in self.speakers:
                if speaker not in self.selected_voices[lang]:
                    return False

                voice = self.selected_voices[lang][speaker].get("voice", "")
                if not voice:
                    return False

        return True

    async def generate_scenario(self):
        """Generate XML scenario"""
        if not self.selected_project:
            yield rx.toast.error("Please select a project!")
            return

        if not self.speakers:
            yield rx.toast.error("No speakers detected in SRT!")
            return

        # Verify all voices selected
        if not self.can_generate:
            yield rx.toast.error("Process stopped: Missing voice selections.")
            return

        self.is_generating = True
        yield rx.toast.info("Starting scenario generation...")

        try:
            generator = CaptionGenerator()
            output_root = PARENT_DIR / "workspace" / self.selected_project
            subtitle_dir = output_root / "subtitles"

            generated_langs = []

            for lang in ["ja", "ko", "en"]:
                srt_path = subtitle_dir / f"{lang}.srt"
                if not srt_path.exists():
                    continue

                content = srt_path.read_text(encoding="utf-8")
                captions = []
                current_speaker = "unknown"

                for line in content.split("\n"):
                    line = line.strip()
                    if "-->" in line or line.isdigit() or not line:
                        continue

                    text = line

                    spk = current_speaker

                    # Regex match both [speaker]: text and [speaker] text
                    match = re.match(r"^\[(.*?)\](?::)?\s*(.*)", line)
                    if match:
                        spk = match.group(1).strip()
                        text = match.group(2).strip()
                        current_speaker = spk

                    # Use generic tag for LLM generation
                    captions.append({"text": f"[{spk}]: {text}"})

                if not captions:
                    continue

                xml_content = generator.generate_xml_scenario(captions, lang)

                # Post-process: Map generic tags to specific voice names
                if xml_content and lang in self.selected_voices:
                    for spk_key, info in self.selected_voices[lang].items():
                        voice_file = info.get("voice")
                        if voice_file:
                            voice_name = Path(voice_file).stem
                            # Replace generic tags with specific voice tags
                            xml_content = xml_content.replace(
                                f"<{spk_key}>", f"<{voice_name}>"
                            )
                            xml_content = xml_content.replace(
                                f"</{spk_key}>", f"</{voice_name}>"
                            )

                xml_path = output_root / f"scenario_{lang}.xml"
                xml_path.write_text(xml_content, encoding="utf-8")
                generated_langs.append(lang)

            if generated_langs:
                yield rx.toast.success(
                    f"Generated scenarios for: {', '.join(generated_langs)}"
                )
            else:
                yield rx.toast.error("No scenarios generated. Please check subtitles.")

        except Exception as e:
            print(f"Error: {e}")
            yield rx.toast.error(f"Generation failed: {e}")

        finally:
            self.is_generating = False


from utils.subtitle_utils import parse_srt, get_kanjis, format_timestamp_json, ms_to_srt
from mutagen.mp3 import MP3
import json
from pydantic import BaseModel


class SubtitleLangData(BaseModel):
    """Structured data for a language in Subtitle Tab"""

    lang: str
    emoji: str
    valid: bool
    audio_count: int
    srt_count: int
    audios: list[str]
    srt_content: str
    srt_path: str


class SubtitleState(rx.State):
    """State for Subtitle Preview and Generation"""

    available_projects: list[str] = []
    selected_project: str = ""

    # List of language data
    lang_list: list[SubtitleLangData] = []

    is_generating: bool = False

    def set_selected_project(self, value: str):
        self.selected_project = value
        if value:
            self._load_resources()

    def on_load(self):
        """Load projects"""
        output_root = PARENT_DIR / "workspace"
        if output_root.exists():
            projects = [p.name for p in output_root.iterdir() if p.is_dir()]
            self.available_projects = sorted(projects)

            # Auto-select first project in SubtitleState
            if self.available_projects and not self.selected_project:
                self.set_selected_project(self.available_projects[0])

        if self.selected_project:
            self._load_resources()

    def _load_resources(self):
        """Scan audios and SRTs for the selected project"""
        if not self.selected_project:
            return

        proj_root = PARENT_DIR / "workspace" / self.selected_project
        audios_root = proj_root / "audios"
        subtitles_root = proj_root / "subtitles"

        new_list = []

        for lang, flag_emoji in [("ja", "🇯🇵"), ("en", "🇺🇸"), ("ko", "🇰🇷")]:
            lang_audio_dir = audios_root / lang
            audio_files = []
            if lang_audio_dir.exists():
                audio_files = sorted([f.name for f in lang_audio_dir.glob("*.mp3")])

            srt_path = subtitles_root / f"{lang}.srt"
            srt_items = []
            srt_content = ""
            if srt_path.exists():
                srt_items = parse_srt(srt_path)
                srt_content = srt_path.read_text(encoding="utf-8")

            audio_count = len(audio_files)
            srt_count = len(srt_items)
            valid = (audio_count == srt_count) and (audio_count > 0)

            new_list.append(
                SubtitleLangData(
                    lang=lang,
                    emoji=flag_emoji,
                    valid=valid,
                    audio_count=audio_count,
                    srt_count=srt_count,
                    audios=audio_files,
                    srt_content=srt_content,
                    srt_path=str(srt_path),
                )
            )

        self.lang_list = new_list

    confirm_dialog_open: bool = False

    def open_confirm_dialog(self):
        """Open the confirmation dialog if project is selected"""
        if not self.selected_project:
            return rx.toast.error("Please select a project!")
        self.confirm_dialog_open = True

    def set_confirm_dialog_open(self, value: bool):
        self.confirm_dialog_open = value

    def close_confirm_dialog(self):
        self.confirm_dialog_open = False

    async def generate_subtitles(self):
        """Generate formatted subtitles and JSON"""
        if not self.selected_project:
            yield rx.toast.error("Please select a project!")
            return

        self.is_generating = True
        yield

        proj_root = PARENT_DIR / "workspace" / self.selected_project
        audios_root = proj_root / "audios"
        subtitles_root = proj_root / "subtitles"

        # New Output Directory
        synced_root = subtitles_root / "synced"
        synced_root.mkdir(parents=True, exist_ok=True)

        generated_files = []

        try:
            for data in self.lang_list:
                if not data.valid:
                    continue

                lang = data.lang

                # Load Resources
                audio_files = sorted(list((audios_root / lang).glob("*.mp3")))
                srt_items = parse_srt(Path(data.srt_path))

                json_output = []
                srt_output_blocks = []

                current_ms = 0
                GAP_MS = 0

                for idx, (audio_path, srt_item) in enumerate(
                    zip(audio_files, srt_items)
                ):
                    # Get Duration
                    mp3 = MP3(audio_path)
                    duration_sec = mp3.info.length
                    duration_ms = int(duration_sec * 1000)

                    # Timestamps (MS for logic, Str for JSON)
                    start_ms = current_ms
                    end_ms = current_ms + duration_ms

                    # 1. SRT Block Construction
                    start_srt = ms_to_srt(start_ms)
                    end_srt = ms_to_srt(end_ms)
                    raw_text = srt_item["text"]

                    # Remove [Speaker] tag for SRT text
                    # Regex to match "[Speaker]: text" or "[Speaker] text"
                    speaker_match = re.match(
                        r"^\[(.*?)\]:?\s*(.*)", raw_text, re.DOTALL
                    )
                    cleaned_text = raw_text

                    if speaker_match:
                        # speaker_name = speaker_match.group(1).strip() # Unused here
                        cleaned_text = speaker_match.group(2).strip()

                        if cleaned_text.startswith(":"):
                            cleaned_text = cleaned_text[1:].strip()

                    srt_block = (
                        f"{idx + 1}\n{start_srt} --> {end_srt}\n{cleaned_text}\n"
                    )
                    srt_output_blocks.append(srt_block)

                    # 2. JSON Construction (Only needed for JA or if we want generic support later)
                    if lang == "ja":
                        start_json = format_timestamp_json(start_ms)
                        end_json = format_timestamp_json(end_ms)

                        # Parse Speaker (Already done above essentially)
                        speaker = "Unknown"
                        if speaker_match:
                            speaker = speaker_match.group(1).strip()

                        entry = {
                            "start": start_json,
                            "end": end_json,
                            "speaker": speaker,
                            "text": cleaned_text,
                            "kanjis": get_kanjis(cleaned_text),
                        }
                        json_output.append(entry)

                    current_ms = end_ms + GAP_MS

                # Save SRT (All languages)
                srt_out_path = synced_root / f"{lang}.srt"
                with open(srt_out_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(srt_output_blocks))
                generated_files.append(srt_out_path.name)

                # Save JSON (Japanese Only)
                if lang == "ja":
                    json_out_path = synced_root / f"{lang}.json"
                    with open(json_out_path, "w", encoding="utf-8") as f:
                        json.dump(json_output, f, indent=2, ensure_ascii=False)
                    generated_files.append(json_out_path.name)

            if generated_files:
                yield rx.toast.success(
                    f"Generated: {', '.join(generated_files)} in 'synced/'"
                )
            else:
                yield rx.toast.warning("No valid languages to process.")

        except Exception as e:
            yield rx.toast.error(f"Generation failed: {e}")

        finally:
            self.is_generating = False
