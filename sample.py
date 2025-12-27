import argparse
import logging
import sys
import os
import json
import copy
import uuid
import re
import time
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

# 외부 라이브러리 의존성 체크
try:
    import google.generativeai as genai
except ImportError:
    print("Error: 'google-generativeai' library is required.")
    print("Please install it using: pip install google-generativeai")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("Warning: 'python-dotenv' library not found. .env file will not be loaded.")
    print("To use .env file, install it using: pip install python-dotenv")
    load_dotenv = None

# -----------------------------------------------------------------------------
# 1. 로깅 및 상수 설정 (Logging & Constants)
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("AutoCapCut")

@dataclass
class ProjectConfig:
    """
    프로젝트 실행에 필요한 설정값을 관리하는 데이터 클래스입니다.
    """
    workspace_dir: Path
    gemini_api_key: str
    target_fps: float = 30.0
    subtitle_font: str = "Keifont"
    subtitle_max_chars: int = 20
    default_segment_duration: float = 3.0  # 자막 동기화 실패 시 기본 지속 시간

# -----------------------------------------------------------------------------
# 2. 도메인 모델 (Domain Models)
# -----------------------------------------------------------------------------
@dataclass
class SubtitleSegment:
    start_time: float  # Seconds
    end_time: float    # Seconds
    original_text: str # Kanji mixed (origin)
    reading_text: str  # Hiragana/Katakana for pronunciation (generated)
    kanjis: List[Dict[str, str]] = field(default_factory=list) # List of {"text": "漢字", "reading": "かんじ"}
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    @property
    def formatted_reading(self) -> str:
        """한자 독음들을 공백으로 구분하여 반환합니다."""
        if not self.kanjis:
            return ""
        return " ".join([k['reading'] for k in self.kanjis])

# -----------------------------------------------------------------------------
# 3. 미디어 스캐너 (Media Scanner)
# -----------------------------------------------------------------------------
class MediaScanner:
    """
    지정된 디렉토리에서 미디어 파일(Video, Audio, Subtitle)을 스캔하고 정렬합니다.
    """
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.videos_dir = base_dir / "videos"
        self.audios_dir = base_dir / "audios"
        self.subtitles_dir = base_dir / "subtitles"

    def _get_sorted_files(self, directory: Path, extensions: List[str]) -> List[Path]:
        if not directory.exists():
            logger.warning(f"디렉토리가 존재하지 않습니다: {directory}")
            return []
        
        files = []
        for ext in extensions:
            files.extend(directory.glob(f"*{ext}"))
        
        # 정렬 우선순위: 1. 파일명 (오름차순) - 사용자 요청
        files.sort(key=lambda f: f.name)
        logger.info(f"'{directory.name}'에서 {len(files)}개의 파일을 발견했습니다. (이름순 정렬)")
        return files

    def scan_videos(self) -> List[Path]:
        return self._get_sorted_files(self.videos_dir, [".mp4", ".mov", ".avi"])

    def scan_audios(self) -> List[Path]:
        return self._get_sorted_files(self.audios_dir, [".mp3", ".wav", ".aac"])

    def scan_subtitles(self) -> List[Path]:
        return self._get_sorted_files(self.subtitles_dir, [".xml", ".srt"])


