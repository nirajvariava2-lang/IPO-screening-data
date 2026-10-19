import json
from datetime import datetime, timezone, timedelta
ev=json.load(open(r'C:\ipo_cache\evidence.json'))
d=json.load(open('data.json',encoding='utf-8'))
IST=timezone(timedelta(hours=5,minutes=30))
SRC={'f5':'debt/equity and operating cash flow','f7':'post-issue promoter holding and pledge','f8':'anchors and auditor opinion'}
for r in d['rows']:
    c=r['company']; e=ev.get(c,{}); r.setdefault('sources',{})
    if c=='Deepa Jewellers':
        if r['f5']=='U':
            r['f5']='F'; r['sources']['f5']='DRHP (SEBI, 2 Jan 2026) p.269: net cash from operating activities Rs (142.60) mn H1 FY26, (98.64) mn FY25 - negative; D/E 0.55 (p.119)'
        if r['f8']=='U':
            r['f8']='P'; r['sources']['f8']='Soft pass: auditors no qualification (DRHP p.27); anchor portion in offer structure (p.3). Confirm allocation in RHP'
        r['sources']['f7']='Pledge: none (DRHP p.99). Post-issue holding blank until price band'
    if c in('Jio Platforms','Tonbo Imaging'):
        r['sources']['f8']='Auditors: no qualification (abridged prospectus p.11-12). Anchors not disclosed until RHP'
    if c in('Zetwerk Manufacturing','Paras Healthcare','Jio Platforms','Tonbo Imaging','Deepa Jewellers'):
        pass
    reasons={}
    for k in ('f5','f7','f8'):
        if r.get(k)=='U':
            if e.get('status')!='ok': reasons[k]='No offer document on SEBI site'
            elif e.get('cur_fixed') or c in('Zetwerk Manufacturing','Paras Healthcare','Jio Platforms','Tonbo Imaging','Deepa Jewellers'):
                reasons[k]=f'Not in SEBI {e["doc_title"][:40]} ({e["doc_date"]}); needs RHP / price band'
            else:
                reasons[k]=f'SEBI filing is DRHP dated {e["doc_date"]} with financials to FY{e.get("fy_fixed")} (older than FY26); RHP not on SEBI'
    if reasons: r['u_reasons']=reasons
    r['passed']=sum(r[f'f{i}']=='P' for i in range(1,9)); r['fails']=sum(r[f'f{i}']=='F' for i in range(1,9)); r['unknown']=sum(r[f'f{i}']=='U' for i in range(1,9))
    if c=='Deepa Jewellers': r['verdict']='Review' if r['passed']>=3 else 'Rejected'
now=datetime.now(IST)
d['as_of']=now.isoformat(timespec='seconds'); d['as_of_label']=now.strftime('%a %d %b %Y, %H:%M IST')
d['sebi_note']='Only filings with FY26+ financials used for F5-F8. 51/53 IPOs have SEBI filings; most are older DRHPs. See u_reasons.'
json.dump(d,open('data.json','w',encoding='utf-8'),indent=1,ensure_ascii=False)
print(d['as_of_label'], sum(1 for r in d['rows'] if r.get('u_reasons')),'rows with reasons')
dm=[r for r in d['rows'] if r['company']=='Deepa Jewellers'][0]; print(dm['f1'],dm['f2'],dm['f3'],dm['f4'],dm['f5'],dm['f6'],dm['f7'],dm['f8'],dm['passed'],dm['verdict'])
