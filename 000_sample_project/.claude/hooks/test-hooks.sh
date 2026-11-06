#!/usr/bin/env bash
# 훅 자체 시험: 훅을 바꾼 뒤 「정말 막히는지」를 실제 입력 JSON 으로 확인한다.
# 실행: bash .claude/hooks/test-hooks.sh   (jq, git 필요)
set -u
here=$(cd "$(dirname "$0")" && pwd)
pass=0
fail=0

check() { # 설명, 기대 종료 코드, 실제 종료 코드
  if [[ "$2" == "$3" ]]; then pass=$((pass + 1)); else fail=$((fail + 1)); echo "실패: $1 (기대 $2, 실제 $3)"; fi
}
pre() { # 명령 문자열 → block-env.sh 종료 코드
  jq -nc --arg c "$1" '{hook_event_name:"PreToolUse",tool_name:"Bash",tool_input:{command:$c}}' | bash "$here/block-env.sh" 2>/dev/null
  echo $?
}

# 막아야 하는 것
for c in "cat .env" "cat .env.local" "cat config/.env" "source .env" "echo A=1 >> .env" "cat prod.env" \
         "cp .env.example .env" "grep KEY .env.production"; do
  check "막기: $c" 2 "$(pre "$c")"
done
# 통과시켜야 하는 것
for c in "npm test" "cat .envrc" "git add .env.example" "cat .env.sample" "ls docs/environment.md" "echo env"; do
  check "통과: $c" 0 "$(pre "$c")"
done
# jq 가 없으면 통과시키지 않고 막는다
nojq_dir=$(mktemp -d)
for b in bash cat tr printf; do p=$(command -v "$b") && ln -s "$p" "$nojq_dir/$b"; done
code=$(printf '{"tool_input":{"command":"npm test"}}' | PATH="$nojq_dir" bash "$here/block-env.sh" 2>/dev/null; echo $?)
check "jq 없음 → 막기" 2 "$code"

# 읽기 전용 에이전트(reviewer)의 Bash
ro() { # 에이전트 이름, 명령 → readonly-agent-bash.sh 종료 코드
  jq -nc --arg a "$1" --arg c "$2" '{tool_name:"Bash",tool_input:{command:$c}} + (if $a == "" then {} else {agent_type:$a} end)' \
    | bash "$here/readonly-agent-bash.sh" 2>/dev/null
  echo $?
}
for c in "git diff" "git diff --staged" "git log --oneline -5" "grep -n TODO src/a.js" "cat README.md"; do
  check "검토자 통과: $c" 0 "$(ro reviewer "$c")"
done
for c in "touch x" "rm -rf build" "git commit -m x" "sed -i s/a/b/ f.txt" "git diff > out.txt" "cat a; rm a" "echo \$(rm a)" "python3 -c 'open(1)'"; do
  check "검토자 막기: $c" 2 "$(ro reviewer "$c")"
done
check "메인 세션은 손대지 않음" 0 "$(ro "" "touch x")"
check "다른 에이전트는 손대지 않음" 0 "$(ro builder "touch x")"
code=$(printf '{"agent_type":"reviewer","tool_input":{"command":"git diff"}}' | PATH="$nojq_dir" bash "$here/readonly-agent-bash.sh" 2>/dev/null; echo $?)
check "jq 없음 → 막기(검토자)" 2 "$code"

# Stop 훅
repo=$(mktemp -d)
(
  cd "$repo" || exit 1
  git init -q && git -c user.email=t@t -c user.name=t commit -q --allow-empty -m init
  stop() { printf '%s' "$1" | bash "$here/stop-uncommitted.sh" 2>/dev/null; echo $?; }
  check "Stop: 깨끗하면 통과" 0 "$(stop '{"stop_hook_active":false}')"
  touch new.txt
  check "Stop: 변경 있으면 막기" 2 "$(stop '{"stop_hook_active":false}')"
  check "Stop: 이미 재촉했으면 통과" 0 "$(stop '{"stop_hook_active":true}')"
  echo "$pass $fail" > "$repo/.counts"
)
read -r pass fail < "$repo/.counts"
plain=$(mktemp -d)
code=$(cd "$plain" && printf '{}' | bash "$here/stop-uncommitted.sh" 2>/dev/null; echo $?)
check "Stop: git 저장소 아니면 통과" 0 "$code"
rm -rf "$repo" "$plain" "$nojq_dir"

echo "훅 시험: 통과 $pass, 실패 $fail"
[[ $fail -eq 0 ]]
