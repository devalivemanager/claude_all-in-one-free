# Handcrafted by Pickle 🥒 for DevAlive Claude Code Pipeline
"""test_task_queue — 비동기 태스크 큐와 백그라운드 워커 시험."""

import asyncio
import os
import tempfile
import unittest

from agent_runner.hitl_gate import HITLGate, EXTERNAL_SEND
from agent_runner.task_queue import (
    STATUS_BLOCKED,
    STATUS_DONE,
    STATUS_FAILED,
    STATUS_QUEUED,
    Task,
    TaskQueue,
)


def run(coro):
    return asyncio.run(coro)


class EchoQueue(TaskQueue):
    """테스트용 큐: echo 핸들러가 payload 를 그대로 돌려준다."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.register_handler("echo", lambda payload: {"echo": payload})


class HandlerRulesTest(unittest.TestCase):
    def setUp(self):
        self.queue = EchoQueue()

    def test_unregistered_handler_rejected(self):
        with self.assertRaises(KeyError):
            self.queue.add("없는_핸들러")

    def test_non_callable_handler_rejected(self):
        with self.assertRaises(TypeError):
            self.queue.register_handler("not_callable", "노호출")


class BasicRunTest(unittest.TestCase):
    def test_tasks_run_to_done_in_order(self):
        q = EchoQueue()
        t1 = q.add("echo", {"n": 1})
        t2 = q.add("echo", {"n": 2})
        run(q.run_until_empty())
        self.assertEqual(t1.status, STATUS_DONE)
        self.assertEqual(t2.status, STATUS_DONE)
        self.assertEqual(t1.result, {"echo": {"n": 1}})
        self.assertEqual(q.summary(), {"done": 2})

    def test_failure_then_retry_then_failed(self):
        q = TaskQueue()
        calls = {"n": 0}

        def flaky(payload):
            calls["n"] += 1
            raise ValueError("못 돌리겠다")

        q.register_handler("flaky", flaky)
        task = q.add("flaky", max_attempts=3)
        run(q.run_until_empty())
        self.assertEqual(task.status, STATUS_FAILED)
        self.assertEqual(task.attempts, 3)
        self.assertEqual(calls["n"], 3)
        self.assertIn("ValueError", task.error)

    def test_async_handler_supported(self):
        q = TaskQueue()

        async def async_ok(payload):
            return "비동기 OK"

        q.register_handler("async_ok", async_ok)
        task = q.add("async_ok")
        run(q.run_until_empty())
        self.assertEqual(task.status, STATUS_DONE)
        self.assertEqual(task.result, "비동기 OK")


class PersistenceTest(unittest.TestCase):
    def test_state_survives_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "tasks.json")
            q1 = EchoQueue(state_path=path)
            q1.add("echo", {"turn": 1})
            q1.add("echo", {"turn": 2})
            self.assertTrue(os.path.exists(path))

            q2 = EchoQueue(state_path=path)  # 새 큐가 이어 받는다
            self.assertEqual(len(q2.all_tasks()), 2)
            run(q2.run_until_empty())
            self.assertEqual(q2.summary(), {"done": 2})
            self.assertEqual(q2.get("echo#2").result, {"echo": {"turn": 2}})


class TaskDataclassTest(unittest.TestCase):
    def test_roundtrip_to_dict(self):
        task = Task(id="echo#1", name="echo", payload={"a": 1})
        raw = task.to_dict()
        again = Task.from_dict(raw)
        self.assertEqual(again.id, "echo#1")
        self.assertEqual(again.payload, {"a": 1})


class HitlIntegrationTest(unittest.TestCase):
    def test_redline_task_blocked_until_approved(self):
        """레드라인 작업은 멈추고, 승인 후에만 실행된다 — HITL 브레이크의 본질."""
        with tempfile.TemporaryDirectory() as tmp:
            gate = HITLGate(state_path=os.path.join(tmp, "approvals.json"))
            q = EchoQueue(state_path=os.path.join(tmp, "tasks.json"), hitl=gate)
            safe = q.add("echo", {"kind": "조판"})
            risky = q.add("echo", {"kind": "메일 발송", "action_type": EXTERNAL_SEND})

            self.assertEqual(safe.status, STATUS_QUEUED)
            self.assertEqual(risky.status, STATUS_BLOCKED)
            self.assertIsNotNone(risky.approval_token)

            run(q.run_until_empty())
            self.assertEqual(safe.status, STATUS_DONE)
            self.assertEqual(risky.status, STATUS_BLOCKED)  # 승인 전엔 절대 안 돈다

            q.approve(risky.approval_token)
            run(q.run_until_empty())
            self.assertEqual(risky.status, STATUS_DONE)

    def test_rejected_task_never_runs(self):
        gate = HITLGate()
        q = EchoQueue(hitl=gate)
        risky = q.add("echo", {"action_type": EXTERNAL_SEND})
        q.reject(risky.approval_token, reason="내용 다시 다듬고 보내자")
        self.assertEqual(risky.status, STATUS_FAILED)
        self.assertIn("반려", risky.error)
        run(q.run_until_empty())
        self.assertEqual(risky.status, STATUS_FAILED)  # 반려된 건 부활하지 않는다

    def test_pending_approvals_lists_blocked_only(self):
        gate = HITLGate()
        q = EchoQueue(hitl=gate)
        q.add("echo", {})
        risky = q.add("echo", {"action_type": EXTERNAL_SEND})
        self.assertEqual([t.id for t in q.pending_approvals()], [risky.id])


if __name__ == "__main__":
    unittest.main()
