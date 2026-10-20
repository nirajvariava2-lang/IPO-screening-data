"""Collect Screener full data + Chittorgarh 'About' text for every listed IPO with a Screener page.

Writes C:\\ipo_cache\\screener_full\\<code>.json and C:\\ipo_cache\\about\\<code>.json ({about, promoters_note}).
"""
import json, re, sys, time
from pathlib import Path
import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
import screener_full

H = {"User-Agent": "Mozilla/5.0"}
ABOUT = Path(r"C:\ipo_cache\about"); ABOUT.mkdir(exist_ok=True)


def about(url):
    s = BeautifulSoup(requests.get(url, headers=H, timeout=60).text, "html.parser")
    for hd in s.find_all(["h2", "h3"]):
        if hd.get_text(strip=True).startswith("About"):
            parts = []
            for el in hd.find_all_next(["p", "ul", "h2", "h3"], limit=14):
                if el.name in ("h2", "h3"):
                    break
                parts.append(el.get_text(" ", strip=True))
            return " ".join(parts)
    return ""


if __name__ == "__main__":
    ind = json.load(open(r"C:\ipo_cache\industry.json"))
    ch = json.load(open(r"C:\ipo_cache\chitt.json"))
    only = sys.argv[1:]
    status = {}
    for c, v in ind.items():
        if only and c not in only:
            continue
        code = v.get("code")
        if not code:
            continue
        try:
            d = screener_full.fetch(code)
        except Exception as e:
            d = None
            print("ERR", c, e)
        a = ""
        try:
            a = about(ch[c]["url"])
        except Exception:
            pass
        (ABOUT / f"{code}.json").write_text(json.dumps({"company": c, "about": a}), encoding="utf-8")
        ok = bool(d)
        yrs = len(d["profit-loss"]["cols"]) if d else 0
        kind = "sales" if d and any(k.startswith("Sales") for k in d["profit-loss"]["rows"]) else ("revenue" if d else "-")
        status[c] = {"code": code, "ok": ok, "years": yrs, "kind": kind, "about": len(a)}
        print(f"{c:28} {code:12} ok={ok} years={yrs} kind={kind} about={len(a)}", flush=True)
        time.sleep(0.8)
    json.dump(status, open(r"C:\ipo_cache\collect_status.json", "w"), indent=1)