# -----------------------------------------------------------------------------
# 4. 자막 처리기 (Subtitle Processor with LLM)
# -----------------------------------------------------------------------------
class SubtitleProcessor:
    """
    XML 자막 파일을 읽고, Gemini LLM을 통해 한자 독음(히라가나)을 포함한 JSON 포맷으로 변환합니다.
    """
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
    def parse_and_convert(self, file_path: Path) -> List[SubtitleSegment]:
        logger.info(f"자막 처리 시작: {file_path.name}")
        
        # 1. 파일 읽기 & Ground Truth 파싱
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 검증을 위한 원본 텍스트 리스트 추출
            ground_truth_texts = re.findall(r'>([^<]+)<', content)
            ground_truth_texts = [t.strip() for t in ground_truth_texts if t.strip()] # 빈 줄 제거
            
        except Exception as e:
            logger.error(f"파일 읽기/파싱 실패: {file_path} - {e}")
            return []

        #        # 프롬프트 구성 (Strict 20 User Constraints)
        prompt = f"""
        당신은 일본어 자막 처리 전문가입니다. 다음 XML 파일의 대사 목록을 분석하여 JSON 형식으로 변환해주세요.
        
        [필수 규칙]
        1. **글자 수 제한**: 한 번에 화면에 표시되는 자막(origin)은 **반드시 20글자 이내**여야 합니다. 
           - 만약 원문이 20글자를 초과한다면, **의미 단위로 자연스럽게 나누어 여러 개의 JSON 항목으로 분리**하세요.
           - 분리된 항목들의 시간(start, end)은 원본 시간을 기준으로 적절히 배분되어야 합니다.
        2. "start", "end": XML의 타임코드를 사용합니다. (분리 시에는 이를 쪼개서 할당)
        3. "origin": 원문 (한자 포함). **20글자 이내 필수**.
        4. "kanjis": 문장 내의 한자 단어와 히라가나 독음을 추출. (분리된 문장에 포함된 한자만 기재)
        
        [입력 데이터]
        {content}
        
        [출력 예시]
        (긴 문장 "同棲可能な賃貸物件をお探しということでよろしいでしょうか。" -> 20자 초과 시 분리 예시)
        [
          {{
            "start": "00:08",
            "end": "00:10",
            "origin": "同棲可能な賃貸物件を",
            "kanjis": [
                {{"text": "同棲", "reading": "どうせい"}},
                {{"text": "可能", "reading": "かのう"}},
                {{"text": "賃貸物件", "reading": "ちんたいぶっけん"}},
                {{"text": "探", "reading": "さが"}}
            ]
          }},
          ...
        ]
        
        JSON 코드 블록만 출력해주세요.
        """
        
        # 3. Retry Loop & Verification
        MAX_RETRIES = 3
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"LLM 요청 시도 {attempt + 1}/{MAX_RETRIES}...")
                response = self.model.generate_content(prompt)
                json_text = self._extract_json(response.text)
                data = json.loads(json_text)
                
                # 검증 수행
                if self._verify_response(data, ground_truth_texts):
                    segments = []
                    for item in data:
                        start_sec = self._time_str_to_seconds(item['start'])
                        end_sec = self._time_str_to_seconds(item['end'])
                        
                        segments.append(SubtitleSegment(
                            start_time=start_sec,
                            end_time=end_sec,
                            original_text=item['origin'],
                            reading_text="", # reading 필드는 이제 제거되었으므로 빈 문자열 혹은 필요시 생성
                            kanjis=item.get('kanjis', [])
                        ))
                    
                    logger.info(f"자막 변환 및 검증 완료: {len(segments)}개의 세그먼트")
                    return segments
                else:
                    logger.warning(f"검증 실패 (시도 {attempt + 1}/{MAX_RETRIES}). 재시도합니다.")
            
            except json.JSONDecodeError:
                logger.error(f"JSON 파싱 실패 (시도 {attempt + 1}/{MAX_RETRIES})")
            except Exception as e:
                logger.error(f"LLM 처리 중 오류 발생 (시도 {attempt + 1}/{MAX_RETRIES}): {e}")
            
            if attempt < MAX_RETRIES - 1:
                time.sleep(1) # 재시도 전 대기

        logger.error("최대 재시도 횟수 초과. 자막 처리에 실패했습니다.")
        return []

    def _verify_response(self, json_data: List[Dict], ground_truth_texts: List[str]) -> bool:
        """
        LLM 응답이 원본과 일치하는지 검증합니다.
        """
        # 1. 개수 비교 (Splitting 기능 활성화 시 개수가 늘어날 수 있으므로 경고만 하고 통과)
        if len(json_data) != len(ground_truth_texts):
            logger.warning(f"참고: 개수 불일치 (JSON: {len(json_data)}, 원본: {len(ground_truth_texts)}) - 문장 분리로 인해 발생할 수 있음.")
            # return False  <-- 분리 기능을 위해 검증 해제

            
        # 2. 필수 필드 확인
        for i, item in enumerate(json_data):
            if "origin" not in item:
                logger.warning(f"검증 실패: 'origin' 필드 누락 (인덱스 {i})")
                return False
            if "kanjis" in item and not isinstance(item["kanjis"], list):
                 logger.warning(f"검증 실패: 'kanjis' 형식이 리스트가 아님 (인덱스 {i})")
                 return False

        return True

    def _extract_json(self, text: str) -> str:
        """마크다운 코드 블록 등에서 순수 JSON 부분만 추출합니다."""
        match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if match:
            return match.group(1)
        return text.strip()

    def _time_str_to_seconds(self, time_str: str) -> float:
        """MM:SS 형식을 초 단위 float으로 변환"""
        try:
            parts = time_str.split(':')
            if len(parts) == 2:
                return float(parts[0]) * 60 + float(parts[1])
            elif len(parts) == 3:
                return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            return 0.0
        except:
            return 0.0

