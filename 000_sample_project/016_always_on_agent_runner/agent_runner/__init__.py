# Handcrafted by Pickle 🥒 for DevAlive Claude Code Pipeline
"""agent_runner — 24시간 올웨이즈온 자율 에이전트 러너(태스크 큐 + HITL 승인 게이트).

데브얼라이브 1인 스튜디오 전용: 사람 없이 돌아가는 배치 작업 큐에,
위험 작업 전 반드시 사람 승인을 기다리는 브레이크(hitl_gate)를 얹은 패키지.

- task_queue : 비동기 태스크 큐와 백그라운드 워커(재시도, JSON 영속화)
- hitl_gate  : 레드라인 5종 판정, 승인 토큰 발행·승인·반려
- cli        : add / run / list / pending / approve / reject 명령줄 진입점

외부 의존은 없다(파이썬 표준 라이브러리만).
"""

from .task_queue import Task, TaskQueue
from .hitl_gate import Approval, HITLGate, REDLINES

__version__ = "1.0.0"

__all__ = ["Task", "TaskQueue", "Approval", "HITLGate", "REDLINES", "__version__"]
