# Handcrafted by Pickle 🥒 for DevAlive Claude Code Pipeline
"""hitl_gate — HITL(Human-In-The-Loop) 승인 브레이크.

자율 에이전트의 방패다. 원본 아키텍처(OpenAI Dots · Meta Muse 공통 기둥 ④)의
「위험 작업 전 스마트폰 팝업 승인」을 데브얼라이브 환경으로 옮긴 것이다.

동작은 단순하다.
1. 레드라인 5종에 걸리는 작업인지 classify 한다.
2. 걸리면 승인 요청을 만들고 1회성 토큰을 발행한다(만료 시간 있음).
3. 사람이 approve(token) 해야만 통과하고, reject(token) 하면 영구 반려다.
   잘못된 토큰·만료된 토큰은 절대 통과시키지 않는다 — 사람의 말이 아니라
   장치로 막는 것이 이 저장소의 규칙이다.

상태는 approvals.json 으로 영속화한다.
"""

from __future__ import annotations

import json
import os
import secrets
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# 레드라인 5종 — 사람 승인 없이는 절대 실행하지 않는 위험 종류
# ---------------------------------------------------------------------------
PAYMENT = "PAYMENT"            # 결제·금전 지출 전부
EXTERNAL_SEND = "EXTERNAL_SEND"  # 외부 이메일 실제 발송, SNS 게시
FORCE_PUSH = "FORCE_PUSH"      # main 브랜치 강제 푸시, 저장소 삭제·권한 변경
DB_DESTROY = "DB_DESTROY"      # DB·원본 파일의 영구 삭제
CONTRACT = "CONTRACT"          # 외부 계약·약관 동의, 유료 구독 확정

#: 레드라인 5종 모음(키 = action_type).
REDLINES: Dict[str, str] = {
    PAYMENT: "결제·금전 지출",
    EXTERNAL_SEND: "외부 발송·게시",
    FORCE_PUSH: "메인 브랜치 강제 푸시·저장소 구조 변경",
    DB_DESTROY: "데이터 영구 삭제",
    CONTRACT: "외부 계약·약관 동의",
}

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_EXPIRED = "expired"

# action_type 이 안 붙은 텍스트에서 레드라인을 의심할 때 보는 표식.
# (과잉 포착이 원칙이다 — 애매하면 승인을 물어본다.)
KEYWORD_HINTS: Dict[str, tuple] = {
    PAYMENT: ("결제", "결제금", "구매", "지출", "결제 확인", "충전", "구독 결제", "pay", "checkout", "charge"),
    EXTERNAL_SEND: ("발송", "메일 전송", "이메일 전송", "게시", "전송", "send_mail", "send email", "sns post"),
    FORCE_PUSH: ("강제 푸시", "force push", "force-push", "브랜치 삭제", "delete branch", "push -f", "main 푸시"),
    DB_DESTROY: ("영구 삭제", "드롭", "truncate", "drop table", "rm -rf", "데이터 삭제", "delete all"),
    CONTRACT: ("계약", "약관 동의", "동의서", "서명", "구독 확정", "accept terms", "sign contract"),
}


class InvalidToken(KeyError):
    """발급된 적 없는 토큰으로 승인·반려하려 할 때."""


@dataclass
class Approval:
    """승인 요청 한 건. token 은 1회성 만료제 승인 열쇠다."""

    token: str
    action_type: str
    description: str = ""
    status: str = STATUS_PENDING
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    decided_at: Optional[float] = None
    decided_by: Optional[str] = None
    reason: str = ""

    def is_expired(self, now: Optional[float] = None) -> bool:
        if self.expires_at <= 0:
            return False
        return (now if now is not None else time.time()) > self.expires_at

    def to_dict(self) -> Dict:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, raw: Dict) -> "Approval":
        return cls(**raw)


