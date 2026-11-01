# idle-cost.py (2026-10-14) : 세션 기록에서 「1시간 넘게 쉬었다가 다시 부른 턴」의 캐시 쓰기 비용 비중을 잰다 (Opus 단가 비율만 사용 : 입력 1, 캐시쓰기 2, 캐시읽기 0.1, 출력 5)
import json, sys, glob, os
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')
import os.path
d = sys.argv[1] if len(sys.argv)>1 else os.path.expanduser('~/.claude/projects')  # 프로젝트 기록 폴더(…/projects/<폴더>)를 넘긴다
files = sorted(glob.glob(d + '/**/*.jsonl', recursive=True), key=os.path.getmtime)[-12:]
tot = {'idle':0.0,'warm':0.0}; cw = {'idle':0.0,'warm':0.0}; n={'idle':0,'warm':0}
for f in files:
    prev = None; seen=set()
    for line in open(f, encoding='utf-8', errors='ignore'):
        try: o = json.loads(line)
        except: continue
        if o.get('type')!='assistant' or o.get('isSidechain'): continue
        m = o.get('message',{}); u = m.get('usage'); mid=m.get('id')
        if not u or mid in seen: continue
        seen.add(mid)
        t = datetime.fromisoformat(o['timestamp'].replace('Z','+00:00'))
        gap = (t-prev).total_seconds()/60 if prev else 0; prev = t
        k = 'idle' if gap>60 else 'warm'
        c = u.get('input_tokens',0)*1 + u.get('cache_creation_input_tokens',0)*2 + u.get('cache_read_input_tokens',0)*0.1 + u.get('output_tokens',0)*5
        tot[k]+=c; cw[k]+=u.get('cache_creation_input_tokens',0)*2; n[k]+=1
T = tot['idle']+tot['warm']
print('파일',len(files),'턴 수',n)
print('1시간 넘게 쉬고 깨운 턴의 비용 비중 : %.1f%%' % (100*tot['idle']/T))
print('전체 중 캐시 쓰기 비중 : %.1f%%' % (100*(cw['idle']+cw['warm'])/T))
print('깨운 턴 1회 평균 비용 / 이어지는 턴 평균 비용 : %.0f배' % ((tot['idle']/max(n['idle'],1))/(tot['warm']/max(n['warm'],1))))
