#!/usr/bin/env bash
# 유튜브 자막을 age 공개키로 암호화해 공개 저장소에 두고, 비밀키를 가진 사람만 여는 도구.
#   잠그기(공개키만 필요) : tools/transcripts.sh encrypt <자막.txt> <영상ID>
#   열기(비밀키 필요)     : TRANSCRIPT_AGE_KEY=... tools/transcripts.sh decrypt <영상ID> [출력 파일]
#   검사(커밋 전 훅)      : tools/transcripts.sh check
# 비밀키는 환경변수 TRANSCRIPT_AGE_KEY 로만 받는다. 파일·저장소·채팅에 쓰지 않는다.
set -euo pipefail
KEYFILE=""

ROOT="$(git rev-parse --show-toplevel)"
DIR="$ROOT/transcripts"
RECIPIENTS="$DIR/recipients.txt"
AGE_HEADER="age-encryption.org/v1"

die() { echo "오류: $*" >&2; exit 1; }
need_age() { command -v age >/dev/null || die "age 가 필요합니다. https://github.com/FiloSottile/age 에서 설치하세요."; }
valid_id() { [[ "$1" =~ ^[A-Za-z0-9_-]{11}$ ]] || die "영상 ID 는 11자(영문·숫자·_·-)여야 합니다: '$1'"; }

encrypt() {
  local src="${1:-}" id="${2:-}"
  [[ -f "$src" ]] || die "자막 파일이 없습니다: '$src'"
  valid_id "$id"; need_age
  grep -q '^age1' "$RECIPIENTS" 2>/dev/null || die "transcripts/recipients.txt 에 공개키(age1...)가 없습니다."
  [[ -s "$src" ]] || die "자막 파일이 비어 있습니다: '$src'"
  age -R "$RECIPIENTS" -a -o "$DIR/$id.txt.age" "$src"
  echo "잠금 완료: transcripts/$id.txt.age (이 파일만 커밋하세요)"
}

decrypt() {
  local id="${1:-}" out="${2:-}"
  valid_id "$id"; need_age
  [[ -f "$DIR/$id.txt.age" ]] || die "암호문이 없습니다: transcripts/$id.txt.age"
  [[ -n "${TRANSCRIPT_AGE_KEY:-}" ]] || die "환경변수 TRANSCRIPT_AGE_KEY(비밀키)가 없습니다."
  # 비밀키를 잠깐 파일로 써야 하므로 본인만 읽는 임시 파일을 만들고 끝나면 지운다.
  # 주의: 함수 안 local 변수는 스크립트가 끝날 때(EXIT) 이미 사라진다. 그래서 전역 변수 KEYFILE 을 쓴다.
  KEYFILE="$(mktemp)"; chmod 600 "$KEYFILE"
  trap 'rm -f "$KEYFILE"' EXIT
  local keyfile="$KEYFILE"
  printf '%s\n' "$TRANSCRIPT_AGE_KEY" > "$keyfile"
  if [[ -n "$out" ]]; then
    case "$(realpath -m "$out")" in "$ROOT"/transcripts/*) die "평문을 transcripts/ 안에 풀지 마세요. 저장소 밖 경로를 쓰세요.";; esac
    age -d -i "$keyfile" -o "$out" "$DIR/$id.txt.age"
  else
    age -d -i "$keyfile" "$DIR/$id.txt.age"
  fi
}

# 커밋하려는 transcripts/ 파일이 모두 age 암호문인지 확인한다(평문 유출 방지)
check() {
  local bad=0 f
  while IFS= read -r f; do
    case "$f" in
      transcripts/README.md|transcripts/recipients.txt) continue ;;
      transcripts/*.txt.age)
        if [[ "$(git show ":$f" | head -c 200)" != *"BEGIN AGE ENCRYPTED FILE"* ]]; then
          echo "차단: $f 는 age 암호문이 아닙니다." >&2; bad=1
        fi ;;
      transcripts/*) echo "차단: $f 는 transcripts/ 에 올릴 수 없는 파일입니다(암호문 *.txt.age 만 허용)." >&2; bad=1 ;;
    esac
  done < <(git diff --cached --name-only --diff-filter=ACMR)
  [[ $bad -eq 0 ]] || die "커밋을 멈췄습니다. 평문 자막이 공개 저장소에 올라가면 되돌릴 수 없습니다."
}

case "${1:-}" in
  encrypt) shift; encrypt "$@" ;;
  decrypt) shift; decrypt "$@" ;;
  check) check ;;
  *) echo "사용법: $0 encrypt <자막.txt> <영상ID> | decrypt <영상ID> [출력 파일] | check" >&2; exit 2 ;;
esac