# -----------------------------------------------------------------------------
# 5. CapCut 프로젝트 생성기 (CapCut Generator)
# -----------------------------------------------------------------------------
class CapCutGenerator:
    """
    CapCut Desktop용 draft_content.json 파일을 생성하여 프로젝트를 구성합니다.
    """
    def __init__(self, config: ProjectConfig):
        self.config = config
        self.project_id = str(uuid.uuid4()).upper()
        self.materials_videos = []
        self.materials_audios = []
        self.subtitles = []
        self.tracks = []
        
        # 기본 캔버스 설정 (템플릿에 따르므로 실제로는 안쓰일 수도 있음)
        self.canvas_width = 1920
        self.canvas_height = 1080

    def create_project(self, videos: List[Path], audios: List[Path], unique_subtitles: List[SubtitleSegment]):
        """
        Cloning 방식: 템플릿의 Video/Text를 복제하여 프로젝트를 구성합니다.
        """
        # 데이터만 준비해두고, 실제 JSON 조립은 save()에서 수행합니다.
        self.materials_videos = videos # Raw Paths
        self.materials_audios = audios # Raw Paths
        self.subtitles = unique_subtitles # Subtitle Objects
        
        logger.info(f"프로젝트 데이터 준비: 비디오 {len(videos)}개, 오디오 {len(audios)}개, 자막 {len(unique_subtitles)}개")

    def _create_text_material(self, proto: Dict, text: str, font_size_scale: float = 1.0) -> Dict:
        """텍스트 내용을 변경하여 새 Material을 생성합니다."""
        m = copy.deepcopy(proto)
        m["id"] = str(uuid.uuid4()).upper()
        
        try:
            content = json.loads(m["content"])
            content["text"] = str(text) 
            # Font Size 조절 (Styles에 있을 경우)
            if "styles" in content:
                for style in content["styles"]:
                    if "font_size" in style:
                        style["font_size"] *= font_size_scale
                    # [Fix] 특수문자/이모지 등으로 인한 스타일 미적용 방지
                    # 범위를 넉넉하게 설정 (len(text) + 5)
                    if "range" in style:
                        style["range"] = [0, len(text) + 5]
                        
            m["content"] = json.dumps(content)
        except Exception as e:
            logger.warning(f"텍스트 컨텐츠 파싱 실패, 기본값 사용: {e}")
            
        return m

    def _get_media_duration(self, path: Path) -> int:
        """ffprobe를 사용하여 미디어 파일의 길이를 마이크로초 단위로 반환합니다."""
        try:
            cmd = [
                'ffprobe', 
                '-v', 'error', 
                '-show_entries', 'format=duration', 
                '-of', 'default=noprint_wrappers=1:nokey=1', 
                str(path)
            ]
            # shell=True는 Windows에서 필요할 수 있지만, 리스트 형태로 전달하면 보통 권장하지 않음.
            # 하지만 PATH 문제를 위해 shell=True가 편할 때가 있음. 여기선 subprocess.call 대신 check_output 사용.
            # Windows에서는 실행파일 찾기 위해 shell=True를 쓰거나 full path 필요.
            # 여기서는 기본적으로 path에 있다고 가정.
            result = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode().strip()
            duration_sec = float(result)
            return int(duration_sec * 1000000) # Microseconds
        except Exception as e:
            logger.warning(f"미디어 길이 측정 실패 ({path.name}): {e}. 기본값 10분을 사용합니다.")
            return 600 * 1000000 # 10 Minutes default

    def save(self, output_root: Optional[Path] = None) -> bool:
        """sample_template.json 템플릿을 기반으로 프로젝트를 생성(복제)하고 저장합니다."""
        project_name = f"{self.config.workspace_dir.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if output_root:
            project_dir = output_root / project_name
            logger.info(f"CapCut Draft 폴더에 직접 저장합니다: {project_dir}")
        else:
            project_dir = self.config.workspace_dir / project_name
            
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. 템플릿 로드 (Sample1220 기반)
        template_path = self.config.workspace_dir / "templates" / "sample_template.json"
        
        if not template_path.exists():
            logger.error(f"필수 템플릿 파일이 없습니다: {template_path}")
            return False

        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                draft_content = json.load(f)
        except Exception as e:
            logger.error(f"템플릿 로드 오류: {e}")
            return False

        # 2. ID 업데이트 (대문자 필수)
        draft_content["id"] = self.project_id
        
        # 3. 프로토타입 추출
        import copy
        
        # Video
        video_proto = draft_content["materials"]["videos"][0] if draft_content["materials"].get("videos") else None
        track_video_proto = next((t["segments"][0] for t in draft_content["tracks"] if t["type"] == "video" and t.get("attribute") == 0 and t["segments"]), None)
        
        # Audio (Check if exists)
        audio_proto = draft_content["materials"]["audios"][0] if draft_content["materials"].get("audios") else None
        # Audio track usually works similarly to video. segment -> material_id.
        track_audio_proto = next((t["segments"][0] for t in draft_content["tracks"] if t["type"] == "audio" and t["segments"]), None)
        
        # Text Prototypes
        text_mats = draft_content["materials"].get("texts", [])
        text_tracks = [t for t in draft_content["tracks"] if t["type"] == "text" and t.get("segments")]
        
        proto_main_mat = text_mats[0] if text_mats else None
        proto_main_seg = text_tracks[0]["segments"][0] if text_tracks else None
        
        # 두 번째 스타일(Reading용)이 있으면 사용, 없으면 메인 복제
        has_dual_style = (len(text_mats) > 1 and len(text_tracks) > 1)
        proto_sub_mat = text_mats[1] if len(text_mats) > 1 else proto_main_mat
        proto_sub_seg = text_tracks[1]["segments"][0] if len(text_tracks) > 1 else proto_main_seg

        if not video_proto or not track_video_proto:
            logger.error("템플릿에 비디오 트랙이나 머티리얼이 없어 복제할 수 없습니다.")
            return False

        # 4. 기존 Materials & Tracks 초기화 (Clean Slate)
        # 사용자의 명확한 요구: "템플릿의 비디오, 오디오, 텍스트는 지워줘야 함"
        # 따라서 프로토타입만 추출한 후, 내용은 싹 비우고 새로 채워넣습니다.
        
        for key in draft_content["materials"]:
             draft_content["materials"][key] = []
        
        draft_content["tracks"] = []

        # 5. 비디오 생성
        new_videos = []
        new_segments_video = []
        current_offset = 0
        
        for vid_path in self.materials_videos:
            duration = self._get_media_duration(vid_path)
            
            # Material
            m = copy.deepcopy(video_proto)
            mid = str(uuid.uuid4()).upper()
            m["id"] = mid
            m["path"] = str(vid_path).replace("\\", "/")
            m["material_name"] = vid_path.name
            m["duration"] = duration
            new_videos.append(m)
            
            # Segment
            s = copy.deepcopy(track_video_proto)
            s["id"] = str(uuid.uuid4()).upper()
            s["material_id"] = mid
            s["source_timerange"] = {"start": 0, "duration": duration}
            s["target_timerange"] = {"start": current_offset, "duration": duration}
            new_segments_video.append(s)
            current_offset += duration
            
        draft_content["materials"]["videos"] = new_videos

        # 6. 오디오 생성 (Scanned Files - Voiceover/SE)
        new_audios = []
        new_segments_audio = []
        current_audio_offset = 0
        
        logger.info(f"오디오 생성 시작. Scanned: {len(self.materials_audios)}개, Proto(Mat): {bool(audio_proto)}, Proto(Track): {bool(track_audio_proto)}")

        # Audio Prototype이 있으면 사용
        if self.materials_audios and audio_proto and track_audio_proto:
            for aud_path in self.materials_audios:
                duration = self._get_media_duration(aud_path)
                logger.info(f"오디오 처리 중: {aud_path.name} (Duration: {duration})")

                # Material
                m = copy.deepcopy(audio_proto)
                mid = str(uuid.uuid4()).upper()
                m["id"] = mid
                m["path"] = str(aud_path).replace("\\", "/")
                # [Fix] 메타데이터 'name' 업데이트 (기본적으로 material_name이 아니라 name임)
                m["name"] = aud_path.name 
                m["duration"] = duration
                new_audios.append(m)

                
                # Segment
                s = copy.deepcopy(track_audio_proto)
                s["id"] = str(uuid.uuid4()).upper()
                s["material_id"] = mid
                s["source_timerange"] = {"start": 0, "duration": duration}
                s["target_timerange"] = {"start": current_audio_offset, "duration": duration}
                new_segments_audio.append(s)
                current_audio_offset += duration
        else:
            logger.warning("오디오 생성 스킵됨: 입력 파일이 없거나 프로토타입을 찾지 못했습니다.")

        
        if new_audios:
            draft_content["materials"]["audios"] = new_audios

        # 7. 자막 생성 (Main + Reading)
        new_texts = []
        new_segments_main = []
        new_segments_reading = []
        
        if proto_main_mat and proto_main_seg and self.subtitles:
            # [Fix] 위치 고정 (Main -550, Reading -420)
            # Canvas 높이 구하기 (Pixel -> Normalized)
            canvas_cfg = draft_content.get("canvas_config", {})
            c_height = canvas_cfg.get("height", 1080.0)
            
            # CapCut Y 좌표는 정규화된 값 (-0.5 ~ 0.5 or similar, Y-down positive)
            # 사용자가 요청한 -550은 위쪽. CapCut에서 위쪽은 Negative일 가능성이 높음.
            # 하지만 1080 캔버스에서 -550은 거의 Top Edge(-540).
            # 사용자의 의도를 그대로 반영하여 Pixel / Height 로 계산.
            pos_y_main = -550.0 / c_height 
            pos_y_read = -420.0 / c_height

            for sub in self.subtitles:
                start_us = int(sub.start_time * 1000000)
                dur_us = int(sub.duration * 1000000)
                
                # (A) Main Text (Origin)
                tm_main = self._create_text_material(proto_main_mat, sub.original_text, font_size_scale=1.0)
                new_texts.append(tm_main)
                
                ts_main = copy.deepcopy(proto_main_seg)
                ts_main["id"] = str(uuid.uuid4()).upper()
                ts_main["material_id"] = tm_main["id"]
                ts_main["target_timerange"] = {"start": start_us, "duration": dur_us}
                ts_main["source_timerange"] = {"start": 0, "duration": dur_us}
                
                # [Fix] 위치 강제 지정 (Robust)
                if "clip" not in ts_main:
                    ts_main["clip"] = {}
                if "transform" not in ts_main["clip"]:
                    ts_main["clip"]["transform"] = {}
                
                ts_main["clip"]["transform"]["x"] = 0.0
                ts_main["clip"]["transform"]["y"] = pos_y_main

                # [Debug] First segment log
                if len(new_segments_main) == 0:
                    logger.info(f"[Debug] Main Seg 0 Transform: {ts_main.get('clip', {}).get('transform')}, Expected Y: {pos_y_main}")

                new_segments_main.append(ts_main)
                
                # (B) Reading Text (Kana)

                reading_txt = sub.formatted_reading 
                if reading_txt:
                    # 두 번째 스타일이 있으면 그대로 쓰고, 없으면 0.6배 축소
                    scale = 1.0 if has_dual_style else 0.6
                    tm_read = self._create_text_material(proto_sub_mat, reading_txt, font_size_scale=scale)
                    new_texts.append(tm_read)
                    
                    ts_read = copy.deepcopy(proto_sub_seg)
                    ts_read["id"] = str(uuid.uuid4()).upper()
                    ts_read["material_id"] = tm_read["id"]
                    ts_read["target_timerange"] = {"start": start_us, "duration": dur_us}
                    ts_read["source_timerange"] = {"start": 0, "duration": dur_us}
                    
                    # [Fix] 위치 강제 지정 (Robust)
                    if "clip" not in ts_read:
                        ts_read["clip"] = {}
                    if "transform" not in ts_read["clip"]:
                        ts_read["clip"]["transform"] = {}
                        
                    ts_read["clip"]["transform"]["x"] = 0.0
                    ts_read["clip"]["transform"]["y"] = pos_y_read

                    new_segments_reading.append(ts_read)


            
            draft_content["materials"]["texts"] = new_texts

        # 8. 트랙 재구성 (New Only)
        new_tracks = []
        
        # 8-1. Video Track
        new_tracks.append({
            "attribute": 0, "flag": 0, "id": str(uuid.uuid4()).upper(),
            "segments": new_segments_video, "type": "video"
        })
        
        # 8-2. Voiceover Track
        if new_segments_audio:
            new_tracks.append({
                 "attribute": 0, "flag": 0, "id": str(uuid.uuid4()).upper(),
                 "segments": new_segments_audio, "type": "audio"
            })
            
        # 8-3. Text Tracks
        if new_segments_main:
            new_tracks.append({
                "attribute": 0, "flag": 0, "id": str(uuid.uuid4()).upper(),
                "segments": new_segments_main, "type": "text"
            })
            
        if new_segments_reading:
            new_tracks.append({
                "attribute": 0, "flag": 0, "id": str(uuid.uuid4()).upper(),
                "segments": new_segments_reading, "type": "text"
            })
            
        draft_content["tracks"] = new_tracks
        
        # Track 구성 결과 로깅
        final_track_types = [t["type"] for t in draft_content["tracks"]]
        logger.info(f"최종 트랙 구성: {final_track_types}")
        
        # 9. 저장 및 등록
        output_file = project_dir / "draft_content.json"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(draft_content, f, indent=4, ensure_ascii=False) # Korean support
            
            # --- [NEW] draft_meta_info.json 생성 logic ---
            meta_template_path = self.config.workspace_dir / "templates" / "temp_meta.txt"
            if meta_template_path.exists():
                try:
                    with open(meta_template_path, 'r', encoding='utf-8') as f:
                        meta_info = json.load(f)
                    
                    meta_info["draft_id"] = self.project_id
                    meta_info["draft_name"] = project_name
                    meta_info["draft_fold_path"] = str(project_dir).replace("\\", "/")
                    meta_info["tm_draft_create"] = int(time.time() * 1000000)
                    meta_info["tm_draft_modified"] = int(time.time() * 1000000)
                    
                    with open(project_dir / "draft_meta_info.json", 'w', encoding='utf-8') as f:
                        json.dump(meta_info, f, indent=4, ensure_ascii=False)
                    logger.info("draft_meta_info.json 생성 완료")
                except Exception as e:
                    logger.warning(f"draft_meta_info.json 생성 실패: {e}")
            else:
                logger.warning(f"temp_meta.txt이 없어 draft_meta_info.json 생성을 건너뜁니다.")

            if output_root:
                cover_path = self._copy_cover_image(output_root, project_dir)
                self._register_to_capcut(output_root, project_dir, project_name, cover_path)
                
            return True
        except Exception as e:
            logger.error(f"프로젝트 파일 저장 실패: {e}")
            return False
            
    def _copy_cover_image(self, root_path: Path, project_path: Path) -> str:
        """다른 프로젝트에서 draft_cover.jpg를 찾아 복사합니다."""
        try:
            # 최근 수정된 프로젝트 순으로 검색
            for other_project in sorted(root_path.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True):
                if not other_project.is_dir(): continue
                
                src_cover = other_project / "draft_cover.jpg"
                if src_cover.exists():
                    dst_cover = project_path / "draft_cover.jpg"
                    import shutil
                    shutil.copy2(src_cover, dst_cover)
                    return str(dst_cover).replace("\\", "/")
            return ""
        except Exception as e:
            logger.warning(f"커버 이미지 복사 실패: {e}")
            return ""

    def _register_to_capcut(self, root_path: Path, project_path: Path, project_name: str, cover_path: str = ""):
        """root_meta_info.json 파일을 수정하여 프로젝트를 CapCut 목록에 등록합니다."""
        meta_file = root_path / "root_meta_info.json"
        
        if not meta_file.exists():
            return 

        try:
            with open(meta_file, 'r', encoding='utf-8') as f:
                meta_data = json.load(f)
            
            now_us = int(time.time() * 1000000)
            
            root_path_str = str(root_path).replace("/", "\\")
            project_path_str = str(project_path).replace("\\", "/") 
            json_file_str = project_path_str + "/draft_content.json"
            
            # 메타데이터 복제 전략
            template_entry = None
            if "all_draft_store" in meta_data and meta_data["all_draft_store"]:
                template_entry = meta_data["all_draft_store"][0]
                
            if template_entry:
                import copy
                new_project = copy.deepcopy(template_entry)
                
                new_project["draft_id"] = self.project_id
                new_project["draft_name"] = project_name
                new_project["draft_fold_path"] = project_path_str
                new_project["draft_json_file"] = json_file_str
                # new_project["draft_root_path"] = root_path_str # Do not modify root path
                new_project["draft_cover"] = cover_path
                new_project["tm_draft_create"] = now_us
                new_project["tm_draft_modified"] = now_us
                
                if "all_draft_store" in meta_data:
                    meta_data["all_draft_store"] = [p for p in meta_data["all_draft_store"] if p.get("draft_id") != self.project_id]
                    meta_data["all_draft_store"].insert(0, new_project)
                    
                with open(meta_file, 'w', encoding='utf-8') as f:
                    json.dump(meta_data, f, indent=4, ensure_ascii=False)
                    
                logger.info(f"CapCut 프로젝트 목록에 등록됨: {project_name}")
            
        except Exception as e:
            logger.error(f"CapCut 프로젝트 등록 중 오류 발생: {e}")

