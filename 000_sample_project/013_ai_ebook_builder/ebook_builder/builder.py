"""조판기 — 챕터를 네 가지 출력(HTML 뷰어·EPUB·인쇄용 HTML·웹북 ZIP)으로 만든다.

- HTML 단독 뷰어 : 파일 하나로 끝나는 뷰어. 검색·테마·인쇄 버튼이 들어가고
  오프라인에서 열린다. Folio의 HTML 내보내기에 대응한다.
- EPUB : 리디북스·애플 북스 등 전자책 리더용. 표준 라이브러리 zipfile 로만 만든다.
- 인쇄용 HTML : 챕터마다 페이지 나눔이 들어가 인쇄→PDF 저장에 바로 쓴다.
- 웹북 ZIP : 버셀 드롭(Vercel Drop) 같은 정적 호스팅에 끌어다 놓으면
  그대로 웹북 URL 이 되는 배포 꾸러미.

여기서는 텍스트를 다듬고 묶는 일만 한다. 본문을 다시 쓰는 일(요약·문장 정리)은
2단계에서 클로드 코드가 맡는다 — 규칙은 README 와 가이드의 PROMPT-0 에 있다.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path

from .cover_generator import CoverSpec, generate_cover_svg
from .toc_generator import Chapter

# 10종 스타일 프리셋. 각 값은 (본문 글꼴 계열, 배경, 글자색, 강조색).
# night 은 야간 독서용, classic 은 구한말 소설 같은 옛 글용이다.
STYLE_PRESETS: dict[str, dict[str, str]] = {
    "novel": {"font": "serif", "bg": "#fbf7f0", "ink": "#2b2118", "accent": "#8c4a2f"},
    "essay": {"font": "serif", "bg": "#faf9f6", "ink": "#333333", "accent": "#666666"},
    "classic": {"font": "serif", "bg": "#f3ecdd", "ink": "#3b2f1e", "accent": "#7a5c2e"},
    "tech": {"font": "sans-serif", "bg": "#ffffff", "ink": "#1f2933", "accent": "#1f6feb"},
    "night": {"font": "sans-serif", "bg": "#14141c", "ink": "#d5d5de", "accent": "#8f8fbf"},
    "poem": {"font": "serif", "bg": "#fdf6f4", "ink": "#4a3232", "accent": "#b46a6a"},
    "report": {"font": "sans-serif", "bg": "#f7f9fb", "ink": "#22313f", "accent": "#3a6ea5"},
    "fairytale": {"font": "sans-serif", "bg": "#fffaf0", "ink": "#4a3520", "accent": "#d08040"},
    "manual": {"font": "sans-serif", "bg": "#f4f8f4", "ink": "#26332b", "accent": "#4a7a4a"},
    "zine": {"font": "sans-serif", "bg": "#f5f5f5", "ink": "#222222", "accent": "#e94560"},
}


@dataclass
class BookMeta:
    """책 한 권의 기본 정보."""

    title: str
    subtitle: str = ""
    author: str = ""
    preset: str = "novel"


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _preset(preset: str) -> dict[str, str]:
    return STYLE_PRESETS.get(preset, STYLE_PRESETS["novel"])


def _validate(meta: BookMeta, chapters: list[Chapter]) -> None:
    if not meta.title.strip():
        raise ValueError("책 제목이 비어 있다")
    if not chapters:
        raise ValueError("챕터가 하나도 없다. 원문을 먼저 읽었는지 확인한다")


def _cover_data_uri(meta: BookMeta) -> str:
    spec = CoverSpec(
        title=meta.title,
        subtitle=meta.subtitle,
        author=meta.author,
        preset=meta.preset,
    )
    svg = generate_cover_svg(spec)
    return "data:image/svg+xml;charset=utf-8," + svg.replace("\n", "").replace('"', "%22")


def _viewer_css(meta: BookMeta) -> str:
    theme = _preset(meta.preset)
    return f"""
