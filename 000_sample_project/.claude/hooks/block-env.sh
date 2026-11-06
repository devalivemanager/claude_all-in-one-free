#!/usr/bin/env bash
# PreToolUse(Bash) 훅: .env 같은 비밀값 파일을 다루는 명령을 막는다.
# 종료 코드 2 = 막고, 표준 에러의 글을 클로드에게 전한다. 0 = 통과.
# 글자 맞추기라서 완벽한 벽은 아니다(예: cat .e""nv). 비밀값은 저장소 밖에 두는 것이 먼저다.

# jq 가 없으면 검사를 못 한다. 조용히 통과시키지 않고(fail-open) 막는다(fail-closed).
if ! command -v jq >/dev/null 2>&1; then
  echo "jq 가 없어 .env 검사 훅을 실행할 수 없다. 사람에게 jq 설치를 요청하라." >&2
  exit 2
fi

command_text=$(jq -r '.tool_input.command // empty')

# 명령을 낱말로 나눠, 이름이 .env 로 끝나거나 .env.<무엇> 인 파일을 찾는다.
# .env.example / .env.sample / .env.template 은 비밀값이 없는 견본이라 허용한다.
# 마지막 낱말 뒤에는 줄바꿈이 없어서 `|| [[ -n "$token" ]]` 가 없으면 그 낱말을 놓친다(명령 끝의 .env 를 못 막음).
while IFS= read -r token || [[ -n "$token" ]]; do
  [[ -z "$token" ]] && continue
  if [[ "$token" =~ (^|/)[^/]*\.env(\.[A-Za-z0-9_-]+)?$ ]] && [[ ! "$token" =~ \.env\.(example|sample|template)$ ]]; then
    echo "비밀값 파일($token)은 다루지 않는다(CLAUDE.md 2절). 값이 필요하면 사람에게 물어라. 견본은 .env.example 을 쓴다." >&2
    exit 2
  fi
done < <(printf '%s' "$command_text" | tr ' \t;|&<>()"`$=,'"'" '\n')

exit 0
