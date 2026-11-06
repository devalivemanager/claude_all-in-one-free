# 016_always_on_agent_runner — 24시간 올웨이즈온 자율 에이전트 러너(HITL 승인 게이트 탑재)

> 🥒 **DevAlive × Pickle**: 클로드 코드(Claude Code) 올웨이즈온 자율 에이전트 파이프라인

클로드 코드 터미널에서 「밤새 회차 조판하고 아침에 결과 보고해줘」 한 마디면 끝까지 돌아가는
배치 러너다. 사람 없이 돌아가는 대신, **위험한 일 앞에서는 반드시 사람 승인을 기다린다** —
OpenAI Dots · Meta Muse 의 공통 기둥 ④(HITL 승인 브레이크)를 데브얼라이브 환경으로 옮긴 것이다.

> 원본 자료 : si studio labs 「OpenAI Dots vs Meta Muse 완전 비교」(성희 님 공유, 2026-11-06)
> 이 샘플이 바꿔서 만든 것 :
> - **상용 올웨이즈온 에이전트의 두 뼈대(태스크 큐 + 승인 게이트)를 로컬에서 재현한다.**
>   전용 클라우드 PC 대신 클로드 코드 세션과 배치 실행으로, 승인 팝업 대신 토큰 발행·승인 장치로 막는다.
> - **「완료했습니다」를 믿지 않는다.** 태스크 성공은 핸들러 반환값으로, 실패는 재시도 상한과
>   오류 기록으로 확정한다. 상태는 JSON 으로 남겨 세션이 끊겨도 이어서 돈다.
> - **레드라인 5종은 장치로 막는다.** 결제·외부 발송·강제 푸시·DB 영구 삭제·계약 동의는
>   승인 토큰 없이는 절대 실행되지 않는다. 토큰은 1회성·만료제다.

## 기술 스택

- Python 3.10 이상, **외부 의존 없음**(표준 라이브러리 asyncio·json·secrets 만 사용)
- 테스트: `unittest`(원하는 경우 `pytest` 로도 돈다)

## 빠른 시작

```bash
# 태스크 등록(일반 작업은 바로 queued, 레드라인 작업은 자동 blocked + 토큰 발행)
python3 -m agent_runner.cli add compose_chapter --payload '{"chapter": "58화"}'
python3 -m agent_runner.cli add echo --payload '{"kind": "메일 발송", "action_type": "EXTERNAL_SEND"}'

# 큐가 빌 때까지 워커 실행 → 레드라인 작업은 blocked 로 남는다
python3 -m agent_runner.cli run

# 승인 대기 목록 확인 → 사람이 확인한 뒤 승인 → 다시 실행
python3 -m agent_runner.cli pending
python3 -m agent_runner.cli approve <토큰>
python3 -m agent_runner.cli run

# 반려도 가능하다
python3 -m agent_runner.cli reject <토큰> --reason "내용 다시 다듬고 보내자"
```

상태 파일은 `output/agent_runner_state/` 아래 `tasks.json`·`approvals.json` 으로 남는다(커밋 대상 아님).

## 레드라인 5종 (사람 승인 없이는 절대 실행하지 않는다)

| action_type | 뜻 |
|---|---|
| `PAYMENT` | 결제·금전 지출 전부 |
| `EXTERNAL_SEND` | 외부 이메일 실제 발송, SNS 게시 |
| `FORCE_PUSH` | main 브랜치 강제 푸시, 저장소 삭제·권한 변경 |
| `DB_DESTROY` | 데이터베이스·원본 파일의 영구 삭제 |
| `CONTRACT` | 외부 계약·약관 동의, 유료 구독 확정 |

## 설계 메모

- **큐(`task_queue.py`)** — 핸들러를 이름으로 등록하고(`register_handler`), `add` 로 쌓고,
  `run_until_empty` 로 돈다. 실패는 `max_attempts` 만큼만 재시도하고 소진되면 `failed` 로 남긴다.
  코루틴 핸들러도 받는다. `blocked` 는 실패가 아니라 「승인을 기다리는 정상 상태」다.
- **게이트(`hitl_gate.py`)** — `classify` 로 레드라인 5종을 판정하고, `request` 가 1회성
  만료 토큰을 발행한다. `approve`·`reject` 외의 길은 없고, 잘못된·만료된 토큰은 전부 거절된다.
  `sniff` 로 자유 텍스트에서 레드라인 후보를 의심할 수 있다(과잉 포착이 원칙).
- **CLI(`cli.py`)** — 위 여섯 동작의 명령줄 진입점. 실제 업무 핸들러는 클로드 코드가
  `register_handler` 로 붙인다(데모 핸들러 3종 내장).

## 테스트

```bash
python3 -m unittest discover -s tests -t .
```

- 큐: 등록 규칙, 순차 실행, 실패·재시도 상한, 비동기 핸들러, 상태 영속화, 승인 연동(멈춤→승인→실행, 반려 부활 없음)
- 게이트: 레드라인 5종 판정, 비레드라인 통과, 토큰 발행·만료·1회성, 잘못된 토큰 거절, 장부 영속화

## 데브얼라이브 실전 시나리오

1. **《밤지기》 야간 배치 조판** — 조판 태스크는 자율 실행, 출간 파일 제출(외부 발송)은 blocked → 아침 승인 후 진행
2. **로블록스 기획서 자동 테스트·커밋** — 일반 브랜치 푸시는 자동, main 강제 푸시는 blocked
3. **유튜브 성과 야간 수집 → 아침 브리핑** — 수집은 자율, 브리핑에 「처리/실패/승인 대기」 세 줄 보고

## 저작권

실습 샘플 코드(`000_sample_project/016_*`)는 묶음의 [`LICENSE-MIT`](../LICENSE-MIT) 를 따른다.
