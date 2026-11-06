"""1단계 전처리: 개인정보 제거, 키워드 집계(일반 코드), 분류·요약(소형 모델) → clean_data.json.

소형 모델의 답은 믿지 않고 검사한다. 형식이 틀린 항목은 성공으로 세지 않고 failures 에 남긴다.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .slm_client import OllamaClient, SLMError

SCHEMA_VERSION = 1
CATEGORIES = ["칭찬", "기능문의", "오류제보", "기타"]

_URL = re.compile(r"https?://\S+")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"\b0\d{1,2}[- .]?\d{3,4}[- .]?\d{4}\b")
_HANDLE = re.compile(r"(?<![\w.])@[\w가-힣._-]{2,}")


def mask_pii(text: str) -> str:
    """본문 속 개인정보(주소·메일·전화·@아이디)를 가린다. 순서가 중요하다(메일을 @아이디보다 먼저)."""
    text = _URL.sub("[링크]", text)
    text = _EMAIL.sub("[메일]", text)
    text = _PHONE.sub("[전화]", text)
    text = _HANDLE.sub("[아이디]", text)
    return text.strip()


def load_texts(path: Path) -> list[str]:
    """댓글·원문을 읽어 본문만 남긴다. 작성자 등 다른 필드는 처음부터 버린다.

    - .txt : 빈 줄을 뺀 한 줄이 한 항목
    - .json: 문자열 목록, 또는 {"text": ...} 객체 목록(author 등은 무시)
    """
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("JSON 입력은 목록이어야 합니다.")
        texts = []
        for i, item in enumerate(data):
            if isinstance(item, str):
                texts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                texts.append(item["text"])
            else:
                raise ValueError(f"{i}번째 항목에 text 가 없습니다.")
    else:
        texts = raw.splitlines()
    return [t for t in (mask_pii(t) for t in texts) if t]


def count_keywords(texts: list[str], keywords: list[str], context: int = 12, max_contexts: int = 3) -> dict:
    """키워드 출현 횟수와 앞뒤 맥락. 세는 일은 모델이 아니라 코드가 한다(정확하고 늘 같다)."""
    result = {}
    for kw in keywords:
        if not kw:
            continue
        total, contexts = 0, []
        for t in texts:
            start = 0
            while (pos := t.find(kw, start)) != -1:
                total += 1
                if len(contexts) < max_contexts:
                    contexts.append(t[max(0, pos - context): pos + len(kw) + context])
                start = pos + len(kw)
        result[kw] = {"count": total, "contexts": contexts}
    return result


def classify(texts: list[str], client: OllamaClient, batch_size: int = 10) -> tuple[list[dict], list[dict]]:
    """항목을 CATEGORIES 중 하나로 나눈다. (분류 결과, 실패 목록)을 돌려준다."""
    results: list[dict] = []
    failures: list[dict] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start: start + batch_size]
        numbered = "\n".join(f"{i}. {t}" for i, t in enumerate(batch))
        prompt = (
            f"아래 댓글을 하나씩 [{', '.join(CATEGORIES)}] 중 하나로 분류하라.\n"
            '형식: {"items": [{"index": 번호, "category": "분류"}]}\n\n' + numbered
        )
        try:
            answer = client.generate_json(prompt)
        except SLMError as e:
            failures += [{"index": start + i, "reason": str(e)} for i in range(len(batch))]
            continue
        got: dict[int, str] = {}
        for item in answer.get("items", []) if isinstance(answer.get("items"), list) else []:
            if isinstance(item, dict) and isinstance(item.get("index"), int) and item["index"] not in got:
                got[item["index"]] = item.get("category")
        for i, text in enumerate(batch):
            cat = got.get(i)
            if cat in CATEGORIES:
                results.append({"index": start + i, "text": text, "category": cat})
            else:
                reason = "응답에 이 항목이 없음" if i not in got else f"알 수 없는 분류: {cat!r}"
                failures.append({"index": start + i, "reason": reason})
    return results, failures


def summarize(text: str, client: OllamaClient, max_bullets: int = 3) -> tuple[list[str], str | None]:
    """핵심 사실 max_bullets 개 요약. (요약, 실패 이유 또는 None)."""
    prompt = (
        f"아래 본문에서 가장 중요한 사실 {max_bullets}개를 한 문장씩 뽑아라. 본문에 없는 내용은 쓰지 마라.\n"
        '형식: {"bullets": ["문장", ...]}\n\n' + text
    )
    try:
        answer = client.generate_json(prompt)
    except SLMError as e:
        return [], str(e)
    bullets = answer.get("bullets")
    if not isinstance(bullets, list) or not bullets or not all(isinstance(b, str) and b.strip() for b in bullets):
        return [], f"요약 형식이 아닙니다: {str(answer)[:80]}"
    if len(bullets) > max_bullets:
        return [b.strip() for b in bullets[:max_bullets]], f"요약이 {len(bullets)}개라 앞의 {max_bullets}개만 씀"
    return [b.strip() for b in bullets], None


def build_clean_data(source: Path, texts: list[str], client: OllamaClient, keywords: list[str], summarize_max: int = 3) -> dict:
    """1단계 결과물. 2단계(클로드)는 이 JSON 만 읽는다."""
    items, failures = classify(texts, client)
    counts = {c: sum(1 for it in items if it["category"] == c) for c in CATEGORIES}
    bullets, summary_failure = summarize("\n".join(texts), client, summarize_max)
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {"file": source.name, "items": len(texts)},
        "model": client.model,
        "classification": {"counts": counts, "items": items, "failures": failures},
        "keywords": count_keywords(texts, keywords),
        "summary": {"bullets": bullets, "failure": summary_failure},
        "metrics": client.metrics.to_dict(),
    }
