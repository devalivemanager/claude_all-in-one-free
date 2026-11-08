"""묶기(ebook) — 삽화가 들어간 단독 HTML 뷰어와 표준 EPUB 을 만든다.

013_ai_ebook_builder 의 조판기를 스틸컷 삽화에 맞게 다듬은 모듈이다.

- HTML 뷰어 : 이미지를 base64 데이터 URI 로 본문에 박아 **파일 하나**로 끝나게 한다.
  오프라인에서 열리고, 공유할 때 파일 하나만 넘기면 된다(013 뷰어의 장점을 그대로 이어받는다).
- EPUB 3 : 이미지를 `images/` 폴더로 번들링하고 매니페스트에 등록한다. 리디북스·애플 북스 등
  전자책 리더용. 표준 라이브러리 zipfile 로만 만든다.
- 용량 최적화 : 캡처 단계에서 너비를 줄이고(-q:v 3) JPEG 품질로 저장하는 방식을 기본으로 하며,
  여기서는 이미지를 그대로 번들링한다(재인코딩으로 화질을 두 번 깎지 않는다).

본문을 다시 쓰는 일(요약·문장 다듬기)은 이 모듈이 아니라 클로드 코드가 맡는다 —
규칙은 README 와 가이드의 PROMPT-0 에 있다.
"""

from __future__ import annotations

import base64
import hashlib
import struct
import uuid
import zipfile
import zlib
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from . import extractor


@dataclass
class BookMeta:
    """책 한 권의 기본 정보."""

    title: str
    subtitle: str = ""
    author: str = ""


@dataclass(frozen=True)
class _Image:
    """출력용으로 정리된 삽화 한 장."""

    name: str  # EPUB 내부 경로 (images/img_0001.png)
    mime: str
    data: bytes
    caption: str  # 타임스탬프 캡션 (00:01:23)


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _is_valid_png(data: bytes) -> bool:
    """PNG 서명과 덩어리(chunk) 구조·CRC 를 훑어 깨지지 않은 PNG 인지 본다.

    캡처가 중간에 끊겨 깨진 파일을 EPUB 에 넣으면 리더가 못 보여 주고
    epubcheck 도 PKG-021(깨진 이미지) ERROR 를 낸다.
    """
    if not data.startswith(_PNG_SIGNATURE):
        return False
    pos = len(_PNG_SIGNATURE)
    first = True
    while pos + 12 <= len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        end = pos + 12 + length
        if end > len(data):
            return False
        body = data[pos + 8:pos + 8 + length]
        crc = struct.unpack(">I", data[pos + 8 + length:end])[0]
        if zlib.crc32(kind + body) & 0xFFFFFFFF != crc:
            return False
        if first and (kind != b"IHDR" or length != 13):
            return False
        first = False
        if kind == b"IEND":
            return end == len(data)
        pos = end
    return False


def _read_still(path: Path) -> bytes | None:
    """스틸컷을 읽는다. 지워졌거나 깨진 파일이면 None(삽화에서만 빼고 본문은 살린다)."""
    try:
        data = Path(path).read_bytes()
    except OSError:
        return None
    return data if _is_valid_png(data) else None


def _collect_images(sections: list) -> list[_Image]:
    """챕터에 배정된 스틸컷을 전부 읽어 출력용 자산으로 정리한다. 없으면 빈 목록."""
    images: list[_Image] = []
    for order, section in enumerate(sections, start=1):
        for frame in section.images:
            data = _read_still(frame.path)
            if data is None:
                continue  # 지워졌거나 깨진 캡처는 삽화에서만 빼고 본문은 살린다
            images.append(
                _Image(
                    name=f"images/img_{order:03d}_{Path(frame.path).stem}.png",
                    mime="image/png",
                    data=data,
                    caption=extractor.format_timestamp(frame.timestamp),
                )
            )
    return images


def _validate(meta: BookMeta, sections: list) -> None:
    if not meta.title.strip():
        raise ValueError("책 제목이 비어 있다")
    if not sections:
        raise ValueError("챕터가 하나도 없다. 자막을 먼저 읽었는지 확인한다")


