# Handcrafted by Pickle 🥒 for DevAlive Claude Code Pipeline
"""스프라이트 시트 슬라이싱과 무한 루프 GIF 조립.

설계 원칙(가이드 문서 5절 「10대 안전·운영 수칙」 대응):
- 생성(AI·절차 코드)과 조립(이 모듈)은 분리한다. 이 모듈은 그림을 판단하지 않고 자른다.
- 시트의 읽는 순서는 왼쪽→오른쪽, 위→아래다(시트를 뽑는 프롬프트의 순서와 같다).
- GIF 는 항상 loop=0(무한 루프)으로 저장하고, 프레임 수는 저장 뒤 코드로 확인한다.
- 투명 시트는 disposal=2(배경 복원)로 저장해 잔상을 막는다.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

DEFAULT_COLS = 3
DEFAULT_ROWS = 2
DEFAULT_TRIM = 2  # 프레임 경계 오차 보정(px): 격자 경계에 흘러든 색 1~2px 을 잘라 낸다
MIN_DURATION_MS = 20  # GIF 규격상 프레임 표시 최소(ms)
DEFAULT_COLORS = 128  # 팔레트 색 수(용량 다이어트 담당)


def slice_sheet(
    sheet: Image.Image,
    cols: int = DEFAULT_COLS,
    rows: int = DEFAULT_ROWS,
    trim: int = DEFAULT_TRIM,
) -> list[Image.Image]:
    """시트를 격자로 자른다. 순서는 왼쪽→오른쪽, 위→아래."""
    if cols < 1 or rows < 1:
        raise ValueError(f"격자는 1x1 이상이어야 합니다: {cols}x{rows}")
    if sheet.width % cols or sheet.height % rows:
        raise ValueError(
            f"시트 크기가 격자로 나눠 떨어지지 않습니다: {sheet.width}x{sheet.height} / {cols}x{rows}"
        )
    w, h = sheet.width // cols, sheet.height // rows
    trim = max(0, int(trim))
    if w - 2 * trim < 1 or h - 2 * trim < 1:
        raise ValueError(f"trim 이 프레임보다 큽니다: trim={trim}, 프레임={w}x{h}")
    frames = []
    for row in range(rows):
        for col in range(cols):
            left, top = col * w, row * h
            frames.append(sheet.crop((left + trim, top + trim, left + w - trim, top + h - trim)))
    return frames


def compute_duration_ms(fps: float | None, duration_ms: int | None, speed: float = 1.0) -> int:
    """--fps 또는 --duration 으로 기본 표시 시간을 정하고 --speed 로 나눠 속도를 조절한다.

    speed=0.5 이면 두 배 길게(느리게), speed=2.0 이면 절반(빠르게). 최소 MIN_DURATION_MS 로 눌러 준다.
    """
    if speed <= 0:
        raise ValueError(f"speed 는 0보다 커야 합니다: {speed}")
    if fps is not None and duration_ms is not None:
        raise ValueError("--fps 와 --duration 중 하나만 지정합니다")
    if fps is not None:
        if fps <= 0:
            raise ValueError(f"fps 는 0보다 커야 합니다: {fps}")
        base = 1000.0 / fps
    elif duration_ms is not None:
        if duration_ms <= 0:
            raise ValueError(f"duration 은 0보다 커야 합니다: {duration_ms}")
        base = float(duration_ms)
    else:
        base = 1000.0 / 3  # 기본: 초당 3프레임(도트 감각에 맞는 기본값)
    return max(MIN_DURATION_MS, int(round(base / speed)))


TRANSPARENT_INDEX = 255  # 모든 투명 프레임이 함께 쓰는 투명색 번호(팔레트 맨 끝 칸)


def _quantize_rgba(frame: Image.Image, colors: int) -> Image.Image:
    """알파가 있는 프레임을 양자화하고 투명 픽셀을 고정 번호 TRANSPARENT_INDEX 로 모은다.

    프레임마다 따로 양자화하면 투명색이 팔레트의 몇 번에 놓일지가 프레임마다 달라진다.
    GIF 저장기는 투명색 번호를 프레임끼리 묶어 쓰므로, 번호가 어긋나면 그 프레임의 투명
    자리가 검은 사각형으로 나와 배경이 깜빡인다. 그래서 그림 색은 0~254 번에만 두고,
    투명 자리는 늘 255 번 한 곳으로 모은다.
    """
    colors = max(2, min(int(colors), TRANSPARENT_INDEX))
    q = frame.quantize(colors=colors, method=Image.FASTOCTREE)
    # 알파째 양자화한 팔레트에서 완전 투명 칸(알파 0)만 투명으로 옮긴다.
    # 반투명 빛 번짐 칸은 예전처럼 색으로 남겨 그림 모양을 바꾸지 않는다.
    rgba = q.getpalette("RGBA")
    clear = {i for i in range(len(rgba) // 4) if rgba[i * 4 + 3] == 0}
    mask = q.point([255 if i in clear else 0 for i in range(256)], "L")
    palette = q.getpalette("RGB")[: TRANSPARENT_INDEX * 3]
    palette += [0] * (TRANSPARENT_INDEX * 3 - len(palette))
    q.putpalette(palette + [0, 0, 0])  # 255 번 = 투명 전용 칸
    q.paste(TRANSPARENT_INDEX, mask=mask)
    q.info["transparency"] = TRANSPARENT_INDEX
    return q


def to_palette(frames: list[Image.Image], colors: int = DEFAULT_COLORS) -> list[Image.Image]:
    """GIF 는 256색 팔레트라서 양자화가 필요하다. 알파(투명)는 고정 투명색 번호로 보존한다."""
    palettized = []
    for f in frames:
        if f.mode == "P":
            palettized.append(f)
        elif "A" in f.getbands():
            palettized.append(_quantize_rgba(f, colors))
        else:
            palettized.append(
                f.convert("RGB").quantize(
                    colors=colors, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG
                )
            )
    return palettized


def frames_to_gif(
    frames: list[Image.Image],
    output_path: Path | str,
    duration_ms: int = 333,
    colors: int = DEFAULT_COLORS,
) -> dict:
    """프레임 묶음을 무한 루프 GIF 로 저장하고 보고용 정보를 돌려준다."""
    if not frames:
        raise ValueError("프레임이 없습니다")
    ms = max(MIN_DURATION_MS, int(duration_ms))
    palettized = to_palette(frames, colors)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    has_alpha = "A" in frames[0].getbands()
    disposal = 2 if has_alpha else 1  # 투명이면 배경 복원, 아니면 겹치기
    extra: dict = {}
    transparency = palettized[0].info.get("transparency")
    if transparency is not None:
        extra["transparency"] = transparency
    palettized[0].save(
        output_path,
        save_all=True,
        append_images=palettized[1:],
        duration=ms,
        loop=0,  # 0 = 무한 루프
        disposal=disposal,
        optimize=True,
        **extra,
    )
    return {
        "frames": len(frames),
        "frame_size": frames[0].size,
        "duration_ms": ms,
        "output": str(output_path),
        "bytes": output_path.stat().st_size,
    }


def frames_to_sheet(
    frames: list[Image.Image],
    cols: int = DEFAULT_COLS,
    rows: int = DEFAULT_ROWS,
    background: tuple[int, ...] | None = None,
) -> Image.Image:
    """프레임 묶음을 다시 시트 한 장으로 엮는다(슬라이싱의 역. 원본 보존·검수용)."""
    if len(frames) != cols * rows:
        raise ValueError(f"프레임 수가 격자와 다릅니다: {len(frames)} / {cols}x{rows}")
    w, h = frames[0].size
    if any(f.size != (w, h) for f in frames):
        raise ValueError("프레임 크기가 서로 다릅니다")
    if background is not None:
        sheet = Image.new("RGB", (w * cols, h * rows), background)
    else:
        sheet = Image.new("RGBA", (w * cols, h * rows), (0, 0, 0, 0))
    for index, frame in enumerate(frames):
        sheet.paste(frame, ((index % cols) * w, (index // cols) * h))
    return sheet


def convert(
    input_path: Path | str,
    output_path: Path | str,
    fps: float | None = None,
    duration_ms: int | None = None,
    speed: float = 1.0,
    cols: int = DEFAULT_COLS,
    rows: int = DEFAULT_ROWS,
    trim: int = DEFAULT_TRIM,
    colors: int = DEFAULT_COLORS,
) -> dict:
    """스프라이트 시트 파일 하나를 무한 루프 GIF 로 변환한다."""
    sheet = Image.open(input_path)
    frames = slice_sheet(sheet, cols=cols, rows=rows, trim=trim)
    ms = compute_duration_ms(fps, duration_ms, speed)
    return frames_to_gif(frames, output_path, duration_ms=ms, colors=colors)
