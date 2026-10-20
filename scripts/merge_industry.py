"""Add industry P/E comparison: row['f3_ind'] (P/F vs industry median) and m.ind_* numbers."""
import json
d=json.load(open('data.json',encoding='utf-8')); I=json.load(open(r'C:\ipo_cache\industry.json'))
chg=0
for r in d['rows']:
    m=r.setdefault('m',{}); i=I.get(r['company'],{}); pe=m.get('pe_post')
    r['f3_ind']=r['f3']
    if i.get('median_pe') and pe is not None:
        m.update({'ind_name':i['industry'],'ind_pe':i['median_pe'],'ind_n':i['peers']})
        if i.get('current_pe') is not None: m['cur_pe']=i['current_pe']
        m['rel']=round(pe/i['median_pe'],2) if pe>0 else None
        r['f3_ind']='P' if (pe>0 and pe<=i['median_pe']) else 'F'
        chg+= r['f3_ind']!=r['f3']
    elif i.get('median_pe'):
        m.update({'ind_name':i['industry'],'ind_pe':i['median_pe'],'ind_n':i['peers']})
json.dump(d,open('data.json','w',encoding='utf-8'),indent=1,ensure_ascii=False)
rows=d['rows']
print('industry P/E for',sum(1 for r in rows if 'ind_pe' in r['m']),'IPOs;','F3 result differs vs 25x rule for',chg)
for r in rows:
    if r['f3_ind']!=r['f3']: print(f"  {r['company']:26} 25x:{r['f3']} industry:{r['f3_ind']}  P/E {r['m'].get('pe_post')} vs {r['m'].get('ind_pe')}")
