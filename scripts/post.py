import json,re,sys
from collections import Counter
from datetime import datetime
sys.path.insert(0,'scripts')
import extract, sebi
ev=json.load(open(r'C:\ipo_cache\evidence.json'))
for c,e in ev.items():
    if e.get('status')!='ok': print(f"{c:28} {e['status']}"); continue
    pgs=extract.pages(sebi.CACHE / re.sub(r'[^A-Za-z0-9._-]','_',e['pdf'].split('/')[-1]))
    cnt=Counter()
    for t in pgs[:200]:
        for y in re.findall(r"(?:March|June|September|December)\s+3[01],\s+(20\d\d)",t): cnt[int(y)]+=1
    d=datetime.strptime(e['doc_date'],'%b %d, %Y')
    ys=[y for y,n in cnt.items() if n>=5 and y<=d.year]
    fy=max(ys) if ys else None
    e['fy_fixed']=fy; e['cur_fixed']=bool(fy and fy>=2026)
    print(f"{c:28} {e['doc_date']:13} {e['doc_title'][:34]:34} fy={fy} cur={e['cur_fixed']} pages={e['pages']}")
json.dump(ev,open(r'C:\ipo_cache\evidence.json','w'),indent=1)
print(sum(1 for e in ev.values() if e.get('cur_fixed')),'current')

