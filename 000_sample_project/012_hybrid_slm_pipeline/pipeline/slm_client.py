"""로컬 Ollama 서버에 붙는 작은 클라이언트(표준 라이브러리만 사용).

- 서버·모델이 없으면 무엇을 실행해야 하는지 한국어로 알려 준다.
- 응답은 JSON 으로만 받는다(format="json"). JSON 이 아니면 실패로 본다.
- 속도는 추정하지 않는다. Ollama 가 돌려주는 실제 토큰 수·시간(eval_count, eval_duration)을 모은다.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field

DEFAULT_URL = "http://localhost:11434"
# 기본 모델은 두지 않는다. 무료 + 상업 이용이 확인된(중국 계열 제외) 모델을 골라 SLM_MODEL 로 정한다.
# 고르는 기준 : README 「로컬 모델 고르기」, 999_document/01_무료·상업이용_도구
DEFAULT_MODEL = None

KOREAN_ONLY = "반드시 한국어로만 간결하게 답한다. 추측하지 말고 주어진 본문에 있는 내용만 쓴다. 출력은 JSON 하나뿐이다."


class SLMError(Exception):
    """소형 모델 호출이나 응답에 문제가 있을 때."""


class OllamaUnavailable(SLMError):
    """Ollama 서버나 모델을 쓸 수 없을 때. 메시지에 해결 방법을 담는다."""


@dataclass
class Metrics:
    calls: int = 0
    prompt_tokens: int = 0
    generated_tokens: int = 0
    generate_seconds: float = 0.0  # 생성에 걸린 시간(eval_duration 합)
    total_seconds: float = 0.0  # 요청 전체 시간(total_duration 합)

    def add(self, resp: dict) -> None:
        self.calls += 1
        self.prompt_tokens += int(resp.get("prompt_eval_count") or 0)
        self.generated_tokens += int(resp.get("eval_count") or 0)
        self.generate_seconds += (resp.get("eval_duration") or 0) / 1e9
        self.total_seconds += (resp.get("total_duration") or 0) / 1e9

    def to_dict(self) -> dict:
        tps = self.generated_tokens / self.generate_seconds if self.generate_seconds > 0 else None
        return {
            "calls": self.calls,
            "prompt_tokens": self.prompt_tokens,
            "generated_tokens": self.generated_tokens,
            "generate_seconds": round(self.generate_seconds, 3),
            "total_seconds": round(self.total_seconds, 3),
            "measured_tokens_per_second": round(tps, 1) if tps is not None else None,
        }


@dataclass
class OllamaClient:
    base_url: str = field(default_factory=lambda: os.environ.get("OLLAMA_URL", DEFAULT_URL))
    model: str | None = field(default_factory=lambda: os.environ.get("SLM_MODEL") or DEFAULT_MODEL)
    timeout: float = 120.0
    metrics: Metrics = field(default_factory=Metrics)

    def _request(self, path: str, payload: dict | None = None, timeout: float | None = None) -> dict:
        url = self.base_url.rstrip("/") + path
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as res:
                return json.loads(res.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise SLMError(f"Ollama 가 {e.code} 로 응답했습니다: {e.read().decode('utf-8', 'replace')[:200]}") from e
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
            raise OllamaUnavailable(
                f"Ollama 서버({self.base_url})에 연결할 수 없습니다. PC 에서 `ollama serve` 를 먼저 실행하세요. ({e})"
            ) from e

    def check_status(self) -> list[str]:
        """서버가 살아 있고 모델이 설치돼 있는지 확인한다. 설치된 모델 이름 목록을 돌려준다."""
        if not self.model:
            raise OllamaUnavailable(
                "쓸 모델이 정해지지 않았습니다. 무료 + 상업 이용이 확인된 모델을 골라 환경변수 SLM_MODEL 에 넣으세요"
                "(README 「로컬 모델 고르기」). 이름은 `ollama list` 로 확인합니다."
            )
        tags = self._request("/api/tags", timeout=3)
        names = [m.get("name", "") for m in tags.get("models", [])]
        if not any(n == self.model or n.split(":")[0] == self.model for n in names):
            raise OllamaUnavailable(
                f"모델 '{self.model}' 이 설치돼 있지 않습니다. `ollama pull {self.model}` 로 받거나, "
                f"`ollama list` 로 이름을 확인해 환경변수 SLM_MODEL 에 넣으세요. (설치된 모델: {', '.join(names) or '없음'})"
            )
        return names

    def generate_json(self, prompt: str, system: str = KOREAN_ONLY) -> dict:
        """프롬프트를 보내고 JSON 객체를 돌려받는다. JSON 이 아니면 SLMError."""
        resp = self._request(
            "/api/generate",
            {
                "model": self.model,
                "system": system,
                "prompt": prompt,
                "format": "json",
                "stream": False,
                "options": {"temperature": 0},
            },
        )
        self.metrics.add(resp)
        text = resp.get("response", "")
        try:
            value = json.loads(text)
        except json.JSONDecodeError as e:
            raise SLMError(f"모델 응답이 JSON 이 아닙니다: {text[:120]!r}") from e
        if not isinstance(value, dict):
            raise SLMError(f"모델 응답이 JSON 객체가 아닙니다: {type(value).__name__}")
        return value
