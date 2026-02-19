"""Data models for the 6-step story script pipeline.

Pipeline Flow:
1. Research → ResearchPacket (MD)
2. Structure → SceneStructure (JSON)
3. Writing → NarrationScript (JSON)
4. Review → ReviewResult (JSON with patches)
5. Formatting → RecordingScript (JSON)
6. SRT → ko.srt (SRT file)
"""

from dataclasses import dataclass, field
from typing import Optional
import json


@dataclass
class ResearchPacket:
    """Step 1 출력: 원시 자료 패킷 (Markdown 형태)

    리서치 단계에서 수집한 순수 자료.
    대본이 아닌 팩트, 정보, 출처만 포함.
    """
    topic: str
    raw_content: str  # 전체 Markdown 내용

    # 구조화된 데이터 (파싱된 경우)
    key_facts: list[str] = field(default_factory=list)
    key_figures: list[str] = field(default_factory=list)  # 주요 인물
    key_events: list[str] = field(default_factory=list)   # 주요 사건
    controversies: list[str] = field(default_factory=list)  # 논쟁점/해석
    fan_theories: list[str] = field(default_factory=list)  # 팬덤 해석
    sources: list[str] = field(default_factory=list)  # 참고 자료

    def to_markdown(self) -> str:
        """Markdown 형태로 반환"""
        return self.raw_content

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "raw_content": self.raw_content,
            "key_facts": self.key_facts,
            "key_figures": self.key_figures,
            "key_events": self.key_events,
            "controversies": self.controversies,
            "fan_theories": self.fan_theories,
            "sources": self.sources,
        }


@dataclass
class SceneInfo:
    """개별 씬 정보 (뼈대만, 실제 문장 없음)"""
    scene_number: int
    title: str
    purpose: str  # "hook" | "setup" | "development" | "tension" | "climax" | "resolution"
    duration_seconds: int  # 예상 소요 시간 (초)
    key_points: list[str] = field(default_factory=list)  # 이 씬에서 다룰 핵심 포인트
    emotional_beat: str = ""  # 감정선: "curiosity" | "tension" | "shock" | "relief" 등
    transition_to_next: str = ""  # 다음 씬으로의 전환 방법

    def to_dict(self) -> dict:
        return {
            "scene_number": self.scene_number,
            "title": self.title,
            "purpose": self.purpose,
            "duration_seconds": self.duration_seconds,
            "key_points": self.key_points,
            "emotional_beat": self.emotional_beat,
            "transition_to_next": self.transition_to_next,
        }


@dataclass
class SceneStructure:
    """Step 2 출력: 씬 구조 (뼈대만)

    실제 나레이션 문장 없이 구조만 정의.
    각 씬의 목적, 핵심 포인트, 전환 로직만 포함.
    """
    topic: str
    target_duration_seconds: int  # 목표 영상 길이 (초, 예: 720 = 12분)
    narrative_arc: str  # 전체 서사 구조 설명
    scenes: list[SceneInfo] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "target_duration_seconds": self.target_duration_seconds,
            "narrative_arc": self.narrative_arc,
            "scenes": [s.to_dict() for s in self.scenes],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "SceneStructure":
        scenes = [
            SceneInfo(
                scene_number=s["scene_number"],
                title=s["title"],
                purpose=s["purpose"],
                duration_seconds=s["duration_seconds"],
                key_points=s.get("key_points", []),
                emotional_beat=s.get("emotional_beat", ""),
                transition_to_next=s.get("transition_to_next", ""),
            )
            for s in data.get("scenes", [])
        ]
        return cls(
            topic=data.get("topic", ""),
            target_duration_seconds=data.get("target_duration_seconds", 600),
            narrative_arc=data.get("narrative_arc", ""),
            scenes=scenes,
        )


@dataclass
class NarrationLine:
    """개별 나레이션 라인"""
    line_id: int
    scene_number: int
    text: str  # 실제 나레이션 문장 (15자 이내 권장)

    def to_dict(self) -> dict:
        return {
            "line_id": self.line_id,
            "scene_number": self.scene_number,
            "text": self.text,
        }


@dataclass
class NarrationScript:
    """Step 3 출력: 나레이션 대본

    실제 읽을 문장들이 담긴 대본.
    """
    topic: str
    lines: list[NarrationLine] = field(default_factory=list)

    @property
    def total_lines(self) -> int:
        return len(self.lines)

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "total_lines": self.total_lines,
            "lines": [l.to_dict() for l in self.lines],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "NarrationScript":
        lines = [
            NarrationLine(
                line_id=l["line_id"],
                scene_number=l["scene_number"],
                text=l["text"],
            )
            for l in data.get("lines", [])
        ]
        return cls(
            topic=data.get("topic", ""),
            lines=lines,
        )


