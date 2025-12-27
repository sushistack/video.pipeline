
import json
import uuid
import shutil
import glob
from pathlib import Path
from typing import Dict, Any, List
from mutagen import File as MutagenFile

class CapCutGenerator:
    """
    CapCut 프로젝트 생성기
    1단계: 구조 및 JSON 핸들러 (완료)
    2단계: 타임라인 빌더 (비디오 및 오디오 트랙)
    """
    
    def __init__(self, output_root: Path):
        self.output_root = output_root
        self.templates_dir = Path(__file__).parent.parent / "assets" / "templates"
        template_path = self.templates_dir / "capcut.draft.template.json"
        
        # 디버그 경로 확인
        print(f"[Debug] Loading Template from: {template_path}")
        if not template_path.exists():
             print(f"[Error] Template file does not exist at {template_path}")
        
        self.draft_template = self._load_json(template_path)
        print(f"[Debug] Loaded JSON Keys: {list(self.draft_template.keys())}")
        print(f"[Debug] Tracks Count in Loaded JSON: {len(self.draft_template.get('tracks', []))}")

        self.meta_template = self._load_json(self.templates_dir / "capcut.draft.meta.info.json")
        
        # 템플릿으로부터 프로젝트 데이터 구조 초기화
        import copy
        self.content = copy.deepcopy(self.draft_template) # DEEPCOPY 필수 (원본 보존)
        self.meta = copy.deepcopy(self.meta_template)
        
        # 트랙 및 머티리얼 리셋 로직은 생성 단계로 이동됨
        # self.content["tracks"] = [] <--- 제거됨: 프로토타입 유지!
        
        # 프로토타이핑을 위해 머티리얼도 유지
        # self.content["materials"] = { ... } <--- 제거됨

        
    def _load_json(self, path: Path) -> Dict[str, Any]:
        """JSON 파일을 에러 처리와 함께 로드합니다."""
        if not path.exists():
            raise FileNotFoundError(f"Template not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def generate_id(self) -> str:
        """CapCut 스타일의 대문자 UUID를 생성합니다."""
        return str(uuid.uuid4()).upper()

    def _parse_time_str(self, time_str: str) -> int:
        """'MM:SS:mmm' 또는 'HH:MM:SS,mmm' 형식을 마이크로초로 변환합니다."""
        # 문자열 정리
        time_str = time_str.replace(',', '.')
        parts = time_str.split(':')
        
        hours = 0
        minutes = 0
        seconds = 0.0
        
        if len(parts) == 3:
            # HH:MM:SS.mmm 또는 MM:SS:mmm ? 
            # 자막 파일은 보통 HH:MM:SS,mmm 형식이지만, 이전 valid_draft는 MM:SS.mss를 사용했음
            # float 규칙에 따라 감지 시도
            # 파이프라인에서 생성된 자막 파일이라면 표준 형식일 가능성이 큼.
            # 초기 단계 출력은 MM:SS:mmm (예: 00:02:472) 사용하여 2초 472ms를 의미했음.
            try:
                if '.' in parts[2]:
                    minutes = int(parts[0])
                    seconds = float(parts[1]) # 잠깐, 형식이 이상함.
                    # 표준 SRT 가정: HH:MM:SS,mmm -> 00:00:02,472
                    # 출력된 값은 '00:00:000', '00:02:472'.
                    # MM:SS:mmm 처럼 보임. 
                    # 00분, 02초, 472ms?
                    hours = 0
                    minutes = int(parts[0])
                    seconds = int(parts[1])
                    milliseconds = int(parts[2])
                    return (hours * 3600 + minutes * 60 + seconds) * 1000000 + milliseconds * 1000
            except:
                pass
                
        # 강력한 폴백 파서
        try:
             # 표준 timedelta 형식 가정
             # 실패 시 파일 형식을 다시 확인해야 함
             pass
        except:
             return 0
             
        # 관측된 '00:00:000' -> MM:SS:mmm 형식을 기반으로 재평가
        try:
            minutes = int(parts[0])
            seconds = int(parts[1])
            milliseconds = int(parts[2])
            return (minutes * 60 + seconds) * 1000000 + milliseconds * 1000
        except:
            pass
            
        print(f"Warning: Could not parse time {time_str}")
        return 0

    def _get_media_duration(self, path: Path) -> int:
        """ffprobe를 사용하여 미디어 길이를 마이크로초 단위로 반환합니다."""
        import subprocess
        try:
            # 비디오에 더 강력한 ffprobe 먼저 시도
            cmd = [
                'ffprobe', 
                '-v', 'error', 
                '-show_entries', 'format=duration', 
                '-of', 'default=noprint_wrappers=1:nokey=1', 
                str(path)
            ]
            # 윈도우 환경 특화: string 출력을 위해 text=True 사용 대신 decode()
            result = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode().strip()
            return int(float(result) * 1000000)
        except Exception as e:
            print(f"[Warning] ffprobe failed for {path.name}: {e}")
            
        # ffprobe 실패 시 mutagen으로 폴백 (주로 오디오용)
        try:
            f = MutagenFile(path)
            if f and f.info:
                return int(f.info.length * 1000000)
        except Exception as e:
             print(f"[Error] mutagen failed for {path.name}: {e}")
             
        return 0

    def add_media_tracks(self, project_name: str):
        """
        2단계: 프로토타입 복제를 사용하여 비디오 및 오디오 트랙 생성.
        """
        project_dir = self.output_root / project_name
        video_dir = project_dir / "simulated"
        audio_dir = project_dir / "audios" / "ja"
        
        # 1. 파일 스캔 및 정렬
        videos = sorted(list(video_dir.glob("*.mp4")))
        audios = sorted(list(audio_dir.glob("*.mp3")))
        
        if len(videos) != len(audios):
            print(f"WARNING: Video count ({len(videos)}) != Audio count ({len(audios)})")
            
        print(f"Found {len(videos)} videos and {len(audios)} audios.")
        
        # --- 프로토타입 추출 ---
        import copy
        
        # 파일에 디버그 로깅
        debug_log_path = self.output_root / "gen_debug.txt"
        with open(debug_log_path, "w", encoding="utf-8") as log:
            log.write(f"Template Tracks Types: {[t['type'] for t in self.content['tracks']]}\n")

            # 비디오 프로토타입
            video_mat_proto = self.content["materials"]["videos"][0] if self.content["materials"].get("videos") else None
            
            track_video_proto = None
            for t in self.content["tracks"]:
                if t["type"] == "video" and t.get("segments"):
                    track_video_proto = t["segments"][0]
                    break
            
            log.write(f"Video Mat Proto: {bool(video_mat_proto)}\n")
            log.write(f"Video Track Proto: {bool(track_video_proto)}\n")

            # 오디오 프로토타입
            audio_mat_proto = self.content["materials"]["audios"][0] if self.content["materials"].get("audios") else None
            
            track_audio_proto = None
            for t in self.content["tracks"]:
                if t["type"] == "audio" and t.get("segments"):
                    track_audio_proto = t["segments"][0]
                    break
            
            log.write(f"Audio Mat Proto: {bool(audio_mat_proto)}\n")
            log.write(f"Audio Track Proto: {bool(track_audio_proto)}\n")

            if not video_mat_proto or not track_video_proto:
                log.write("ERROR: Missing Video Prototypes\n")
                print("Error: Could not find Video prototypes in template.")
                return 

        # 명확성을 위해 이름 변경
        video_proto = video_mat_proto
        audio_proto = audio_mat_proto


        # --- 기존 내용 삭제 ---
        self.content["materials"]["videos"] = []
        self.content["materials"]["audios"] = []
        # 트랙 리스트를 완전히 다시 빌드합니다.
        # 하지만 로직 분리를 위해 'Text' 트랙 플레이스홀더는 유지해야 할까요?
        # 사실 sample.py는 안전을 위해 모든 트랙을 삭제합니다.
        # 하지만 process_subtitles는 별도의 단계(Step)입니다.
        # 여기서 비디오/오디오 트랙을 정리하거나, 트랙 전체를 지우고 순서대로 다시 만들어야 합니다.
        # 여기서는 트랙을 정리하고 다시 추가하겠습니다.
        # 주의: process_subtitles는 추가(append)를 가정합니다.
        # 따라서 여기서 비디오/오디오 머티리얼을 정리하고,
        # 기존 비디오/오디오 트랙을 제거합니다.
        
        self.content["tracks"] = [t for t in self.content["tracks"] if t["type"] not in ["video", "audio"]]
        
        if not videos:
             print("Error: No videos found for audio-driven timeline.")
             return

        # 2. 시퀀스 처리 (오디오 기반)
        current_time_us = 0
        new_video_segments = []
        new_audio_segments = []
        
        # 오디오 개수에 맞춰 진행
        count = len(audios)
        
        for i in range(count):
            aud_path = audios[i]
            # 비디오가 오디오보다 적으면 재활용
            vid_path = videos[i % len(videos)]
            
            # --- 오디오 처리 ---
            if audio_proto and track_audio_proto:
                aud_duration = self._get_media_duration(aud_path)
                aud_material_id = self.generate_id()
                
                # 머티리얼 복제
                m_aud = copy.deepcopy(audio_proto)
                m_aud["id"] = aud_material_id
                m_aud["path"] = str(aud_path.absolute()).replace("\\", "/")
                m_aud["duration"] = aud_duration
                self.content["materials"]["audios"].append(m_aud)
                
                # 세그먼트 복제
                s_aud = copy.deepcopy(track_audio_proto)
                s_aud["id"] = self.generate_id()
                s_aud["material_id"] = aud_material_id
                s_aud["source_timerange"] = {"start": 0, "duration": aud_duration}
                s_aud["target_timerange"] = {"start": current_time_us, "duration": aud_duration}
                s_aud["render_index"] = i
                new_audio_segments.append(s_aud)
            else:
                # 프로토타입이 있으면 발생하지 않지만 안전장치
                aud_duration = 0

            # --- 비디오 처리 ---
            # 비디오 길이는 이 세그먼트의 오디오 길이와 일치해야 함
            # 전체 비디오 파일을 사용하거나, 오디오보다 길면 자름.
            # 비디오가 오디오보다 짧으면 CapCut이 마지막 프레임을 정지시킬 수 있음.
            
            vid_file_dur = self._get_media_duration(vid_path)
            vid_material_id = self.generate_id()
            
            # 머티리얼 복제
            m_vid = copy.deepcopy(video_proto)
            m_vid["id"] = vid_material_id
            m_vid["path"] = str(vid_path.absolute()).replace("\\", "/")
            m_vid["duration"] = vid_file_dur
            self.content["materials"]["videos"].append(m_vid)
            
            # 세그먼트 복제
            s_vid = copy.deepcopy(track_video_proto)
            s_vid["id"] = self.generate_id()
            s_vid["material_id"] = vid_material_id
            
            # 소스: 0부터 min(비디오길이, 오디오길이)까지
            # 오디오 클립 내에서 비디오 내용을 반복(Loop)할 것인가? 아니오, 보통 한 번만 재생.
            source_dur = min(vid_file_dur, aud_duration)
            
            s_vid["source_timerange"] = {"start": 0, "duration": source_dur}
            # 타겟: 오디오 길이와 정확히 일치
            s_vid["target_timerange"] = {"start": current_time_us, "duration": aud_duration}
            s_vid["render_index"] = i
            new_video_segments.append(s_vid)
            
            # 오디오 길이만큼 타임라인 전진
            current_time_us += aud_duration
            
        # 3. 콘텐츠에 트랙 추가
        # 세그먼트를 담을 새로운 트랙 객체 생성
        if new_video_segments:
            self.content["tracks"].append({
                "id": self.generate_id(),
                "type": "video",
                "attribute": 0,
                "segments": new_video_segments
            })
            
        if new_audio_segments:
            self.content["tracks"].append({
                "id": self.generate_id(),
                "type": "audio",
                "attribute": 0,
                "segments": new_audio_segments
            })
        
        # 총 지속 시간 업데이트
        self.content["duration"] = current_time_us

    def _split_text(self, text: str) -> List[str]:
        """텍스트를 최대 16글자씩 분할하여 리스트로 반환합니다."""
        # 이미 개행문자가 있는지 확인 (수동 줄바꿈)
        if '\n' in text:
            # Re-split long lines? Or respect manual? 
            # 일단 입력이 자동 줄바꿈이 필요하다고 가정.
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
        """텍스트의 문자 인덱스를 (요미가나, 원본 길이, 칸지 인덱스) 튜플로 매핑합니다."""
        mapping = {}
        k_ptr = 0
        t_ptr = 0
        while t_ptr < len(text) and k_ptr < len(kanjis):
            target = kanjis[k_ptr]['kanji']
            try:
                found_idx = text.index(target, t_ptr)
                # 텍스트, 원본 길이, 그리고 kanjis 배열 내 인덱스를 함께 저장
                mapping[found_idx] = (kanjis[k_ptr]['yomigana'], len(target), k_ptr)
                t_ptr = found_idx + 1 # 계속 스캔하기 위해 첫 글자 다음으로 이동
                # 이중 매칭 방지를 위해 토큰 길이만큼 건너뜀
                t_ptr = found_idx + len(target)
                k_ptr += 1
            except ValueError:
                k_ptr += 1
        return mapping




    def process_subtitles(self, project_name: str):
        """
        3단계 & 4단계: 프로토타입 복제를 이용한 자막 처리.
        """
        sub_path = self.output_root / project_name / "subtitles" / "synced" / "ja.json"
        if not sub_path.exists():
            print(f"No subtitle file found at {sub_path}")
            return

        with open(sub_path, "r", encoding="utf-8") as f:
            subtitles = json.load(f)

        # --- PROTOTYPE EXTRACTION (TEXT) ---
        import copy
        
        text_mats = self.content["materials"].get("texts", [])
        text_tracks = [t for t in self.content["tracks"] if t["type"] == "text" and t.get("segments")]
        
        if not text_tracks:
            print("Error: No text tracks found in template for prototyping.")
            return

        # Main Prototype
        proto_main_mat = text_mats[0] if text_mats else None
        proto_main_seg = text_tracks[0]["segments"][0] if text_tracks else None
        
        # Ruby Prototype
        has_ruby_proto = len(text_mats) > 1 and len(text_tracks) > 1
        proto_ruby_mat = text_mats[1] if has_ruby_proto else proto_main_mat
        proto_ruby_seg = text_tracks[1]["segments"][0] if has_ruby_proto else proto_main_seg

        if not proto_main_mat or not proto_main_seg:
             print("Error: Could not extract Main Text prototype.")
             return

        # --- CLEAR EXISTING TEXT ---
        self.content["materials"]["texts"] = []
        self.content["tracks"] = [t for t in self.content["tracks"] if t["type"] != "text"]

        new_main_segments = []
        # 요미가나를 칸지 인덱스(k_ptr)별로 분리하여 관리
        # 예: ruby_segments_by_idx[0] = [모든 자막의 첫 번째 한자 요미가나들]
        from collections import defaultdict
        ruby_segments_by_idx = defaultdict(list)
        
        seg_counter = 0

        # 프레임 레이트 설정 (30 FPS)
        FPS = 30.0
        FRAME_US = int(1000000 / FPS) # 33333
        SAFETY_GAP_US = FRAME_US # 1 frame gap

        def snap_to_frame(us: int) -> int:
            """마이크로초를 가장 가까운 프레임 경계로 스냅(반올림) 합니다."""
            frames = round(us / FRAME_US)
            return frames * FRAME_US

        num_subs = len(subtitles)
        
        for i, sub in enumerate(subtitles):
            raw_text = sub.get("text", "")
            kanjis = sub.get("kanjis", [])
            
            # --- Audio Sync Logic ---
            # 사용자 요청: "자막 길이가 오디오길이랑 안 맞는경우가 있어서 그거 오디오 기준으로 잘라줘"
            # JSON의 start/end 대신, 이미 생성된 오디오 트랙의 타이밍을 사용합니다.
            
            # 오디오 트랙 세그먼트 찾기 (Step 2에서 생성됨)
            # 오디오 트랙이 여러 개일 수 있으나, add_media_tracks에서 순서대로 생성함.
            # 여기서는 "audio" 타입 트랙의 세그먼트들을 평탄화해서 가져오거나, 
            # 단순히 순서대로 매칭합니다. (1 Sub = 1 Audio File 가정)
            
            # 오디오 세그먼트 리스트 캐싱 (루프 밖에서 해야 효율적이지만, 안전하게 여기서 찾음)
            if i == 0:
                self.audio_segments_flat = []
                for t in self.content["tracks"]:
                    if t["type"] == "audio":
                         self.audio_segments_flat.extend(t.get("segments", []))
                
                # 오디오 세그먼트 정렬 (render_index 기준)
                self.audio_segments_flat.sort(key=lambda x: x.get("render_index", 0))

            if i < len(self.audio_segments_flat):
                # 오디오 기준 타이밍 강제 적용
                aud_seg = self.audio_segments_flat[i]
                start_us = aud_seg["target_timerange"]["start"]
                duration_us = aud_seg["target_timerange"]["duration"]
                end_us = start_us + duration_us
            else:
                # 오디오가 부족한 경우 (예외 처리)
                # 기존 로직 폴백 혹은 건너뛰기
                print(f"Warning: No audio segment found for subtitle {i}. Skipping.")
                continue

            # 로직: Gap Filling, Overlap 방지 등은 오디오 트랙이 이미 처리되었으므로 불필요.
            # 오디오 자체가 타임라인을 정의함.
            # 단, 트랙 압축(Visual Stacking)을 위해 겹침이 있는지 확인해야 하나?
            # 오디오가 겹치지 않는다면 자막도 겹치지 않음.
            # Step 2에서 오디오는 순차적으로 배치됨 (current_time_us += dur).
            # 따라서 겹침 없음. 1ms Safety Gap도 필요 없음 (딱 붙어있음).
            # 하지만 "Visual Gap"이 걱정된다면 1ms를 줄여주는 센스?
            # 아니, 오디오대로 컷하라고 했으니 정확히 맞춥니다.
            
            if duration_us <= 0:
                 continue
            
            # 수정: Map과 Loop 간 인덱스 불일치 방지를 위한 텍스트 정제
            # 줄바꿈 문자를 제거하여 'clean_text' 인덱스와 'lines' 순회 인덱스가 정확히 일치하도록 함.
            clean_text = raw_text.replace('\n', '')
            
            yomi_map = self._map_yomigana(clean_text, kanjis)
            
            # 포맷팅 적용 (16자 초과 시 분할)
            # _split_text는 이제 clean_text를 받음
            lines = self._split_text(clean_text) 
            final_text = "\n".join(lines)
            
            # --- 메인 자막 ---
            self._add_text_segment_clone(
                new_main_segments, 
                proto_main_mat, 
                proto_main_seg, 
                final_text, 
                start_us, 
                duration_us, 
                seg_counter
            )
            
            # --- 요미가나 ---
            CHAR_WIDTH = 0.035
            # 줄 간격 조정 - 사용자 피드백 "너무 좁다". 0.155로 증가.
            LINE_HEIGHT = 0.2
            
            # 좌표계 수정:
            # 사용자 피드백 증거: 값이 클수록 위쪽에 위치함 (Y-Up 양수 좌표계).
            # 하지만 템플릿은 하단 1/3 지점이 0.6944 (양수)임.
            # (0,0)이 좌상단이고 반전된 게 아니라면 모순됨.
            # 
            # 반전 증거: 1행(0.92)이 0행(0.77)보다 위에 나타남.
            # 0.92가 0.77보다 시각적으로 위에 있다면 -> Y-UP은 양수.
            # 하단에 배치하려면 Y는 음수여야 함 (0이 중앙이라고 가정 시).
            
            # -0.75(너무 낮음/묻힘)에서 -0.4(하단 1/3 지점)로 조정
            MAIN_Y = -0.4 
            RUBY_Y_OFFSET = -1.185
            
            num_lines = len(lines)
            
            # 스택 로직: 0행을 맨 위에, 1행을 그 아래에 배치.
            # Y-UP이 양수이므로: 0행이 가장 높은 Y, 1행은 더 낮은 Y를 가짐.
            # 시작 Y (맨 윗줄) = MAIN_Y + (스택 절반 높이)?
            # 혹은 MAIN_Y가 "앵커" (바닥 라인?)
            # MAIN_Y를 중심으로 블록을 정렬함.
            
            # 블록 높이 = (줄 수 - 1) * 줄 간격
            # 최상단 Y = 중심 Y + (블록 높이 절반)
            start_y = MAIN_Y + ((num_lines - 1) * LINE_HEIGHT * 0.5)
            
            char_offset_global = 0 
            
            # 폰트 크기/스케일에 따른 표준 너비
            FULL_WIDTH = 0.0580 # 한자 기본 너비 (우측 밀림 방지를 위해 0.035에서 축소)
            HALF_WIDTH = 0.0290 # ASCII/공백용
            
            def get_char_width(c):
                 # 단순 휴리스틱: ord(c) < 128 (ASCII) -> 절반 너비
                 # 반각 카나도 체크해야 할까? 현재는 ASCII만.
                 return HALF_WIDTH if ord(c) < 128 else FULL_WIDTH

            for line_idx, line in enumerate(lines):
                line_len = len(line)
                
                # 아래로 쌓기: 다음 줄은 높이를 뺌(-)
                base_y = start_y - (line_idx * LINE_HEIGHT)
                
                # 라인의 총 시각적 너비 계산
                total_visual_width = sum(get_char_width(c) for c in line)
                
                # 라인 중심을 기준으로 각 글자의 중심 위치가 필요함.
                # 시작 X (왼쪽) = 0.5 - (총 너비 / 2)
                
                current_x = 0.5 - (total_visual_width / 2)
                
                for char_i, char in enumerate(line):
                    cw = get_char_width(char)
                    center_pos = current_x + (cw / 2)
                    
                    if char_offset_global in yomi_map:
                        # 튜플 언패킹 업데이트: (text, span_len, k_idx)
                        ruby_text, span_len, k_idx = yomi_map[char_offset_global]
                        
                        # 그룹 너비 계산 ("순서 이상함" 버그 수정)
                        # char_i ... char_i + span_len - 1 까지의 너비 필요
                        # 범위 체크 (단어가 줄바꿈에 걸리면 범위 자름)
                        safe_span = min(span_len, line_len - char_i)
                        
                        group_width = 0
                        for k in range(safe_span):
                             group_width += get_char_width(line[char_i + k])
                        
                        # 그룹의 중심 = 현재 X + (그룹 너비 / 2)
                        center_x = current_x + (group_width / 2)
                        ruby_y = base_y - RUBY_Y_OFFSET
                        
                        self._add_ruby_segment_clone(
                            ruby_segments_by_idx[k_idx], # 해당 인덱스의 리스트에 추가
                            proto_ruby_mat,
                            proto_ruby_seg,
                            ruby_text,
                            start_us, 
                            duration_us,
                            center_x,
                            ruby_y,
                            seg_counter
                        )
                    
                    current_x += cw
                    char_offset_global += 1
                    
            seg_counter += 1

        # Create Tracks for segments
        if new_main_segments:
            self.content["tracks"].append({
                "id": self.generate_id(),
                "type": "text",
                "attribute": 0,
                "segments": new_main_segments
            })
            
        # 요미가나 트랙 생성: 인덱스 순서대로 별도의 트랙 생성
        # kanjis[0] -> Track 4, kanjis[1] -> Track 5 ...
        sorted_indices = sorted(ruby_segments_by_idx.keys())
        for idx in sorted_indices:
             segments = ruby_segments_by_idx[idx]
             if segments:
                self.content["tracks"].append({
                    "id": self.generate_id(),
                    "type": "text",
                    "attribute": 0,
                    "segments": segments
                })

    def _create_text_material(self, proto: Dict, text: str, scale: float = 1.0, is_ruby: bool = False) -> Dict:
        """클론에서 콘텐츠 텍스트 및 스타일을 업데이트합니다."""
        import copy
        m = copy.deepcopy(proto)
        m["id"] = self.generate_id()
        
        try:
            content = json.loads(m["content"])
            content["text"] = text
            
            # 스타일 규칙 적용
            styles = content.get("styles", [])
            if styles:
                # 새 텍스트 길이를 커버하도록 범위 업데이트
                for s in styles:
                    s["range"] = [0, len(text)]
                    
                    # 필요시 폰트 크기 일관성 유지 (5.0), 혹은 프로토타입 신뢰
                    # s["size"] = 5.0 
                
            m["content"] = json.dumps(content, ensure_ascii=False)
            
            # 외부 속성 (꼭 필요한 경우만 업데이트, 아니면 프로토타입 신뢰)
            # m["font_size"] = 5.0 
            # 줄 간격 오버라이드 제거
            
        except Exception as e:
            print(f"Error parsing text content: {e}")
            
        return m

    def _add_text_segment_clone(self, target_list: List, proto_mat: Dict, proto_seg: Dict, 
                               text: str, start_us: int, duration_us: int, render_index: int):
        import copy
        # Create Material
        new_mat = self._create_text_material(proto_mat, text, is_ruby=False)
        self.content["materials"]["texts"].append(new_mat)
        
        # Create Segment
        s = copy.deepcopy(proto_seg)
        s["id"] = self.generate_id()
        s["material_id"] = new_mat["id"]
        s["target_timerange"] = {"start": start_us, "duration": duration_us}
        s["source_timerange"] = {"start": 0, "duration": duration_us}
        s["render_index"] = render_index
        
        if "clip" not in s: s["clip"] = {}
        if "transform" not in s["clip"]: s["clip"]["transform"] = {}
        if "scale" not in s["clip"]: s["clip"]["scale"] = {}
        
        # Coords (Main)
        s["clip"]["transform"]["x"] = 0.5052
        s["clip"]["transform"]["y"] = 0.6944
        s["clip"]["scale"] = {"x": 1.0, "y": 1.0}
        
        target_list.append(s)

    def _add_ruby_segment_clone(self, target_list: List, proto_mat: Dict, proto_seg: Dict,
                               text: str, start_us: int, duration_us: int, 
                               x: float, y: float, render_index: int):
        import copy
        # Create Material
        new_mat = self._create_text_material(proto_mat, text, is_ruby=True)
        self.content["materials"]["texts"].append(new_mat)
        
        # Create Segment
        s = copy.deepcopy(proto_seg)
        s["id"] = self.generate_id()
        s["material_id"] = new_mat["id"]
        s["target_timerange"] = {"start": start_us, "duration": duration_us}
        s["source_timerange"] = {"start": 0, "duration": duration_us}
        s["render_index"] = render_index
        
        if "clip" not in s: s["clip"] = {}
        if "transform" not in s["clip"]: s["clip"]["transform"] = {}
        if "scale" not in s["clip"]: s["clip"]["scale"] = {}
        
        # Coords (Ruby)
        s["clip"]["transform"]["x"] = x
        s["clip"]["transform"]["y"] = y
        s["clip"]["scale"] = {"x": 0.6, "y": 0.6}
        
        target_list.append(s)
    
    def _write_project_files(self, draft_dir: Path, project_name: str):
        """프로젝트 파일을 특정 디렉토리에 쓰는 내부 헬퍼 함수."""
        if draft_dir.exists():
            shutil.rmtree(draft_dir)
        draft_dir.mkdir(parents=True, exist_ok=True)

        # 메타 정보 업데이트
        # CapCut은 메타 정보에 절대 경로를 기대할까요? 
        # draft_root_path는 보통 폴더를 가리킴.
        
        # CapCut 네이티브 폴더로 이동할 때 경로가 정확한지 확인.
        self.meta["draft_id"] = self.generate_id()
        self.meta["draft_name"] = project_name
        self.meta["draft_root_path"] = str(draft_dir).replace("\\", "/")
        self.meta["draft_fold_path"] = str(draft_dir).replace("\\", "/")
        self.meta["tm_duration"] = self.content.get("duration", 0)
        
        # 파일 쓰기
        self._write_json(draft_dir / "draft_content.json", self.content)
        self._write_json(draft_dir / "draft_meta_info.json", self.meta)
        
        # 커버 복사 (옵션)
        cover_src = self.templates_dir / "draft_cover.jpg"
        if cover_src.exists():
            shutil.copy(cover_src, draft_dir / "draft_cover.jpg")

    def save_project(self, project_name: str) -> Path:
        """기본 출력 디렉토리 workspace/{project_name}/capcut_draft 에 저장"""
        draft_dir = self.output_root / project_name / "capcut_draft"
        self._write_project_files(draft_dir, project_name)
        return draft_dir

    def export_to_capcut(self, project_name: str) -> Path:
        """
        CapCut 로컬 데이터 폴더로 직접 내보냅니다.
        경로: %LOCALAPPDATA%/CapCut/User Data/Projects/com.lveditor.draft/{project_name}_{timestamp}
        """
        import os
        from datetime import datetime
        
        local_appdata = os.environ.get("LOCALAPPDATA")
        if not local_appdata:
            # 폴백
            local_appdata = str(Path.home() / "AppData" / "Local")
            
        base_dir = Path(local_appdata) / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
        
        # 타임스탬프가 포함된 폴더명 생성: 예: project_20231226_1830
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        folder_name = f"{project_name}_{timestamp}"
        
        draft_dir = base_dir / folder_name
        
        # 베이스 디렉토리가 존재하는지 확인 (사용자가 CapCut을 설치하지 않았을 수 있음)
        if not base_dir.exists():
            print(f"Warning: CapCut draft directory not found at {base_dir}")
            # 그래도 생성을 시도해볼까요?
            base_dir.mkdir(parents=True, exist_ok=True)
            
        print(f"Exporting to CapCut Native Path: {draft_dir}")
        
        self._write_project_files(draft_dir, folder_name) # CapCut 목록 혼란 방지를 위해 폴더명을 드래프트 이름으로 사용
        return draft_dir

    def _write_json(self, path: Path, data: Dict[str, Any]):
        """JSON 파일을 씁니다."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    # 테스트 스텁
    print("Testing CapCutGenerator Step 3...")
    root = Path(__file__).parent.parent / "workspace"
    generator = CapCutGenerator(root)
    
    test_project = "sample" 
    
    try:
        generator.add_media_tracks(test_project)
        generator.process_subtitles(test_project) # Step 3
        saved_path = generator.save_project(test_project)
        print(f"Project saved to: {saved_path}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error: {e}")



