import json,re,sys
sys.path.insert(0,'scripts')
import derive, extract, sebi
d=json.load(open('data.json',encoding='utf-8'))
ch=json.load(open(r'C:\ipo_cache\chitt.json'))
ev=json.load(open(r'C:\ipo_cache\evidence.json'))
for r in d['rows']:
    c=r['company']; x=ch.get(c,{}); e=ev.get(c,{}); r.setdefault('sources',{}); r.setdefault('stale',{})
    pgs=None
    if e.get('status')=='ok' and e['pages']>=100:
        pgs=extract.pages(sebi.CACHE/re.sub(r'[^A-Za-z0-9._-]','_',e['pdf'].split('/')[-1]))
    tag=f"FY{str(e.get('fy_fixed'))[2:]}" if e.get('fy_fixed') else 'older'
    cu=x.get('url','')
    if r['f7']=='U' and x.get('post') is not None:
        post=x['post']; pn=derive.pledge_none(pgs) if pgs else None
        if post<50:
            r['f7']='F'; r['sources']['f7']=f"Promoter holding after issue {post}% (pre {x['pre']}%) - Chittorgarh {cu}"
        else:
            r['f7']='P'; r['sources']['f7']=f"Promoter holding after issue {post}% (pre {x['pre']}%) - Chittorgarh {cu}; "+(f"no pledge per SEBI DRHP p.{pn}" if pn else "pledge not confirmed in DRHP text")
            r['stale']['f7']=tag if pn else 'pledge unconfirmed'
    if r['f8']=='U' and x.get('anchor'):
        nq=derive.no_qualification(pgs) if pgs else None
        if nq:
            r['f8']='P'; r['sources']['f8']=f"Anchor allocation exists (Chittorgarh {cu}); no auditor qualification (SEBI DRHP p.{nq}). Confirm in RHP"; r['stale']['f8']=tag
for r in d['rows']:
    r['passed']=sum(r[f'f{i}']=='P' for i in range(1,9)); r['fails']=sum(r[f'f{i}']=='F' for i in range(1,9)); r['unknown']=sum(r[f'f{i}']=='U' for i in range(1,9))
    r['verdict']=derive.verdict(r)
json.dump(d,open('data.json','w',encoding='utf-8'),indent=1,ensure_ascii=False)
for k in ('f2','f3','f4','f5','f6','f7','f8'): print(k,'U=',sum(r[k]=='U' for r in d['rows']))
print('rows with any U:',sum(1 for r in d['rows'] if r['unknown']))
for r in d['rows']:
    if r['unknown']: print(f"{r['company']:28} {r['status'] or 'Listed':22}", ''.join(r[f'f{i}'] for i in range(1,9)))
