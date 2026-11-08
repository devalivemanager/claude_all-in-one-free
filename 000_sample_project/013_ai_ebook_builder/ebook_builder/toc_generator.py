"""목차(챕터) 분할기.

외부 모델 없이 규칙(마크다운 제목, 「제N장」, 「N.」 번호)만으로
챕터 경계를 찾는다. 모델을 쓰지 않으므로 결과가 늘 같고 비용이 0원이다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Chapter:
    """하나의 챕터. `source` 는 어느 입력 파일에서 나왔는지 표시다."""

    title: str
    body: str
    source: str = ""
    chunks: list[str] = field(default_factory=list)

    def with_chunks(self, max_chars: int = 4000) -> "Chapter":
        """본문을 AI 재생성 단위(청크)로 잘라 둔다. 부분 재생성의 기준이 된다."""
        self.chunks = chunk_by_length(self.body, max_chars)
        return self


# 챕터 경계로 인정할 제목 줄들.
# - 마크다운 제목(#, ##)
# - 「제1장」「제 12 장」처럼 붙는 장 표기
# - 「3. 병사의 하루」처럼 「숫자.」로 시작하는 줄
_MD_HEADING = re.compile(r"^#{1,3}\s+(.+?)\s*#*\s*$")
_NUM_HEADING = re.compile(r"^제\s*(\d+)\s*장\s*[:.·]?\s*(.*)$")
_DOT_HEADING = re.compile(r"^(\d{1,2})\.\s*(\S.*)$")

# 이 패턴으로 시작하면 내용이 있어도 제목으로 세지 않는다(표·인용 등).
_NOT_A_HEADING = re.compile(r"^(\||>|```)")


def looks_like_heading(line: str) -> bool:
    """한 줄이 챕터 제목으로 쓸 만한 줄인지 본다."""
    stripped = line.strip()
    if not stripped or len(stripped) > 80:
        return False
    if _NOT_A_HEADING.match(stripped):
        return False
    if _MD_HEADING.match(stripped):
        return True
    if _NUM_HEADING.match(stripped):
        return True
    if _DOT_HEADING.match(stripped):
        return True
    return False


def heading_text(line: str) -> str | None:
    """제목 줄에서 꾸미기(#, 번호 표기)를 덜어낸 제목을 돌려준다. 제목이 아니면 None."""
    stripped = line.strip()
    match = _MD_HEADING.match(stripped)
    if match:
        return match.group(1).strip()
    match = _NUM_HEADING.match(stripped)
    if match:
        base = match.group(2).strip()
        return base or f"제{match.group(1)}장"
    match = _DOT_HEADING.match(stripped)
    if match:
        return match.group(2).strip()
    return None


def split_into_chapters(
    text: str,
    source: str = "",
    min_chapter_chars: int = 40,
) -> list[Chapter]:
    """원문을 챕터 목록으로 나눈다.

    - 제목 줄이 하나도 없으면 원문 전체를 「서문」 한 챕터로 묶는다(파일이 여러 개여도
      파일명이 곧 챕터가 되지 않게, 「내용이 챕터 수를 정한다」).
    - 제목 아래에 본문이 `min_chapter_chars` 미만인 껍데기 제목은 앞 챕터의 본문으로 합친다.
    """
    if not text.strip():
        return []

    lines = text.splitlines()
    found: list[tuple[str, int]] = []
    for index, line in enumerate(lines):
        if looks_like_heading(line):
            title = heading_text(line)
            if title:
                found.append((title, index))

    if not found:
        return [Chapter(title="서문", body=text.strip(), source=source).with_chunks()]

    chapters: list[Chapter] = []
    for order, (title, index) in enumerate(found):
        body_start = index + 1
        body_end = found[order + 1][1] if order + 1 < len(found) else len(lines)
        body = "\n".join(lines[body_start:body_start + (body_end - body_start)]).strip()
        is_last = order + 1 == len(found)
        if len(body) < min_chapter_chars and chapters and not is_last:
            # 껍데기 제목: 본문이 너무 짧고 뒤에 다른 챕터가 더 있으면 앞 챕터에 붙인다.
            # 마지막 챕터는 합쳐서 잃어버리지 않게 반드시 남긴다.
            previous = chapters[-1]
            previous.body = f"{previous.body}\n\n{title}\n{body}".strip()
            continue
        chapters.append(
            Chapter(title=title, body=body, source=source).with_chunks()
        )
    if not chapters:
        return [Chapter(title="서문", body=text.strip(), source=source).with_chunks()]
    return chapters


def chunk_by_length(text: str, max_chars: int = 4000) -> list[str]:
    """문단(빈 줄) 경계를 존중하면서 `max_chars` 안으로 본문을 자른다.

    한 문단이 `max_chars` 보다 길면 그 문단만 문장 경계로 자른다.
    """
    if max_chars <= 0:
        raise ValueError("max_chars 는 1 이상이어야 한다")

    paragraphs = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        if current:
            chunks.append("\n\n".join(current).strip())
            current = []
            current_len = 0

    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            flush()
            chunks.extend(_split_long_paragraph(paragraph, max_chars))
            continue
        extra = len(paragraph) + (2 if current else 0)
        if current_len + extra > max_chars:
            flush()
        current.append(paragraph)
        current_len += len(paragraph) + (2 if len(current) > 1 else 0)
    flush()
    return chunks or [text.strip()]


def _split_long_paragraph(paragraph: str, max_chars: int) -> list[str]:
    """문단 하나가 길 때 문장(마침표·물음표·느낌표·줄바꿈) 경계로 자른다."""
    sentences = re.split(r"(?<=[.!?。！?])\s+|(?<=\n)", paragraph.strip())
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if not sentence.strip():
            continue
        while len(sentence) > max_chars:
            chunks.append(sentence[:max_chars])
            sentence = sentence[max_chars:]
        if current and len(current) + len(sentence) + 1 > max_chars:
            chunks.append(current.strip())
            current = ""
        current = f"{current} {sentence}".strip()
    if current.strip():
        chunks.append(current.strip())
    return chunks


def detect_title(text: str, fallback: str = "제목 없음") -> str:
    """원문에서 책 제목 후보를 찾는다. 첫 마크다운 H1(# )을 제목으로 삼는다."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and len(stripped) > 2:
            return stripped[2:].strip()[:80]
    return fallback
