#!/usr/bin/env bash
# 저장소 자가 점검 : 공개 저장소에 있으면 안 되는 것(해로운 것)과 정리할 것(불필요·중복)을 찾아 보고만 한다.
# 지우거나 고치는 일은 하지 않는다. 결과를 보고 사람이(또는 점검을 맡은 세션이) 판단해 정리한다.
#
# 사용법 : bash tools/self-check.sh            # 빠른 점검(수 초)
#          bash tools/self-check.sh --tests    # 예제 14개 시험 수 대조까지(1분 안팎)
# 종료 코드 : 0 걸린 것 없음 / 1 해로운 것(반드시 처리) / 3 정리 후보만 있음
#
# 금지 이름(이 저장소에서 빼기로 한 모델·도구·상용 제품) 목록은 공개 저장소에 글자로 남기지 않으려고
# 소문자 단어의 sha256 앞 16자리로만 적는다. 새 이름을 더하려면 :
#   python3 -c "import hashlib;print(hashlib.sha256('이름'.lower().encode()).hexdigest()[:16])"

set -u
cd "$(dirname "$0")/.." || exit 2

python3 - "$@" <<'PY'
import hashlib, re, subprocess, sys
from collections import defaultdict

HARM, TIDY = [], []          # 해로운 것 / 정리 후보
def git(*a):
    return subprocess.run(['git', *a], capture_output=True, text=True).stdout
files = [f for f in git('ls-files').splitlines() if 'node_modules/' not in f]

# 1) 해로운 것 ---------------------------------------------------------------
SECRET = re.compile(r'sk-ant-[A-Za-z0-9_-]{10}|AKIA[0-9A-Z]{16}|BEGIN (RSA|OPENSSH|EC) PRIVATE|ghp_[A-Za-z0-9]{30}|xox[bp]-[0-9]')
BANNED = {  # 해시 → 분류
    '0bc3c605e8ed7d61': '중국 계열', '9e66a118b9a0fb8c': '중국 계열', '6f7ac1823da81d2e': '중국 계열',
    '67f2d22514622d1b': '중국 계열', 'e4f9c522e1c89280': '중국 계열', 'fb49d6d5dd712290': '중국 계열',
    '2a62945e88351cb2': '중국 계열', '3669ffb921cca6ee': '중국 계열', '9b4cc9f33a3ba132': '중국 계열',
    '7d7ec221a4472494': '중국 계열', '32161e08e0f2abdf': '중국 계열', 'd9d95432b8952786': '중국 계열',
    'ccb0921c69850177': '중국 계열', '93430e07b4eb7ecd': '중국 계열', 'db891901f4b59543': '중국 계열',
    '0882d0ba2fbfd04d': '상용 제품', '6c01afcffcaf79d5': '상용 제품', 'b04b52f3cf7b0705': '상용 제품',
    '37fb76df3bbabc90': '상용 제품', '98385778976b5ef1': '상용 제품', '79886c7ff2de6c0e': '상용 제품',
    'da07d09708ca1697': '상용 제품', '888f2b6c91131581': '상용 제품',
}
WORD = re.compile(r'[a-z0-9]+|[가-힣]+')
for f in files:
    if f.startswith('transcripts/') and not (f.endswith('.dvl') or f.endswith('README.md')):
        HARM.append(f'평문 자막이 추적됨 : {f}')
    if re.search(r'(^|/)\.env($|\.)', f) and not re.search(r'\.(example|sample|template)$', f):
        HARM.append(f'.env 파일이 추적됨 : {f}')
    try:
        text = open(f, encoding='utf-8').read()
    except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
        continue
    for n, line in enumerate(text.splitlines(), 1):
        if SECRET.search(line):
            HARM.append(f'비밀값 모양 : {f}:{n}')
        for w in set(WORD.findall(line.lower())):
            kind = BANNED.get(hashlib.sha256(w.encode()).hexdigest()[:16])
            if kind:
                HARM.append(f'{kind} 이름 : {f}:{n}')

# 2) 정리 후보 ----------------------------------------------------------------
ART = re.compile(r'(^|/)(dist|target|\.venv|__pycache__|\.pytest_cache|output|\.hallmark)/|\.DS_Store$|\.pyc$|\.log$|~$|\.swp$')
for f in files:
    if ART.search(f):
        TIDY.append(f'빌드 산출물·임시 파일이 추적됨 : {f}')
size = {}
for line in subprocess.run(['git', 'ls-files', '-z'], capture_output=True).stdout.split(b'\0'):
    f = line.decode()
    if f and 'node_modules/' not in f:
        try:
            import os; s = os.path.getsize(f)
            if s > 1_000_000: TIDY.append(f'1MB 넘는 파일 : {f} ({s // 1024}KB)')
        except OSError: pass

# 내용이 같은 파일. 일부러 둔 것(훅, 빈 __init__.py, 스킬별 LICENSE, 예제마다 따로 두는 도우미·설정 파일)은 뺀다.
# 예제는 폴더 하나만 받아도 돌아가야 하므로 browser.mjs·pytest.ini 가 예제끼리 같아도 합치지 않는다.
INTENDED = re.compile(r'^\.githooks/|/__init__\.py$|/LICENSE(\.txt)?$|^000_sample_project/0\d\d_[^/]+/(src/browser\.mjs|pytest\.ini)$')
by_hash = defaultdict(list)
for line in git('ls-files', '-s').splitlines():
    _, h, _, f = line.split(None, 3)
    if 'node_modules/' not in f and not INTENDED.search(f):
        by_hash[h].append(f)
for fs in by_hash.values():
    if len(fs) > 1:
        TIDY.append('내용이 같은 파일 : ' + ', '.join(fs))

# 도구표에서 같은 도구가 두 행에 나오는지(첫 칸 기준)
import glob
for p in glob.glob('999_document/04_*/*.md'):
    seen = defaultdict(list)
    for n, line in enumerate(open(p, encoding='utf-8').read().splitlines(), 1):
        if line.startswith('| ') and not line.startswith('|---'):
            for name in re.split(r'\s*·\s*', line.split('|')[1].strip().strip('*')):
                key = re.sub(r'\(.*?\)|\*', '', name).strip().lower()
                if key and key not in ('도구·모델', '용도', '도구', '판정'):
                    seen[key].append(n)
    for k, ns in seen.items():
        if len(ns) > 1:
            TIDY.append(f'도구표에 두 번 나옴 : {k} ({p} {ns}줄)')

# 3) 결과 ----------------------------------------------------------------------
for x in HARM: print('[해로움]', x)
for x in TIDY: print('[정리 후보]', x)
print(f'점검 파일 {len(files)}개 · 해로움 {len(HARM)} · 정리 후보 {len(TIDY)}')
sys.exit(1 if HARM else 3 if TIDY else 0)
PY
status=$?

if [[ "${1:-}" == "--tests" ]]; then
  bash 000_sample_project/scripts/check-sample-tests.sh || { [[ $status -eq 0 ]] && status=3; }
fi
exit $status
