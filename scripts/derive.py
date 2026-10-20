"""Derive F5/F7/F8 from SEBI DRHPs (older data, flagged via row['stale'][fK] = 'FY25').

Only fills cells that are still 'U'. Each fill stores its source text/page in row['sources'][fK].
"""
import json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract, sebi

NUMRE = r"\(?-?\d[\d,]*(?:\.\d+)?\)?"
CURRENT = {"Zetwerk Manufacturing", "Paras Healthcare", "Jio Platforms", "Tonbo Imaging"}


def nums(s):
    return [extract.tonum(x) for x in re.findall(NUMRE, s)]


def opcf(pgs):
    for p, t in extract.grep(pgs, r"net cash[^\n]{0,40}operating activit[^\n]*", 0, limit=60):
        ns = [x for x in nums(t.split("activit")[-1]) if not (1990 < abs(x) < 2100 and x == int(x))]
        if len(ns) >= 2:
            return p, ns[:4]


def de_ratio(pgs):
    for p, t in extract.grep(pgs, r"debt[\s/-]*(?:to[\s/-]*)?equity ratio[^\n]*", 0, limit=60):
        ns = [x for x in nums(re.sub(r"\(\d\)", "", t.split("atio", 1)[-1])) if 0 <= x < 15 and round(x, 2) == x]
        if ns:
            return p, ns[:4]


def pledge_none(pgs):
    r = extract.grep(pgs, r"(?:none of|no)[^.\n]{0,80}(?:equity shares|shares)[^.\n]{0,80}(?:pledge|encumb)|not (?:been )?(?:pledged|subject to any pledge)", 0, limit=1)
    return r[0][0] if r else None


def no_qualification(pgs):
    r = extract.grep(pgs, r"(?:no|not (?:provided|expressed|included)[^.]{0,30}any|not any) qualification", 0, limit=1)
    return r[0][0] if r else None


def anchor_in_structure(pgs):
    r = extract.grep(pgs[:60], r"anchor investor portion", 0, limit=1)
    return r[0][0] if r else None


def post_pct(flag):
    m = re.search(r"promoter[^|;]{0,25}?(\d{1,3}(?:\.\d+)?)%[^|;]{0,12}post", flag, re.I) or \
        re.search(r"post-?(?:issue|offer)[^|;]{0,30}promoter[^|;]{0,15}?(\d{1,3}(?:\.\d+)?)%", flag, re.I)
    return float(m.group(1)) if m else None


def apply(row, e, pgs, fy):
    c = row["company"]
    row.setdefault("sources", {}); row.setdefault("stale", {})
    tag = f"FY{str(fy)[2:]}" if fy else "older"
    doc = f"SEBI {e['doc_title'][:40]} ({e['doc_date']})"

    # F5
    if row["f5"] == "U":
        o, d = opcf(pgs), de_ratio(pgs)
        fail = (o and o[1][0] <= 0) or (d and d[1][0] > 1)
        ok = o and d and o[1][0] > 0 and d[1][0] <= 1
        if fail or ok:
            row["f5"] = "F" if fail else "P"
            bits = []
            if o: bits.append(f"operating cash flow {o[1][0]:g} mn (p.{o[0]}; prior {', '.join(f'{x:g}' for x in o[1][1:3])})")
            if d: bits.append(f"D/E {d[1][0]:g} (p.{d[0]})")
            row["sources"]["f5"] = f"{doc}: " + "; ".join(bits)
            row["stale"]["f5"] = tag
    # F7
    if row["f7"] == "U":
        pn, pp = pledge_none(pgs), post_pct(row.get("flag", ""))
        if pp is not None and pp < 50:
            row["f7"] = "F"; row["sources"]["f7"] = f"Post-issue promoter holding {pp}% < 50% (flag, Chittorgarh)"
        elif pp is not None and pn:
            row["f7"] = "P"; row["sources"]["f7"] = f"Post-issue promoter holding {pp}% (Chittorgarh); no pledge ({doc} p.{pn})"; row["stale"]["f7"] = tag
        elif pn:
            row["sources"]["f7"] = f"No pledge ({doc} p.{pn}); post-issue % not in DRHP"
    # F8
    if row["f8"] == "U":
        nq, an = no_qualification(pgs), anchor_in_structure(pgs)
        if nq and an:
            row["f8"] = "P"
            row["sources"]["f8"] = f"Soft pass: no auditor qualification ({doc} p.{nq}); anchor portion in offer structure (p.{an}). Confirm in RHP"
            row["stale"]["f8"] = tag


def reasons(row, e, fy):
    r = {}
    for k in ("f5", "f7", "f8"):
        if row[k] == "U":
            if e.get("status") != "ok":
                r[k] = "No offer document on SEBI site"
            elif k == "f7":
                r[k] = row.get("sources", {}).get("f7") or "Promoter holding/pledge not found in DRHP text; needs RHP"
            else:
                r[k] = f"Not found in SEBI {e['doc_title'][:30]} ({e['doc_date']}); needs RHP"
    row["u_reasons"] = r


def verdict(row):
    p = row["passed"]
    flag_rej = row["verdict"] == "Rejected" and p >= 3
    if flag_rej or p <= 2:
        return "Rejected"
    if p >= 7 and not row.get("stale") and not row.get("soft"):
        return "Qualified"
    return "Provisional" if p >= 5 else "Review"


if __name__ == "__main__":
    d = json.load(open(sys.argv[1], encoding="utf-8"))
    ev = json.load(open(sebi.CACHE / "evidence.json", encoding="utf-8"))
    for row in d["rows"]:
        c = row["company"]; e = ev.get(c, {})
        fy = e.get("fy_fixed")
        if e.get("status") == "ok" and e["pages"] >= 100:
            pgs = extract.pages(sebi.CACHE / re.sub(r"[^A-Za-z0-9._-]", "_", e["pdf"].split("/")[-1]))
            apply(row, e, pgs, fy)
        reasons(row, e, fy)
        row["passed"] = sum(row[f"f{i}"] == "P" for i in range(1, 9))
        row["fails"] = sum(row[f"f{i}"] == "F" for i in range(1, 9))
        row["unknown"] = sum(row[f"f{i}"] == "U" for i in range(1, 9))
        row["verdict"] = verdict(row)
    json.dump(d, open(sys.argv[1], "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for k in ("f4", "f5", "f6", "f7", "f8"):
        print(k, "U =", sum(r[k] == "U" for r in d["rows"]))

