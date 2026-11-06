"""명령행 진입점 — 한 줄 배치 러너.

사용 예:
    python -m youtube_to_ebook https://youtu.be/VIDEO_ID
    python -m youtube_to_ebook https://youtu.be/VIDEO_ID -o output --format html,epub
    python -m youtube_to_ebook https://youtu.be/VIDEO_ID --format html --interval 15
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="youtube_to_ebook",
        description="유튜브 영상 URL 하나로 자막 대본 + 핵심 장면 스틸컷이 힌 삽화 전자책(HTML/EPUB)을 만듭니다.",
    )
    parser.add_argument("url", help="유튜브 영상 URL")
    parser.add_argument("-o", "--out", type=Path, default=Path("output"), help="결과 폴더 (기본: output)")
    parser.add_argument("--format", default="html,epub", help="출력 형식, 쉼표 구분: html,epub (기본: html,epub)")
    parser.add_argument("--lang", default="ko,en", help="자막 언어 우선순위, 쉼표 구분 (기본: ko,en)")
    parser.add_argument("--subtitle-interval", type=float, default=60.0,
                        help="챕터 묶음 간격(초) (기본: 60, 유튜브 공식 챕터가 있으면 그걸 따른다)")
    parser.add_argument("--interval", type=float, default=10.0, help="스틸컷 캡처 간격(초) (기본: 10)")
    parser.add_argument("--max-height", type=int, default=720, help="내려받을 영상 최대 세로 해상도 (기본: 720)")
    parser.add_argument("--max-width", type=int, default=1280, help="스틸컷 최대 가로 해상도 (기본: 1280)")
    parser.add_argument("--title", default="", help="책 제목 (기본: 영상 제목)")
    parser.add_argument("--author", default="", help="저자 (기본: 채널 이름)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    formats = tuple(f.strip() for f in args.format.split(",") if f.strip())
    result = pipeline.build_book(
        url=args.url,
        out_dir=args.out,
        formats=formats,
        languages=[lang.strip() for lang in args.lang.split(",") if lang.strip()],
        subtitle_interval=args.subtitle_interval,
        capture_interval=args.interval,
        max_width=args.max_width,
        title=args.title,
        author=args.author,
    )
    for warning in result.warnings:
        print(f"[경고] {warning}", file=sys.stderr)
    for name, path in result.outputs.items():
        print(f"[완료] {name}: {path}")
    if not result.outputs:
        print("전자책을 만들지 못했습니다.", file=sys.stderr)
        return 1
    print(
        f"챕터 {result.chapters}개 · 자막 문장 {result.cues}개 · 스틸컷 {result.frames}장",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
