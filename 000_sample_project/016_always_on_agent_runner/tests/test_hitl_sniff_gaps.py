"""test_hitl_sniff_gaps — 승인 게이트의 낱말 판정(sniff)이 흔한 위험 명령을 놓치지 않는지 본다.

2026-11-06 실측 : 위험 명령 15가지 중 8가지가 레드라인 없이 통과했다
(git push --force, rm -r -f, gh repo delete, 메일 보내기, 약관에 동의 등).
게이트의 원칙은 「과잉 포착」이므로, 평범한 작업은 통과시키되 위험 명령은 반드시 잡아야 한다.
"""

import unittest

from agent_runner.hitl_gate import CONTRACT, DB_DESTROY, EXTERNAL_SEND, FORCE_PUSH, HITLGate

# (명령, 반드시 들어 있어야 할 레드라인)
MUST_CATCH = [
    ("git push --force origin main", FORCE_PUSH),
    ("git push --force-with-lease origin main", FORCE_PUSH),
    ("git push origin +main", FORCE_PUSH),
    ("gh repo delete devalive/x", FORCE_PUSH),
    ("rm -r -f /data", DB_DESTROY),
    ("find /data -delete", DB_DESTROY),
    ("DELETE FROM payroll", DB_DESTROY),
    ("메일 보내기", EXTERNAL_SEND),
    ("send the newsletter to all users", EXTERNAL_SEND),
    ("약관에 동의", CONTRACT),
]

# 평범한 작업 : 아무 레드라인도 걸리면 안 된다(과잉 포착이라도 일상 작업까지 막으면 쓸 수 없다)
MUST_PASS = ["이번 주 보고서 요약하기", "3장 원고 조판하기", "git push origin main", "테스트 돌리기"]


class SniffGapTest(unittest.TestCase):
    def test_common_dangerous_commands_are_caught(self):
        for text, redline in MUST_CATCH:
            with self.subTest(text=text):
                self.assertIn(redline, HITLGate.sniff(text))

    def test_everyday_work_is_not_flagged(self):
        for text in MUST_PASS:
            with self.subTest(text=text):
                self.assertEqual(HITLGate.sniff(text), [])


if __name__ == "__main__":
    unittest.main()