def _book_uid(meta: BookMeta) -> str:
    """EPUB 고유번호. `urn:uuid:` + UUID 4 형식(epubcheck OPF-085 기준).

    제목·저자에서 결정론적으로 만들어, 같은 책을 다시 빌드해도 번호가 같다.
    버전·변형 비트는 UUID 4 규격대로 둔다.
    """
    digest = hashlib.sha256(f"{meta.title}\n{meta.author}".encode("utf-8")).digest()
    return "urn:uuid:" + str(uuid.UUID(bytes=digest[:16], version=4))


# 리더가 package.opf 를 찾는 길잡이. 없으면 epubcheck RSC-002 FATAL.
_CONTAINER_XML = """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
<rootfiles>
<rootfile full-path="package.opf" media-type="application/oebps-package+xml"/>
</rootfiles>
</container>
"""


def _data_uri(image: _Image) -> str:
    encoded = base64.b64encode(image.data).decode("ascii")
    return f"data:{image.mime};base64,{encoded}"


def build_html(meta: BookMeta, sections: list) -> str:
    """삽화가 박힌 단독 HTML 뷰어 하나를 문자열로 만든다(이미지 포함, 오프라인 열림)."""
    _validate(meta, sections)
    collected = _collect_images(sections)
    by_caption: dict[str, _Image] = {img.caption: img for img in collected}

    toc = "\n".join(
        f'<li><a href="#ch-{index}">{_escape(s.title)}</a></li>'
        for index, s in enumerate(sections)
    )
    body_parts: list[str] = []
    for index, section in enumerate(sections):
        body_parts.append(f'<section id="ch-{index}"><h1>{_escape(section.title)}</h1>')
        for paragraph in [p for p in section.body.split("\n\n") if p.strip()]:
            body_parts.append(f"<p>{_escape(paragraph)}</p>")
        for frame in section.images:
            caption = extractor.format_timestamp(frame.timestamp)
            image = by_caption.get(caption)
            if image is None:
                continue
            body_parts.append(
                f'<figure class="illus"><img src="{_data_uri(image)}" alt="{caption} 장면">'
                f"<figcaption>{caption} 장면</figcaption></figure>"
            )
        body_parts.append("</section>")

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_escape(meta.title)}</title>
<style>
body {{ background: #fbf7f0; color: #2b2118; font-family: 'Noto Serif KR', serif;
      margin: 0; line-height: 1.9; }}
