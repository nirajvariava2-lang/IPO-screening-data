import json,re,sys
sys.path.insert(0,'scripts')
import derive, extract, sebi
d=json.load(open('data.json',encoding='utf-8'))
sc=json.load(open(r'C:\ipo_cache\screener.json'))
ch=json.load(open(r'C:\ipo_cache\chitt.json'))
ev=json.load(open(r'C:\ipo_cache\evidence.json'))
QUAL=r"(?:no|not (?:provided|expressed|included|contain|contained)[^.]{0,40}any|not any|without any|nil)[ \-]*(?:audit\s*)?(?:qualification|qualified opinion|adverse remark|reservation)|unmodified (?:audit )?opinion|unqualified"
for r in d['rows']:
    c=r['company']; r.setdefault('sources',{}); r.setdefault('stale',{}); e=ev.get(c,{})
    s=sc.get(c)
    if r['f5']=='U' and s and s['equity']>0 and s['ocf'] is not None:
        de=round(s['debt']/s['equity'],2); ok=de<=1 and s['ocf']>0
        r['f5']='P' if ok else 'F'
        r['sources']['f5']=f"{s['period']} (Screener {s['url']}): borrowings {s['debt']:g} / equity {s['equity']:g} = D/E {de}; operating cash flow {s['ocf']:g} cr"
    if r['f8']=='U' and e.get('status')=='ok':
        pgs=extract.pages(sebi.CACHE/re.sub(r'[^A-Za-z0-9._-]','_',e['pdf'].split('/')[-1]))
        x=ch.get(c,{}); anchor=x.get('anchor') or derive.anchor_in_structure(pgs[:60])
        hit=extract.grep(pgs,QUAL,0,limit=1)
        if anchor and hit:
            tag=f"FY{str(e.get('fy_fixed'))[2:]}" if e.get('fy_fixed') else 'older'
            r['f8']='P'; r['sources']['f8']=f"Anchor allocation exists; no auditor qualification (SEBI {e['doc_title'][:30]} p.{hit[0][0]}). Confirm in RHP"; r['stale']['f8']=tag
for r in d['rows']:
    r['passed']=sum(r[f'f{i}']=='P' for i in range(1,9)); r['fails']=sum(r[f'f{i}']=='F' for i in range(1,9)); r['unknown']=sum(r[f'f{i}']=='U' for i in range(1,9))
    r['verdict']=derive.verdict(r)
    r['u_reasons']={k:(r['sources'].get(k) or 'Not available from SEBI/NSE sources yet') for k in ('f1','f2','f3','f4','f5','f6','f7','f8') if r[k]=='U'}
json.dump(d,open('data.json','w',encoding='utf-8'),indent=1,ensure_ascii=False)
for k in ('f2','f3','f4','f5','f6','f7','f8'): print(k,'U=',sum(r[k]=='U' for r in d['rows']))
for r in d['rows']:
    if r['unknown']: print(f"{r['company']:28} {r.get('status') or 'Listed':24}", ''.join(r[f'f{i}'] for i in range(1,9)))
