import json,re,time,requests
from bs4 import BeautifulSoup
h={'User-Agent':'Mozilla/5.0'}
d=json.load(open('data.json',encoding='utf-8'))
SLUG={'HD Fire Protect':'hd-fire-protect-ipo','Zetwerk Manufacturing':'zetwerk-manufacturing-businesses-ipo','Jio Platforms':'jio-platforms-ipo','Paras Healthcare':'paras-healthcare-ipo','SRIT India':'srit-india-ipo','Rays of Belief':'rays-of-belief-ipo','German Green Steel':'german-green-steel-and-power-ipo','SS Retail':'ss-retail-ipo','ESDS Software':'esds-software-solutions-ipo','Kanohar Electricals':'kanohar-electricals-ipo','Glass Wall Systems':'glass-wall-systems-india-ipo','Shiprocket':'shiprocket-ipo'}
def num(x):
    try: return int(re.sub(r'[^\d]','',x))
    except: return None
res={}
for r in d['rows']:
    c=r['company']
    m=re.search(r'chittorgarh\.com/ipo/([^/]+)/(\d+)',r.get('source_url',''))
    u=f"https://www.chittorgarh.com/ipo/{m.group(1)}/{m.group(2)}/" if m else f"https://www.chittorgarh.com/ipo/{SLUG.get(c)}/"
    try:
        rr=requests.get(u,headers=h,timeout=60,allow_redirects=True)
    except Exception as e: print('ERR',c,e); continue
    s=BeautifulSoup(rr.text,'html.parser')
    pre=post=anch=None; tot=None; closes=None
    for tb in s.find_all('table'):
        rows=[[x.get_text(' ',strip=True) for x in tr.find_all(['th','td'])] for tr in tb.find_all('tr')]
        for x in rows:
            if not x: continue
            if x[0].startswith('Promoter') and len(x)==3 and '%' in x[1] and '%' in x[2]:
                pre,post=float(x[1].strip('%')),float(x[2].strip('%'))
            if re.search(r'Anchor (Investor$|Investor Shares Offered|Portion)',x[0].lstrip('− -')) and len(x)>1 and anch is None:
                v=re.sub(r'[^\d.]','',x[1]); anch=float(v) if v else anch
            if x[0].startswith('IPO Closes On') or x[0].startswith('IPO Close'): closes=x[1]
            if x[0]=='No. of times subscribed' and len(x)>1: tot=x[-1]
    res[c]={'url':rr.url,'pre':pre,'post':post,'anchor':anch,'closes':closes}
    print(f"{c:28} pre={pre} post={post} anchor={anch} closes={closes}")
    time.sleep(0.6)
json.dump(res,open(r'C:\ipo_cache\chitt.json','w'))


