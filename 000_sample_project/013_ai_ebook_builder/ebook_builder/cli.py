"""CLI — 텍스트 파일들을 한 줄로 전자책(HTML·EPUB·인쇄용·웹북 ZIP)으로 빌드한다.

예)
    python -m ebook_builder.cli build data/*.txt --title "밤지기 옛이야기 대본집" \\
        --author "데브얼라이브" --preset novel --outdir output

- 원본 파일은 읽기만 하고 절대 고치지 않는다.
- 산출물은 --outdir 아래에 4종(단독 HTML 뷰어, EPUB, 인쇄용 HTML, 웹북 ZIP)이 모두 생긴다.
- 외부 패키지·API 키 없이 돈다. 본문 다시 쓰기(요약)는 클로드 코드가 하는 일이다.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .builder import BookMeta, build_epub, build_html, build_print_html, build_webbook_zip
from .cover_generator import CoverSpec, generate_cover_svg
from .toc_generator import Chapter, detect_title, split_into_chapters  # noqa: F401 (재수출)


def load_chapters(paths: list[Path], max_chars: int = 4000) -> tuple[list[Chapter], str]:
    """파일들을 읽어 챕터 목록으로 나눈다. 반환값은 (챕터들, 결합된 원문).

    파일 이름은 챕터 제목이 되지 않는다. 내용의 제목 줄이 챕터를 정한다.
    """
    if not paths:
        raise SystemExit("입력 파일이 없다. 텍스트 파일 경로를 하나 이상 주라.")
    joined_parts: list[str] = []
    chapters: list[Chapter] = []
    for path in paths:
        text = Path(path).read_text(encoding="utf-8")
        joined_parts.append(text)
        found = split_into_chapters(text, source=str(path))
        if not found:
            # 빈 파일은 조용히 건너뛴다.
            continue
        first, rest = found[0], found[1:]
        if chapters and chapters[-1].title == first.title:
            # 파일이 바뀌어도 주제가 이어지면 한 챕터로 합친다.
            chapters[-1].body = f"{chapters[-1].body}\n\n{first.body}".strip()
            chapters.extend(rest)
        else:
            chapters.extend(found)
    if not chapters:
        raise SystemExit("읽은 내용이 비어 있다.")
    joined = "\n\n".join(joined_parts)
    # 청크는 결합 본문 기준으로 다시 잡는다(챕터별 재생성 단위).
    for ch in chapters:
        ch.with_chunks(max_chars=max_chars)
    return chapters, joined


def build_all(args: argparse.Namespace) -> list[Path]:
    paths = [Path(p) for p in args.inputs]
    chapters, joined = load_chapters(paths, max_chars=args.chunk_chars)

    title = args.title or detect_title(joined, fallback=Path(paths[0]).stem)
    meta = BookMeta(
        title=title,
        subtitle=args.subtitle or "",
        author=args.author or "",
        preset=args.preset,
    )

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    cover_svg = generate_cover_svg(
        CoverSpec(
            title=meta.title,
            subtitle=meta.subtitle,
            author=meta.author,
            preset=meta.preset,
        )
    )

    outputs: dict[str, object] = {
        "viewer.html": build_html(meta, chapters, cover=cover_svg),
        "print.html": build_print_html(meta, chapters),
        "book.epub": build_epub(meta, chapters, cover=cover_svg),
        "webbook.zip": build_webbook_zip(meta, chapters),
        "cover.svg": cover_svg,
    }
    written: list[Path] = []
    for name, payload in outputs.items():
        target = outdir / name
        if isinstance(payload, bytes):
            target.write_bytes(payload)
        else:
            target.write_text(str(payload), encoding="utf-8")
        written.append(target)

    # 목차 보고서: 클로드 코드가 검토하기 좋게 남긴다.
    toc_lines = [f"# 목차 — {meta.title}", ""]
    for index, ch in enumerate(chapters):
        toc_lines.append(f"{index + 1}. {ch.title} ({len(ch.chunks)}청크, {len(ch.body)}자)")
    (outdir / "toc.md").write_text("\n".join(toc_lines) + "\n", encoding="utf-8")
    written.append(outdir / "toc.md")
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ebook_builder",
        description="원본 텍스트를 전자책 4종(HTML 뷰어·EPUB·인쇄용 HTML·웹북 ZIP)으로 묶는다.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="파일들을 읽어 전자책 4종을 만든다")
    build.add_argument("inputs", nargs="+", help="원본 텍스트/마크다운 파일들")
    build.add_argument("--title", default="", help="책 제목(비우면 원문 H1 에서 찾는다)")
    build.add_argument("--subtitle", default="")
    build.add_argument("--author", default="")
    build.add_argument("--preset", default="novel", help="스타일 프리셋 키(기본 novel)")
    build.add_argument("--outdir", default="output", help="산출물 폴더(기본 output)")
    build.add_argument("--chunk-chars", type=int, default=4000, help="AI 재생성 청크 크기(자)")

    presets = sub.add_parser("presets", help="스타일 프리셋 목록을 본다")
    presets.add_argument("--json", action="store_true", help="JSON 으로 출력")

    args = parser.parse_args(argv)
    if args.command == "presets":
        from .builder import STYLE_PRESETS

        if args.json:
            import json

            print(json.dumps(STYLE_PRESETS, ensure_ascii=False, indent=2))
        else:
            for name, theme in STYLE_PRESETS.items():
                print(f"{name:10s} 글꼴={theme['font']:10s} 배경={theme['bg']}")
        return 0

    written = build_all(args)
    for path in written:
        print(f"만듦 {path}")
    print("\n전자책 산출물 완료.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
