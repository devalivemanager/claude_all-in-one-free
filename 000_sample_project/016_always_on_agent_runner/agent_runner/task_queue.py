# Handcrafted by Pickle 🥒 for DevAlive Claude Code Pipeline
"""task_queue — 비동기 태스크 큐와 백그라운드 워커.

사람 없이 돌아가는 배치 작업의 심장이다. 설계 원칙은 세 가지.

1. 자율: run_until_empty() 한 번이면 큐가 빌 때까지 워커가 알아서 돈다.
2. 끈기: 실패한 태스크는 max_attempts 만큼만 재시도하고, 소진되면 failed 로 남겨
   사람에게 보고한다(무한 재시도 방지).
3. 순종: 레드라인 작업(HITLGate 가 잡아낸 것)은 실행하지 않고 blocked 로 멈추고
   승인 토큰을 발급한다. approve(token) 로 풀린 뒤에만 실행된다.

상태는 tasks.json 으로 영속화해 세션이 끊겨도 「어디까지 했는지」가 남는다.
외부 의존 없음: 파이썬 표준 라이브러리(asyncio, json, dataclasses)만 쓴다.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

# 태스크가 가질 수 있는 상태. blocked 는 「승인을 기다리며 멈춰 있는 것」으로,
# 실패가 아니라 게이트가 정상 작동한 상태다.
STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_DONE = "done"
STATUS_FAILED = "failed"
STATUS_BLOCKED = "blocked"

#: 태스크가 다루는 외부 세계의 위험 종류(hitl_gate.REDLINES 의 키).
#: payload 또는 태스크 등록 시 action_type 으로 명시하면 그것을 우선 본다.
ACTION_TYPE_KEY = "action_type"


@dataclass
class Task:
    """큐에 쌓이는 작업 한 건."""

    id: str
    name: str
    payload: Dict[str, Any] = field(default_factory=dict)
    status: str = STATUS_QUEUED
    attempts: int = 0
    max_attempts: int = 1
    result: Optional[Any] = None
    error: Optional[str] = None
    approval_token: Optional[str] = None  # blocked 상태일 때 발급된 승인 토큰
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def touch(self) -> None:
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Task":
        return cls(**raw)


class TaskQueue:
    """핸들러 이름으로 작업을 등록받아, 백그라운드 워커로 끝까지 돌리는 큐.

    Parameters
    ----------
    state_path:
        주어지면 큐 상태를 그 JSON 파일에 저장하고, 생성 시 파일이 있으면 이어 받는다.
    hitl:
        HITLGate. 주어지면 레드라인 작업을 blocked 로 잡아 승인 토큰을 붙인다.
    """

    def __init__(self, state_path: Optional[str] = None, hitl=None) -> None:
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {}
        self._tasks: Dict[str, Task] = {}
        self._counter = 0
        self.state_path = state_path
        self.hitl = hitl
        if state_path and os.path.exists(state_path):
            self.load(state_path)

    # ------------------------------------------------------------------ 등록
    def register_handler(self, name: str, handler: Callable[[Dict[str, Any]], Any]) -> None:
        """태스크 종류 하나를 실행부(핸들러)와 묶는다. 코루틴 함수도 받는다."""
        if not callable(handler):
            raise TypeError(f"핸들러는 호출 가능해야 한다: {name!r}")
        self._handlers[name] = handler

    def add(self, name: str, payload: Optional[Dict[str, Any]] = None,
            max_attempts: int = 1, action_type: Optional[str] = None) -> Task:
        """작업을 큐에 쌓는다. action_type 이 레드라인이면 즉시 blocked 로 만든다."""
        if name not in self._handlers:
            raise KeyError(f"등록되지 않은 핸들러: {name!r}")
        self._counter += 1
        task = Task(
            id=f"{name}#{self._counter}",
            name=name,
            payload=dict(payload or {}),
            max_attempts=max(1, int(max_attempts)),
        )
        resolved_type = action_type or task.payload.get(ACTION_TYPE_KEY)
        if self.hitl is not None and resolved_type and self.hitl.is_redline(resolved_type):
            approval = self.hitl.request(resolved_type, description=task.id)
            task.approval_token = approval.token
            task.status = STATUS_BLOCKED
        self._tasks[task.id] = task
        self.save()
        return task

    # ------------------------------------------------------------------ 조회
    def get(self, task_id: str) -> Task:
        return self._tasks[task_id]

    def all_tasks(self) -> List[Task]:
        return list(self._tasks.values())

    def pending_approvals(self) -> List[Task]:
        return [t for t in self._tasks.values() if t.status == STATUS_BLOCKED]

    def summary(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for t in self._tasks.values():
            out[t.status] = out.get(t.status, 0) + 1
        return out

    # ------------------------------------------------------------------ 실행
    async def run_until_empty(self) -> Dict[str, int]:
        """큐가 빌 때까지 워커를 돌린다. blocked 태스크는 건드리지 않고 남긴다."""
        while True:
            runnable = [
                t for t in self._tasks.values()
                if t.status in (STATUS_QUEUED, STATUS_RUNNING)
            ]
            if not runnable:
                break
            await asyncio.gather(*[self._run_one(t) for t in runnable])
        self.save()
        return self.summary()

    async def _run_one(self, task: Task) -> None:
        # 승인을 한 번도 받지 못한 레드라인 작업만 다시 잡는다.
        # approve 로 풀려 나온 태스크(approval_token 이 있고 승인 완료)는 실행한다.
        if (self.hitl is not None and task.approval_token is None
                and self._is_redline_task(task)):
            approval = self.hitl.request(
                self._action_type(task), description=task.id
            )
            task.approval_token = approval.token
            task.status = STATUS_BLOCKED
            task.touch()
            return
        handler = self._handlers[task.name]
        task.status = STATUS_RUNNING
        task.attempts += 1
        task.touch()
        try:
            result = handler(task.payload)
            if asyncio.iscoroutine(result):
                result = await result
            task.result = result
            task.error = None
            task.status = STATUS_DONE
        except Exception as exc:  # 실패는 기록하고 재시도 상한에서 멈춘다
            task.error = f"{type(exc).__name__}: {exc}"
            if task.attempts >= task.max_attempts:
                task.status = STATUS_FAILED
            else:
                task.status = STATUS_QUEUED
        task.touch()

    def _action_type(self, task: Task) -> Optional[str]:
        return task.payload.get(ACTION_TYPE_KEY)

    def _is_redline_task(self, task: Task) -> bool:
        action = self._action_type(task)
        return bool(action and self.hitl.is_redline(action))

    # ------------------------------------------------------------------ 승인 연동
    def approve(self, token: str) -> Task:
        """승인 토큰으로 blocked 태스크를 풀어 큐로 되돌린다."""
        if self.hitl is None:
            raise RuntimeError("HITL 게이트가 없는 큐에는 승인이 필요 없다")
        self.hitl.approve(token)
        for t in self._tasks.values():
            if t.approval_token == token and t.status == STATUS_BLOCKED:
                t.status = STATUS_QUEUED
                t.touch()
                self.save()
                return t
        raise LookupError(f"토큰에 묶인 blocked 태스크가 없다: {token}")

    def reject(self, token: str, reason: str = "") -> Task:
        """승인 토큰으로 blocked 태스크를 반려해 영구 실패 처리한다."""
        if self.hitl is None:
            raise RuntimeError("HITL 게이트가 없는 큐에는 반려가 필요 없다")
        self.hitl.reject(token, reason=reason)
        for t in self._tasks.values():
            if t.approval_token == token and t.status == STATUS_BLOCKED:
                t.status = STATUS_FAILED
                t.error = f"반려됨: {reason}" if reason else "반려됨"
                t.touch()
                self.save()
                return t
        raise LookupError(f"토큰에 묶인 blocked 태스크가 없다: {token}")

    # ------------------------------------------------------------------ 영속화
    def save(self) -> None:
        if not self.state_path:
            return
        os.makedirs(os.path.dirname(self.state_path) or ".", exist_ok=True)
        tmp = self.state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump([t.to_dict() for t in self._tasks.values()], fh,
                      ensure_ascii=False, indent=2)
        os.replace(tmp, self.state_path)

    def load(self, state_path: str) -> None:
        with open(state_path, encoding="utf-8") as fh:
            raw = json.load(fh)
        self._tasks = {d["id"]: Task.from_dict(d) for d in raw}
        for t in self._tasks.values():
            try:
                self._counter = max(self._counter, int(t.id.rsplit("#", 1)[1]))
            except (IndexError, ValueError):
                pass
