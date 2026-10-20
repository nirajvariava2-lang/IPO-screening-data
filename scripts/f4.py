import json,re,sys,time,requests
from bs4 import BeautifulSoup
h={'User-Agent':'Mozilla/5.0'}
d=json.load(open('data.json',encoding='utf-8'))
def f(x):
    try: return float(re.sub(r'[^\d.]','',x))
    except: return None
n=0
for r in d['rows']:
    if r['f4']!='U' or r.get('status') in ('Open now','Upcoming'): continue
    m=re.search(r'chittorgarh\.com/ipo/([^/]+)/(\d+)',r.get('source_url',''))
    if not m: continue
    u=f"https://www.chittorgarh.com/ipo_subscription/{m.group(1)}/{m.group(2)}/"
    t=requests.get(u,headers=h,timeout=60).text
    s=BeautifulSoup(t,'html.parser'); tot=None
    for tb in s.find_all('table'):
        for tr in tb.find_all('tr'):
            c=[x.get_text(' ',strip=True) for x in tr.find_all(['th','td'])]
            if c and c[0]=='No. of times subscribed' and f(c[-1]): tot=f(c[-1])
            if c and c[0]=='Total' and len(c)==2 and 'x' in c[1] and tot is None: tot=f(c[1])
    if tot is None: print('no data',r['company']); continue
    r['f4']='P' if tot>=3 else 'F'
    r.setdefault('sources',{})['f4']=f"Final subscription {tot:g}x overall (Chittorgarh {u}); QIB split not shown on page, so QIB demand not separately verified"
    r.setdefault('soft',{})['f4']='total only'
    n+=1; print(f"{r['company']:28} {tot:g}x -> {r['f4']}"); time.sleep(0.7)
json.dump(d,open('data.json','w',encoding='utf-8'),indent=1,ensure_ascii=False)
print(n,'filled')
