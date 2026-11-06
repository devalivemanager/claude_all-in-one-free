# Handcrafted by Pickle 🥒 for DevAlive Claude Code Pipeline
"""외부 API 없이 도트 캐릭터 프레임을 절차적으로 생성한다(클로드 코드 단독 실행의 기본 공급원).

네 가지 기본 모션을 6프레임(3x2 시트용)으로 찍어 낸다:
- walk   : 도트 캐릭터 걷는 모션(다리 교차 + 몸통 들썩)
- wave   : 손 흔들기 인사(2회 루프)
- pulse  : 등불·소품 주위 빛 반짝임(오라 숨쉬기)
- bounce : 공 튀기기(기하학 모션)

전부 결정론적이다. 같은 인자면 언제나 같은 프레임이 나오므로 테스트·재현·diff 검수가 된다.
캐릭터는 16x16 도트 격자에 그리고 지정 크기로 확대한다(섞임 없는 깨끗한 픽셀 확대).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from PIL import Image, ImageDraw

DEFAULT_FRAMES = 6  # 3열 2행 시트의 기본 프레임 수


@dataclass
class PixelSpec:
    """도트 캐릭터의 규격. palette 의 색은 (R, G, B) 또는 (R, G, B, A)."""

    size: int = 64  # 프레임 한 칸 크기(px). 도트 원본 16px 를 이 크기로 확대한다
    dot: int = 16  # 도트 격자 해상도
    background: tuple[int, ...] | None = None  # None 이면 투명
    palette: dict[str, tuple[int, ...]] = field(
        default_factory=lambda: {
            "outline": (24, 20, 32, 255),
            "body": (58, 64, 96, 255),
            "skin": (236, 196, 152, 255),
            "accent": (255, 200, 80, 255),
            "glow": (255, 236, 160, 255),
            "ground": (70, 60, 80, 255),
        }
    )

    def __post_init__(self) -> None:
        if self.size < self.dot:
            raise ValueError(f"size 는 dot({self.dot}) 이상이어야 합니다: {self.size}")
        if self.dot < 4:
            raise ValueError(f"dot 은 4 이상이어야 합니다: {self.dot}")


MOTIONS = ("walk", "wave", "pulse", "bounce")


def _canvas(spec: PixelSpec) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    mode = "RGBA" if spec.background is None else "RGB"
    image = Image.new(mode, (spec.size, spec.size), spec.background or (0, 0, 0, 0))
    return image, ImageDraw.Draw(image)


def _scale(spec: PixelSpec, value: float) -> int:
    """도트 격자 좌표를 실제 픽셀 좌표로 옮긴다."""
    return round(value * spec.size / spec.dot)


def _rect(draw: ImageDraw.ImageDraw, spec: PixelSpec, box: tuple[float, float, float, float],
          color: tuple[int, ...]) -> None:
    x0, y0, x1, y1 = (_scale(spec, v) for v in box)
    draw.rectangle((x0, y0, max(x1, x0 + 1) - 1, max(y1, y0 + 1) - 1), fill=color)


def _draw_character(
    draw: ImageDraw.ImageDraw,
    spec: PixelSpec,
    leg_dx: int,
    body_dy: int,
    arm_height: int,
) -> None:
    """16x16 도트 격자에 옷 입은 작은 캐릭터를 그린다.

    leg_dx 는 다리 벌어짐(-3~3), body_dy 는 몸 들썩(0~1), arm_height 는 오른팔
    들어 올린 높이(0=내린 팔, 4=번쩍). 프레임마다 자세가 달라야 GIF 프레임이 합쳐지지
    않으므로, 모션마다 자세표를 미리 정해 둔다.
    """
    p = spec.palette
    cx = spec.dot / 2
    _rect(draw, spec, (cx - 4, 11 + body_dy, cx + 4, 13 + body_dy), p["ground"])  # 그림자
    _rect(draw, spec, (cx - 3 + leg_dx, 9 + body_dy, cx - 1, 12 + body_dy), p["outline"])  # 왼다리
    _rect(draw, spec, (cx + 1, 9 + body_dy, cx + 3 + leg_dx, 12 + body_dy), p["outline"])  # 오른다리
    _rect(draw, spec, (cx - 3, 5 + body_dy, cx + 3, 9 + body_dy), p["body"])  # 몸통
    _rect(draw, spec, (cx - 3, 5 + body_dy, cx + 3, 6 + body_dy), p["accent"])  # 두루마기 띠
    arm_y = 6 - arm_height + body_dy  # 팔이 올라갈수록 어깨 위로
    _rect(draw, spec, (cx + 3, arm_y, cx + 5, arm_y + 2), p["body"])  # 오른팔(흔드는 팔)
    _rect(draw, spec, (cx - 5, 6 + body_dy, cx - 3, 8 + body_dy), p["body"])  # 왼팔
    _rect(draw, spec, (cx - 2, 1 + body_dy, cx + 2, 5 + body_dy), p["skin"])  # 머리
    _rect(draw, spec, (cx - 2, 1 + body_dy, cx + 2, 2 + body_dy), p["outline"])  # 갓머리
    _rect(draw, spec, (cx - 1, 3 + body_dy, cx - 1, 3 + body_dy), p["outline"])  # 왼눈
    _rect(draw, spec, (cx + 1, 3 + body_dy, cx + 1, 3 + body_dy), p["outline"])  # 오른눈


# 모션별 자세표. 여섯 프레임이 전부 달라야 GIF 프레임이 병합되지 않고,
# 마지막이 첫 자세 가까이로 돌아와 루프가 끊기지 않는다(가이드 수칙 2·4).
WALK_POSE = [  # (다리 벌어짐, 몸 들썩): 걷는 사이클
    (1, 1), (3, 0), (0, 1), (-1, 1), (-3, 0), (0, 0),
]
WAVE_POSE = [  # (팔 높이, 몸 들썩): 손을 두 번 흔들며 인사
    (1, 0), (3, 0), (4, 1), (2, 1), (0, 0), (1, 1),
]
PULSE_GLOW = (4, 6, 8, 9, 5, 3)  # 등불 빛 반지름: 숨쉬듯 넓어졌다 좁아진다
BOUNCE_HEIGHT = (0, 4, 8, 6, 2, 1)  # 공 높이: 착지 후 살짝 떠오른 채로 루프


def _motion_walk(spec: PixelSpec, t: int, frames: int) -> Image.Image:
    image, draw = _canvas(spec)
    leg_dx, body_dy = WALK_POSE[t % len(WALK_POSE)]
    _draw_character(draw, spec, leg_dx=leg_dx, body_dy=body_dy, arm_height=0)
    _rect(draw, spec, (2, 14, 13, 15), spec.palette["ground"])  # 길
    return image


def _motion_wave(spec: PixelSpec, t: int, frames: int) -> Image.Image:
    image, draw = _canvas(spec)
    arm_height, body_dy = WAVE_POSE[t % len(WAVE_POSE)]
    _draw_character(draw, spec, leg_dx=0, body_dy=body_dy, arm_height=arm_height)
    return image


def _motion_pulse(spec: PixelSpec, t: int, frames: int) -> Image.Image:
    """등불 주위 빛 반짝임. 등불 자체는 흔들리지 않고 빛만 숨쉰다(가이드 수칙 4·배경 고정)."""
    image, draw = _canvas(spec)
    p = spec.palette
    glow_r = PULSE_GLOW[t % len(PULSE_GLOW)]
    cx, cy = spec.dot / 2, spec.dot / 2
    for dx in range(-glow_r, glow_r + 1):
        for dy in range(-glow_r, glow_r + 1):
            if dx * dx + dy * dy <= glow_r * glow_r:
                _rect(draw, spec, (cx + dx, cy + dy, cx + dx, cy + dy), p["glow"])
    _rect(draw, spec, (cx - 1, cy - 4, cx + 1, cy - 3), p["outline"])  # 등불 꼭지
    _rect(draw, spec, (cx - 2, cy - 3, cx + 2, cy + 3), p["accent"])  # 등불 몸(고정)
    _rect(draw, spec, (cx - 1, cy + 3, cx + 1, cy + 4), p["outline"])  # 등불 받침
    return image


def _motion_bounce(spec: PixelSpec, t: int, frames: int) -> Image.Image:
    image, draw = _canvas(spec)
    p = spec.palette
    height = BOUNCE_HEIGHT[t % len(BOUNCE_HEIGHT)]
    ball_r = 2
    cx = spec.dot / 2
    ground_y = 14
    ball_y = ground_y - height - ball_r
    _rect(draw, spec, (2, 14, 13, 15), p["ground"])
    shadow = max(1, 3 - height // 4)
    _rect(draw, spec, (cx - shadow, 14, cx + shadow, 15), p["outline"])
    for dx in range(-ball_r, ball_r + 1):
        for dy in range(-ball_r, ball_r + 1):
            if dx * dx + dy * dy <= ball_r * ball_r:
                _rect(draw, spec, (cx + dx, ball_y + dy, cx + dx, ball_y + dy), p["accent"])
    return image


_MOTION_FN = {
    "walk": _motion_walk,
    "wave": _motion_wave,
    "pulse": _motion_pulse,
    "bounce": _motion_bounce,
}


def generate_frames(
    motion: str = "walk",
    frames: int = DEFAULT_FRAMES,
    spec: PixelSpec | None = None,
) -> list[Image.Image]:
    """절차적 모션 프레임 묶음을 만든다. 외부 API·네트워크가 없어도 즉시 나온다."""
    if motion not in _MOTION_FN:
        raise ValueError(f"지원하지 않는 모션입니다: {motion} (가능: {', '.join(MOTIONS)})")
    if frames < 2:
        raise ValueError(f"프레임 수는 2 이상이어야 합니다: {frames}")
    spec = spec or PixelSpec()
    return [_MOTION_FN[motion](spec, t, frames) for t in range(frames)]
