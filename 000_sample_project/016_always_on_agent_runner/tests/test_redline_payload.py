"""test_redline_payload — 이름표(action_type) 없는 위험 작업도 큐가 멈춰 세우는지 본다.

2026-11-06 실측 : `add echo --payload '{"kind":"메일 발송"}'`,
`add echo --payload '{"command":"git push --force origin main"}'` 가 승인 없이 done 이 됐다.
큐가 payload 를 HITLGate.sniff 로 살피지 않았기 때문이다.
고친 뒤 규칙 : 이름표가 없으면 payload 전체를 sniff 해 레드라인이 하나라도 걸리면 blocked,
이름표가 있어도 payload 에서 다른 레드라인이 나오면 함께 묶는다.
"""

import asyncio
import json
import os
import tempfile
import unittest

from agent_runner.hitl_gate import DB_DESTROY, EXTERNAL_SEND, FORCE_PUSH, PAYMENT, HITLGate
from agent_runner.task_queue import STATUS_BLOCKED, STATUS_DONE, STATUS_QUEUED, TaskQueue


def run(coro):
    return asyncio.run(coro)


def make_queue(**kw):
    q = TaskQueue(hitl=HITLGate(), **kw)
    q.register_handler("echo", lambda payload: {"echo": payload})
    return q


# (이름표 없는 payload, 반드시 묶여야 할 레드라인)
RISKY_UNLABELED = [
    ({"kind": "메일 발송"}, EXTERNAL_SEND),
    ({"command": "git push --force origin main"}, FORCE_PUSH),
    ({"command": "rm -r -f /data"}, DB_DESTROY),
    ({"sql": "DELETE FROM payroll"}, DB_DESTROY),
    ({"steps": [{"cmd": "rm -rf /tmp/원본"}]}, DB_DESTROY),  # 중첩된 값도 펼쳐 본다
]

PLAIN = [
    {"kind": "3장 원고 조판하기"},
    {"chapter": "58화"},
    {"task": "이번 주 보고서 요약하기", "n": 3},
    {},
]


class UnlabeledRedlineTest(unittest.TestCase):
    def test_risky_unlabeled_payload_is_blocked(self):
        for payload, redline in RISKY_UNLABELED:
            with self.subTest(payload=payload):
                q = make_queue()
                task = q.add("echo", payload)
                run(q.run_until_empty())
                self.assertEqual(task.status, STATUS_BLOCKED)
                self.assertIsNotNone(task.approval_token)
                self.assertIn(redline, task.redlines)
                self.assertIsNone(task.result)

    def test_plain_payload_still_runs_to_done(self):
        for payload in PLAIN:
            with self.subTest(payload=payload):
                q = make_queue()
                task = q.add("echo", payload)
                self.assertEqual(task.status, STATUS_QUEUED)
                run(q.run_until_empty())
                self.assertEqual(task.status, STATUS_DONE)
                self.assertEqual(task.redlines, [])

    def test_approved_unlabeled_task_runs_once_approved(self):
        q = make_queue()
        task = q.add("echo", {"kind": "메일 발송"})
        q.approve(task.approval_token)
        run(q.run_until_empty())
        self.assertEqual(task.status, STATUS_DONE)  # 승인 뒤에는 다시 막지 않는다

    def test_label_and_payload_redlines_are_bundled(self):
        q = make_queue()
        task = q.add("echo", {"action_type": EXTERNAL_SEND,
                              "command": "git push --force origin main"})
        self.assertEqual(task.status, STATUS_BLOCKED)
        self.assertEqual(task.redlines[0], EXTERNAL_SEND)  # 이름표가 맨 앞
        self.assertIn(FORCE_PUSH, task.redlines)
        approval = q.hitl._get(task.approval_token)
        self.assertIn(FORCE_PUSH, approval.description)

    def test_harmless_label_does_not_hide_risky_payload(self):
        q = make_queue()
        task = q.add("echo", {"action_type": "COMPOSE", "sql": "DELETE FROM payroll"})
        self.assertEqual(task.status, STATUS_BLOCKED)
        self.assertIn(DB_DESTROY, task.redlines)  # (payroll 의 pay 로 PAYMENT 도 잡힌다 — 과잉 포착)

    def test_task_loaded_from_old_state_is_checked_before_running(self):
        """고치기 전에 쌓인 tasks.json(토큰 없이 queued)도 실행 직전에 다시 살핀다."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "tasks.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump([{"id": "echo#1", "name": "echo", "status": "queued",
                            "payload": {"command": "git push --force origin main"}}], fh)
            q = make_queue(state_path=path)
            run(q.run_until_empty())
            task = q.get("echo#1")
            self.assertEqual(task.status, STATUS_BLOCKED)
            self.assertIn(FORCE_PUSH, task.redlines)


class HandlerBoundRedlineTest(unittest.TestCase):
    def test_handler_registered_with_redline_always_blocks(self):
        q = TaskQueue(hitl=HITLGate())
        q.register_handler("charge_card", lambda p: "ok", redlines=[PAYMENT])
        task = q.add("charge_card", {"amount": 1000})  # payload 에 낱말이 없어도
        self.assertEqual(task.status, STATUS_BLOCKED)
        self.assertEqual(task.redlines, [PAYMENT])

    def test_handler_redline_must_be_one_of_five(self):
        q = TaskQueue(hitl=HITLGate())
        with self.assertRaises(ValueError):
            q.register_handler("x", lambda p: None, redlines=["조판"])


if __name__ == "__main__":
    unittest.main()