# -----------------------------------------------------------------------------
# 6. 메인 실행 로직 (Main Execution)
# -----------------------------------------------------------------------------
def main():
    # .env 파일 로드
    if load_dotenv:
        load_dotenv()
        
    parser = argparse.ArgumentParser(description="CapCut 자동화 스크립트")
    parser.add_argument("-d", "--dir", type=Path, required=True, help="작업 디렉토리 경로 (videos, audios, subtitles 포함)")
    
    # API KEY: 환경 변수(GEMINI_API_KEY)가 있으면 선택, 없으면 필수
    env_api_key = os.getenv("GEMINI_API_KEY")
    parser.add_argument("-k", "--api-key", type=str, required=not bool(env_api_key), 
                        default=env_api_key, 
                        help="Google Gemini API Key (or set GEMINI_API_KEY env var)")
    
    parser.add_argument("-v", "--verbose", action="store_true", help="상세 로그 출력")
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        
    logger.info("=== AutoCapCut 스크립트 시작 ===")

    if not args.api_key:
        logger.error("API Key가 누락되었습니다. 인수(-k) 또는 .env(GEMINI_API_KEY)를 확인해주세요.")
        sys.exit(1)

    # 1. 설정 초기화
    config = ProjectConfig(workspace_dir=args.dir, gemini_api_key=args.api_key)
    
    # 2. 미디어 스캔
    try:
        scanner = MediaScanner(config.workspace_dir)
        videos = scanner.scan_videos()
        audios = scanner.scan_audios()
        subtitles = scanner.scan_subtitles()
        
        if not videos and not subtitles:
            logger.error("처리할 비디오나 자막 파일이 없습니다.")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"미디어 스캔 중 오류: {e}")
        sys.exit(1)

    # 3. 자막 처리 (LLM or Cache)
    processed_subtitles = []
    if subtitles:
        processor = SubtitleProcessor(config.gemini_api_key)
        for sub_file in subtitles:
            json_path = sub_file.with_suffix('.json')
            
            # 캐싱 로직: 이미 변환된 JSON 파일이 있으면 LLM 생략
            if json_path.exists():
                logger.info(f"기존 자막 파일 발견: {json_path.name} - LLM 요청을 건너뜁니다.")
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    for item in data:
                        start_sec = processor._time_str_to_seconds(item['start'])
                        end_sec = processor._time_str_to_seconds(item['end'])
                        processed_subtitles.append(SubtitleSegment(
                            start_time=start_sec,
                            end_time=end_sec,
                            original_text=item['origin'],
                            reading_text="", # reading 필드 제거됨
                            kanjis=item.get('kanjis', [])
                        ))
                except Exception as e:
                    logger.error(f"기존 JSON 파일 로드 실패 ({json_path}): {e}. LLM 재시도 권장.")
            else:
                # LLM 요청
                segments = processor.parse_and_convert(sub_file)
                processed_subtitles.extend(segments)
                
                # 결과 JSON 저장
                if segments:
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json_data = [
                            {
                                "start": f"{int(s.start_time//60):02d}:{int(s.start_time%60):02d}",
                                "end": f"{int(s.end_time//60):02d}:{int(s.end_time%60):02d}",
                                "origin": s.original_text,
                                "kanjis": s.kanjis
                            } for s in segments
                        ]
                        json.dump(json_data, f, indent=4, ensure_ascii=False)
                    logger.info(f"변환된 자막 JSON 저장됨: {json_path}")

    # 4. CapCut 프로젝트 생성
    generator = CapCutGenerator(config)
    generator.create_project(videos, audios, processed_subtitles)
    
    # 저장 경로 자동 감지 (CapCut 로컬 draft 폴더)
    capcut_draft_dir = None
    if os.name == 'nt' and 'LOCALAPPDATA' in os.environ:
        possible_dir = Path(os.environ['LOCALAPPDATA']) / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
        if possible_dir.exists():
            capcut_draft_dir = possible_dir
    
    # 프로젝트 저장 및 등록
    if generator.save(output_root=capcut_draft_dir):
        logger.info("모든 작업이 성공적으로 완료되었습니다.")
    else:
        logger.error("작업 중 오류가 발생했습니다.")
        sys.exit(1)

if __name__ == "__main__":
    main()
