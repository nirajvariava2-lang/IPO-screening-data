import json
d=json.load(open('data.json',encoding='utf-8'))
out=[]
for r in d['rows']:
    x={k:v for k,v in r.items() if k not in('sources','stale','soft','u_reasons','m')}
    x['as_of_label']=d['as_of_label']; x['m']=json.dumps(r.get('m',{}),ensure_ascii=False,separators=(',',':'))
    for k in ('f1','f2','f3','f4','f5','f6','f7','f8'):
        x['old_'+k]=(r.get('stale') or {}).get(k) or ('total only' if (r.get('soft') or {}).get(k) else '')
        x['src_'+k]=(r.get('sources') or {}).get(k) or (r.get('u_reasons') or {}).get(k,'')
    out.append(x)
json.dump(out,open('ipo_screen_v3.json','w',encoding='utf-8'),ensure_ascii=False)
print(len(out))
