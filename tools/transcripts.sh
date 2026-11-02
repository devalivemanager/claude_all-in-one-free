#!/usr/bin/env bash
# 유튜브 자막 「에스페란토」 변환 도구 — 우리만의 공용 번역기.
# 목적: 자막 원문(저작물)이 공개 저장소에서 평문으로 보이지 않게 가린다.
#       보안 장치가 아니다. 이 저장소를 받은 누구나 자동으로 풀 수 있다(고정 변환: gzip + base64).
#
#   평문   : transcripts/plain/<영상ID>.txt   (항상 git 제외)
#   변환본 : transcripts/<영상ID>.txt.eo      (이것만 커밋)
#
#   setup    : 훅을 켜고 지금 있는 변환본을 푼다(클론마다 한 번)
#   sync-enc : plain/ 의 자막을 변환본으로 만든다(커밋 전 훅이 자동 실행)
#   sync-dec : 변환본을 plain/ 에 푼다(checkout·pull 후 훅이 자동 실행)
#   encode <자막.txt> <영상ID> / decode <영상ID> [출력 파일] / check : 수동 사용·검사
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
DIR="$ROOT/transcripts"
PLAIN="$DIR/plain"
HEADER="DEVALIVE-EO1"   # 변환본 첫 줄. 형식이 바뀌면 숫자를 올린다

die() { echo "오류: $*" >&2; exit 1; }
warn() { echo "transcripts: $*" >&2; }
is_id() { [[ "$1" =~ ^[A-Za-z0-9_-]{11}$ ]]; }
valid_id() { is_id "$1" || die "영상 ID 는 11자(영문·숫자·_·-)여야 합니다: '$1'"; }

# 같은 내용이면 항상 같은 결과가 나오도록 gzip 에 -n(이름·시각 기록 안 함)을 쓴다
to_eo() { printf '%s\n' "$HEADER"; gzip -n -9 -c | base64 | tr -d '\n' | fold -w 76; printf '\n'; }
from_eo() {
  local first; IFS= read -r first || true
  [[ "$first" == "$HEADER" ]] || die "변환본 형식이 아닙니다(첫 줄이 $HEADER 가 아님)."
  tr -d '\n\r' | base64 --decode | gzip -d -c
}

encode() {
  local src="${1:-}" id="${2:-}"
  [[ -f "$src" ]] || die "자막 파일이 없습니다: '$src'"
  valid_id "$id"
  [[ -s "$src" ]] || die "자막 파일이 비어 있습니다: '$src'"
  to_eo < "$src" > "$DIR/$id.txt.eo"
  echo "변환: transcripts/$id.txt.eo"
}

decode() {
  local id="${1:-}" out="${2:-}"
  valid_id "$id"
  [[ -f "$DIR/$id.txt.eo" ]] || die "변환본이 없습니다: transcripts/$id.txt.eo"
  if [[ -n "$out" ]]; then
    case "$(realpath -m "$out")" in
      "$PLAIN"/*) ;;
      "$DIR"/*) die "평문은 transcripts/plain/ 이나 저장소 밖에만 푸세요." ;;
    esac
    from_eo < "$DIR/$id.txt.eo" > "$out"
  else
    from_eo < "$DIR/$id.txt.eo"
  fi
}

sync_enc() {
  shopt -s nullglob
  local p id eo tmp
  for p in "$PLAIN"/*.txt; do
    id="$(basename "$p" .txt)"
    is_id "$id" || { warn "건너뜀: plain/$id.txt (파일 이름은 <영상ID 11자>.txt 여야 합니다)"; continue; }
    [[ -s "$p" ]] || { warn "건너뜀: plain/$id.txt 가 비어 있습니다."; continue; }
    eo="$DIR/$id.txt.eo"; tmp="$(mktemp)"
    to_eo < "$p" > "$tmp"
    if [[ -f "$eo" ]] && cmp -s "$tmp" "$eo"; then rm -f "$tmp"; continue; fi
    mv "$tmp" "$eo"
    git -C "$ROOT" add -- "transcripts/$id.txt.eo"
    echo "자동 변환: transcripts/$id.txt.eo"
  done
}

sync_dec() {
  shopt -s nullglob
  local eo id out tmp
  for eo in "$DIR"/*.txt.eo; do
    mkdir -p "$PLAIN"
    id="$(basename "$eo" .txt.eo)"; out="$PLAIN/$id.txt"; tmp="$(mktemp)"
    if ! (from_eo < "$eo" > "$tmp") 2>/dev/null; then rm -f "$tmp"; warn "풀지 못함: $id (형식 오류)"; continue; fi
    if [[ -f "$out" ]] && cmp -s "$tmp" "$out"; then rm -f "$tmp"; continue; fi
    if [[ -f "$out" && "$out" -nt "$eo" ]]; then rm -f "$tmp"; warn "로컬에서 고친 plain/$id.txt 를 유지합니다(다음 커밋 때 변환됨)."; continue; fi
    mv "$tmp" "$out"
    echo "자동 풀기: transcripts/plain/$id.txt"
  done
}

# 커밋하려는 transcripts/ 파일이 변환본·안내 문서뿐인지 확인한다(평문 노출 방지)
check() {
  local bad=0 f
  while IFS= read -r f; do
    case "$f" in
      transcripts/README.md) continue ;;
      transcripts/*.txt.eo)
        if [[ "$(git -C "$ROOT" show ":$f" | head -1)" != "$HEADER" ]]; then
          echo "차단: $f 는 변환본 형식이 아닙니다." >&2; bad=1
        fi ;;
      transcripts/*) echo "차단: $f 는 올릴 수 없습니다(transcripts/ 에는 변환본 *.txt.eo 만)." >&2; bad=1 ;;
    esac
  done < <(git -C "$ROOT" diff --cached --name-only --diff-filter=ACMR)
  [[ $bad -eq 0 ]] || die "커밋을 멈췄습니다. 평문 자막이 공개 저장소에 올라가면 되돌릴 수 없습니다."
}

setup() {
  git -C "$ROOT" config core.hooksPath .githooks
  mkdir -p "$PLAIN"
  echo "훅 켬: 커밋 때 자동 변환, checkout·pull 후 자동 풀기"
  sync_dec
}

case "${1:-}" in
  setup) setup ;;
  sync-enc) sync_enc ;;
  sync-dec) sync_dec ;;
  encode) shift; encode "$@" ;;
  decode) shift; decode "$@" ;;
  check) check ;;
  *) echo "사용법: $0 setup | sync-enc | sync-dec | encode <자막.txt> <영상ID> | decode <영상ID> [출력 파일] | check" >&2; exit 2 ;;
esac
