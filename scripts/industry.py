"""Industry P/E per IPO: Screener industry classification + median P/E of the industry's listed companies.

Writes C:\\ipo_cache\\industry.json: {company: {industry, level, peers, median_pe, current_pe, code}}
"""
import json, re, statistics, sys, time
import requests
from bs4 import BeautifulSoup

H = {"User-Agent": "Mozilla/5.0"}
CACHE = r"C:\ipo_cache"
_pe_cache = {}


def symbols(url):
    s = BeautifulSoup(requests.get(url, headers=H, timeout=60).text, "html.parser")
    for tr in s.find_all("tr"):
        x = [t.get_text(" ", strip=True) for t in tr.find_all(["th", "td"])]
        if x and x[0].startswith("BSE Script Code") and len(x) > 1:
            return [p.strip() for p in x[1].split("/")][::-1]
    return []


def industry_pes(path):
    if path in _pe_cache:
        return _pe_cache[path]
    r = requests.get("https://www.screener.in" + path, headers=H, timeout=60)
    pes = []
    if r.status_code == 200:
        s = BeautifulSoup(r.text, "html.parser")
        tb = s.select_one("table")
        if tb:
            rows = [[c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])] for tr in tb.find_all("tr")]
            hdr = rows[0]
            if "P/E" in hdr:
                i = hdr.index("P/E")
                for x in rows[1:]:
                    try:
                        v = float(x[i].replace(",", ""))
                        if v > 0:
                            pes.append(v)
                    except Exception:
                        pass
    _pe_cache[path] = pes
    time.sleep(0.5)
    return pes


def company(code):
    for suf in ("consolidated/", ""):
        r = requests.get(f"https://www.screener.in/company/{code}/{suf}", headers=H, timeout=60)
        if r.status_code != 200:
            continue
        s = BeautifulSoup(r.text, "html.parser")
        links = [(a.get("href"), a.get_text(strip=True)) for a in s.select('#peers a[href^="/market/"]')]
        cur = None
        m = re.search(r"Stock P/E\s*([\d\.]+)", s.get_text(" ", strip=True))
        if m:
            cur = float(m.group(1))
        if links:
            return {"links": links, "current_pe": cur, "url": r.url}
    return None


if __name__ == "__main__":
    ch = json.load(open(CACHE + r"\chitt.json"))
    out = {}
    for c, v in ch.items():
        try:
            codes = [x for x in symbols(v["url"]) if x and x != "NA"]
        except Exception:
            codes = []
        info = None
        for code in codes:
            info = company(code)
            if info:
                info["code"] = code
                break
        if not info:
            print(f"{c:28} no Screener page"); continue
        res = {"code": info["code"], "current_pe": info["current_pe"]}
        for href, name in info["links"][::-1]:  # narrowest industry first
            pes = industry_pes(href)
            if len(pes) >= 8:
                res.update({"industry": name, "peers": len(pes), "median_pe": round(statistics.median(pes), 1)})
                break
        out[c] = res
        print(f"{c:28} {res}", flush=True)
        time.sleep(0.5)
    json.dump(out, open(CACHE + r"\industry.json", "w"), indent=1)