class HITLGate:
    """위험 작업을 잡아내고, 사람 승인 없이는 통과시키지 않는 게이트.

    Parameters
    ----------
    state_path:
        승인 장부(approvals.json) 경로. 주어지면 영속화하고 생성 시 이어 받는다.
    ttl_seconds:
        승인 요청 유효 시간. 0 이하면 만료 없음. 기본 12시간.
    """

    def __init__(self, state_path: Optional[str] = None, ttl_seconds: float = 12 * 3600) -> None:
        self._approvals: Dict[str, Approval] = {}
        self.state_path = state_path
        self.ttl_seconds = float(ttl_seconds)
        if state_path and os.path.exists(state_path):
            self.load(state_path)

    # ------------------------------------------------------------------ 판정
    @staticmethod
    def classify(action_type: str) -> Optional[str]:
        """명시된 action_type 이 레드라인이면 그 키를, 아니면 None 을 돌려준다."""
        action = (action_type or "").strip().upper()
        return action if action in REDLINES else None

    @staticmethod
    def sniff(text: str) -> List[str]:
        """자유 텍스트에서 레드라인 후보를 뽑는다(과잉 포착). 레드라인 5종 안에서만 판정한다."""
        lowered = (text or "").lower()
        hits = []
        for action, words in KEYWORD_HINTS.items():
            if any(w in lowered for w in words):
                hits.append(action)
        return hits

    @staticmethod
    def is_redline(action_type: str) -> bool:
        return HITLGate.classify(action_type) is not None

    # ------------------------------------------------------------------ 요청
    def request(self, action_type: str, description: str = "") -> Approval:
        """승인 요청을 만들고 1회성 토큰을 발행한다. 이미 통과·반려된 같은 종류 요청도
        새 요청으로 다시 물어본다(위험 작업은 매번 확인한다)."""
        resolved = self.classify(action_type)
        if resolved is None:
            raise ValueError(f"레드라인이 아닌 작업에는 승인이 필요 없다: {action_type!r}")
        token = secrets.token_hex(8)
        approval = Approval(
            token=token,
            action_type=resolved,
            description=description,
            expires_at=time.time() + self.ttl_seconds if self.ttl_seconds > 0 else 0.0,
        )
        self._approvals[token] = approval
        self.save()
        return approval

    def _get(self, token: str) -> Approval:
        approval = self._approvals.get(token)
        if approval is None:
            raise InvalidToken(token)
        return approval

    # ------------------------------------------------------------------ 결정
    def approve(self, token: str, approver: str = "human") -> Approval:
        """승인. 만료·이미 결정된 요청은 거절한다."""
        approval = self._get(token)
        now = time.time()
        if approval.status == STATUS_PENDING and approval.is_expired(now):
            approval.status = STATUS_EXPIRED
            approval.decided_at = now
            approval.reason = "승인 유효 시간이 지났다"
            self.save()
            raise InvalidToken(f"만료된 승인 요청: {token}")
        if approval.status != STATUS_PENDING:
            raise InvalidToken(f"이미 결정된 승인 요청({approval.status}): {token}")
        approval.status = STATUS_APPROVED
        approval.decided_at = now
        approval.decided_by = approver
        self.save()
        return approval

    def reject(self, token: str, reason: str = "", approver: str = "human") -> Approval:
        """반려. pending 인 요청만 반려할 수 있다."""
        approval = self._get(token)
        if approval.status != STATUS_PENDING:
            raise InvalidToken(f"이미 결정된 승인 요청({approval.status}): {token}")
        approval.status = STATUS_REJECTED
        approval.decided_at = time.time()
        approval.decided_by = approver
        approval.reason = reason
        self.save()
        return approval

    # ------------------------------------------------------------------ 조회
    def status(self, token: str) -> str:
        return self._get(token).status

    def pending(self) -> List[Approval]:
        return [a for a in self._approvals.values() if a.status == STATUS_PENDING]

    def all(self) -> List[Approval]:
        return list(self._approvals.values())

    # ------------------------------------------------------------------ 영속화
    def save(self) -> None:
        if not self.state_path:
            return
        os.makedirs(os.path.dirname(self.state_path) or ".", exist_ok=True)
        tmp = self.state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump([a.to_dict() for a in self._approvals.values()], fh,
                      ensure_ascii=False, indent=2)
        os.replace(tmp, self.state_path)

    def load(self, state_path: str) -> None:
        with open(state_path, encoding="utf-8") as fh:
            raw = json.load(fh)
        self._approvals = {a["token"]: Approval.from_dict(a) for a in raw}
