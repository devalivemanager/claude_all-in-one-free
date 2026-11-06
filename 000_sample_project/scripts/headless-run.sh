#!/usr/bin/env bash
# 사람 없이(예약 작업·CI) 클로드 코드를 한 번 돌리는 틀. docs/09_고급_헤드리스와자동화.md 참고.
#
# 사용법: bash scripts/headless-run.sh <지시문 파일> <결과 파일>
#   예)   bash scripts/headless-run.sh prompts/daily-review.md reports/daily-review.md
#
# 지키는 것
#   1. 할 일이 없으면 클로드를 부르지 않고 조용히 끝낸다(마지막으로 본 커밋과 같으면 종료 코드 0, 출력 없음).
#   2. 클로드에는 읽기 도구만 준다(--tools). 결과 파일은 이 스크립트가 쓴다.
#   3. 반복 횟수와 비용에 상한을 건다. 비용 상한은 「넘으면 멈춤」이지 그 금액에서 끊기는 벽이 아니다.
#   4. 종료 코드만 믿지 않는다. subtype 이 success 이고 결과가 비어 있지 않을 때만 성공이다.
#      (도구가 막혀 일을 못 해도 클로드 코드는 종료 코드 0 을 낼 수 있다)
#
# 종료 코드: 0 성공 또는 할 일 없음 · 1 클로드가 오류·한도로 멈춤 · 2 결과가 비어 있음 · 3 사용법·환경 오류
# 환경 변수: CLAUDE_BIN(기본 claude) · MAX_TURNS(기본 10) · MAX_BUDGET_USD(기본 1.00) · STATE_FILE(기본 <결과 파일>.last-commit)
set -u

if [[ $# -ne 2 ]]; then
  echo "사용법: bash scripts/headless-run.sh <지시문 파일> <결과 파일>" >&2
  exit 3
fi
prompt_file=$1
result_file=$2
claude_bin=${CLAUDE_BIN:-claude}
max_turns=${MAX_TURNS:-10}
max_budget=${MAX_BUDGET_USD:-1.00}
state_file=${STATE_FILE:-$result_file.last-commit}

for tool in jq git "$claude_bin"; do
  command -v "$tool" >/dev/null 2>&1 || { echo "필요한 명령이 없다: $tool" >&2; exit 3; }
done
[[ -s "$prompt_file" ]] || { echo "지시문 파일이 없거나 비어 있다: $prompt_file" >&2; exit 3; }

# 1) 할 일이 없으면 조용히 끝낸다
head_commit=$(git rev-parse HEAD 2>/dev/null) || { echo "git 저장소 안에서 실행한다" >&2; exit 3; }
if [[ -f "$state_file" && "$(cat "$state_file")" == "$head_commit" ]]; then
  exit 0
fi

# 2·3) 읽기 도구만, 상한을 걸고 실행. 지시문은 표준 입력으로 넘긴다(따옴표·길이 문제 없이)
mkdir -p "$(dirname "$result_file")"
run_json="$result_file.run.json"
"$claude_bin" -p --output-format json \
  --tools "Read,Grep,Glob" \
  --max-turns "$max_turns" --max-budget-usd "$max_budget" \
  < "$prompt_file" > "$run_json" 2> "$result_file.stderr"
claude_code=$?

# 4) 종료 코드가 아니라 내용으로 판정한다
subtype=$(jq -r '.subtype // "없음"' "$run_json" 2>/dev/null || echo "읽기 실패")
cost=$(jq -r '.total_cost_usd // 0' "$run_json" 2>/dev/null || echo 0)
result=$(jq -r '.result // ""' "$run_json" 2>/dev/null || true)

if [[ "$subtype" != "success" ]]; then
  echo "실패: 클로드가 끝까지 하지 못했다(subtype=$subtype, 종료 코드 $claude_code, 비용 \$$cost). 기록: $run_json" >&2
  exit 1
fi
if [[ -z "${result//[[:space:]]/}" ]]; then
  echo "실패: 클로드는 성공이라고 했지만 결과가 비어 있다(비용 \$$cost). 기록: $run_json" >&2
  exit 2
fi

printf '%s\n' "$result" > "$result_file"
echo "$head_commit" > "$state_file"
echo "완료: $result_file (비용 \$$cost)"
