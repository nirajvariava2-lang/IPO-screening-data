import json,re,sys
sys.path.insert(0,'scripts')
import derive,extract,sebi
d=json.load(open('data.json',encoding='utf-8')); ev=json.load(open(r'C:\ipo_cache\evidence.json'))
n=0
for r in d['rows']:
    m=r['m']; e=ev.get(r['company'],{})
    if 'ocf' in m or e.get('status')!='ok' or e['pages']<100: continue
    pgs=extract.pages(sebi.CACHE/re.sub(r'[^A-Za-z0-9._-]','_',e['pdf'].split('/')[-1]))
    o=derive.opcf(pgs)
    if o: m['ocf']=o[1][0]; m['ocf_unit']='mn'; m['ocf_period']=f"FY{str(e.get('fy_fixed'))[2:]} DRHP" if e.get('fy_fixed') else 'DRHP'; n+=1
json.dump(d,open('data.json','w',encoding='utf-8'),indent=1,ensure_ascii=False)
print(n,'OCF added;',sum(1 for r in d['rows'] if 'ocf' in r['m']),'total')
