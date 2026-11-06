"""원클릭 러너: 1단계(로컬 소형 모델 전처리) → 2단계(클로드 코드 최종 작성).

사용:
  python -m pipeline.run_hybrid_pipeline --input data/samples/comments_sample.json --skill blog-writer --keywords 쌀,도깨비
  --stage2 auto      : `claude` 명령이 있으면 헤드리스(claude -p)로 작성, 없으면 지시문 파일만 만든다(기본)
  --stage2 headless  : 반드시 claude -p 로 작성(없으면 오류)
  --stage2 manual    : 지시문 파일만 만든다(클로드 코드 세션에 직접 넘긴다)

종료 코드: 0 정상, 1 실행 오류(서버 없음·작성 실패 등), 2 잘못된 인자.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

from .preprocess import build_clean_data, load_texts
from .slm_client import OllamaClient, SLMError

ROOT = Path(__file__).resolve().parent.parent
SKILLS = {"blog-writer": "blog", "scenario-writer": "scenario", "weekly-report": "reports"}


def skill_text(name: str) -> str:
    path = ROOT / ".claude" / "skills" / name / "SKILL.md"
    if not path.exists():
        raise FileNotFoundError(f"스킬이 없습니다: {path}")
    return path.read_text(encoding="utf-8")


def build_instruction(skill: str, clean: dict) -> str:
    """2단계 지시문. 스킬 규격 + 1단계 JSON 만 넘긴다(원문 전체를 넘기지 않아 토큰을 아낀다)."""
    return "\n".join([
        f"아래 스킬 규격({skill})을 지켜 결과물을 마크다운으로만 작성하라.",
        "자료는 아래 clean_data.json 뿐이다. JSON 에 없는 사실은 지어내지 말고, 필요한 곳에는 [확인 필요] 라고 적어라.",
        "failures 에 있는 항목은 분류되지 않은 것이니 수치에 넣지 마라.",
        "",
        "--- 스킬 규격 ---",
        skill_text(skill),
        "--- clean_data.json ---",
        json.dumps(clean, ensure_ascii=False, indent=2),
    ])


# 2단계 한 번에 쓸 수 있는 비용 상한(달러). 글 한 편은 보통 0.1달러 안팎이다.
STAGE2_MAX_BUDGET_USD = "1.00"


def run_claude_headless(instruction: str, timeout: int = 600) -> str:
    """claude -p 로 2단계를 실행한다(사람 없이 한 번 답하고 끝나는 모드). 지시문은 표준 입력으로 넘긴다.

    - 글쓰기에는 도구가 필요 없으므로 --tools "" 로 모두 끈다. 도구 설명이 빠져 입력이 크게 줄어든다
      (실측 : 같은 짧은 지시에 $0.0897 → $0.0186).
    - 종료 코드만 믿지 않고 --output-format json 의 subtype 과 빈 답을 검사한다(19장).
    """
    result = subprocess.run(
        ["claude", "-p", "표준 입력으로 받은 지시를 그대로 수행하라.",
         "--tools", "", "--output-format", "json", "--max-budget-usd", STAGE2_MAX_BUDGET_USD],
        input=instruction, capture_output=True, text=True, encoding="utf-8", timeout=timeout,
    )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"claude -p 실패(종료 코드 {result.returncode}): {result.stderr.strip()[:300]}") from None
    if data.get("subtype") != "success" or data.get("is_error"):
        raise RuntimeError(f"claude -p 실패({data.get('subtype')}, 종료 코드 {result.returncode})")
    text = (data.get("result") or "").strip()
    if not text:
        raise RuntimeError("claude -p 가 성공으로 끝났지만 쓴 글이 비어 있습니다")
    return text + "\n"


def main(argv: list[str] | None = None, client: OllamaClient | None = None, claude_runner=None, which=shutil.which,
         out_root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description="로컬 소형 모델 전처리 + 클로드 코드 작성 파이프라인")
    parser.add_argument("--input", required=True, help="댓글(.json/.txt) 또는 원문(.txt)")
    parser.add_argument("--skill", required=True, choices=sorted(SKILLS))
    parser.add_argument("--keywords", default="", help="쉼표로 구분한 집계 키워드")
    parser.add_argument("--stage2", default="auto", choices=["auto", "headless", "manual"])
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0

    out_root = out_root or ROOT
    client = client or OllamaClient()
    src = Path(args.input)
    try:
        texts = load_texts(src)
        if not texts:
            print("오류: 입력에 처리할 내용이 없습니다.", file=sys.stderr)
            return 1
        client.check_status()
        clean = build_clean_data(src, texts, client, [k.strip() for k in args.keywords.split(",") if k.strip()])
    except (SLMError, ValueError, OSError) as e:
        print(f"오류: {e}", file=sys.stderr)
        return 1

    processed = out_root / "data" / "processed" / "clean_data.json"
    processed.parent.mkdir(parents=True, exist_ok=True)
    processed.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")

    instruction = build_instruction(args.skill, clean)
    stamp = date.today().isoformat()
    mode = args.stage2
    if mode == "auto":
        mode = "headless" if which("claude") else "manual"
    if mode == "headless" and not which("claude"):
        print("오류: claude 명령이 없습니다. --stage2 manual 로 지시문 파일을 만들어 클로드 코드에 넘기세요.", file=sys.stderr)
        return 1

    if mode == "headless":
        try:
            body = (claude_runner or run_claude_headless)(instruction)
        except (RuntimeError, subprocess.TimeoutExpired, OSError) as e:
            print(f"오류: 2단계 작성 실패 - {e}", file=sys.stderr)
            return 1
        result_path = out_root / "output" / SKILLS[args.skill] / f"{stamp}_{args.skill}.md"
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(body, encoding="utf-8")
        stage2 = ("클로드 코드(claude -p)", str(result_path.relative_to(out_root)))
    else:
        result_path = out_root / "output" / "prompts" / f"{stamp}_{args.skill}_instruction.md"
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(instruction, encoding="utf-8")
        stage2 = ("사람이 클로드 코드에 전달", str(result_path.relative_to(out_root)))

    m = clean["metrics"]
    fails = len(clean["classification"]["failures"])
    speed = f"{m['measured_tokens_per_second']} 토큰/초(실측)" if m["measured_tokens_per_second"] else "측정값 없음"
    print("| 단계 | 수행 | 실측 | 결과물 |")
    print("|---|---|---|---|")
    print(f"| 1 전처리 | 로컬 {clean['model']} | 호출 {m['calls']}회, 생성 {m['generated_tokens']} 토큰, {speed}, 분류 실패 {fails}건 | {processed.relative_to(out_root)} |")
    print(f"| 2 작성 | {stage2[0]} | - | {stage2[1]} |")
    if clean["summary"]["failure"]:
        print(f"경고: 요약 - {clean['summary']['failure']}", file=sys.stderr)
    if fails:
        print(f"경고: 분류하지 못한 항목 {fails}건(clean_data.json 의 failures 참고)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
