"""Fetch the full Screener dataset for one company code into C:\\ipo_cache\\screener_full\\<code>.json.

Tables (annual P&L, balance sheet, cash flow, ratios, quarterly shareholding), top ratios, industry path and peers.
"""
import json, re, sys, time
from pathlib import Path
import requests
from bs4 import BeautifulSoup

H = {"User-Agent": "Mozilla/5.0"}
OUT = Path(r"C:\ipo_cache\screener_full")
OUT.mkdir(exist_ok=True)


def table(s, sec):
    tb = s.select_one(f"#{sec} table")
    if not tb:
        return None
    hdr = [t.get_text(" ", strip=True) for t in tb.find("thead").find_all("th")]
    rows = {}
    for tr in tb.find("tbody").find_all("tr"):
        x = [t.get_text(" ", strip=True) for t in tr.find_all(["th", "td"])]
        if x and x[0]:
            rows[re.sub(r"\s*\+$", "", x[0])] = x[1:]
    return {"cols": hdr[1:], "rows": rows}


def fetch(code):
    for suf in ("consolidated/", ""):
        r = requests.get(f"https://www.screener.in/company/{code}/{suf}", headers=H, timeout=60)
        if r.status_code != 200:
            continue
        s = BeautifulSoup(r.text, "html.parser")
        if not s.select_one("#profit-loss table"):
            continue
        d = {"code": code, "url": r.url, "name": s.select_one("h1").get_text(strip=True)}
        d["top"] = {}
        for li in s.select("#top-ratios li"):
            k = li.select_one(".name").get_text(" ", strip=True)
            v = li.select_one(".value").get_text(" ", strip=True)
            d["top"][k] = v
        d["about"] = (s.select_one(".about") or s.select_one("#top .sub")).get_text(" ", strip=True) if (s.select_one(".about") or s.select_one("#top .sub")) else ""
        for sec in ("profit-loss", "balance-sheet", "cash-flow", "ratios"):
            d[sec] = table(s, sec)
        sh = {}
        for key in ("quarterly", "yearly"):
            sh[key] = table(s, f"shareholding") if key == "quarterly" else None
        d["shareholding"] = table(s, "shareholding")
        d["quarters"] = table(s, "quarters")
        d["industry"] = [(a.get_text(strip=True), a.get("href")) for a in s.select('#peers a[href^="/market/"]')]
        pros = [li.get_text(" ", strip=True) for li in s.select(".pros li")]
        cons = [li.get_text(" ", strip=True) for li in s.select(".cons li")]
        d["pros"], d["cons"] = pros, cons
        # price / peers via ajax
        m = re.search(r'data-warehouse-id="(\d+)"', r.text) or re.search(r'/api/company/(\d+)/peers', r.text)
        if m:
            p = requests.get(f"https://www.screener.in/api/company/{m.group(1)}/peers/", headers=H, timeout=60)
            if p.status_code == 200:
                ps = BeautifulSoup(p.text, "html.parser")
                tb = ps.select_one("table")
                if tb:
                    rows = [[c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])] for tr in tb.find_all("tr")]
                    d["peers"] = rows
        (OUT / f"{code}.json").write_text(json.dumps(d, indent=1), encoding="utf-8")
        return d
    return None


if __name__ == "__main__":
    d = fetch(sys.argv[1])
    if not d:
        print("not found"); sys.exit(1)
    print(d["name"], d["url"])
    print("top:", d["top"])
    for sec in ("profit-loss", "balance-sheet", "cash-flow", "ratios", "shareholding"):
        t = d[sec]
        print(sec, t["cols"] if t else None, list(t["rows"])[:12] if t else None)
    print("peers", (d.get("peers") or [])[:4])
    print("industry", d["industry"])
    print("pros", d["pros"][:3], "cons", d["cons"][:3])
