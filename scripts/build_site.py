"""Build the standalone public page (index.html) from the dashboard page source.

Usage: python scripts/build_site.py <dashboard_page.html>   (the page text saved from the artifact's files/index.html)
Writes C:\ipo_repo\index.html. The page fetches ipo_screen_v3.json from the same folder.
"""
import json, sys

src = sys.argv[1] if len(sys.argv) > 1 else r"C:\ipo_cache\dash\new4.json"
raw = open(src, encoding="utf-8").read()
t = json.loads(raw)["text"] if src.endswith(".json") else raw
t = t.replace("Prepared for Niraj Variava, CA", "Screening aid only, not investment advice")

head = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>IPO Screening Desk</title>
<style>
:root{--color-fg:#1f2328;--color-fg-muted:#5b6470;--color-bg:#f6f4ef;--color-panel:#fff;--color-border-line:#dcd8cf;--color-ok:#1a7f4b;--color-warn:#b26a00;--color-bad:#c0392b;
--font-anthropic-sans:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;--font-anthropic-serif:Georgia,"Times New Roman",serif;
--cds-font-size-title:2rem;--cds-font-size-heading:1.05rem;--cds-font-size-body:.9rem;--cds-font-size-caption:.76rem;--cds-font-weight-medium:600;
--cds-gap-sm:8px;--cds-gap-md:16px;--cds-gap-lg:24px;--cds-pad-xs:4px;--cds-pad-sm:8px;--cds-pad-md:12px;--cds-pad-lg:16px;--cds-radius:8px;
--cds-chart-muted:#b9b6ad;--cds-surface-popover:#fff;--cds-border:#cfcac0;--cds-shadow-popover:0 4px 14px rgba(0,0,0,.15);--dc0:#4a6fa5}
@media(prefers-color-scheme:dark){:root{--color-fg:#ece9e1;--color-fg-muted:#a39f95;--color-bg:#1b1a17;--color-panel:#25231f;--color-border-line:#3a372f;--color-ok:#4cc38a;--color-warn:#e0a03a;--color-bad:#ef7a6c;--cds-chart-muted:#5a564c;--cds-surface-popover:#2c2a25;--cds-border:#4a463d}}
html,body{margin:0;background:var(--color-bg);color:var(--color-fg)}
#dash-root{padding:16px clamp(12px,2vw,28px)}
</style></head><body><div id="dash-root">
"""

shim = """<script>
window.dash=(function(){const calcs=[],cbs=[],store={};let rows=null,err=null;
function compute(){calcs.forEach(c=>{try{store[c.id]={status:'ok',data:c.fn(...c.inputs.map(i=>i==='screen'?rows:store[i].data))};}catch(e){store[c.id]={status:'error',data:[]};}});}
return{calc(id,o){calcs.push({id,inputs:o.inputs,fn:o.fn});if(rows)compute();},
loader(){},colors:[],refresh(){},params(){return{}},setParams(){},resetParams(){},setLink(){},
data(id){if(id==='screen')return err?{status:'error',data:[]}:rows?{status:'ok',data:rows}:{status:'loading',data:[]};return store[id]||{status:'loading',data:[]};},
onData(fn){cbs.push(fn);fn();window.addEventListener('resize',()=>fn());},
_load(){fetch('ipo_screen_v3.json?'+Date.now()).then(r=>r.json()).then(j=>{rows=j;compute();cbs.forEach(f=>f());}).catch(e=>{err=e;cbs.forEach(f=>f());});}};})();
</script>
"""

tail = """
<script>dash._load();</script>
</div></body></html>"""

out = head + shim + t + tail
open(r"C:\ipo_repo\index.html", "w", encoding="utf-8").write(out)
print(len(out))
