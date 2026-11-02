#!/usr/bin/env bash
# 유튜브 자막 자동 암호화 도구.
# 자막 원문(저작물)이 공개 저장소에 평문으로 드러나지 않게, age 로 잠근 *.txt.age 만 커밋한다.
#
#   평문 위치 : transcripts/plain/<영상ID>.txt   (항상 git 제외)
#   암호문    : transcripts/<영상ID>.txt.age     (이것만 커밋)
#
#   setup     : 훅을 켜고 지금 있는 암호문을 푼다(클론마다 한 번)
#   sync-enc  : plain/ 의 새 파일·바뀐 파일을 잠근다(커밋 전 훅이 자동 실행)
#   sync-dec  : 비밀키가 있으면 암호문을 plain/ 에 푼다(checkout·pull 후 훅이 자동 실행)
#   encrypt <자막.txt> <영상ID> / decrypt <영상ID> [출력 파일] / check : 수동 사용·검사
#
# 비밀키 찾는 순서: 환경변수 TRANSCRIPT_AGE_KEY(키 문자열) → TRANSCRIPT_AGE_KEY_FILE(키 파일 경로)
#                  → ~/.config/devalive/transcript-key.txt
# 비밀키는 파일·저장소·채팅에 쓰지 않는다.
set -euo pipefail
KEYFILE=""
TMPKEY=""
trap 'if [[ -n "$TMPKEY" ]]; then rm -f "$TMPKEY"; fi' EXIT

ROOT="$(git rev-parse --show-toplevel)"
DIR="$ROOT/transcripts"
PLAIN="$DIR/plain"
RECIPIENTS="$DIR/recipients.txt"
DEFAULT_KEY_FILE="$HOME/.config/devalive/transcript-key.txt"

die() { echo "오류: $*" >&2; exit 1; }
warn() { echo "transcripts: $*" >&2; }
need_age() { command -v age >/dev/null || die "age 가 필요합니다. https://github.com/FiloSottile/age 에서 설치하세요."; }
is_id() { [[ "$1" =~ ^[A-Za-z0-9_-]{11}$ ]]; }
valid_id() { is_id "$1" || die "영상 ID 는 11자(영문·숫자·_·-)여야 합니다: '$1'"; }
has_recipients() { grep -q '^age1' "$RECIPIENTS" 2>/dev/null; }

# 비밀키를 찾으면 KEYFILE 에 경로를 두고 0, 없으면 1.
# 환경변수 문자열은 본인만 읽는 임시 파일에 잠깐 쓰고, 스크립트가 끝나면 지운다(맨 위 trap).
load_key() {
  [[ -n "$KEYFILE" ]] && return 0
  if [[ -n "${TRANSCRIPT_AGE_KEY:-}" ]]; then
    TMPKEY="$(mktemp)"; chmod 600 "$TMPKEY"
    printf '%s\n' "$TRANSCRIPT_AGE_KEY" > "$TMPKEY"
    KEYFILE="$TMPKEY"
  elif [[ -n "${TRANSCRIPT_AGE_KEY_FILE:-}" && -f "$TRANSCRIPT_AGE_KEY_FILE" ]]; then
    KEYFILE="$TRANSCRIPT_AGE_KEY_FILE"
  elif [[ -f "$DEFAULT_KEY_FILE" ]]; then
    KEYFILE="$DEFAULT_KEY_FILE"
  else
    return 1
  fi
}

encrypt() {
  local src="${1:-}" id="${2:-}"
  [[ -f "$src" ]] || die "자막 파일이 없습니다: '$src'"
  valid_id "$id"; need_age
  has_recipients || die "transcripts/recipients.txt 에 공개키(age1...)가 없습니다."
  [[ -s "$src" ]] || die "자막 파일이 비어 있습니다: '$src'"
  age -R "$RECIPIENTS" -a -o "$DIR/$id.txt.age" "$src"
  echo "잠금: transcripts/$id.txt.age"
}

