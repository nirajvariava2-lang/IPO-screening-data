"""Collect F5-F8 evidence for every IPO in data.json from SEBI-hosted offer documents.

Writes cache/evidence.json (value + document + page for each finding). Does not edit data.json:
a document is only usable for a filter when its latest financial year is current (see `current`).
"""
import json, re, sys, traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sebi, extract

ROOT = Path(__file__).resolve().parent.parent
CURRENT_FY = 2026


def pdate(s):
    try:
        return datetime.strptime(s, "%b %d, %Y")
    except Exception:
        return datetime.min


def latest_fy(pgs):
    yrs = []
    for t in pgs[:160]:
        yrs += [int(y) for y in re.findall(r"(?:March|June|September|December)\s+3[01],\s+(20\d\d)", t)]
    return max(yrs) if yrs else None


def best_doc(docs):
    docs = [d for d in docs if sebi.rank(d["title"]) < 5] or docs
    return sorted(docs, key=lambda d: (sebi.rank(d["title"]), -pdate(d["date"]).toordinal()))[0]


def run(company, disc):
    docs = disc.get("docs", [])
    if not docs:
        return {"status": "no SEBI document found"}
    d = best_doc(docs)
    urls = sebi.pdf_links(d)
    if not urls:
        return {"status": "no PDF link", "doc": d["title"], "page": d["page"]}
    big = None
    for u in urls:
        f = sebi.download(u)
        if big is None or f.stat().st_size > big[1].stat().st_size:
            big = (u, f)
    u, f = big
    pgs = extract.pages(f)
    fy = latest_fy(pgs)
    return {
        "status": "ok", "doc_title": d["title"], "doc_date": d["date"], "doc_page": d["page"], "pdf": u,
        "pages": len(pgs), "latest_fy": fy, "current": bool(fy and fy >= CURRENT_FY),
        "promoter": extract.promoter(pgs), "auditor": extract.auditor(pgs)[:6],
        "anchors": extract.anchors(pgs), "cashflow": extract.cashflow(pgs), "debt": extract.debt(pgs),
        "fin": extract.fin(pgs),
    }


if __name__ == "__main__":
    disc = json.load(open(sebi.CACHE / "discovery.json", encoding="utf-8"))
    outp = sebi.CACHE / "evidence.json"
    ev = json.load(open(outp, encoding="utf-8")) if outp.exists() else {}
    only = sys.argv[1:]
    for c, dd in disc.items():
        if only and c not in only:
            continue
        if c in ev and ev[c].get("status") == "ok":
            continue
        try:
            ev[c] = run(c, dd)
        except Exception as e:
            ev[c] = {"status": "error: " + repr(e)[:200]}
            traceback.print_exc()
        e = ev[c]
        print(f"{c:30} {e['status'][:30]:30} fy={e.get('latest_fy')} current={e.get('current')} pages={e.get('pages')}", flush=True)
        json.dump(ev, open(outp, "w", encoding="utf-8"), indent=1, default=str)

