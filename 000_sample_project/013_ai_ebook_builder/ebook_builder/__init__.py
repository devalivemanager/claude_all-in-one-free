"""ebook_builder — 원본 텍스트를 전자책(HTML·EPUB·인쇄용·웹북)으로 묶는 파이프라인.

Folio(웹 앱)의 흐름을 따라하되, 브라우저 복붙 대신 클로드 코드가
한 줄 명령으로 돌릴 수 있게 만든 데브얼라이브 샘플이다.
"""

from .builder import (
    STYLE_PRESETS,
    build_epub,
    build_html,
    build_print_html,
    build_webbook_zip,
)
from .cover_generator import generate_cover_svg
from .toc_generator import Chapter, chunk_by_length, detect_title, split_into_chapters

__all__ = [
    "Chapter",
    "STYLE_PRESETS",
    "build_epub",
    "build_html",
    "build_print_html",
    "build_webbook_zip",
    "chunk_by_length",
    "detect_title",
    "generate_cover_svg",
    "split_into_chapters",
]

__version__ = "0.1.0"
