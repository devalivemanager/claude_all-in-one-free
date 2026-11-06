# Handcrafted by Pickle 🥒 for DevAlive Claude Code Pipeline
"""한 줄 CLI: `python -m sprite_to_gif.cli {generate|convert|batch}` + 벡터 모드.

- generate : 절차적 도트 프레임을 직접 생성해 GIF(옵션으로 시트 PNG 까지)로 저장 — 외부 연결 0
- convert  : 스프라이트 시트 한 장을 무한 루프 GIF 로
- batch    : 폴더의 시트 전부를 일괄 변환(실패는 모아 보고하고 계속 진행한다)
- --mode vector : 서브커맨드 없이 바로 벡터 모션. 예)
  `python -m sprite_to_gif.cli --mode vector --preset lantern --size 256 --output lantern_loop.gif`
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

from . import converter, generator, sources, vector_generator


def _duration_args(args: argparse.Namespace) -> dict:
    return {"fps": args.fps, "duration_ms": args.duration, "speed": args.speed}


def _report(label: str, info: dict) -> None:
    w, h = info["frame_size"]
    print(f"{label}: {info['frames']}프레임 {w}x{h} 프레임당 {info['duration_ms']}ms "
          f"→ {info['output']} ({info['bytes']:,} bytes)")


def cmd_generate(args: argparse.Namespace) -> int:
    bg = tuple(int(x) for x in args.background.split(",")) if args.background else None
    spec = generator.PixelSpec(size=args.size, dot=args.dot, background=bg,
                               palette=generator.PixelSpec().palette)
    frames = sources.frames_from_procedural(args.motion, args.frames, spec)
    if args.save_sheet:
        sheet = converter.frames_to_sheet(frames, cols=args.cols, rows=args.rows)
        sheet.save(args.save_sheet)
        print(f"시트 저장: {args.save_sheet} ({sheet.width}x{sheet.height})")
    info = converter.frames_to_gif(frames, args.output, duration_ms=args.duration or 333,
                                   colors=args.colors)
    _report("완료", info)
    return 0


def cmd_vector(args: argparse.Namespace) -> int:
    """벡터 모션 엔진 한 돌기: 프리셋 하나로 칼선 무한 루프 GIF 를 뽑아 준다."""
    preset = args.preset or vector_generator.PRESETS[0]
    spec = vector_generator.VectorSpec(size=args.size)
    frames = vector_generator.generate_vector_frames(preset, frames=args.frames, spec=spec)
    # 벡터 모션은 움직임이 부드러운 게 얼굴이라 기본 표시 시간을 도트(333ms)보다 짧게 100ms 로 잡는다
    ms = converter.compute_duration_ms(
        args.fps, args.duration if (args.fps or args.duration) else 100, speed=args.speed
    )
    info = converter.frames_to_gif(frames, args.output, duration_ms=ms, colors=args.colors)
    _report(f"벡터 완료({preset})", info)
    return 0


def cmd_convert(args: argparse.Namespace) -> int:
    info = converter.convert(args.input, args.output, cols=args.cols, rows=args.rows,
                             trim=args.trim, colors=args.colors, **_duration_args(args))
    _report("완료", info)
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    input_dir, output_dir = Path(args.input_dir), Path(args.output_dir)
    patterns = ("*.png", "*.jpg", "*.jpeg", "*.webp")
    paths = sorted({p for pattern in patterns for p in input_dir.glob(pattern)})
    if not paths:
        print(f"시트가 없습니다: {input_dir}", file=sys.stderr)
        return 1
    ok, failed = [], []
    for path in paths:
        out = output_dir / (path.stem + ".gif")
        try:
            info = converter.convert(path, out, cols=args.cols, rows=args.rows,
                                     trim=args.trim, colors=args.colors, **_duration_args(args))
            ok.append((path.name, info))
            _report(path.name, info)
        except Exception as exc:  # 폭주 하나가 전체를 멈추지 않게: 실패는 모아 보고한다
            failed.append((path.name, str(exc)))
            print(f"실패: {path.name}: {exc}", file=sys.stderr)
    print(f"\n총 {len(paths)} 중 성공 {len(ok)}, 실패 {len(failed)}")
    for name, reason in failed:
        print(f"  실패 사유 - {name}: {reason}")
    return 0 if not failed else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sprite_to_gif", description="스프라이트 시트 → 무한 루프 GIF")
    # 최상단 옵션: 서브커맨드 없이 `--mode vector` 만으로 도는 벡터 모드용
    parser.add_argument("--mode", default=None, choices=["vector"],
                        help="생성 방식. vector = SVG 벡터 모션 엔진(서브커맨드 없이 바로 돈다)")
    parser.add_argument("--preset", default=None, choices=vector_generator.PRESETS,
                        help="벡터 프리셋: lantern|crosshair|pulse_ring|spin_emblem")
    parser.add_argument("--frames", type=int, default=None, help="프레임 수(벡터 기본: 프리셋마다 6/8/12)")
    parser.add_argument("--size", type=int, default=None, help="프레임 크기 px(벡터 기본 256)")
    parser.add_argument("--output", default=None, help="저장 경로(벡터 기본 vector_loop.gif)")
    parser.add_argument("--fps", type=float, default=None, help="초당 프레임 수(예: 3)")
    parser.add_argument("--duration", type=int, default=None, help="프레임당 표시 시간 ms(예: 350)")
    parser.add_argument("--speed", type=float, default=1.0, help="재생 속도 배수 0.25~2.0")
    parser.add_argument("--colors", type=int, default=converter.DEFAULT_COLORS, help="팔레트 색 수")

    sub = parser.add_subparsers(dest="command", required=False)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--fps", type=float, default=None, help="초당 프레임 수(예: 3)")
        p.add_argument("--duration", type=int, default=None, help="프레임당 표시 시간 ms(예: 350)")
        p.add_argument("--speed", type=float, default=1.0, help="재생 속도 배수 0.25~2.0")
        p.add_argument("--colors", type=int, default=converter.DEFAULT_COLORS, help="팔레트 색 수")

    p_gen = sub.add_parser("generate", help="절차적 도트 프레임을 직접 만들어 GIF 로 (외부 연결 0)")
    p_gen.add_argument("--motion", default="walk", choices=generator.MOTIONS, help="모션 종류")
    p_gen.add_argument("--frames", type=int, default=generator.DEFAULT_FRAMES, help="프레임 수(기본 6)")
    p_gen.add_argument("--size", type=int, default=64, help="프레임 크기 px")
    p_gen.add_argument("--dot", type=int, default=16, help="도트 격자 해상도")
    p_gen.add_argument("--background", default=None, help="배경색 R,G,B (기본 투명)")
    p_gen.add_argument("--save-sheet", default=None, help="시트 PNG 도 함께 저장(검수·원본 보존용)")
    p_gen.add_argument("--cols", type=int, default=converter.DEFAULT_COLS)
    p_gen.add_argument("--rows", type=int, default=converter.DEFAULT_ROWS)
    p_gen.add_argument("--output", default="motion.gif")
    common(p_gen)
    p_gen.set_defaults(fn=cmd_generate)

    p_conv = sub.add_parser("convert", help="시트 한 장을 GIF 로")
    p_conv.add_argument("--input", required=True)
    p_conv.add_argument("--output", default="motion.gif")
    p_conv.add_argument("--grid", default="3x2", help="격자, 예) 3x2")
    p_conv.add_argument("--trim", type=int, default=converter.DEFAULT_TRIM, help="경계 보정 px")
    common(p_conv)
    p_conv.set_defaults(fn=cmd_convert)

    p_batch = sub.add_parser("batch", help="폴더의 시트 전부를 GIF 로")
    p_batch.add_argument("--input-dir", required=True)
    p_batch.add_argument("--output-dir", required=True)
    p_batch.add_argument("--grid", default="3x2")
    p_batch.add_argument("--trim", type=int, default=converter.DEFAULT_TRIM)
    common(p_batch)
    p_batch.set_defaults(fn=cmd_batch)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.speed < 0.25 or args.speed > 2.0:
        parser.error("--speed 는 0.25~2.0 사이로")
    if args.command is None:
        # 서브커맨드 없이 --mode vector(--preset …) 로만 온 경우: 벡터 모드로 받는다
        if args.mode == "vector" or args.preset:
            args.size = args.size if args.size is not None else 256
            args.output = args.output if args.output is not None else "vector_loop.gif"
            return cmd_vector(args)
        parser.error("명령을 하나 골라 주세요: generate|convert|batch (또는 --mode vector)")
    if getattr(args, "grid", None):
        args.cols, args.rows = (int(x) for x in args.grid.lower().split("x"))
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
