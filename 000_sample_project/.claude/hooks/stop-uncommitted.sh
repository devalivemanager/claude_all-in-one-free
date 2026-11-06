#!/usr/bin/env bash
# Stop 훅: 커밋 안 된 변경이 있으면 끝내기 전에 한 번 알린다.
# - 이미 이 훅 때문에 계속하는 중(stop_hook_active=true)이면 다시 막지 않는다.
#   일부러 커밋을 미루는 경우(다른 작업이 파일을 쓰는 중 등)에 끝없이 재촉하지 않기 위해서다.
# - git 저장소가 아니면 아무것도 하지 않는다.

active=false
if command -v jq >/dev/null 2>&1; then
  active=$(jq -r '.stop_hook_active // false')
fi
[[ "$active" == "true" ]] && exit 0

changes=$(git status --porcelain 2>/dev/null) || exit 0
if [[ -n "$changes" ]]; then
  echo "커밋 안 된 변경이 있다($(printf '%s\n' "$changes" | wc -l | tr -d ' ')개). git status 로 확인하고, 끝난 작업이면 커밋하라. 일부러 남겨 두는 것이면 그 이유를 보고하고 끝내라." >&2
  exit 2
fi
exit 0