decrypt() {
  local id="${1:-}" out="${2:-}"
  valid_id "$id"; need_age
  [[ -f "$DIR/$id.txt.age" ]] || die "암호문이 없습니다: transcripts/$id.txt.age"
  load_key || die "비밀키가 없습니다(TRANSCRIPT_AGE_KEY 또는 $DEFAULT_KEY_FILE)."
  if [[ -n "$out" ]]; then
    case "$(realpath -m "$out")" in
      "$PLAIN"/*) ;;  # plain/ 은 git 제외 폴더라 허용
      "$DIR"/*) die "평문은 transcripts/plain/ 이나 저장소 밖에만 푸세요." ;;
    esac
    age -d -i "$KEYFILE" -o "$out" "$DIR/$id.txt.age"
  else
    age -d -i "$KEYFILE" "$DIR/$id.txt.age"
  fi
}

# plain/ 의 새 파일·바뀐 파일만 잠가서 스테이징한다. 내용이 같으면 기존 암호문을 그대로 둔다
# (age 는 잠글 때마다 결과가 달라서, 매번 잠그면 내용이 같아도 커밋에 변경이 생긴다).
sync_enc() {
  shopt -s nullglob
  local files=("$PLAIN"/*.txt)
  [[ ${#files[@]} -gt 0 ]] || return 0
  need_age
  if ! has_recipients; then warn "recipients.txt 에 공개키가 없어 자동 잠금을 건너뜁니다(평문은 git 제외라 올라가지 않음)."; return 0; fi
  local p id enc key=0
  load_key && key=1 || true
  for p in "${files[@]}"; do
    id="$(basename "$p" .txt)"
    is_id "$id" || { warn "건너뜀: plain/$id.txt (파일 이름은 <영상ID 11자>.txt 여야 합니다)"; continue; }
    [[ -s "$p" ]] || { warn "건너뜀: plain/$id.txt 가 비어 있습니다."; continue; }
    enc="$DIR/$id.txt.age"
    if [[ -f "$enc" ]]; then
      if [[ $key -eq 0 ]]; then warn "비밀키가 없어 $id 의 변경 여부를 확인할 수 없어 건너뜁니다."; continue; fi
      if age -d -i "$KEYFILE" "$enc" 2>/dev/null | cmp -s - "$p"; then continue; fi
    fi
    age -R "$RECIPIENTS" -a -o "$enc" "$p"
    git -C "$ROOT" add -- "transcripts/$id.txt.age"
    echo "자동 잠금: transcripts/$id.txt.age"
  done
}

# 비밀키가 있으면 암호문을 plain/ 에 푼다. 없으면 아무것도 하지 않는다(암호문만 보임).
# plain/ 쪽을 로컬에서 고쳤고 그쪽이 더 새 파일이면 덮어쓰지 않는다.
sync_dec() {
  shopt -s nullglob
  local encs=("$DIR"/*.txt.age)
  [[ ${#encs[@]} -gt 0 ]] || return 0
  command -v age >/dev/null || { warn "age 가 없어 자동 풀기를 건너뜁니다."; return 0; }
  load_key || return 0
  mkdir -p "$PLAIN"
  local enc id out tmp
  for enc in "${encs[@]}"; do
    id="$(basename "$enc" .txt.age)"
    out="$PLAIN/$id.txt"
    tmp="$(mktemp)"
    if ! age -d -i "$KEYFILE" -o "$tmp" "$enc" 2>/dev/null; then
      rm -f "$tmp"; warn "풀지 못함: $id (이 비밀키로 잠근 파일이 아닙니다)"; continue
    fi
    if [[ -f "$out" ]] && cmp -s "$tmp" "$out"; then rm -f "$tmp"; continue; fi
    if [[ -f "$out" && "$out" -nt "$enc" ]]; then rm -f "$tmp"; warn "로컬에서 고친 plain/$id.txt 를 유지합니다(다음 커밋 때 잠김)."; continue; fi
    mv "$tmp" "$out"
    echo "자동 풀기: transcripts/plain/$id.txt"
  done
}

# 커밋하려는 transcripts/ 파일이 모두 허용된 것인지 확인한다(평문 유출 방지)
check() {
  local bad=0 f
  while IFS= read -r f; do
    case "$f" in
      transcripts/README.md|transcripts/recipients.txt) continue ;;
      transcripts/*.txt.age)
        if [[ "$(git -C "$ROOT" show ":$f" | head -c 200)" != *"BEGIN AGE ENCRYPTED FILE"* ]]; then
          echo "차단: $f 는 age 암호문이 아닙니다." >&2; bad=1
        fi ;;
      transcripts/*) echo "차단: $f 는 올릴 수 없습니다(transcripts/ 에는 암호문 *.txt.age 만)." >&2; bad=1 ;;
    esac
  done < <(git -C "$ROOT" diff --cached --name-only --diff-filter=ACMR)
  [[ $bad -eq 0 ]] || die "커밋을 멈췄습니다. 평문 자막이 공개 저장소에 올라가면 되돌릴 수 없습니다."
}

setup() {
  git -C "$ROOT" config core.hooksPath .githooks
  mkdir -p "$PLAIN"
  echo "훅 켬: 커밋 때 자동 잠금, checkout·pull 후 자동 풀기"
  if load_key; then sync_dec; else echo "비밀키가 없어 자동 풀기는 하지 않습니다(암호문만 보임)."; fi
}

case "${1:-}" in
  setup) setup ;;
  sync-enc) sync_enc ;;
  sync-dec) sync_dec ;;
  encrypt) shift; encrypt "$@" ;;
  decrypt) shift; decrypt "$@" ;;
  check) check ;;
  *) echo "사용법: $0 setup | sync-enc | sync-dec | encrypt <자막.txt> <영상ID> | decrypt <영상ID> [출력 파일] | check" >&2; exit 2 ;;
esac
