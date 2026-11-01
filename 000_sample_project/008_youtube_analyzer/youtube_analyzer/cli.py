"""명령행 진입점.

사용 예:
    python -m youtube_analyzer https://youtu.be/VIDEO_ID
    python -m youtube_analyzer --video lecture.mp4 --subtitle lecture.ko.vtt
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from . import downloader, frames, report, subtitles


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="youtube_analyzer",
        description="유튜브 영상(또는 로컬 영상)을 대본 + 장면 캡처 + Markdown 보고서로 변환합니다.",
    )
    parser.add_argument("url", nargs="?", help="유튜브 영상 URL")
    parser.add_argument("--video", type=Path, help="로컬 영상 파일(URL 대신 사용)")
    parser.add_argument("--subtitle", type=Path, help="로컬 자막 파일 .vtt/.srt (URL 대신 사용)")
    parser.add_argument("--title", default="", help="로컬 파일 분석 시 보고서 제목")
    parser.add_argument("-o", "--out", type=Path, default=Path("output"), help="결과 폴더 (기본: output)")
    parser.add_argument("--lang", default="ko,en", help="자막 언어 우선순위, 쉼표 구분 (기본: ko,en)")
    parser.add_argument("--interval", type=float, default=10.0, help="장면 캡처 간격(초) (기본: 10)")
    parser.add_argument("--section", type=float, default=60.0, help="보고서 구간 길이(초) (기본: 60)")
    parser.add_argument("--max-height", type=int, default=720, help="내려받을 영상 최대 세로 해상도 (기본: 720)")
    parser.add_argument("--no-frames", action="store_true", help="장면 캡처 생략(자막만)")
    parser.add_argument("--scenes", action="store_true",
                        help="컷 전환 감지 + 컷마다 장면 캡처 (쇼츠·광고 분석용)")
    parser.add_argument("--scene-threshold", type=float, default=0.3,
                        help="컷 전환 민감도 0~1, 낮을수록 민감 (기본: 0.3)")
    return parser


def run(args: argparse.Namespace) -> Path:
    """분석을 실행하고 보고서 경로를 돌려준다."""
    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    languages = [lang.strip() for lang in args.lang.split(",") if lang.strip()]

    if args.url:
        print(f"[1/3] 영상 정보·자막 내려받는 중: {args.url}")
        result = downloader.download(
            args.url, out_dir / "source", languages,
            with_video=not args.no_frames, max_height=args.max_height,
        )
        info, subtitle_path, video_path = result.info, result.subtitle, result.video
        for warning in result.warnings:
            print(f"      경고: {warning}")
    else:
        print("[1/3] 로컬 파일 사용")
        source = args.video or args.subtitle
        info = downloader.VideoInfo(video_id=source.stem, title=args.title or source.stem)
        subtitle_path, video_path = args.subtitle, args.video

    transcript = subtitles.load_transcript(subtitle_path) if subtitle_path else []
    print(f"      대본 {len(transcript)}개 구간" + ("" if subtitle_path else " (자막 없음)"))

    captured: list[frames.Frame] = []
    cuts: list[float] | None = None
    if video_path and not args.no_frames:
        print(f"[2/3] {args.interval:g}초 간격으로 장면 캡처 중")
        if not info.duration:
            info.duration = frames.probe_duration(video_path)
        captured = frames.extract_frames(video_path, out_dir / "frames", args.interval)
        print(f"      장면 {len(captured)}장")
        if args.scenes:
            cuts = frames.detect_scenes(video_path, args.scene_threshold)
            # 컷 직후 화면을 캡처한다(전환 효과 중간을 피하려고 0.1초 뒤)
            captured += frames.extract_frames_at(
                video_path, out_dir / "frames", [c + 0.1 for c in cuts], prefix="cut"
            )
            print(f"      컷 전환 {len(cuts)}회 감지, 컷 장면 {len(cuts)}장 캡처")
    else:
        print("[2/3] 장면 캡처 생략" + (" (영상이 없어 컷 전환 감지도 생략)" if args.scenes else ""))

    print("[3/3] 보고서 작성 중")
    (out_dir / "transcript.txt").write_text(report.build_transcript_text(transcript), encoding="utf-8")
    (out_dir / "info.json").write_text(json.dumps(asdict(info), ensure_ascii=False, indent=2), encoding="utf-8")
    report_path = out_dir / "report.md"
    report_path.write_text(
        report.build_report(info, transcript, captured, out_dir, args.section, cuts), encoding="utf-8"
    )
    print(f"완료: {report_path}")
    return report_path


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.url and not (args.video or args.subtitle):
        parser.error("유튜브 URL 또는 --video/--subtitle 중 하나는 필요합니다.")
    if args.url and (args.video or args.subtitle):
        parser.error("URL과 로컬 파일(--video/--subtitle)은 함께 쓸 수 없습니다.")
    if not 0 < args.scene_threshold < 1:
        parser.error("--scene-threshold는 0과 1 사이여야 합니다.")
    for path in (args.video, args.subtitle):
        if path and not path.is_file():
            parser.error(f"파일이 없습니다: {path}")
    try:
        run(args)
    except frames.FfmpegNotFoundError as error:
        print(f"오류: {error}", file=sys.stderr)
        return 1
    except Exception as error:  # yt-dlp 네트워크 오류 등
        print(f"오류: {type(error).__name__}: {error}", file=sys.stderr)
        if "Tunnel connection failed" in str(error):
            print(
                "안내: 네트워크가 유튜브 접속을 막고 있습니다. "
                "www.youtube.com, *.googlevideo.com 접속을 허용하거나 --video/--subtitle 로컬 파일을 쓰세요.",
                file=sys.stderr,
            )
        return 1
    return 0
