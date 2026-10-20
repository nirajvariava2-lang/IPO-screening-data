"""Merge metrics.json + screener.json into data.json rows as row['m'] (dict of display numbers)."""
import json,re
d=json.load(open('data.json',encoding='utf-8'))
M=json.load(open(r'C:\ipo_cache\metrics.json')); S=json.load(open(r'C:\ipo_cache\screener.json'))
KEEP=['price_band','issue_price','lot','sale_type','dates','listed_on','issue_cr','fresh_cr','ofs_cr','fresh_pct','objects','pe_pre','pe_post','eps_pre','eps_post','mcap_pre','mcap_post','promoter_pre','promoter_post','anchor_cr','sub_total','sub_qib','sub_nii','sub_retail','rev_cagr','pat_cagr','revenue','pat','periods','borrowing','networth','de_calc']
for r in d['rows']:
    x=M.get(r['company'],{}); m={k:x[k] for k in KEEP if x.get(k) is not None}
    kp=x.get('kpi') or {}
    for k,lab in (('roe','ROE'),('roce','ROCE'),('ronw','RoNW'),('pat_margin','PAT Margin'),('ebitda_margin','EBITDA Margin')):
        if lab in kp:
            v=[t for t in kp[lab] if t]; 
            if v: m[k]=v[0]
    s=S.get(r['company'])
    if s and s.get('equity'):
        m['de']=round(s['debt']/s['equity'],2); m['de_period']=s['period']; m['ocf']=s['ocf']; m['ocf_period']=s['period']
    elif m.get('de_calc') is not None:
        m['de']=m['de_calc']; m['de_period']='latest restated period (borrowing / net worth)'
    # fall back to numbers quoted in the F5 source note
    src=(r.get('sources') or {}).get('f5','')
    mo=re.search(r'operating cash flow (?:Rs )?\(?(-?[\d,\.]+)\)?\s*(mn|cr)?',src)
    if 'ocf' not in m and mo:
        v=float(mo.group(1).replace(',',''));
        if '(' in mo.group(0): v=-abs(v)
        m['ocf']=v; m['ocf_unit']=mo.group(2) or ''
    r['m']=m
json.dump(d,open('data.json','w',encoding='utf-8'),indent=1,ensure_ascii=False)
print(sum(1 for r in d['rows'] if r['m'].get('de') is not None),'with D/E;',sum(1 for r in d['rows'] if r['m'].get('ocf') is not None),'with OCF;',sum(1 for r in d['rows'] if r['m'].get('pe_post') is not None),'with PE')
