"""테스트용 가짜 Ollama 서버. 실제 Ollama 없이 /api/tags, /api/generate 를 흉내 낸다."""
from __future__ import annotations

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeOllama:
    def __init__(self, models=("example-small-model:latest",)):
        self.models = list(models)
        self.requests: list[dict] = []
        # 프롬프트를 받아 모델이 낼 "response" 문자열을 돌려주는 함수. 테스트마다 바꾼다.
        self.answer = self.default_answer
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # 테스트 출력이 시끄럽지 않게
                pass

            def _send(self, body: dict, status=200):
                data = json.dumps(body, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                if self.path == "/api/tags":
                    self._send({"models": [{"name": n} for n in fake.models]})
                else:
                    self._send({"error": "not found"}, 404)

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                fake.requests.append(body)
                self._send({
                    "response": fake.answer(body["prompt"]),
                    "prompt_eval_count": 50,
                    "eval_count": 20,
                    "eval_duration": 100_000_000,  # 0.1초 → 200 토큰/초
                    "total_duration": 150_000_000,
                })

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()

    @staticmethod
    def default_answer(prompt: str) -> str:
        """정상 응답: 분류 요청이면 번호마다 규칙대로, 요약 요청이면 세 줄."""
        if "분류하라" in prompt:
            items = []
            for m in re.finditer(r"^(\d+)\. (.*)$", prompt, re.M):
                text = m.group(2)
                cat = "오류제보" if "끊겨" in text else "기능문의" if ("?" in text or "나요" in text) else "칭찬" if ("재밌" in text or "생각나" in text) else "기타"
                items.append({"index": int(m.group(1)), "category": cat})
            return json.dumps({"items": items}, ensure_ascii=False)
        return json.dumps({"bullets": ["나그네가 쌀 서 말을 지고 고개를 넘었다", "도깨비 셋이 쌀을 나눠 달라고 했다", "도깨비들은 금방망이를 두고 사라졌다"]}, ensure_ascii=False)