body {{ background: {theme['bg']}; color: {theme['ink']};
      font-family: var(--font), 'Noto Serif KR', 'Noto Sans KR', serif;
      margin: 0; line-height: 1.9; }}
main {{ max-width: 680px; margin: 0 auto; padding: 24px 20px 80px; }}
h1 {{ font-size: 1.6rem; margin: 2.2rem 0 0.4rem; color: {theme['accent']}; }}
h2 {{ font-size: 1.25rem; margin: 1.8rem 0 0.3rem; }}
hr {{ border: 0; border-top: 1px solid {theme['ink']}22; margin: 1.6rem 0; }}
blockquote {{ margin: 0; padding: 0 0 0 14px; border-left: 3px solid {theme['accent']}; }}
code {{ background: {theme['ink']}11; padding: 1px 5px; border-radius: 4px; }}
pre {{ overflow-x: auto; background: {theme['ink']}0d; padding: 12px; border-radius: 8px; }}
.cover {{ text-align: center; padding: 40px 0 10px; }}
.cover img {{ max-width: 280px; width: 100%; border-radius: 6px; }}
.toc {{ margin: 24px 0; padding: 16px 20px; border: 1px solid {theme['ink']}22; border-radius: 10px; }}
.toc a {{ color: {theme['accent']}; text-decoration: none; }}
mark {{ background: {theme['accent']}44; color: inherit; }}
#toolbar {{ position: sticky; top: 0; display: flex; gap: 8px; padding: 10px 20px;
           background: {theme['bg']}; border-bottom: 1px solid {theme['ink']}22; z-index: 2; }}
#toolbar button {{ border: 1px solid {theme['ink']}33; background: transparent; color: {theme['ink']};
                  border-radius: 6px; padding: 4px 10px; cursor: pointer; }}
