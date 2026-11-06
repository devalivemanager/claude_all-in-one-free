#!/usr/bin/env bash
# headless-run.sh 자체 시험. 진짜 클로드 대신 가짜 claude 로 돈다(비용 없음).
# 실행: bash scripts/test-headless-run.sh
set -u
here=$(cd "$(dirname "$0")" && pwd)
pass=0
fail=0
check() { if [[ "$2" == "$3" ]]; then pass=$((pass + 1)); else fail=$((fail + 1)); echo "실패: $1 (기대 $2, 실제 $3)"; fi; }

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cd "$work" || exit 1
git init -q && git -c user.email=t@t -c user.name=t commit -q --allow-empty -m init
echo "오늘 바뀐 것을 요약하라" > prompt.md

# 가짜 claude: FAKE_MODE 에 따라 다른 JSON 을 내고, 불린 횟수를 calls 에 남긴다
cat > fake-claude <<'FAKE'
#!/usr/bin/env bash
echo x >> "$FAKE_CALLS"
cat > /dev/null
case "$FAKE_MODE" in
  success)  echo '{"subtype":"success","is_error":false,"result":"요약: 변경 1건","total_cost_usd":0.01}' ;;
  blank)    echo '{"subtype":"success","is_error":false,"result":"  ","total_cost_usd":0.01}' ;;
  maxturns) echo '{"subtype":"error_max_turns","is_error":true,"total_cost_usd":0.09}'; exit 1 ;;
  budget)   echo '{"subtype":"error_max_budget_usd","is_error":true,"total_cost_usd":0.08}'; exit 1 ;;
  garbage)  echo 'not json' ;;
esac
FAKE
chmod +x fake-claude
export CLAUDE_BIN="$work/fake-claude" FAKE_CALLS="$work/calls"
run() { FAKE_MODE=$1 bash "$here/headless-run.sh" prompt.md out/report.md >/dev/null 2>&1; echo $?; }
calls() { [[ -f calls ]] && wc -l < calls | tr -d ' ' || echo 0; }

check "성공 → 0" 0 "$(run success)"
check "성공 → 결과 파일" "요약: 변경 1건" "$(cat out/report.md 2>/dev/null)"
check "같은 커밋이면 클로드를 다시 부르지 않음(호출 1번)" "0 1" "$(run success) $(calls)"

git -c user.email=t@t -c user.name=t commit -q --allow-empty -m next
check "반복 한도 → 1" 1 "$(run maxturns)"
check "비용 한도 → 1" 1 "$(run budget)"
check "성공인데 결과가 비어 있음 → 2" 2 "$(run blank)"
check "JSON 이 아님 → 1" 1 "$(run garbage)"
check "실패한 뒤에는 다음 실행에서 다시 시도" 0 "$(run success)"
check "인자 없음 → 3" 3 "$(bash "$here/headless-run.sh" >/dev/null 2>&1; echo $?)"

echo "헤드리스 실행 시험: 통과 $pass, 실패 $fail"
[[ $fail -eq 0 ]]
