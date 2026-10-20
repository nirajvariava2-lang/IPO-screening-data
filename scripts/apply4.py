import json,sys
sys.path.insert(0,'scripts')
import derive
d=json.load(open('data.json',encoding='utf-8'))
R={r['company']:r for r in d['rows']}
def setf(c,k,v,src,tag=None):
    r=R[c]; r[k]=v; r.setdefault('sources',{})[k]=src
    if tag: r.setdefault('stale',{})[k]=tag
setf('Fusion CX','f5','P','FY25 (SEBI DRHP p.295): operating cash flow Rs 1,012.46 mn positive; D/E 0.48 (266.86/552.46, from filing summary)','FY25')
setf('Nityas Gems & Jewellery','f2','P','Fresh issue only; proceeds for working capital (up to Rs 700 mn) and general corporate purposes; no debt repayment or OFS (SEBI abridged prospectus p.4)','FY25')
setf('Nityas Gems & Jewellery','f6','P','Revenue Rs 116.7 mn (FY23) to Rs 968.5 mn (FY25); PAT Rs 2.5 mn to Rs 97.9 mn (SEBI abridged prospectus p.6)','FY25')
setf('Nityas Gems & Jewellery','f8','F','No anchor allocation shown for this issue on Chittorgarh (QIB ex-anchor 1.06x); auditors report no qualification (SEBI abridged p.9)')
setf('Rentomojo','f8','F','SEBI DRHP (abridged p.11) refers to auditor qualifications given effect in the restated financials; see DRHP pages 246 and 334')
setf('Kanohar Electricals','f8','P','Soft pass: anchor Rs 316.72 cr allocated (Chittorgarh); no auditor qualification reported in RHP summaries; RHP text not read. Confirm in RHP','RHP unread')
for r in d['rows']:
    r['passed']=sum(r[f'f{i}']=='P' for i in range(1,9)); r['fails']=sum(r[f'f{i}']=='F' for i in range(1,9)); r['unknown']=sum(r[f'f{i}']=='U' for i in range(1,9))
    r['verdict']=derive.verdict(r)
    r['u_reasons']={k:(r['sources'].get(k) or 'Not available yet') for k in ('f1','f2','f3','f4','f5','f6','f7','f8') if r[k]=='U'}
json.dump(d,open('data.json','w',encoding='utf-8'),indent=1,ensure_ascii=False)
inc=[r['company'] for r in d['rows'] if r['unknown']]
print(len(d['rows'])-len(inc),'complete;',len(inc),'pending:',inc)
