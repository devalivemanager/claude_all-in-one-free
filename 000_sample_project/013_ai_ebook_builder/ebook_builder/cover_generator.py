"""SVG 표지 자동 생성기.

제목·부제·스타일 프리셋만으로
결정론적(deterministic) 표지를 코드로 그린다. 생성 AI를 쓰지 않으므로
같은 입력은 언제나 같은 표지가 나오고, 한글 글자도 이미지 생성기처럼 뭉개지지 않는다.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass
class CoverSpec:
    title: str
    subtitle: str = ""
    author: str = ""
    preset: str = "novel"
    seed: str = ""  # 비워 두면 제목의 해시로 결정한다


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# 스타일 프리셋별 표지 배경(그라데이션)과 글자색. builder.STYLE_PRESETS 의 키와 맞춘다.
_COVER_THEMES = {
    "novel": ("#1a2332", "#3d5a80", "#f5e9d0"),
    "essay": ("#f5f0e8", "#d4c5a9", "#3b3226"),
    "classic": ("#2d2418", "#6b4f2e", "#e8d5b7"),
    "tech": ("#0d1117", "#1f6feb", "#e6edf3"),
    "night": ("#0a0a12", "#2a2a4a", "#c9c9e8"),
    "poem": ("#fdf6f0", "#e8b4b8", "#5a3a3a"),
    "report": ("#f0f4f8", "#8898aa", "#22313f"),
    "fairytale": ("#fff8e7", "#f4a259", "#5c3a1e"),
    "manual": ("#eef2ee", "#5a7d5a", "#26332b"),
    "zine": ("#1a1a2e", "#e94560", "#f5f5f5"),
}


def _text_lines(text: str, max_per_line: int = 16, max_lines: int = 3) -> list[str]:
    """긴 제목을 몇 줄로 나눈다. 한글은 글자 수 기준으로만 자른다."""
    lines: list[str] = []
    remaining = text.strip()
    while remaining and len(lines) < max_lines:
        lines.append(remaining[:max_per_line])
        remaining = remaining[max_per_line:]
    if remaining:  # 너무 긴 제목은 마지막 줄을 줄임표로 맺는다
        lines[-1] = lines[-1][: max_per_line - 1] + "…"
    return lines


def generate_cover_svg(spec: CoverSpec) -> str:
    """표지 SVG 문자열을 만든다. 같은 입력이면 항상 같은 문자열이다."""
    if not spec.title.strip():
        raise ValueError("표지 제목이 비어 있다")
    preset = spec.preset if spec.preset in _COVER_THEMES else "novel"
    top, bottom, ink = _COVER_THEMES[preset]
    seed = spec.seed or spec.title
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()

    # 해시 앞부분으로 장식 원의 위치를 정한다. 디자인이 살짝씩 달라진다.
    cx = 60 + int(digest[:3], 16) % 280
    cy = 160 + int(digest[3:6], 16) % 200
    r = 90 + int(digest[6:8], 16) % 80

    title_lines = _text_lines(spec.title)
    base_y = 430 - (len(title_lines) - 1) * 30
    title_svg = "".join(
        f'\n  <text x="60" y="{base_y + i * 60}" font-size="44" font-weight="700" '
        f'fill="{ink}" font-family="\'Noto Serif KR\', serif">'
        f"{_escape(line)}</text>"
        for i, line in enumerate(title_lines)
    )
    subtitle_svg = ""
    if spec.subtitle.strip():
        sub = spec.subtitle.strip()[:40]
        subtitle_svg = (
            f'\n  <text x="60" y="{base_y + len(title_lines) * 60}" '
            f'font-size="20" fill="{ink}" opacity="0.8" '
            f"font-family=\"'Noto Sans KR', sans-serif\">{_escape(sub)}</text>"
        )
    author_svg = ""
    if spec.author.strip():
        author_svg = (
            f'\n  <text x="60" y="880" font-size="18" fill="{ink}" opacity="0.7" '
            f"font-family=\"'Noto Sans KR', sans-serif\">{_escape(spec.author.strip()[:30])}</text>"
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1000" viewBox="0 0 1000 1000">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{top}"/>
      <stop offset="100%" stop-color="{bottom}"/>
    </linearGradient>
  </defs>
  <rect width="1000" height="1000" fill="url(#bg)"/>
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="{ink}" opacity="0.10"/>
  <circle cx="{1000 - cx}" cy="{1000 - cy}" r="{r // 2}" fill="{ink}" opacity="0.08"/>
  <rect x="60" y="120" width="72" height="6" fill="{ink}" opacity="0.85"/>{title_svg}{subtitle_svg}{author_svg}
</svg>
"""
