# Handcrafted by Pickle 🥒 for DevAlive Claude Code Pipeline
"""sprite_to_gif — 스프라이트 시트/프레임 묶음을 무한 루프 GIF로 만드는 데브얼라이브 전용 도구.

- converter        : 3x2(기본) 스프라이트 시트 슬라이싱과 GIF 조립(속도·트리밍·팔레트 최적화)
- generator        : 외부 API 없이 PIL 로 도트 캐릭터 프레임을 절차적으로 생성(walk·wave·pulse·bounce)
- vector_generator : SVG 벡터 모션 엔진 — 베지어 곡선 프리셋(lantern·crosshair·pulse_ring·spin_emblem)
- sources          : 프레임 묶음의 공급원. 로컬 절차 생성이 기본이고, 이미지 생성 API 를 붙일 수 있다
- cli              : `python -m sprite_to_gif.cli generate|convert|batch` + `--mode vector`
"""

from .converter import convert, compute_duration_ms, frames_to_gif, frames_to_sheet, slice_sheet
from .generator import MOTIONS, PixelSpec, generate_frames
from .vector_generator import PRESETS, VectorSpec, generate_vector_frames, render_vector_frame

__all__ = [
    "convert",
    "compute_duration_ms",
    "frames_to_gif",
    "frames_to_sheet",
    "slice_sheet",
    "generate_frames",
    "PixelSpec",
    "MOTIONS",
    "generate_vector_frames",
    "render_vector_frame",
    "VectorSpec",
    "PRESETS",
]