@media print {{
  #toolbar, .no-print {{ display: none; }}
  body {{ background: #fff; color: #000; }}
  h1 {{ page-break-before: always; }}
}}
"""


def _body_to_html(body: str) -> str:
    """본문을 아주 단순한 HTML 로 바꾼다. 외부 라이브러리 없이.

    지원 : # 제목, > 인용, - 목록, ``` 코드 블록, 빈 줄 문단 구분.
    """
    out: list[str] = []
    in_code = False
    list_open = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_code:
                out.append("</code></pre>")
                in_code = False
            else:
                if list_open:
                    out.append("</ul>")
                    list_open = False
                out.append("<pre><code>")
                in_code = True
            continue
        if in_code:
            out.append(_escape(line))
            continue
        if not stripped:
            if list_open:
                out.append("</ul>")
                list_open = False
            continue
        if stripped.startswith("#"):
            if list_open:
                out.append("</ul>")
                list_open = False
            level = min(len(stripped) - len(stripped.lstrip("#")), 4)
            out.append(f"<h{level}>{_inline_md(stripped.lstrip('# ').strip())}</h{level}>")
            continue
        if stripped.startswith(">"):
            if list_open:
                out.append("</ul>")
                list_open = False
            out.append(f"<blockquote>{_inline_md(stripped.lstrip('> ').strip())}</blockquote>")
            continue
        if stripped.startswith("- "):
            if not list_open:
                out.append("<ul>")
                list_open = True
            out.append(f"<li>{_inline_md(stripped[2:].strip())}</li>")
            continue
        if list_open:
            out.append("</ul>")
            list_open = False
        out.append(f"<p>{_inline_md(stripped)}</p>")
    if in_code:
        out.append("</code></pre>")
    if list_open:
        out.append("</ul>")
    return "\n".join(out)


def _inline_md(text: str) -> str:
    """굵게·기울임·코드만. 문장 안의 낮은 복병(마크다운 오용)을 줄인다."""
    escaped = _escape(text)
    # 굵게: **b** 또는 __b__
    escaped = _md_bold(escaped)
    escaped = _md_italic(escaped)
    escaped = _md_code(escaped)
    return escaped


def _md_bold(text: str) -> str:
    parts = text.split("**")
    if len(parts) >= 3 and len(parts) % 2 == 1:
        out = parts[0]
        for i in range(1, len(parts), 2):
            out += f"<strong>{parts[i]}</strong>"
            if i + 1 < len(parts):
                out += parts[i + 1]
        return out
    return text


def _md_italic(text: str) -> str:
    parts = text.split("_")
    if len(parts) >= 3 and len(parts) % 2 == 1:
        out = parts[0]
        for i in range(1, len(parts), 2):
            out += f"<em>{parts[i]}</em>"
            if i + 1 < len(parts):
                out += parts[i + 1]
        return out
    return text


def _md_code(text: str) -> str:
    parts = text.split("`")
    if len(parts) >= 3 and len(parts) % 2 == 1:
        out = parts[0]
        for i in range(1, len(parts), 2):
            out += f"<code>{parts[i]}</code>"
            if i + 1 < len(parts):
                out += parts[i + 1]
        return out
    return text


def _toc_html(chapters: list[Chapter]) -> str:
    items = "\n".join(
        f'<li><a href="#ch-{index}">{_escape(ch.title)}</a></li>'
        for index, ch in enumerate(chapters)
    )
    return f'<nav class="toc no-print"><strong>차례</strong>\n<ul>\n{items}\n</ul></nav>'


def build_html(meta: BookMeta, chapters: list[Chapter], cover: str | None = None) -> str:
    """단독 HTML 뷰어 하나를 문자열로 만든다.

    `cover` 에 SVG 문자열을 넣으면 그것을 쓰고, None 이면 표지 생성기를 돌린다.
    API 키 같은 비밀값은 이 HTML 에 전혀 들어가지 않는다(배포 전 점검표 항목).
    """
    _validate(meta, chapters)
    svg = cover if cover is not None else generate_cover_svg(
        CoverSpec(title=meta.title, subtitle=meta.subtitle, author=meta.author, preset=meta.preset)
    )
    cover_uri = "data:image/svg+xml;charset=utf-8," + svg.replace("\n", "").replace('"', "%22")

    body_parts: list[str] = [
        f'<div class="cover"><img src="{cover_uri}" alt="표지"></div>',
        _toc_html(chapters),
    ]
    for index, ch in enumerate(chapters):
        body_parts.append(f'<section id="ch-{index}"><h1>{_escape(ch.title)}</h1>')
        body_parts.append(_body_to_html(ch.body))
        body_parts.append("</section>")

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_escape(meta.title)}</title>
<style>:root {{ --font: {_preset(meta.preset)['font']}; }}{_viewer_css(meta)}</style>
</head>
<body>
<div id="toolbar" class="no-print">
  <button onclick="window.print()">인쇄 / PDF 저장</button>
  <button onclick="toggleTheme()">야간 모드</button>
  <button onclick="toggleSearch()">찾기</button>
</div>
<div id="searchbar" class="no-print" style="display:none; position:sticky; top:44px; padding:8px 20px; background:{_preset(meta.preset)['bg']};">
  <input id="q" placeholder="찾을 말…" oninput="doSearch()" style="width:60%">
  <span id="qcount" style="margin-left:8px"></span>
</div>
<main>
{chr(10).join(body_parts)}
</main>
<script>
function toggleTheme() {{
  var on = document.body.dataset.night === "1";
  document.body.dataset.night = on ? "0" : "1";
  var saved = getComputedStyle(document.body);
  document.body.style.filter = on ? "" : "invert(0.05)";
  document.querySelectorAll("section, .toc, #toolbar, #searchbar").forEach(function (el) {{
    el.style.backgroundColor = on ? "" : "#14141c";
    el.style.color = on ? "" : "#d5d5de";
  }});
}}
function toggleSearch() {{
  var bar = document.getElementById("searchbar");
  bar.style.display = bar.style.display === "none" ? "block" : "none";
  if (bar.style.display === "block") document.getElementById("q").focus();
}}
function doSearch() {{
  var q = document.getElementById("q").value;
  var count = 0;
  document.querySelectorAll("mark[data-search]").forEach(function (m) {{
    var parent = m.parentNode;
    m.replaceWith(document.createTextNode(m.textContent));
    parent.normalize();
  }});
  if (!q) {{ document.getElementById("qcount").textContent = ""; return; }}
  var walker = document.createTreeWalker(document.querySelector("main"), NodeFilter.SHOW_TEXT);
  var nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  var lower = q.toLowerCase();
  nodes.forEach(function (node) {{
    var text = node.nodeValue;
    var low = text.toLowerCase();
    var idx = low.indexOf(lower);
    if (idx === -1) return;
    var frag = document.createDocumentFragment();
    var pos = 0;
    while (idx !== -1) {{
      frag.appendChild(document.createTextNode(text.slice(pos, idx)));
      var mark = document.createElement("mark");
      mark.setAttribute("data-search", "1");
      mark.textContent = text.slice(idx, idx + q.length);
      frag.appendChild(mark);
      count += 1;
      pos = idx + q.length;
      idx = low.indexOf(lower, pos);
    }}
    frag.appendChild(document.createTextNode(text.slice(pos)));
    node.parentNode.replaceChild(frag, node);
  }});
  document.getElementById("qcount").textContent = count + "곳";
}}
</script>
</body>
</html>
"""


def build_print_html(meta: BookMeta, chapters: list[Chapter]) -> str:
    """인쇄용 HTML. 브라우저 인쇄(→PDF 저장)에 바로 쓴다.

    - 표지·차례 뒤 챕터마다 `page-break-before` 로 페이지를 나눈다.
    - 표·인용이 페이지 경계에서 잘리지 않게 `break-inside: avoid` 를 둔다.
    """
    _validate(meta, chapters)
    sections = "\n".join(
        f'<section class="chapter" id="ch-{index}">\n<h1>{_escape(ch.title)}</h1>\n'
        f"{_body_to_html(ch.body)}\n</section>"
        for index, ch in enumerate(chapters)
    )
    theme = _preset(meta.preset)
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>{_escape(meta.title)} — 인쇄용</title>
<style>
@page {{ margin: 22mm 18mm; }}
body {{ font-family: {theme['font']}, 'Noto Serif KR', 'Noto Sans KR', serif;
       color: #111; line-height: 1.9; }}
.cover {{ text-align: center; page-break-after: always; }}
.cover img {{ max-width: 60%; }}
h1 {{ page-break-before: always; break-after: avoid; }}
h2, h3 {{ break-after: avoid; }}
table, blockquote, pre {{ break-inside: avoid; }}
.toc {{ page-break-after: always; }}
</style>
</head>
<body>
<div class="cover">
  <img src="{_cover_data_uri(meta)}" alt="표지">
  <h1 style="page-break-before:auto">{_escape(meta.title)}</h1>
  <p>{_escape(meta.subtitle)}</p>
  <p>{_escape(meta.author)}</p>
</div>
<nav class="toc"><strong>차례</strong>
<ul>
{chr(10).join(f'<li>{_escape(ch.title)}</li>' for ch in chapters)}
</ul>
</nav>
{sections}
</body>
</html>
"""


def build_epub(meta: BookMeta, chapters: list[Chapter], cover: str | None = None) -> bytes:
    """EPUB 3 전자책 바이트를 만든다. 표준 라이브러리 zipfile 만 쓴다.

    - mimetype 은 압축 없이(store) 맨 앞에 와야 한다.
    - 이미지·폰트 없이 XHTML+CSS 만으로 꾸민다. 리더 호환성이 가장 높다.
    """
    _validate(meta, chapters)
    svg = cover if cover is not None else generate_cover_svg(
        CoverSpec(title=meta.title, subtitle=meta.subtitle, author=meta.author, preset=meta.preset)
    )
    theme = _preset(meta.preset)
    uid = "urn:uuid:" + __import__("hashlib").sha256(meta.title.encode()).hexdigest()[:32]

    def xhtml(ch: Chapter, index: int) -> str:
        return f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="ko">
<head><meta charset="utf-8"/><title>{_escape(ch.title)}</title>
<link rel="stylesheet" type="text/css" href="style.css"/></head>
<body>
<h1>{_escape(ch.title)}</h1>
{_body_to_html(ch.body)}
</body>
</html>
"""

    spine = "".join(f'<itemref idref="ch{i}"/>' for i in range(len(chapters)))
    manifest = "".join(
        f'<item id="ch{i}" href="ch{i}.xhtml" media-type="application/xhtml+xml"/>'
        for i in range(len(chapters))
    )
    package = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="uid">{uid}</dc:identifier>
<dc:title>{_escape(meta.title)}</dc:title>
<dc:language>ko</dc:language>
<dc:creator>{_escape(meta.author)}</dc:creator>
<dc:description>{_escape(meta.subtitle)}</dc:description>
<meta property="dcterms:modified">2026-01-01T00:00:00Z</meta>
</metadata>
<manifest>
<item id="cover" href="cover.svg" media-type="image/svg+xml" properties="svg"/>
<item id="css" href="style.css" media-type="text/css"/>
<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
{manifest}
</manifest>
<spine>{spine}</spine>
</package>
"""
    nav_items = "\n".join(
        f'<li><a href="ch{i}.xhtml">{_escape(ch.title)}</a></li>'
        for i, ch in enumerate(chapters)
    )
    nav = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="ko">
<head><meta charset="utf-8"/><title>차례</title></head>
<body><nav epub:type="toc"><h1>차례</h1><ol>
{nav_items}
</ol></nav></body>
</html>
"""
    css = f"""body {{ color: {theme['ink']}; line-height: 1.9; }}
h1 {{ color: {theme['accent']}; }}
"""

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # mimetype 은 반드시 첫 항목, 무압축.
        zf.writestr(
            zipfile.ZipInfo("mimetype"),
            "application/epub+zip",
            compress_type=zipfile.ZIP_STORED,
        )
        zf.writestr("cover.svg", svg)
        zf.writestr("style.css", css)
        zf.writestr("nav.xhtml", nav)
        zf.writestr("package.opf", package)
        for i, ch in enumerate(chapters):
            zf.writestr(f"ch{i}.xhtml", xhtml(ch, i))
    return buffer.getvalue()


def build_webbook_zip(meta: BookMeta, chapters: list[Chapter]) -> bytes:
    """웹북 배포 꾸러미(ZIP)를 만든다.

    안에는 정적 사이트 3개 파일(index.html, book.json, 404.html)이 들어 있고,
    버셀 드롭 같은 정적 호스팅에 ZIP 을 끌어다 놓으면 바로 웹북 URL 이 된다.
    index.html 은 단독 HTML 뷰어와 같은 파일이므로 로컬에서 열어도 된다.
    """
    html = build_html(meta, chapters)
    manifest = json.dumps(
        {
            "title": meta.title,
            "subtitle": meta.subtitle,
            "author": meta.author,
            "preset": meta.preset,
            "chapters": [{"title": ch.title, "source": ch.source} for ch in chapters],
            "format": "devalive-webbook/1",
        },
        ensure_ascii=False,
        indent=2,
    )
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("index.html", html)
        zf.writestr("book.json", manifest)
        zf.writestr(
            "404.html",
            "<!DOCTYPE html><html lang=\"ko\"><meta charset=\"utf-8\">"
            "<body><p>그런 쪽이 없다. 차례에서 다시 골라 보자.</p></body></html>",
        )
    return buffer.getvalue()
