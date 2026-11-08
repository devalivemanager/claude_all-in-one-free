# Handcrafted by Pickle 🥒 for DevAlive Claude Code Pipeline
"""cli — 올웨이즈온 에이전트 러너 명령줄 진입점.

    python3 -m agent_runner.cli add <핸들러> [--payload '{...}'] [--max-attempts N]
    python3 -m agent_runner.cli run                       # 큐가 빌 때까지 실행
    python3 -m agent_runner.cli list                      # 태스크 목록
    python3 -m agent_runner.cli pending                   # 승인 대기 목록(토큰 포함)
    python3 -m agent_runner.cli approve <토큰>             # 승인(사람 확인 후)
    python3 -m agent_runner.cli reject <토큰> --reason 사유

상태는 --state-dir (기본 ./output/agent_runner_state) 아래 tasks.json,
approvals.json 으로 남는다. 데모 핸들러가 기본 등록돼 있어 등록 없이 바로 돌려 볼 수 있다.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict

from .hitl_gate import HITLGate
from .task_queue import TaskQueue

DEFAULT_STATE_DIR = "output/agent_runner_state"

#: 승인·반려가 거절됐을 때의 종료 코드(틀린 토큰·이미 쓴 토큰·만료·반려 후 승인 등).
EXIT_REFUSED = 2


def make_handlers() -> Dict[str, Any]:
    """기본 데모 핸들러. 실제 업무 핸들러는 클로드 코드가 register_handler 로 붙인다."""
    def echo(payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"echo": payload}

    def compose_chapter(payload: Dict[str, Any]) -> Dict[str, Any]:
        chapter = payload.get("chapter", "무제")
        return {"composed": f"{chapter} 조판 완료", "lines": len(str(chapter)) + 10}

    def collect_stats(payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"collected": payload.get("sources", []), "night_batch": True}

    return {"echo": echo, "compose_chapter": compose_chapter, "collect_stats": collect_stats}


def build_queue(state_dir: str) -> TaskQueue:
    gate = HITLGate(state_path=f"{state_dir}/approvals.json")
    queue = TaskQueue(state_path=f"{state_dir}/tasks.json", hitl=gate)
    for name, handler in make_handlers().items():
        queue.register_handler(name, handler)
    return queue


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="agent_runner", description="올웨이즈온 자율 에이전트 러너")
    parser.add_argument("--state-dir", default=DEFAULT_STATE_DIR, help="상태 파일 디렉터리")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="태스크 등록")
    p_add.add_argument("handler", help="등록된 핸들러 이름")
    p_add.add_argument("--payload", default="{}", help="JSON payload")
    p_add.add_argument("--max-attempts", type=int, default=1)

    sub.add_parser("run", help="큐가 빌 때까지 워커 실행")
    sub.add_parser("list", help="태스크 목록")
    sub.add_parser("pending", help="승인 대기 목록")

    p_appr = sub.add_parser("approve", help="승인 토큰 승인")
    p_appr.add_argument("token")
    p_rej = sub.add_parser("reject", help="승인 토큰 반려")
    p_rej.add_argument("token")
    p_rej.add_argument("--reason", default="")

    args = parser.parse_args(argv)
    queue = build_queue(args.state_dir)

    if args.cmd == "add":
        try:
            payload = json.loads(args.payload)
        except json.JSONDecodeError as exc:
            print(f"payload 는 JSON 이어야 한다: {exc}", file=sys.stderr)
            return 2
        try:
            task = queue.add(args.handler, payload=payload, max_attempts=args.max_attempts)
        except KeyError:  # 오타 난 처리기 이름도 traceback 없이 한 줄로 알린다
            names = ", ".join(sorted(make_handlers()))
            print(f"등록되지 않은 처리기: {args.handler} (쓸 수 있는 처리기 : {names})", file=sys.stderr)
            return 2
        print(json.dumps({"id": task.id, "status": task.status, "token": task.approval_token},
                         ensure_ascii=False))
        return 0

    if args.cmd == "run":
        import asyncio
        summary = asyncio.run(queue.run_until_empty())
        pending = queue.pending_approvals()
        print(json.dumps({"summary": summary,
                          "blocked": [t.id for t in pending],
                          "note": "승인 대기가 있으면 pending → approve(사람 확인) → run 으로 이어서"
                          }, ensure_ascii=False))
        return 0

    if args.cmd == "list":
        rows = [{"id": t.id, "status": t.status, "attempts": t.attempts,
                 "error": t.error} for t in queue.all_tasks()]
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "pending":
        rows = [{"task": t.id, "token": t.approval_token,
                 "action_type": t.payload.get("action_type") or (t.redlines[0] if t.redlines else None),
                 "redlines": t.redlines} for t in queue.pending_approvals()]
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    if args.cmd in ("approve", "reject"):
        verb = "승인" if args.cmd == "approve" else "반려"
        try:
            if args.cmd == "approve":
                task = queue.approve(args.token)
            else:
                task = queue.reject(args.token, reason=args.reason)
        except LookupError as exc:  # InvalidToken 포함. 거절은 정상 동작이라 traceback 없이 한 줄로 알린다
            detail = exc.args[0] if exc.args else args.token
            print(f"{verb} 거절: {detail} (pending 으로 승인 대기 토큰을 확인하라)", file=sys.stderr)
            return EXIT_REFUSED
        print(json.dumps({"id": task.id, "status": task.status}, ensure_ascii=False))
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
