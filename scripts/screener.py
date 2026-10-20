import json,re,time,requests
from bs4 import BeautifulSoup
h={'User-Agent':'Mozilla/5.0'}
d=json.load(open('data.json',encoding='utf-8'))
ch=json.load(open(r'C:\ipo_cache\chitt.json'))
def n(x):
    try: return float(x.replace(',','').replace('%',''))
    except: return None
out={}
for r in d['rows']:
    c=r['company']
    if r['f5']!='U': continue
    u=ch.get(c,{}).get('url')
    if not u or 'ipo/' not in u: continue
    s=BeautifulSoup(requests.get(u,headers=h,timeout=60).text,'html.parser')
    sym=None
    for tr in s.find_all('tr'):
        x=[t.get_text(' ',strip=True) for t in tr.find_all(['th','td'])]
        if x and x[0].startswith('BSE Script Code'): sym=x[1]
    if not sym: print(c,'no symbol'); continue
    parts=[p.strip() for p in sym.split('/')]
    codes=[p for p in parts[::-1] if p and p!='NA']
    got=None
    for code in codes:
        for suf in ('consolidated/','') :
            rr=requests.get(f"https://www.screener.in/company/{code}/{suf}",headers=h,timeout=60)
            if rr.status_code!=200: continue
            sp=BeautifulSoup(rr.text,'html.parser')
            def row(sec,label):
                tb=sp.select_one(f'#{sec} table')
                if not tb: return None
                hdr=[t.get_text(strip=True) for t in tb.find('thead').find_all('th')]
                for tr in tb.find_all('tr'):
                    x=[t.get_text(' ',strip=True) for t in tr.find_all(['th','td'])]
                    if x and x[0].startswith(label) and len(x)>2:
                        return hdr,x
            b=row('balance-sheet','Borrowings'); eq=row('balance-sheet','Equity Capital'); rs=row('balance-sheet','Reserves'); cf=row('cash-flow','Cash from Operating')
            if b and eq and rs and cf:
                hdr=b[0]; i=len(hdr)-1
                while i>0 and n(b[1][i]) is None: i-=1
                debt=n(b[1][i]); equity=(n(eq[1][i]) or 0)+(n(rs[1][i]) or 0); ocf=n(cf[1][i]) if i<len(cf[1]) else None
                got={'code':code,'url':rr.url,'period':hdr[i],'debt':debt,'equity':equity,'ocf':ocf}
                break
        if got: break
    out[c]=got; print(f"{c:26} {sym:22} {got}"); time.sleep(1)
json.dump(out,open(r'C:\ipo_cache\screener.json','w'))
