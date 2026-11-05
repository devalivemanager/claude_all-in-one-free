#!/usr/bin/env bash
# 예제 12개의 시험을 모두 돌리고, 실제 통과 개수를 README.md 표의 「테스트」 칸과 맞춰 본다.
# 출간 전·문서 수정 뒤에 돌려 「README 숫자 = 실제 숫자」를 확인하는 동기화 점검용이다.
#
# 사용법 : bash scripts/check-sample-tests.sh [예제 폴더 이름 ...]
#   인자가 없으면 12개 전부. 예) bash scripts/check-sample-tests.sh 003_fullstack_todo 009_scroll_video_hero
# 종료 코드 : 0 모두 일치·통과 / 1 실패하거나 숫자가 다름 / 2 도구가 없어 돌리지 못한 예제가 있음
#
# 원본을 더럽히지 않는다 : pytest 캐시는 끄고(-p no:cacheprovider), 빌드 산출물(target/ 등)은 각 예제의 .gitignore 대상이다.

set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
README="${SAMPLE_README:-$ROOT/README.md}"   # 점검 장치 자체를 시험할 때만 다른 표를 넘긴다

# README 표에서 「| [폴더](폴더/) | … | 48개 |」의 숫자를 읽는다
expected() {
  grep -E "^\| \[$1\]" "$README" | awk -F'|' '{print $(NF-1)}' | grep -oE '[0-9]+' | head -n1
}

# 예제별 실행 명령. 출력은 parse 가 읽는다.
run_tests() {
  case "$1" in
    001_hr_payroll)         rm -rf target/surefire-reports; mvn -q -o test >/dev/null 2>&1; echo "mvn_exit=$?" ;;
    002_fi_ledger|008_youtube_analyzer)
                            .venv/bin/python -m pytest -q -p no:cacheprovider 2>&1 ;;
    005_inventory_api)      go test -count=1 -v ./... 2>&1 ;;
    007_attendance_cli)     cargo test -q 2>&1 ;;
    012_hybrid_slm_pipeline) python3 -m unittest discover -s tests -t . 2>&1 ;;
    *)                      npm test --silent 2>&1 ;;
  esac
}

# 출력에서 「통과 실패」 두 숫자를 뽑는다
parse() {
  local name="$1" out="$2" pass fail
  case "$name" in
    001_hr_payroll)
      read -r pass fail < <(python3 - "$ROOT/$name/target/surefire-reports" <<'PY'
import glob, re, sys
t = f = 0
for p in glob.glob(sys.argv[1] + '/TEST-*.xml'):
    head = re.search(r'<testsuite[^>]*>', open(p, encoding='utf-8').read()).group(0)
    get = lambda k: int(re.search(k + r'="(\d+)"', head).group(1))
    t += get('tests'); f += get('failures') + get('errors')
print(t - f, f)
PY
) ;;
    002_fi_ledger|008_youtube_analyzer)
      pass=$(grep -oE '[0-9]+ passed' <<<"$out" | tail -n1 | grep -oE '[0-9]+')
      fail=$(grep -oE '[0-9]+ (failed|error)' <<<"$out" | grep -oE '[0-9]+' | paste -sd+ | bc 2>/dev/null) ;;
    005_inventory_api)
      pass=$(grep -c -- '--- PASS' <<<"$out"); fail=$(grep -c -- '--- FAIL' <<<"$out") ;;
    007_attendance_cli)
      pass=$(grep -oE 'ok\. [0-9]+ passed' <<<"$out" | grep -oE '[0-9]+' | paste -sd+ | bc)
      fail=$(grep -oE '[0-9]+ failed' <<<"$out" | grep -oE '[0-9]+' | paste -sd+ | bc) ;;
    012_hybrid_slm_pipeline)
      local ran; ran=$(grep -oE 'Ran [0-9]+ test' <<<"$out" | grep -oE '[0-9]+')
      fail=$(grep -oE '(failures|errors)=[0-9]+' <<<"$out" | grep -oE '[0-9]+' | paste -sd+ | bc)
      pass=$(( ${ran:-0} - ${fail:-0} )) ;;
    *)
      if grep -q '^# pass' <<<"$out"; then            # node --test
        pass=$(grep -oE '^# pass [0-9]+' <<<"$out" | grep -oE '[0-9]+')
        fail=$(grep -oE '^# fail [0-9]+' <<<"$out" | grep -oE '[0-9]+')
      else                                            # vitest
        pass=$(grep -E '^ *Tests ' <<<"$out" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+')
        fail=$(grep -E '^ *Tests ' <<<"$out" | grep -oE '[0-9]+ failed' | grep -oE '[0-9]+')
      fi ;;
  esac
  echo "${pass:-0} ${fail:-0}"
}

# 예제를 돌리는 데 필요한 도구가 있는지
missing_tool() {
  case "$1" in
    001_hr_payroll) command -v mvn >/dev/null || echo mvn ;;
    002_fi_ledger|008_youtube_analyzer) [[ -x "$ROOT/$1/.venv/bin/python" ]] || echo ".venv(README 의 설치 절차)" ;;
    005_inventory_api) command -v go >/dev/null || echo go ;;
    007_attendance_cli) command -v cargo >/dev/null || echo cargo ;;
    012_hybrid_slm_pipeline) command -v python3 >/dev/null || echo python3 ;;
    *) # 외부 패키지가 있는 예제만 node_modules 가 필요하다(009·010·011 은 node 내장 기능만 쓴다)
       if node -e 'const p=require(process.argv[1]);process.exit(Object.keys({...p.dependencies,...p.devDependencies}).length?0:1)' "$ROOT/$1/package.json"; then
         [[ -d "$ROOT/$1/node_modules" ]] || echo "node_modules(npm install)"
       fi ;;
  esac
}

if [[ $# -gt 0 ]]; then names=("$@"); else
  mapfile -t names < <(grep -oE '^\| \[0[0-9]{2}_[a-z_]+\]' "$README" | grep -oE '0[0-9]{2}_[a-z_]+')
fi

status=0; total_exp=0; total_pass=0
printf '%-26s %6s %6s %6s  %s\n' "예제" "README" "통과" "실패" "판정"
for name in "${names[@]}"; do
  exp=$(expected "$name"); exp=${exp:-?}
  [[ "$exp" =~ ^[0-9]+$ ]] && total_exp=$((total_exp + exp))
  tool=$(missing_tool "$name")
  if [[ -n "$tool" ]]; then
    printf '%-26s %6s %6s %6s  %s\n' "$name" "$exp" "-" "-" "건너뜀 : $tool 없음"
    [[ $status -eq 0 ]] && status=2; continue
  fi
  out=$(cd "$ROOT/$name" && run_tests "$name")
  read -r pass fail < <(parse "$name" "$out")
  if [[ "$fail" != 0 ]]; then verdict="실패"; status=1
  elif [[ "$pass" != "$exp" ]]; then verdict="README 와 다름"; status=1
  else verdict="일치"; fi
  printf '%-26s %6s %6s %6s  %s\n' "$name" "$exp" "$pass" "$fail" "$verdict"
  total_pass=$((total_pass + pass))
done
printf '%-26s %6s %6s\n' "합계" "$total_exp" "$total_pass"
exit $status
