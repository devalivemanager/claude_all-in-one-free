"""한 줄 CLI: `python -m sprite_to_gif.cli {generate|convert|batch}`.

- generate : 절차적 도트 프레임을 직접 생성해 GIF(옵션으로 시트 PNG 까지)로 저장 — 외부 연결 0
- convert  : 스프라이트 시트 한 장을 무한 루프 GIF 로
- batch    : 폴더의 시트 전부를 일괄 변환(실패는 모아 보고하고 계속 진행한다)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

from . import converter, generator, sources


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
    sub = parser.add_subparsers(dest="command", required=True)

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
    if getattr(args, "grid", None):
        args.cols, args.rows = (int(x) for x in args.grid.lower().split("x"))
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
