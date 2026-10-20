import json
d=json.load(open('data.json',encoding='utf-8'))
out=[]
for r in d['rows']:
    x={k:v for k,v in r.items() if k not in('sources','stale','soft','u_reasons')}
    x['as_of_label']=d['as_of_label']
    for k in ('f1','f2','f3','f4','f5','f6','f7','f8'):
        st=(r.get('stale') or {}).get(k) or ('total only' if (r.get('soft') or {}).get(k) else '')
        x['old_'+k]=st
        x['src_'+k]=(r.get('sources') or {}).get(k) or (r.get('u_reasons') or {}).get(k,'') if r[k]!='P' or True else ''
    out.append(x)
json.dump(out,open('ipo_screen_v3.json','w',encoding='utf-8'),ensure_ascii=False)
print(len(out), sum(1 for x in out for k in ('f4','f5','f7','f8') if x['old_'+k]),'older-data cells')