@dataclass
class ReviewPatch:
    """개별 수정 사항"""
    line_id: int
    issue_type: str  # "weak_hook" | "low_tension" | "fact_error" | "too_long" | "unclear"
    original_text: str
    suggested_text: str
    reason: str

    def to_dict(self) -> dict:
        return {
            "line_id": self.line_id,
            "issue_type": self.issue_type,
            "original_text": self.original_text,
            "suggested_text": self.suggested_text,
            "reason": self.reason,
        }


@dataclass
class ReviewResult:
    """Step 4 출력: 검증 결과

    전체 재작성이 아닌 부분 수정(패치) 형태.
    """
    overall_score: int  # 1-10
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    patches: list[ReviewPatch] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "overall_score": self.overall_score,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "patches": [p.to_dict() for p in self.patches],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "ReviewResult":
        patches = [
            ReviewPatch(
                line_id=p["line_id"],
                issue_type=p["issue_type"],
                original_text=p["original_text"],
                suggested_text=p["suggested_text"],
                reason=p["reason"],
            )
            for p in data.get("patches", [])
        ]
        return cls(
            overall_score=data.get("overall_score", 5),
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            patches=patches,
        )

    def apply_to_script(self, script: NarrationScript) -> NarrationScript:
        """패치를 적용하여 수정된 스크립트 반환"""
        # line_id -> suggested_text 매핑
        patch_map = {p.line_id: p.suggested_text for p in self.patches}

        new_lines = []
        for line in script.lines:
            if line.line_id in patch_map:
                new_lines.append(NarrationLine(
                    line_id=line.line_id,
                    scene_number=line.scene_number,
                    text=patch_map[line.line_id],
                ))
            else:
                new_lines.append(line)

        return NarrationScript(topic=script.topic, lines=new_lines)


@dataclass
class RecordingInstruction:
    """개별 녹음 지시"""
    line_id: int
    scene_number: int
    text: str
    tone: str = "normal"  # "normal" | "slow" | "fast" | "whisper" | "emphasis"
    pause_before: float = 0.0  # 이 라인 앞 휴지 (초)
    pause_after: float = 0.3  # 이 라인 뒤 휴지 (초)
    bgm_cue: Optional[str] = None  # BGM 변경 지시 (예: "tension_build", "calm_ambient")
    sfx_cue: Optional[str] = None  # 효과음 지시 (예: "door_creak", "heartbeat")
    visual_note: Optional[str] = None  # 비주얼 노트 (예: "SCP 문서 UI 삽입")

    def to_dict(self) -> dict:
        return {
            "line_id": self.line_id,
            "scene_number": self.scene_number,
            "text": self.text,
            "tone": self.tone,
            "pause_before": self.pause_before,
            "pause_after": self.pause_after,
            "bgm_cue": self.bgm_cue,
            "sfx_cue": self.sfx_cue,
            "visual_note": self.visual_note,
        }


@dataclass
class RecordingScript:
    """Step 5 출력: 녹음용 스크립트 (최종)

    실제 녹음과 편집에 필요한 모든 정보 포함.
    JSON 형태로 저장됨.
    """
    topic: str
    total_estimated_duration: int  # 예상 총 길이 (초)
    instructions: list[RecordingInstruction] = field(default_factory=list)
    bgm_list: list[str] = field(default_factory=list)  # 사용 권장 BGM 목록
    sfx_list: list[str] = field(default_factory=list)  # 사용 권장 효과음 목록

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "total_estimated_duration": self.total_estimated_duration,
            "total_lines": len(self.instructions),
            "bgm_list": self.bgm_list,
            "sfx_list": self.sfx_list,
            "instructions": [i.to_dict() for i in self.instructions],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "RecordingScript":
        instructions = [
            RecordingInstruction(
                line_id=i["line_id"],
                scene_number=i["scene_number"],
                text=i["text"],
                tone=i.get("tone", "normal"),
                pause_before=i.get("pause_before", 0.0),
                pause_after=i.get("pause_after", 0.3),
                bgm_cue=i.get("bgm_cue"),
                sfx_cue=i.get("sfx_cue"),
                visual_note=i.get("visual_note"),
            )
            for i in data.get("instructions", [])
        ]
        return cls(
            topic=data.get("topic", ""),
            total_estimated_duration=data.get("total_estimated_duration", 0),
            instructions=instructions,
            bgm_list=data.get("bgm_list", []),
            sfx_list=data.get("sfx_list", []),
        )
