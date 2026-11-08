# 012_hybrid_slm_pipeline — 로컬 소형 모델 전처리 × 클로드 코드 최종 작성

댓글·원문처럼 양이 많은 텍스트를 **PC 의 작은 로컬 모델(Ollama)** 이 먼저 정리하고, **클로드 코드**는 정리된 JSON 만 받아 블로그 글·시나리오·주간 보고서를 쓰는 2단계 파이프라인입니다.
비싼 큰 모델에 원문 전체를 넣지 않아 토큰을 아끼고, 반복 작업은 스크립트 한 줄로 돌립니다.

```
[원본] 댓글 수백 개 / 긴 원문
   │  1단계 (PC, 로컬 Ollama) ── 개인정보 가리기 → 분류·요약(작은 모델) + 키워드 집계(일반 코드)
   ▼
data/processed/clean_data.json   ← 두 단계를 잇는 약속(형식은 아래)
   │  2단계 (클로드 코드) ── .claude/skills/ 규격 + JSON → 블로그 글 / 시나리오 / 보고서
   ▼
output/blog · output/scenario · output/reports   ← 게시는 사람이 확인한 뒤에
```

> 이 샘플은 「무료 로컬 모델 + 클로드」 조합을 소개한 자료(네이버 블로그 AI상상력대장, 유튜브 No2vg7PXDcU)를 데브얼라이브 환경에 맞게 다시 설계한 것입니다.
> 자료의 설명 중 아래는 **바꿔서** 만들었습니다.
> - **키워드 세기는 모델이 아니라 코드가 한다.** 정확하고 결과가 늘 같다.
> - **작은 모델의 답은 검사한다.** JSON 이 아니거나 정해진 분류가 아니면 성공으로 세지 않고 `failures` 에 남긴다.
> - **속도·비용은 추정하지 않고 잰다.** Ollama 가 돌려주는 실제 토큰 수·시간으로 「토큰/초」를 계산해 기록한다.
> - **파이썬이 클로드 코드를 직접 조종할 수는 없다.** 2단계는 `claude -p`(사람 없이 한 번 답하는 모드)로 하고, `claude` 명령이 없으면 지시문 파일을 만들어 사람이 넘긴다.

## 기술 스택

