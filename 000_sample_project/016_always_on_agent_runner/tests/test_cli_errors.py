"""test_cli_errors — 승인이 거절될 때 CLI 가 파이썬 오류 추적(traceback) 대신 한 줄 안내를 내는지 본다.

2026-11-06 실측 : 틀린 토큰, 이미 쓴 토큰, 반려 후 승인 모두 InvalidToken traceback 과
종료 코드 1 이 나왔다. 고친 뒤 : stderr 에 한국어 안내 한 줄, 종료 코드 2(EXIT_REFUSED).
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class CliRefusalTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.state = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def cli(self, *args):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run(
            [sys.executable, "-m", "agent_runner.cli", "--state-dir", self.state, *args],
            cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8",
        )

    def blocked_token(self):
        out = self.cli("add", "echo", "--payload", '{"action_type": "EXTERNAL_SEND"}')
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)["token"]

    def assert_refused(self, proc):
        self.assertNotIn("Traceback", proc.stderr)
        self.assertNotIn("Traceback", proc.stdout)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, "")
        lines = proc.stderr.strip().splitlines()
        self.assertEqual(len(lines), 1, proc.stderr)
        self.assertIn("승인", lines[0])

    def test_wrong_token(self):
        self.blocked_token()
        self.assert_refused(self.cli("approve", "가짜토큰"))
        self.assert_refused(self.cli("reject", "가짜토큰"))

    def test_reused_token(self):
        token = self.blocked_token()
        ok = self.cli("approve", token)
        self.assertEqual(ok.returncode, 0)
        self.assertEqual(json.loads(ok.stdout)["status"], "queued")  # 정상 경로는 그대로
        self.assert_refused(self.cli("approve", token))

    def test_approve_after_reject(self):
        token = self.blocked_token()
        self.assertEqual(self.cli("reject", token, "--reason", "다시").returncode, 0)
        self.assert_refused(self.cli("approve", token))
        self.assert_refused(self.cli("reject", token))

    def test_unknown_handler(self):
        # 2026-11-08 : 처리기 이름 오타도 KeyError traceback 대신 한 줄 안내여야 한다
        proc = self.cli("add", "ehco")
        self.assertNotIn("Traceback", proc.stderr)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, "")
        lines = proc.stderr.strip().splitlines()
        self.assertEqual(len(lines), 1, proc.stderr)
        self.assertIn("등록되지 않은 처리기", lines[0])
        self.assertIn("echo", lines[0])  # 쓸 수 있는 이름을 함께 알려 준다


if __name__ == "__main__":
    unittest.main()
