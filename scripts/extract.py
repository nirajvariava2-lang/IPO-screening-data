"""Extract F5-F8 evidence from an offer-document PDF. Each finding carries its page reference."""
import json, re
from pathlib import Path
from pypdf import PdfReader

TXT = Path(r"C:\ipo_cache") / "txt"
TXT.mkdir(parents=True, exist_ok=True)
NUM = r"\(?-?[\d,]+(?:\.\d+)?\)?"


def pages(pdf):
    """List of page texts (cached as json)."""
    f = TXT / (Path(pdf).stem + ".json")
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    out = []
    for p in PdfReader(str(pdf)).pages:
        try:
            out.append(p.extract_text() or "")
        except Exception:
            out.append("")
    f.write_text(json.dumps(out), encoding="utf-8")
    return out


def tonum(s):
    s = s.strip()
    neg = s.startswith("(") or s.startswith("-")
    v = float(re.sub(r"[^\d.]", "", s) or "nan")
    return -v if neg else v


def grep(pgs, pattern, ctx=0, flags=re.I, limit=8):
    res = []
    for i, t in enumerate(pgs):
        for m in re.finditer(pattern, t, flags):
            res.append((i + 1, t[max(0, m.start() - ctx): m.end() + ctx].replace("\n", " ")))
            if len(res) >= limit:
                return res
    return res


def promoter(pgs):
    """F7: pre/post-offer promoter holding and pledge."""
    out = {"pre": None, "post": None, "pledge": None, "src": []}
    for pg, s in grep(pgs, r"promoters?(?: and promoter group)?[^\n]{0,60}\n?[^\n]{0,80}?(\d{1,3}\.\d{1,2})\s*%", 250, limit=40):
        pass
    # shareholding table rows: "Promoters ... pre-offer % ... post-offer %"
    rows = grep(pgs, r"total\s*\(?[A-Z]\)?\s*[^\n]{0,40}promoters?[^\n]*", 0, limit=10)
    pledge = grep(pgs, r"(pledge[d]?|encumbered|encumbrance)[^.\n]{0,160}(promoter)|(promoter)[^.\n]{0,160}(pledge[d]?|encumbrance)", 120, limit=6)
    out["pledge_hits"] = [(p, t[:300]) for p, t in pledge]
    out["rows"] = [(p, t[:200]) for p, t in rows]
    return out


def auditor(pgs):
    """F8: qualification / emphasis / adverse remarks in the restated report."""
    q = grep(pgs, r"(qualified opinion|qualification|adverse (?:opinion|remark)|emphasis of matter|material uncertainty|disclaimer of opinion)", 200, limit=25)
    hits = []
    for p, t in q:
        low = t.lower()
        if any(k in low for k in ("auditor", "audit report", "restated", "opinion")) and "risk" not in low[:30]:
            hits.append((p, t[:400]))
    return hits


def anchors(pgs):
    return [(p, t[:300]) for p, t in grep(pgs, r"anchor investor portion[^.\n]{0,200}", 60, limit=3)]


def cashflow(pgs):
    return [(p, t[:300]) for p, t in grep(pgs, r"net cash (?:flows? )?(?:generated )?(?:from|used in|\(used in\)|from/\(used in\)|from/ \(used in\))[^\n]{0,40}operating activit[^\n]*", 0, limit=6)]


def debt(pgs):
    return [(p, t[:300]) for p, t in grep(pgs, r"debt[\s/-]*(?:to[\s/-]*)?equity ratio[^\n]*", 0, limit=6)]


def fin(pgs):
    rev = grep(pgs, r"revenue from operations[^\n]*" + NUM + r"[^\n]*" + NUM + r"[^\n]*" + NUM, 0, limit=4)
    pat = grep(pgs, r"(?:restated )?profit(?:/\(loss\))?(?: after tax)?(?: for the (?:year|period))?[^\n]*" + NUM + r"[^\n]*" + NUM + r"[^\n]*" + NUM, 0, limit=4)
    return {"rev": rev, "pat": pat}


if __name__ == "__main__":
    import sys
    pgs = pages(sys.argv[1])
    print(len(pgs), "pages")
    for k, fn in (("promoter", promoter), ("auditor", auditor), ("anchors", anchors),
                  ("cashflow", cashflow), ("debt", debt), ("fin", fin)):
        print("==", k)
        print(json.dumps(fn(pgs), indent=1, default=str)[:3500])

