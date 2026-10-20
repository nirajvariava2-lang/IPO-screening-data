"""Dashboard page edit: P/E test toggle (fixed 25x vs industry median). Reads/writes C:\\ipo_cache\\dash\\*.json."""
import json

t = json.load(open(r"C:\ipo_cache\dash\new4.json", encoding="utf-8"))["text"]


def rep(a, b):
    global t
    assert t.count(a) == 1, (t.count(a), a[:80])
    t = t.replace(a, b)


# 1. toggle control
rep("""   <button class="btn" id="reset" style="margin-top:12px;width:100%">Reset filters</button>""",
    """   <div class="field" style="margin-top:12px"><label>P/E test (F3)</label>
    <div class="seg" id="pe"><button data-p="abs" class="on">Fixed 25x</button><button data-p="ind">Vs industry</button></div>
    <div class="pill" id="pe-note" style="margin-top:4px;line-height:1.4">Pass if post-issue P/E is positive and 25x or less.</div></div>
   <button class="btn" id="reset" style="margin-top:12px;width:100%">Reset filters</button>""")
rep("const S={g:'all',v:'all',q:'',minp:0,nof:'all',sort:'default',dir:1,sel:null};",
    "const S={g:'all',v:'all',q:'',minp:0,nof:'all',sort:'default',dir:1,sel:null,pe:'abs'};")
rep("Object.assign(S,{g:'all',v:'all',q:'',minp:0,nof:'all',sort:'default',dir:1});",
    "Object.assign(S,{g:'all',v:'all',q:'',minp:0,nof:'all',sort:'default',dir:1,pe:'abs'});document.querySelectorAll('#pe button').forEach(x=>x.classList.toggle('on',x.dataset.p==='abs'));")
rep("$('seg').addEventListener('click',",
    "$('pe').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;S.pe=b.dataset.p;document.querySelectorAll('#pe button').forEach(x=>x.classList.toggle('on',x===b));draw();});\n$('seg').addEventListener('click',")

# 2. effective rows in the chosen P/E mode
rep("const allr=ok?sc.data:[];allr.forEach(r=>{if(!r.mm){try{r.mm=JSON.parse(r.m||'{}')}catch(e){r.mm={}}}});const rows=allr.filter(r=>r.unknown===0);const pend=allr.filter(r=>r.unknown>0);",
    """const raw=ok?sc.data:[];raw.forEach(r=>{if(!r.mm){try{r.mm=JSON.parse(r.m||'{}')}catch(e){r.mm={}}}});
 const allr=raw.map(r=>{if(S.pe!=='ind'||!r.f3_ind||r.f3_ind===r.f3)return r;const c=Object.assign({},r,{f3:r.f3_ind});
  c.passed=FK.filter(f=>c[f]==='P').length;c.fails=FK.filter(f=>c[f]==='F').length;c.unknown=FK.filter(f=>c[f]==='U').length;
  const older=FK.some(f=>c['old_'+f]);c.verdict=(c.passed<=2||c.gov_flag)?'Rejected':(c.passed>=7&&!older)?'Qualified':c.passed>=5?'Provisional':'Review';return c;});
 const rows=allr.filter(r=>r.unknown===0);const pend=allr.filter(r=>r.unknown>0);
 $('pe-note').textContent=S.pe==='ind'?'Pass if post-issue P/E is positive and at or below the median P/E of the largest listed companies in the same industry (Screener, up to 25 companies). IPOs with no industry data keep the 25x result.':'Pass if post-issue P/E is positive and 25x or less.';
 const f3h=document.querySelector('th[data-field=f3] .fn');if(f3h)f3h.textContent=S.pe==='ind'?'P/E ≤ industry':'P/E ≤25x';""")

# 3. KPIs and distribution computed from the effective rows
rep(" const kp=dash.data('kpi');\n if(ok&&kp.status==='ok'){",
    " const kp={status:ok?'ok':'loading',data:[{k:'total',n:rows.length},{k:'qualified',n:rows.filter(r=>r.verdict==='Qualified').length},{k:'provisional',n:rows.filter(r=>r.verdict==='Provisional').length},{k:'review',n:rows.filter(r=>r.verdict==='Review').length},{k:'rejected',n:rows.filter(r=>r.verdict==='Rejected').length},{k:'live',n:rows.filter(r=>r.group==='Open / upcoming').length}]};\n if(ok&&kp.status==='ok'){")
rep("const dd=dash.data('dist');", "const dd={status:'ok',data:[0,1,2,3,4,5,6,7,8].map(p=>({passed:p,n:rows.filter(r=>r.passed===p).length}))};")

# 4. numbers in cells and detail
rep(" if(f==='f3')return m.pe_post!=null?(m.pe_post<0?'loss':m.pe_post.toFixed(1)+'x P/E'):'';",
    " if(f==='f3')return m.pe_post!=null?(m.pe_post<0?'loss':m.pe_post.toFixed(1)+'x'+(S.pe==='ind'&&m.ind_pe!=null?' vs '+m.ind_pe.toFixed(1)+'x':' P/E')):'';")
rep("""(m.mcap_post!=null?' · market cap ₹'+fx(m.mcap_post,0)+' cr':'');}""",
    """(m.mcap_post!=null?' · market cap ₹'+fx(m.mcap_post,0)+' cr':'')+(m.ind_pe!=null?' · industry median '+m.ind_pe.toFixed(1)+'x ('+m.ind_name+', top '+m.ind_n+' listed)'+(m.rel!=null?' → '+m.rel.toFixed(2)+'x of industry':''):'')+(m.cur_pe!=null?' · trading P/E now '+m.cur_pe.toFixed(1)+'x':'');}""")
rep("c2.className='rl';c2.textContent=RULE[f];", "c2.className='rl';c2.textContent=(f==='f3'&&S.pe==='ind')?'Post-issue P/E ≤ industry median':RULE[f];")
rep("text: 'x'", "text: 'x'") if False else None

json.dump({"text": t}, open(r"C:\ipo_cache\dash\new5.json", "w", encoding="utf-8"))
print("ok", len(t))