main {{ max-width: 720px; margin: 0 auto; padding: 24px 20px 80px; }}
h1 {{ color: #8c4a2f; margin: 2.2rem 0 0.4rem; }}
figure.illus {{ margin: 1.6rem 0; text-align: center; }}
figure.illus img {{ max-width: 100%; border-radius: 8px; border: 1px solid #2b211822; }}
figcaption {{ font-size: 0.85rem; color: #8c4a2f; margin-top: 4px; }}
.toc {{ margin: 24px 0; padding: 16px 20px; border: 1px solid #2b211822; border-radius: 10px; }}
.toc a {{ color: #8c4a2f; text-decoration: none; }}
@media print {{ .toc {{ display: none; }} h1 {{ page-break-before: always; }} }}
</style>
</head>
<body>
<main>
<nav class="toc"><strong>차례</strong>
<ul>
{toc}
</ul></nav>
{chr(10).join(body_parts)}
</main>
</body>
</html>
"""


def build_epub(meta: BookMeta, sections: list) -> bytes:
    """삽화가 번들링된 EPUB 3 바이트를 만든다. 표준 라이브러리 zipfile 만 쓴다.

    - mimetype 은 압축 없이(store) 맨 앞에 와야 하고, 바로 뒤에 META-INF/container.xml 이
      package.opf 의 위치를 알려 준다.
    - 이미지는 `images/` 폴더로 넣고 매니페스트에 등록한다(EPUB 이미지 번들링 규격).
      읽지 못한(지워진·깨진) 캡처는 매니페스트·본문에서도 빼서 없는 파일을 가리키지 않게 한다.
    """
    _validate(meta, sections)
    # 챕터별 이미지 배분(EPUB 내부 경로 images/img_0000.png 로 이름을 다시 붙인다)
    per_chapter: list[list[_Image]] = []
    counter = 0
    for section in sections:
        batch: list[_Image] = []
        for frame in section.images:
            data = _read_still(frame.path)
            if data is None:
                continue  # 지워졌거나 깨진 캡처는 삽화에서만 빼고 본문은 살린다
            batch.append(
                _Image(
                    name=f"images/img_{counter:04d}.png",
                    mime="image/png",
                    data=data,
                    caption=extractor.format_timestamp(frame.timestamp),
                )
            )
            counter += 1
        per_chapter.append(batch)
    collected = [img for batch in per_chapter for img in batch]
    uid = _book_uid(meta)
    # 값이 빈 dc 항목은 쓰지 않는다(빈 태그는 epubcheck RSC-005 ERROR).
    optional_meta = "".join(
        f"<dc:{tag}>{_escape(value.strip())}</dc:{tag}>\n"
        for tag, value in (("creator", meta.author), ("description", meta.subtitle))
        if value.strip()
    )

    def xhtml(section, index: int, images: list[_Image]) -> str:
        figures = "\n".join(
            f'<figure><img src="{_escape(img.name)}" alt="{img.caption} 장면"/>'
            f"<figcaption>{img.caption} 장면</figcaption></figure>"
            for img in images
        )
        paragraphs = "\n".join(
            f"<p>{_escape(p)}</p>" for p in section.body.split("\n\n") if p.strip()
        )
        return f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="ko">
<head><meta charset="utf-8"/><title>{_escape(section.title)}</title>
<link rel="stylesheet" type="text/css" href="style.css"/></head>
<body>
<h1>{_escape(section.title)}</h1>
{paragraphs}
{figures}
</body>
</html>
"""

    image_items = "".join(
        f'<item id="img{i}" href="{_escape(img.name)}" media-type="{img.mime}"/>'
        for i, img in enumerate(collected)
    )
    manifest = "".join(
        f'<item id="ch{i}" href="ch{i}.xhtml" media-type="application/xhtml+xml"/>'
        for i in range(len(sections))
    )
    spine = "".join(f'<itemref idref="ch{i}"/>' for i in range(len(sections)))
    package = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="uid">{uid}</dc:identifier>
<dc:title>{_escape(meta.title)}</dc:title>
<dc:language>ko</dc:language>
{optional_meta}<meta property="dcterms:modified">2026-01-01T00:00:00Z</meta>
</metadata>
<manifest>
<item id="css" href="style.css" media-type="text/css"/>
<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
{image_items}
{manifest}
</manifest>
<spine>{spine}</spine>
</package>
"""
    nav_items = "\n".join(
        f'<li><a href="ch{i}.xhtml">{_escape(s.title)}</a></li>'
        for i, s in enumerate(sections)
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
    css = "body { color: #2b2118; line-height: 1.9; }\nh1 { color: #8c4a2f; }\nfigure { text-align: center; margin: 1.2em 0; }\nfigure img { max-width: 100%; }\nfigcaption { font-size: 0.85em; color: #8c4a2f; }\n"

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            zipfile.ZipInfo("mimetype"),
            "application/epub+zip",
            compress_type=zipfile.ZIP_STORED,
        )
        zf.writestr("META-INF/container.xml", _CONTAINER_XML)
        zf.writestr("style.css", css)
        zf.writestr("nav.xhtml", nav)
        zf.writestr("package.opf", package)
        for i, (section, batch) in enumerate(zip(sections, per_chapter)):
            zf.writestr(f"ch{i}.xhtml", xhtml(section, i, batch))
            for img in batch:
                zf.writestr(img.name, img.data)
    return buffer.getvalue()


def write_outputs(
    meta: BookMeta,
    sections: list,
    out_dir: Path,
    formats: tuple[str, ...] = ("html", "epub"),
) -> dict[str, Path]:
    """지정한 형식(html, epub)의 전자책 파일을 out_dir 에 쓴다."""
    written: dict[str, Path] = {}
    out_dir.mkdir(parents=True, exist_ok=True)
    if "html" in formats:
        path = out_dir / "ebook.html"
        path.write_text(build_html(meta, sections), encoding="utf-8")
        written["html"] = path
    if "epub" in formats:
        path = out_dir / "ebook.epub"
        path.write_bytes(build_epub(meta, sections))
        written["epub"] = path
    return written
