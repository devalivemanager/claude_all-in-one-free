#!/usr/bin/env python3
"""yt_transcript.py - turn a YouTube transcript into clean, time-stamped text split into chunks.
(youtube-to-skill-kit · Python 3 standard library only · read-only except the output folder)

Input (any one):
  transcript.txt   pasted from YouTube "Show transcript" (lines like "1:23" + text, or "1:23 text")
  captions.vtt     WebVTT file (auto captions' repeated rolling lines are de-duplicated)
  captions.srt     SubRip file
  https://youtu.be/...   needs yt-dlp (free, open source: pip install yt-dlp) - captions only, no video

Usage:
  python yt_transcript.py transcript.txt                 # -> out/transcript.txt + out/chunks/
  python yt_transcript.py captions.vtt --chunk 10 --out work
  python yt_transcript.py https://youtu.be/XXXX --lang ko,en

Output lines look like "[03:15] text". Chunks are cut every --chunk minutes (default 10)
so a long video is analysed piece by piece instead of losing the middle.
Written 2026-10-03.
"""
import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile

TS_RANGE = re.compile(r"(\d{1,2}:)?(\d{1,2}):(\d{2})[.,]\d{1,3}\s*-->\s*")
TS_ONLY = re.compile(r"^\s*((\d{1,2}):)?(\d{1,2}):(\d{2})\s*$")
TS_LEAD = re.compile(r"^\s*((\d{1,2}):)?(\d{1,2}):(\d{2})\s+(.+)$")
TAGS = re.compile(r"<[^>]+>")


def secs(h, m, s):
    return int(h or 0) * 3600 + int(m) * 60 + int(s)


def fmt(t):
    h, r = divmod(int(t), 3600)
    m, s = divmod(r, 60)
    return "%d:%02d:%02d" % (h, m, s) if h else "%02d:%02d" % (m, s)


def parse_cues(text):
    """VTT / SRT -> [(sec, line)] ; drops auto-caption rolling duplicates"""
    out, cur, last = [], None, ""
    for raw in text.splitlines():
        line = raw.strip()
        mm = TS_RANGE.search(line)
        if mm:
            h = (mm.group(1) or "").rstrip(":") or 0
            cur = secs(h, mm.group(2), mm.group(3))
            continue
        if not line or cur is None or line.isdigit() or line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
            continue
        clean = TAGS.sub("", line).strip()
        if not clean or clean == last:
            continue
        # rolling captions repeat the previous line as the first line of the next cue
        if out and clean in out[-1][1]:
            continue
        out.append((cur, clean))
        last = clean
    return out


def parse_pasted(text):
    """YouTube 'Show transcript' copy -> [(sec, line)]"""
    out, cur = [], None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = TS_ONLY.match(line)
        if m:
            cur = secs(m.group(2), m.group(3), m.group(4))
            continue
        m = TS_LEAD.match(line)
        if m:
            cur = secs(m.group(2), m.group(3), m.group(4))
            line = m.group(5).strip()
        if cur is None:
            cur = 0
        if out and out[-1][0] == cur:
            out[-1] = (cur, out[-1][1] + " " + line)
        else:
            out.append((cur, line))
    return out


def ytdlp_cmd():
    exe = shutil.which("yt-dlp")
    if exe:
        return [exe]
    try:
        import yt_dlp  # noqa: F401
        return [sys.executable, "-m", "yt_dlp"]
    except ImportError:
        return None


def fetch(url, langs):
    cmd = ytdlp_cmd()
    if cmd is None:
        sys.exit("  yt-dlp is not installed -> pip install yt-dlp   (or paste the transcript into a .txt file)")
    # 2026-10-03 fix: ask ONE language at a time, in order. Asking "ko,en" together made YouTube
    # refuse the auto-translated 'en' track with HTTP 429 and the whole run failed.
    errors = []
    for lg in [x.strip() for x in langs.split(",") if x.strip()]:
        tmp = tempfile.mkdtemp(prefix="ytsub_")
        args = cmd + ["--skip-download", "--write-subs", "--write-auto-subs", "--sub-format", "vtt",
                      "--sub-langs", lg, "-o", os.path.join(tmp, "sub.%(ext)s"), url]
        r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
        files = sorted(glob.glob(os.path.join(tmp, "*.vtt")))
        if files:
            return open(files[0], encoding="utf-8", errors="replace").read(), os.path.basename(files[0])
        last = r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "no captions in this language"
        errors.append("%s: %s" % (lg, last))
    hint = ""
    if any("429" in e for e in errors):
        hint = "\n  -> YouTube is rate-limiting (HTTP 429). Wait a few minutes, try one language (--lang ko), or paste the transcript."
    sys.exit("  could not fetch captions\n    " + "\n    ".join(errors) + hint
             + "\n  -> fallback: copy YouTube 'Show transcript' into a .txt file and pass that file")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="transcript .txt/.vtt/.srt or a YouTube URL")
    ap.add_argument("--chunk", type=float, default=10, help="minutes per chunk (default 10)")
    ap.add_argument("--out", default="out", help="output folder (default out)")
    ap.add_argument("--lang", default="ko,en", help="caption languages for URL input (default ko,en)")
    a = ap.parse_args()

    src = a.source
    if re.match(r"https?://", src):
        text, name = fetch(src, a.lang)
        cues = parse_cues(text)
        origin = "%s (%s)" % (src, name)
    else:
        if not os.path.isfile(src):
            sys.exit("  file not found: %s" % src)
        text = open(src, encoding="utf-8-sig", errors="replace").read()
        cues = parse_cues(text) if ("-->" in text) else parse_pasted(text)
        origin = os.path.abspath(src)
    if not cues:
        sys.exit("  no transcript lines found in: %s" % src)

    os.makedirs(os.path.join(a.out, "chunks"), exist_ok=True)
    for old in glob.glob(os.path.join(a.out, "chunks", "chunk_*.txt")):
        os.remove(old)
    lines = ["[%s] %s" % (fmt(t), s) for t, s in cues]
    with open(os.path.join(a.out, "transcript.txt"), "w", encoding="utf-8") as f:
        f.write("# source: %s\n" % origin)
        f.write("\n".join(lines) + "\n")

    span = max(1, int(a.chunk * 60))
    groups = {}
    for (t, s), l in zip(cues, lines):
        groups.setdefault(int(t // span), []).append(l)
    for i, k in enumerate(sorted(groups), 1):
        with open(os.path.join(a.out, "chunks", "chunk_%02d.txt" % i), "w", encoding="utf-8") as f:
            f.write("# chunk %d : %s ~ %s\n" % (i, fmt(k * span), fmt((k + 1) * span)))
            f.write("\n".join(groups[k]) + "\n")

    print("  source   : %s" % origin)
    print("  lines    : %d  (length %s)" % (len(lines), fmt(cues[-1][0])))
    print("  chunks   : %d x %g min  -> %s" % (len(groups), a.chunk, os.path.join(a.out, "chunks")))
    print("  next     : run instruction A (02_지시문.md) on the chunks, then B in a fresh context")
    return 0


if __name__ == "__main__":
    sys.exit(main())
