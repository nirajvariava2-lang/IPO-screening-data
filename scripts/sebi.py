"""SEBI public-issue document discovery and download."""
import json, re, time
from pathlib import Path
import requests
from bs4 import BeautifulSoup

BASE = "https://www.sebi.gov.in"
LIST = BASE + "/sebiweb/home/HomeAction.do?doListing=yes&sid=3&ssid=15&smid=10"
H = {"User-Agent": "Mozilla/5.0"}
CACHE = Path(r"C:\ipo_cache")
CACHE.mkdir(exist_ok=True)

_s = requests.Session()
_s.get(LIST, headers=H, timeout=60)

STOP = re.compile(r"\b(limited|ltd|private|pvt|india|technologies|technology|industries|enterprises|"
                  r"manufacturing|businesses|and|&)\b\.?", re.I)


def queries(name):
    """Search keyword candidates, most specific first."""
    clean = re.sub(r"[^\w\s']", " ", name).strip()
    words = clean.split()
    out = [clean, " ".join(words[:2]), words[0]]
    seen, res = set(), []
    for q in out:
        if q and q.lower() not in seen:
            seen.add(q.lower()); res.append(q)
    return res


def search(q):
    d = {"nextValue": "1", "next": "s", "search": q, "fromDate": "", "toDate": "", "fromYear": "",
         "toYear": "", "deptId": "", "sid": "3", "ssid": "15", "smid": "10", "ssidhidden": "15",
         "intmid": "-1", "sText": "Filings", "ssText": "Public Issues", "smText": "", "doDirect": "-1"}
    r = _s.post(BASE + "/sebiweb/ajax/home/getnewslistinfo.jsp", data=d,
                headers={**H, "X-Requested-With": "XMLHttpRequest", "Referer": LIST}, timeout=60)
    soup = BeautifulSoup(r.text.split("#@#")[0], "html.parser")
    rows = []
    for tr in soup.select("tr.odd, tr.even"):
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue
        a = tds[1].find("a", href=True)
        if not a:
            continue
        pdfs = [x["href"].strip() for x in BeautifulSoup(a.get("title", ""), "html.parser").find_all("a", href=True)]
        rows.append({"date": tds[0].get_text(strip=True), "title": a.get_text(" ", strip=True),
                     "page": a["href"], "pdfs": pdfs})
    return rows


def rank(title):
    t = title.lower()
    if 'addendum' in t or 'corrigendum' in t:
        return 5
    if "red herring" in t or "rhp" in t and "drhp" not in t and "udrhp" not in t:
        return 0
    if "prospectus" in t and "draft" not in t and "dap" not in t:
        return 1
    if "udrhp" in t:
        return 2
    if "drhp" in t or "draft" in t:
        return 3
    return 4


def find_docs(company):
    for q in queries(company):
        rows = search(q)
        key = re.sub(r"[^a-z0-9 ]", "", company.lower()).split()[0]
        rows = [r for r in rows if key in r["title"].lower()]
        if rows:
            rows.sort(key=lambda r: (rank(r["title"]), ))
            return q, rows
        time.sleep(0.5)
    return None, []


def pdf_links(row):
    """Return PDF urls for a row, resolving the html detail page if needed."""
    if row["pdfs"]:
        return row["pdfs"]
    t = _s.get(row["page"], headers=H, timeout=60).text
    urls = re.findall(r"file=(https?://[^\"'&\s]+\.pdf)", t) or re.findall(r"[\"'](https?://[^\"']*sebi_data[^\"']*\.pdf)", t)
    return list(dict.fromkeys(urls))

def download(url):
    fn = CACHE / re.sub(r"[^A-Za-z0-9._-]", "_", url.split("/")[-1])
    if not fn.exists():
        for attempt in range(4):
            try:
                r = _s.get(url, headers=H, timeout=180)
                r.raise_for_status()
                fn.write_bytes(r.content)
                break
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(3)
    return fn


if __name__ == "__main__":
    import sys
    data = json.load(open(Path(__file__).resolve().parent.parent / "data.json", encoding="utf-8"))
    out = {}
    for row in data["rows"]:
        c = row["company"]
        q, docs = find_docs(c)
        out[c] = {"query": q, "docs": [{"date": d["date"], "title": d["title"], "page": d["page"], "pdfs": d["pdfs"]} for d in docs]}
        print(f"{c:32} {len(docs)} docs", "|", docs[0]["title"][:70] if docs else "")
    json.dump(out, open(CACHE / "discovery.json", "w", encoding="utf-8"), indent=1)




