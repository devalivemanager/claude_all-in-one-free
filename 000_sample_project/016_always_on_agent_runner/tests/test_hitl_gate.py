# Handcrafted by Pickle 🥒 for DevAlive Claude Code Pipeline
"""test_hitl_gate — 승인 브레이크 시험. 사람의 말이 아니라 장치로 막는지 검증한다."""

import os
import tempfile
import unittest

from agent_runner.hitl_gate import (
    CONTRACT,
    DB_DESTROY,
    EXTERNAL_SEND,
    FORCE_PUSH,
    PAYMENT,
    REDLINES,
    HITLGate,
    InvalidToken,
)


class ClassificationTest(unittest.TestCase):
    def test_five_redlines_are_recognized(self):
        for action in (PAYMENT, EXTERNAL_SEND, FORCE_PUSH, DB_DESTROY, CONTRACT):
            self.assertTrue(HITLGate.is_redline(action), action)
            self.assertEqual(HITLGate.classify(action), action)

    def test_non_redline_actions_pass_freely(self):
        self.assertFalse(HITLGate.is_redline("compose_chapter"))
        self.assertFalse(HITLGate.is_redline(""))
        self.assertIsNone(HITLGate.classify("조판"))

    def test_lowercase_and_whitespace_normalized(self):
        self.assertEqual(HITLGate.classify("  payment  "), PAYMENT)

    def test_redline_table_has_exactly_five_kinds(self):
        self.assertEqual(len(REDLINES), 5)
        self.assertEqual(set(REDLINES), {PAYMENT, EXTERNAL_SEND, FORCE_PUSH, DB_DESTROY, CONTRACT})

    def test_sniff_suspects_keywords(self):
        self.assertIn(EXTERNAL_SEND, HITLGate.sniff("이 메일을 실제로 발송한다"))
        self.assertIn(DB_DESTROY, HITLGate.sniff("drop table users"))
        self.assertEqual(HITLGate.sniff("소설 조판"), [])


class RequestApproveTest(unittest.TestCase):
    def setUp(self):
        self.gate = HITLGate()

    def test_request_issues_pending_with_token(self):
        approval = self.gate.request(PAYMENT, description="구독 결제")
        self.assertEqual(approval.status, "pending")
        self.assertTrue(approval.token)
        self.assertEqual(self.gate.status(approval.token), "pending")
        self.assertEqual(len(self.gate.pending()), 1)

    def test_request_rejects_non_redline(self):
        with self.assertRaises(ValueError):
            self.gate.request("조판", description="위험하지 않은 일")

    def test_approve_with_token_passes_once(self):
        approval = self.gate.request(EXTERNAL_SEND)
        self.gate.approve(approval.token)
        self.assertEqual(self.gate.status(approval.token), "approved")
        with self.assertRaises(InvalidToken):  # 승인은 두 번 못 쓴다
            self.gate.approve(approval.token)

    def test_wrong_token_never_passes(self):
        self.gate.request(PAYMENT)
        with self.assertRaises(InvalidToken):
            self.gate.approve("가짜토큰")

    def test_reject_then_approve_fails(self):
        approval = self.gate.request(DB_DESTROY)
        self.gate.reject(approval.token, reason="원본은 남긴다")
        self.assertEqual(self.gate.status(approval.token), "rejected")
        with self.assertRaises(InvalidToken):
            self.gate.approve(approval.token)


class ExpiryTest(unittest.TestCase):
    def test_expired_approval_cannot_pass(self):
        gate = HITLGate(ttl_seconds=100)
        approval = gate.request(CONTRACT)
        # 시계를 101초 뒤로 돌린 셈 친다
        self.assertTrue(approval.is_expired(now=approval.created_at + 101))
        # 만료 판정은 approve 내부에서 now 로 하므로, expires_at 을 과거로 당겨 시험한다
        approval.expires_at = approval.created_at - 1
        # 만료 판정은 approve 내부에서 now 로 하므로, expires_at 을 과거로 당겨 시험한다
        approval.expires_at = approval.created_at - 1
        with self.assertRaises(InvalidToken):
            gate.approve(approval.token)
        self.assertEqual(approval.status, "expired")

    def test_zero_ttl_means_never_expires(self):
        gate = HITLGate(ttl_seconds=0)
        approval = gate.request(FORCE_PUSH)
        self.assertFalse(approval.is_expired())
        gate.approve(approval.token)
        self.assertEqual(approval.status, "approved")


class PersistenceTest(unittest.TestCase):
    def test_approval_ledger_survives_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "approvals.json")
            g1 = HITLGate(state_path=path)
            a = g1.request(PAYMENT, description="포인트 충전")
            self.assertTrue(os.path.exists(path))

            g2 = HITLGate(state_path=path)
            self.assertEqual(g2.status(a.token), "pending")
            g2.approve(a.token)
            self.assertEqual(g2.status(a.token), "approved")

    def test_atomic_write_leaves_no_tmp(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "approvals.json")
            gate = HITLGate(state_path=path)
            gate.request(EXTERNAL_SEND)
            self.assertFalse(os.path.exists(path + ".tmp"))


if __name__ == "__main__":
    unittest.main()