- Python 3.11 이상, **표준 라이브러리만** 사용(설치할 패키지 없음)
- PC: [Ollama](https://ollama.com) + 무료 + 상업 이용이 확인된 작은 모델(기본값 없음, 아래 「로컬 모델 고르기」)
- 2단계: Claude Code CLI(`claude`)
- 테스트: `unittest` 33개 — **가짜 Ollama 서버**로 돌아서 Ollama 없이도 된다

## 폴더 구조

```
012_hybrid_slm_pipeline/
├── .claude/skills/
│   ├── blog-writer/SKILL.md      # 테크 블로그 글 규격
│   ├── scenario-writer/SKILL.md  # 옛이야기 롱폼 시나리오 규격
│   └── weekly-report/SKILL.md    # 주간 보고서 규격
├── pipeline/
│   ├── slm_client.py             # Ollama 연결·상태 확인·JSON 강제·실측값
│   ├── preprocess.py             # 개인정보 가리기, 키워드 집계, 분류·요약, clean_data.json
│   └── run_hybrid_pipeline.py    # 원클릭 러너(1단계 → 2단계)
├── data/samples/                 # 예제(이 샘플을 위해 새로 쓴 가상의 댓글·옛이야기)
├── tests/                        # 가짜 Ollama 서버 + 테스트
└── (실행하면 생김, git 제외) data/raw/ · data/processed/ · output/
```

## 실행 방법 (PC)

```bash
# 0) Ollama 준비: 모델 이름은 ollama list 로 확인한다
ollama serve                                   # 다른 창에서 켜 둔다
ollama pull <모델 이름>                         # 「로컬 모델 고르기」를 통과한 모델
export SLM_MODEL=<모델 이름>                    # Windows PowerShell: $env:SLM_MODEL="..."  (정하지 않으면 안내하고 멈춘다)

# 1) 실행
cd 000_sample_project/012_hybrid_slm_pipeline
python -m pipeline.run_hybrid_pipeline --input data/samples/comments_sample.json --skill blog-writer --keywords 쌀,도깨비
```

출력 예(가짜 Ollama 로 실행한 모습. 숫자는 가짜 서버가 준 값이라 실제 속도가 아니다):

```
| 단계 | 수행 | 실측 | 결과물 |
|---|---|---|---|
| 1 전처리 | 로컬 example-small-model | 호출 2회, 생성 40 토큰, 200.0 토큰/초(실측), 분류 실패 0건 | data/processed/clean_data.json |
| 2 작성 | 사람이 클로드 코드에 전달 | - | output/prompts/2026-11-02_blog-writer_instruction.md |
```

| 옵션 | 뜻 |
|---|---|
| `--input` | 댓글(`.json`: 문자열 목록 또는 `{"text": ...}` 목록, 작성자 등 다른 필드는 버림) 또는 원문(`.txt`: 한 줄이 한 항목) |
| `--skill` | `blog-writer` · `scenario-writer` · `weekly-report` |
| `--keywords` | 쉼표로 구분한 집계 키워드 |
| `--stage2` | `auto`(기본: `claude` 가 있으면 작성까지, 없으면 지시문만) · `headless`(반드시 `claude -p`) · `manual`(지시문 파일만) |

환경변수: `OLLAMA_URL`(기본 `http://localhost:11434`), `SLM_MODEL`.
종료 코드: 정상 0, 실행 오류(서버 없음·모델 없음·2단계 실패) 1, 잘못된 인자 2.

## clean_data.json 형식 (두 단계의 약속)

```json
{
  "schema_version": 1,
  "created_at": "2026-11-02T13:00:00+00:00",
  "source": {"file": "comments_sample.json", "items": 6},
  "model": "example-small-model",
  "classification": {
    "counts": {"칭찬": 2, "기능문의": 2, "오류제보": 1, "기타": 1},
    "items": [{"index": 0, "text": "…", "category": "칭찬"}],
    "failures": [{"index": 7, "reason": "알 수 없는 분류: '감동'"}]
  },
  "keywords": {"쌀": {"count": 2, "contexts": ["쌀 서 말 이야기 너무 "]}},
  "summary": {"bullets": ["…", "…", "…"], "failure": null},
  "metrics": {"calls": 2, "prompt_tokens": 100, "generated_tokens": 40, "generate_seconds": 0.2, "total_seconds": 0.3, "measured_tokens_per_second": 200.0}
}
```

- 분류는 `칭찬`·`기능문의`·`오류제보`·`기타` 넷뿐이다. 그 밖의 답이나 빠진 항목은 `failures` 로 간다.
- 본문의 링크·메일·전화번호·`@아이디` 는 `[링크]`·`[메일]`·`[전화]`·`[아이디]` 로 가려진다.

## 테스트

```bash
python -m unittest discover -s tests -t .     # 33개, Ollama 없이 가짜 서버로
```

- 연결: 모델을 정하지 않으면 서버에 묻기 전에 안내하고 멈춤, 모델 설치 확인(`:latest` 태그 포함), 모델 없음 → `ollama pull` 안내, 서버 없음 → `ollama serve` 안내, JSON 형식·한국어 규칙·temperature 0 을 보내는지, JSON 이 아닌 답은 실패, 실측값 계산
- 개인정보: 링크·메일·전화·아이디 가리기, 작성자 필드 버리기
- 집계: 모든 출현을 정확히, 겹치는 경우 두 번 세지 않기
- 분류: 정상, 모르는 분류·빠진 항목·망가진 응답은 실패, 10개씩 나눠 보내도 번호가 맞는지
- 요약: 형식 검사, 너무 많으면 잘라 내고 알림
- 러너: 지시문 모드, 헤드리스 모드(가짜 `claude`), `claude` 없으면 지시문으로, 2단계 실패는 종료 코드 1, 서버 없으면 아무 파일도 만들지 않음, 분류 실패 경고
- 스킬 3개의 형식
- 2단계 호출(가짜 `claude`): 도구를 끄고(`--tools ""`) JSON 으로 받고 비용 상한을 거는지, 글만 돌려주는지, 비용 상한에 걸린 종료·성공인데 빈 답은 실패로 보는지

## 로컬 모델 고르기 (전제 : 무료 + 상업 이용 가능)

이 파이프라인의 결과(블로그 글·시나리오·보고서)로 수익을 낼 수 있으려면, 1단계 모델이 **무료이면서 상업적으로 써도 되는 것**이어야 한다. `ollama pull` 하기 전에 아래를 본다.

| 확인 | 통과 기준 | 이런 것은 탈락·보류 |
|---|---|---|
| 1. 가중치 라이선스 | Apache 2.0, MIT 처럼 상업 이용이 열린 것 | CC-BY-NC(비상업), 연구용 라이선스, 「확정 중」. 수정 MIT·자체 라이선스는 **조건 항**(매출 상한, 서비스형 제공 금지 등)을 원문으로 읽고 판단 |
| 2. 크기 대 내 메모리 | 모델 파일이 내 PC 메모리(그래픽 메모리 또는 RAM)에 여유 있게 들어감 | 「공개됐다」만 보고 고르지 않는다. 한 번에 일부만 쓰는 모델도 전체를 메모리에 올려야 한다 |
| 3. 내 과제로 시험 | `--keywords` 를 넣고 돌려 **분류 실패 건수**와 **실측 토큰/초**를 본다(이 파이프라인이 기록한다) | 남의 비교표 1등이라도 내 댓글 분류에서 실패가 많으면 쓰지 않는다 |

- 판정을 모아 둔 표 : [`999_document/01_무료·상업이용_도구/무료·상업이용_도구목록.md`](../../999_document/01_무료·상업이용_도구/무료·상업이용_도구목록.md). 같은 계열이라도 크기마다 라이선스가 다를 수 있어 모델마다 확인한다. **중국 회사·기관이 만든 모델은 쓰지 않는다**(도구표 기준)
- 그래서 기본 모델을 두지 않았다. `SLM_MODEL` 을 정하지 않으면 실행기가 이 표를 보라고 안내하고 종료 코드 1로 멈춘다(파일은 만들지 않는다).
- 이 파이프라인의 결과를 남에게 「모델 API」로 빌려주는 것은 아니지만, 라이선스에 따라 「결과물을 파는 것」과 「모델을 서비스로 제공하는 것」의 조건이 다를 수 있다. 원문에서 둘을 나눠 읽는다.

## 확인하지 못한 것 (PC 에서 직접 재서 채운다)

- 이 클라우드 환경에는 Ollama 가 없어서 **실제 작은 모델의 속도·분류 품질은 재지 않았다.** README 의 숫자는 가짜 서버 값이다.
- 2단계는 이 환경에서 진짜 `claude -p` 로 돌려 보았다(2026-11-06, 1단계는 가짜 서버). 블로그 글 한 편(약 4.7KB)이 30초 안팎에 나오고, JSON 에 없는 사실은 「[확인 필요]」로 남겼다.
- 2단계는 글만 쓰므로 도구를 끈다(`--tools ""`). 같은 짧은 지시를 켜고·끄고 재 보니 비용이 $0.0897 → $0.0186, 블로그 글 한 편에서는 입력 토큰(캐시 포함)이 79,948 → 9,648 로 줄었다. 끄지 않으면 쓰지도 않는 도구 설명이 매번 실린다.
- 성공 판정은 종료 코드가 아니라 결과 JSON 의 `subtype` 과 빈 답으로 한다. 한 번의 비용 상한은 `STAGE2_MAX_BUDGET_USD`(1달러)다.

## 주의

- 댓글·원문은 다른 사람의 글이다. `data/raw/`, `data/processed/`, `output/` 은 git 에서 제외돼 있다. 공개 저장소에 올리지 않는다.
- 결과 글은 사람이 확인한 뒤에 게시한다. 작은 모델의 분류는 틀릴 수 있다(분류 실패 건수를 꼭 본다).

---

Copyright (c) 2026 devalive · [MIT 라이선스](../LICENSE-MIT)
