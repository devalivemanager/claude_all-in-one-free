#!/usr/bin/env bash
# PreToolUse(Bash) 훅: 「읽기만 하는」 서브에이전트(기본: reviewer)의 Bash 를 읽기 명령으로 묶는다.
# 메인 세션과 다른 에이전트의 Bash 에는 손대지 않는다.
#
# 왜 훅인가
# - 에이전트 지시문의 「읽기만 한다」는 부탁이다. tools 에 Bash 가 있으면 파일을 고칠 수 있다.
# - 에이전트 설정의 permissionMode: plan 은 메인 세션이 acceptEdits·auto·bypassPermissions 이면 무시된다.
# - 에이전트 파일 안(frontmatter)의 훅은 폴더를 신뢰한 대화형 세션에서만 돈다(-p 헤드리스에서는 건너뜀).
#   그래서 settings.json 의 훅에서 입력의 agent_type 으로 골라 막는다.
#
# 종료 코드 2 = 막고 이유를 클로드에게 전한다. 0 = 통과.

readonly_agents=${READONLY_AGENTS:-reviewer}   # 쉼표로 여러 개: "reviewer,auditor"

if ! command -v jq >/dev/null 2>&1; then
  echo "jq 가 없어 읽기 전용 에이전트 검사를 할 수 없다. 사람에게 jq 설치를 요청하라." >&2
  exit 2
fi

input=$(cat)
agent=$(printf '%s' "$input" | jq -r '.agent_type // empty')
[[ -z "$agent" ]] && exit 0                       # 메인 세션
[[ ",$readonly_agents," == *",$agent,"* ]] || exit 0  # 읽기 전용 목록에 없는 에이전트

cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // empty')

# 명령을 잇거나 파일로 내보내는 기호가 있으면 막는다(읽기 명령 뒤에 쓰기를 붙이는 것 방지)
if [[ "$cmd" == *[\;\&\|\>\<\`\$]* || "$cmd" == *$'\n'* ]]; then
  echo "$agent 에이전트는 읽기만 한다. 명령을 잇거나 파일로 내보내는 기호(; & | > < \` \$)는 쓸 수 없다: $cmd" >&2
  exit 2
fi

# 읽기 명령만 허용
if [[ "$cmd" =~ ^(git[[:space:]]+(diff|status|log|show|blame)|ls|cat|head|tail|wc|grep|rg)([[:space:]]|$) ]]; then
  exit 0
fi
echo "$agent 에이전트는 읽기만 한다. 허용: git diff·status·log·show·blame, ls, cat, head, tail, wc, grep, rg. 막힌 명령: $cmd" >&2
exit 2
