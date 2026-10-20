import json
t=json.load(open(r'C:\ipo_cache\dash\new.json',encoding='utf-8'))['text']
def rep(a,b,cnt=1):
    global t
    assert t.count(a)==cnt,(t.count(a),a[:70]); t=t.replace(a,b)
# KPI calcs only over complete rows
rep("fn:(screen)=>[\n {k:'total'","fn:(all)=>{const screen=all.filter(r=>r.unknown===0);return [\n {k:'total'")
rep("{k:'live',n:screen.filter(r=>r.group==='Open / upcoming').length}]});","{k:'live',n:screen.filter(r=>r.group==='Open / upcoming').length}];}});")
rep("fn:(screen)=>['f1','f2','f3','f4','f5','f6','f7','f8'].map(f=>({filter:f,pass:screen.filter(r=>r[f]==='P').length,fail:screen.filter(r=>r[f]==='F').length,unknown:screen.filter(r=>r[f]==='U').length}))});","fn:(all)=>{const screen=all.filter(r=>r.unknown===0);return ['f1','f2','f3','f4','f5','f6','f7','f8'].map(f=>({filter:f,pass:screen.filter(r=>r[f]==='P').length,fail:screen.filter(r=>r[f]==='F').length,unknown:screen.filter(r=>r[f]==='U').length}));}});")
rep("fn:(screen)=>[0,1,2,3,4,5,6,7,8].map(p=>({passed:p,n:screen.filter(r=>r.passed===p).length}))});","fn:(all)=>{const screen=all.filter(r=>r.unknown===0);return [0,1,2,3,4,5,6,7,8].map(p=>({passed:p,n:screen.filter(r=>r.passed===p).length}));}});")
# page shows only complete rows; pending listed
rep("const rows=ok?sc.data:[];\n if(ok){drawTop(rows);","const allr=ok?sc.data:[];const rows=allr.filter(r=>r.unknown===0);const pend=allr.filter(r=>r.unknown>0);\n if(ok){drawTop(rows,pend);")
rep("function drawTop(rows){","function drawTop(rows,pend){")
rep("""  ban.className='ban bad sec';$('ban-h').textContent='Today’s answer: do not apply to any open or upcoming IPO';
  $('ban-p').textContent='All '+open.length+' IPOs still open for bidding fail at least one of your 8 checks.'+(best?' The closest is '+best.company+' with '+best.passed+' of 8 passed.':'')+' Checks marked not verified need the RHP.';}""","""  ban.className='ban warn sec';$('ban-h').textContent='Only IPOs with all 8 checks verified are shown';
  $('ban-p').textContent=pend.length+' IPOs are hidden until no check is left as “?”: '+pend.map(r=>r.company+' ('+(r.group==='Listed'?'listed':(r.status||'upcoming').toLowerCase())+')').join(', ')+'. Open and upcoming IPOs cannot be complete before bidding closes and the RHP is filed.';
  if(!live.length)document.getElementById('live').parentElement.style.display='none';}""")
rep("const act1=live.filter","if(!live.length)document.getElementById('live').parentElement.style.display='none';\n const act1=live.filter")
json.dump({'text':t},open(r'C:\ipo_cache\dash\new2.json','w',encoding='utf-8'))
print('ok')
