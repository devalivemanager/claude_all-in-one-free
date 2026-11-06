# Handcrafted by Pickle 🥒 for DevAlive Claude Code Pipeline
"""SVG 기반 벡터 모션 엔진 — 아무리 확대해도 선이 깨지지 않는 수학적 프레임 생성.

도트(generator) 모션의 다음 단계. 베지어 곡선과 삼각함수로 프레임을 「식」으로
적어 넣고, 고해상도로 래스터화한 뒤(수퍼샘플링 안티에일리어싱) 지정 크기로
줄여 계단 없는 칼선을 만든다. 외부 무거운 툴(Cairo·Inkscape·librsvg) 의존성
제로 — 순수 파이썬 + Pillow 만으로 돈다.

네 가지 프리셋:
- lantern     : 밤지기 흑등 — 바람에 부드럽게 흔들리는 랜턴 바디 + 일렁이는
                불꽃 베지어 패스 + 빛 번짐 오라
- crosshair   : 로블록스/SF 조준선 — 360도 부드럽게 회전하는 정밀 눈금선 +
                중심부 맥동(Pulse) 링
- pulse_ring  : 에너지 게이지/비콘 — 동심원 벡터 파동이 부드럽게 퍼져 나감
- spin_emblem : 데브얼라이브/문양 — 회전하는 기하학적 엠블럼 심볼

루프의 비밀: 모든 움직임을 phase = t/프레임수 의 주기함수(sin·cos·mod) 로만
쓴다. phase 1.0 의 그림은 수학적으로 phase 0.0 과 같으므로 첫 프레임과 끝
프레임이 자연스럽게 이어지고, 이 성질은 시험(test_vector.py)이 코드로 검증한다.
전부 결정론적이다 — 같은 인자면 언제나 같은 프레임이 나온다.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from PIL import Image, ImageDraw

# 프리셋별 기본 프레임 수. 6프레임(3x2 시트) 또는 8/12프레임(부드러운 회전용).
PRESET_FRAMES = {
    "lantern": 12,
    "crosshair": 12,
    "pulse_ring": 8,
    "spin_emblem": 6,
}
PRESETS = tuple(PRESET_FRAMES)


@dataclass
class VectorSpec:
    """벡터 모션의 규격. palette 의 색은 (R, G, B, A).

    supersample 배 크기로 그린 뒤 size 로 줄이는(Lanczos) 것이 칼선의 원리다.
    예: size=256, supersample=4 → 1024px 로 그려 256px 로 축소.
    """

    size: int = 256  # 최종 프레임 한 칸 크기(px)
    supersample: int = 4  # 래스터화 배율(안티에일리어싱). 1 이면 계단 현상이 돌아온다
    background: tuple[int, ...] | None = None  # None 이면 투명
    palette: dict[str, tuple[int, ...]] = field(
        default_factory=lambda: {
            "outline": (30, 26, 38, 255),  # 밤지기 먹색 선
            "body": (58, 64, 96, 255),
            "accent": (255, 200, 80, 255),  # 등불·엠블럼 주황금
            "flame": (255, 236, 160, 255),  # 불꽃 심지 밝은 노랑
            "glow": (255, 214, 120, 255),  # 빛 번짐
            "cyan": (80, 240, 255, 255),  # SF 조준선
            "steel": (160, 220, 255, 255),
            "signal": (255, 96, 72, 255),  # 조준선 중심 신호색
            "deep": (36, 52, 120, 255),  # 엠블럼 남색
        }
    )

    def __post_init__(self) -> None:
        if self.size < 8:
            raise ValueError(f"size 는 8 이상이어야 합니다: {self.size}")
        if self.supersample < 1:
            raise ValueError(f"supersample 은 1 이상이어야 합니다: {self.supersample}")

    @property
    def canvas(self) -> int:
        """실제로 그릴 고해상도 캔버스 한 변(px)."""
        return self.size * self.supersample


# ---------------------------------------------------------------- 좌표 도구
def _sx(spec: VectorSpec, value: float) -> float:
    """0~1 정규화 좌표를 고해상도 캔버스 좌표로 옮긴다."""
    return value * spec.canvas


def _sw(value: float, spec: VectorSpec) -> float:
    """선 굵기도 좌표와 같은 배율로 키운다."""
    return max(1.0, value * spec.supersample)


def _rotate(x: float, y: float, cx: float, cy: float, angle: float) -> tuple[float, float]:
    """(x, y) 를 (cx, cy) 기준 angle 라디안만큼 회전한다."""
    dx, dy = x - cx, y - cy
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    return (cx + dx * cos_a - dy * sin_a, cy + dx * sin_a + dy * cos_a)


def _bezier(points: list[tuple[float, float]], samples: int = 48) -> list[tuple[float, float]]:
    """베지어 곡선을 직선 조각으로 샘플링한다.

    점 4개면 3차(cubic), 3개면 2차(quadratic). SVG path 의 C/Q 와 같은 식이다.
    """
    if len(points) == 4:
        p0, p1, p2, p3 = points

        def at(t: float) -> tuple[float, float]:
            u = 1 - t
            return (
                u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0],
                u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1],
            )

    elif len(points) == 3:
        p0, p1, p2 = points

        def at(t: float) -> tuple[float, float]:
            u = 1 - t
            return (
                u**2 * p0[0] + 2 * u * t * p1[0] + t**2 * p2[0],
                u**2 * p0[1] + 2 * u * t * p1[1] + t**2 * p2[1],
            )

    else:
        raise ValueError(f"베지어 점은 3개(2차) 또는 4개(3차)여야 합니다: {len(points)}")
    return [at(i / (samples - 1)) for i in range(samples)]


class _Frame:
    """투명 레이어를 얹어 가며 그리는 프레임 캔버스.

    Pillow 의 ImageDraw 는 반투명 색을 덮어쓰기 때문에(합성이 아니라), 반투명
    요소는 레이어에 그려 alpha_composite 로 붙인다. 이렇게 해야 빛 번짐이
    진짜 «번짐» 으로 보인다.
    """

    def __init__(self, spec: VectorSpec) -> None:
        self.spec = spec
        self.base = Image.new("RGBA", (spec.canvas, spec.canvas),
                              spec.background or (0, 0, 0, 0))

    def layer(self) -> Image.Image:
        return Image.new("RGBA", (self.spec.canvas, self.spec.canvas), (0, 0, 0, 0))

    def paste(self, layer: Image.Image) -> None:
        self.base.alpha_composite(layer)

    def draw(self) -> ImageDraw.ImageDraw:
        return ImageDraw.Draw(self.base)

    def finish(self) -> Image.Image:
        out = self.base.resize((self.spec.size, self.spec.size), Image.LANCZOS)
        if self.spec.background is None:
            return out
        return out.convert("RGB")

    # 편의 그리기: 정규화 좌표 → 캔버스 좌표 변환을 안으로 삼킨다
    def circle(self, cx: float, cy: float, r: float, color: tuple[int, ...],
               width: float = 0.0) -> None:
        """원. width=0 이면 채운 원, 아니면 그 굵기의 테두리 선."""
        draw = self.draw()
        box = (_sx(self.spec, cx - r), _sx(self.spec, cy - r),
               _sx(self.spec, cx + r), _sx(self.spec, cy + r))
        if width <= 0:
            draw.ellipse(box, fill=color)
        else:
            draw.ellipse(box, outline=color, width=round(_sw(width, self.spec)))

    def poly(self, points: list[tuple[float, float]], color: tuple[int, ...],
             width: float = 1.5, close: bool = False) -> None:
        pts = [(_sx(self.spec, x), _sx(self.spec, y)) for x, y in points]
        if close and len(pts) > 2:
            pts.append(pts[0])
        self.draw().line(pts, fill=color, width=round(_sw(width, self.spec)), joint="curve")

    def soft_dot(self, cx: float, cy: float, r: float, color: tuple[int, ...],
                 alpha: int) -> None:
        """반투명 원 한 개를 레이어로 얹는다(빛 번짐의 재료)."""
        layer = self.layer()
        draw = ImageDraw.Draw(layer)
        box = (_sx(self.spec, cx - r), _sx(self.spec, cy - r),
               _sx(self.spec, cx + r), _sx(self.spec, cy + r))
        draw.ellipse(box, fill=color[:3] + (alpha,))
        self.paste(layer)


# ---------------------------------------------------------------- 프리셋 1: 밤지기 흑등 랜턴
def _lantern(spec: VectorSpec, phase: float) -> Image.Image:
    """바람에 흔들리는 랜턴. 흔들림·일렁임·빛 번짐이 전부 phase 의 주기함수다."""
    f = _Frame(spec)
    p = spec.palette
    cx, hang = 0.5, 0.16  # 그네 걸이(꼭지) 위치 — 랜턴은 여기서 매달려 흔들린다
    angle = 0.10 * math.sin(2 * math.pi * phase) + 0.04 * math.sin(4 * math.pi * phase + math.pi / 2)

    # 빛 번짐 오라: 밝아졌다 어두워지기를 숨쉬듯(호흡 곡선)
    breath = 0.5 + 0.5 * math.sin(2 * math.pi * phase)  # 0→1→0
    for i, (r, a) in enumerate([(0.30, 26), (0.22, 40), (0.15, 60), (0.10, 90)]):
        f.soft_dot(cx, 0.52, r * (1 + 0.10 * breath), p["glow"], int(a * (0.7 + 0.3 * breath)))

    # 랜턴 몸통: 매달린 점을 기준으로 회전하는 곡선 폴리곤(베지어 옆선)
    def rt(x: float, y: float) -> tuple[float, float]:
        return _rotate(x, y, cx, hang, angle)

    body: list[tuple[float, float]] = []
    body += _bezier([rt(0.40, 0.40), rt(0.38, 0.32), rt(0.46, 0.28), rt(0.50, 0.28)], 24)   # 왼쪽 어깨 곡선
    body += _bezier([rt(0.50, 0.28), rt(0.54, 0.28), rt(0.62, 0.32), rt(0.60, 0.40)], 24)[1:]  # 오른쪽 어깨
    body += _bezier([rt(0.60, 0.40), rt(0.64, 0.60), rt(0.58, 0.70), rt(0.50, 0.72)], 24)[1:]  # 오른쪽 배 곡선
    body += _bezier([rt(0.50, 0.72), rt(0.42, 0.70), rt(0.36, 0.60), rt(0.40, 0.40)], 24)[1:]  # 왼쪽 배
    fill_layer = f.layer()
    ImageDraw.Draw(fill_layer).polygon(
        [(_sx(spec, x), _sx(spec, y)) for x, y in body], fill=p["accent"][:3] + (235,)
    )
    f.paste(fill_layer)
    f.poly(body + [body[0]], p["outline"], width=2.2)

    # 꼭지와 받침
    f.poly([rt(cx, hang), rt(cx, 0.26)], p["outline"], width=2.0)
    f.poly([rt(0.42, 0.74), rt(0.58, 0.74)], p["outline"], width=2.4)
    # 창살(흑등 격자)
    for fx in (0.45, 0.50, 0.55):
        f.poly([rt(fx, 0.34), rt(fx, 0.68)], p["outline"][:3] + (140,), width=1.2)

    # 불꽃: 베지어 패스로 일렁이는 물결 — 제어점이 물결치며 팁이 흔들린다
    flame_base = rt(0.50, 0.66)
    flick = math.sin(2 * math.pi * phase)
    flick2 = math.sin(2 * math.pi * phase + math.pi / 3)  # 같은 주기, 다른 위상 — 반 주기 대칭을 깬다
    tip = rt(0.50 + 0.035 * flick, 0.40 + 0.02 * flick2)
    c1 = rt(0.455 + 0.02 * flick2, 0.56)
    c2 = rt(0.545 + 0.02 * flick, 0.56)
    flame = _bezier([flame_base, c1, c2, tip], 32)
    f.poly(flame, p["flame"], width=3.0)
    f.poly(_bezier([flame_base, rt(0.475, 0.58), rt(0.515, 0.58), rt(0.50, 0.50 + 0.02 * flick)], 24),
           p["accent"], width=1.6)
    f.soft_dot(*flame_base, r=0.035, color=p["flame"], alpha=230)  # 불꽃 심지 빛
    return f.finish()


# ---------------------------------------------------------------- 프리셋 2: SF 조준선
def _crosshair(spec: VectorSpec, phase: float) -> Image.Image:
    """360도 회전 눈금선 + 맥동 링. 회전각이 2π*phase 라 루프가 끊기지 않는다."""
    f = _Frame(spec)
    p = spec.palette
    cx, cy, ring_r = 0.5, 0.5, 0.36
    spin = 2 * math.pi * phase

    # 외곽 눈금 24개 — 큰 눈금(매 90도)은 길고 굵게
    for k in range(24):
        a = spin + 2 * math.pi * k / 24
        major = k % 6 == 0
        r_in = ring_r - (0.09 if major else 0.04)
        r_out = ring_r
        f.poly([(cx + r_in * math.cos(a), cy + r_in * math.sin(a)),
                (cx + r_out * math.cos(a), cy + r_out * math.sin(a))],
               p["cyan"] if major else p["steel"],
               width=2.6 if major else 1.2)

    # 고정 코너 브래킷(카메라 프레임 느낌) — 회전과 대비되는 고정자
    for sx in (-1, 1):
        for sy in (-1, 1):
            ox, oy = cx + sx * 0.40, cy + sy * 0.40
            f.poly([(ox - sx * 0.07, oy), (ox, oy), (ox, oy - sy * 0.07)], p["steel"], width=2.0)

    # 중심 맥동 링: 크기와 알파가 같은 위상으로 숨쉰다
    pulse = 0.5 + 0.5 * math.sin(2 * math.pi * phase)
    f.circle(cx, cy, 0.10 + 0.045 * pulse, p["cyan"][:3] + (int(120 + 100 * pulse),), width=2.2)
    f.circle(cx, cy, 0.035, p["signal"])
    f.soft_dot(cx, cy, 0.09 + 0.03 * pulse, p["cyan"], int(60 + 60 * pulse))
    return f.finish()


# ---------------------------------------------------------------- 프리셋 3: 에너지 파동
def _pulse_ring(spec: VectorSpec, phase: float) -> Image.Image:
    """동심원 파동이 계속 퍼져 나간다. (phase + k/K) % 1 이라 k 개 파동이 촘촘히 이어진다."""
    f = _Frame(spec)
    p = spec.palette
    cx, cy, rings, max_r = 0.5, 0.5, 3, 0.44
    for k in range(rings):
        travel = (phase + k / rings) % 1.0
        r = 0.06 + (max_r - 0.06) * travel
        fade = 1 - travel  # 퍼질수록 옅어진다
        f.circle(cx, cy, r, p["cyan"][:3] + (int(30 + 200 * fade),), width=1.5 + 3.5 * fade)
    beat = 0.5 + 0.5 * math.sin(2 * math.pi * phase)
    f.circle(cx, cy, 0.05 + 0.015 * beat, p["cyan"])
    f.soft_dot(cx, cy, 0.12 + 0.03 * beat, p["cyan"], int(70 + 60 * beat))
    return f.finish()


# ---------------------------------------------------------------- 프리셋 4: 회전 엠블럼
def _spin_emblem(spec: VectorSpec, phase: float) -> Image.Image:
    """데브얼라이브 문양 — 남색 육각형 안에서 금색 삼각형이 반대로 도는 기하학 심볼."""
    f = _Frame(spec)
    p = spec.palette
    cx, cy = 0.5, 0.5
    outer = 2 * math.pi * phase          # 바깥 육각형: 시계 방향
    inner = -2 * math.pi * phase * 1.5   # 안쪽 삼각형: 반대로 더 빠르게(정수 배 회전이라 루프가 맞다)

    hexagon = [(cx + r * math.cos(outer + 2 * math.pi * k / 6),
                cy + r * math.sin(outer + 2 * math.pi * k / 6))
               for k, r in [(k, 0.40) for k in range(6)]]
    f.poly(hexagon + [hexagon[0]], p["deep"], width=3.0)
    for x, y in hexagon:  # 꼭짓점 점
        f.circle(x, y, 0.018, p["deep"])

    tri = [(cx + r * math.cos(inner + 2 * math.pi * k / 3 - math.pi / 2),
            cy + r * math.sin(inner + 2 * math.pi * k / 3 - math.pi / 2))
           for k, r in [(k, 0.22) for k in range(3)]]
    fill = f.layer()
    ImageDraw.Draw(fill).polygon([(_sx(spec, x), _sx(spec, y)) for x, y in tri],
                                 fill=p["accent"][:3] + (220,))
    f.paste(fill)
    f.poly(tri + [tri[0]], p["outline"], width=2.0)

    beat = 0.5 + 0.5 * math.sin(2 * math.pi * phase)
    f.circle(cx, cy, 0.05 + 0.012 * beat, p["flame"])
    f.soft_dot(cx, cy, 0.11 + 0.02 * beat, p["accent"], int(80 + 60 * beat))
    return f.finish()


_VECTOR_FN = {
    "lantern": _lantern,
    "crosshair": _crosshair,
    "pulse_ring": _pulse_ring,
    "spin_emblem": _spin_emblem,
}


def render_vector_frame(preset: str, phase: float, spec: VectorSpec | None = None) -> Image.Image:
    """phase(0~1, 1.0 은 0.0 과 같은 그림) 한 장을 벡터 그래픽으로 렌더링한다."""
    if preset not in _VECTOR_FN:
        raise ValueError(f"지원하지 않는 벡터 프리셋입니다: {preset} (가능: {', '.join(PRESETS)})")
    return _VECTOR_FN[preset](spec or VectorSpec(), phase % 1.0)


def generate_vector_frames(
    preset: str,
    frames: int | None = None,
    spec: VectorSpec | None = None,
) -> list[Image.Image]:
    """벡터 모션 프레임 묶음을 만든다. 첫 프레임과 끝 프레임이 자연스럽게 이어진다."""
    if preset not in _VECTOR_FN:
        raise ValueError(f"지원하지 않는 벡터 프리셋입니다: {preset} (가능: {', '.join(PRESETS)})")
    if frames is None:
        frames = PRESET_FRAMES[preset]
    if frames < 2:
        raise ValueError(f"프레임 수는 2 이상이어야 합니다: {frames}")
    return [render_vector_frame(preset, t / frames, spec) for t in range(frames)]
