import json
p=r'C:\ipo_cache\dash\index.html'
t=open(p,encoding='utf-8').read()
def rep(a,b):
    global t
    assert t.count(a)==1,(t.count(a),a[:60]); t=t.replace(a,b)
rep('<div class="asof">Data as of Sun 18 Oct 2026, 07:55 IST<br>','<div class="asof">Data as of <span id="asof">…</span><br>')
rep('.fc.P{color:var(--color-ok)}','.fc.old{opacity:.5}.fc small{display:block;font-size:.6rem;font-weight:400;color:var(--color-fg-muted);line-height:1}.fc.P{color:var(--color-ok)}')
rep('.meter i.P{background:var(--color-ok)}','.meter i.old{opacity:.45}.meter i.P{background:var(--color-ok)}')
rep("const i=document.createElement('i');i.className=r[f];m.append(i);","const i=document.createElement('i');i.className=r[f]+(r['old_'+f]?' old':'');m.append(i);")
rep("s.className='fc '+r[f];s.textContent=sym(r[f]);td.append(s);tr.append(td);","s.className='fc '+r[f]+(r['old_'+f]?' old':'');s.textContent=sym(r[f]);if(r['old_'+f]){const sm=document.createElement('small');sm.textContent=r['old_'+f]==='total only'?'total':r['old_'+f];s.append(sm);}td.title=r['src_'+f]||'';td.append(s);tr.append(td);")
rep("const c=document.createElement('span');c.className='fc '+r[f];c.textContent=sym(r[f]);fl.append(a,b,c);});","const c=document.createElement('span');c.className='fc '+r[f]+(r['old_'+f]?' old':'');c.textContent=sym(r[f])+(r['old_'+f]?' '+r['old_'+f]:'');fl.append(a,b,c);if(r['src_'+f]){const n=document.createElement('div');n.style.cssText='grid-column:1/-1;color:var(--color-fg-muted);font-size:.7rem;margin:-2px 0 4px';n.textContent=r['src_'+f];fl.append(n);}});")
rep("if(ok)drawTop(rows);","if(ok){drawTop(rows);if(rows[0])$('asof').textContent=rows[0].as_of_label;}")
rep("<p>F3, F5, F7 and F8 need the RHP. Until checked they stay “?”.</p>","<p><b>Lighter ✓/✕ with a year (e.g. FY25)</b> means the value comes from an older SEBI draft offer document (DRHP), not the final RHP. “total” on F4 means overall subscription only; the QIB split was not available. Hover a cell or open a row for the source. “?” rows give the reason in the detail panel.</p>")
json.dump({'text':t},open(r'C:\ipo_cache\dash\new.json','w',encoding='utf-8'))
print(len(t))
