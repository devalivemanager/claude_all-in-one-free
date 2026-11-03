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
nojq=$(mktemp -d)
for b in bash cat tr printf; do p=$(command -v "$b") && ln -s "$p" "$nojq/$b"; done
code=$(printf '{"tool_input":{"command":"npm test"}}' | PATH="$nojq" bash "$here/block-env.sh" 2>/dev/null; echo $?)
check "jq 없음 → 막기" 2 "$code"
rm -rf "$nojq"

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
rm -rf "$repo" "$plain"

echo "훅 시험: 통과 $pass, 실패 $fail"
[[ $fail -eq 0 ]]
