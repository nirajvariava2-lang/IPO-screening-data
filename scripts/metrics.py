"""Collect decision numbers per IPO from its Chittorgarh page into cache/metrics.json.

Output per company: price, issue size, fresh/OFS, objects, P/E, market cap, promoter pre/post,
anchor, subscription, financial history, D/E, ROE/ROCE, CAGR. Used by the dashboard detail panel.
"""
import json, re, sys, time
from pathlib import Path
import requests
from bs4 import BeautifulSoup

H = {"User-Agent": "Mozilla/5.0"}
CACHE = Path(r"C:\ipo_cache")


def num(x):
    if x is None:
        return None
    s = str(x).replace(",", "").replace("₹", "").replace("%", "").replace("x", "").strip()
    neg = s.startswith("(") or s.startswith("-")
    m = re.search(r"\d+(?:\.\d+)?", s)
    if not m:
        return None
    v = float(m.group())
    return -v if neg else v


def cr(x):
    m = re.search(r"₹\s*([\d,\.]+)\s*Cr", x or "")
    return float(m.group(1).replace(",", "")) if m else None


def cagr(first, last, years):
    if first and last and first > 0 and last > 0 and years > 0:
        return round(((last / first) ** (1 / years) - 1) * 100, 1)


def parse(url):
    s = BeautifulSoup(requests.get(url, headers=H, timeout=60).text, "html.parser")
    out = {"url": url}
    tables = []
    for tb in s.find_all("table"):
        tables.append([[c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])] for tr in tb.find_all("tr")])
    kv = {}
    for t in tables:
        for r in t:
            if len(r) == 2:
                kv.setdefault(r[0], r[1])
    out["price_band"] = kv.get("Price Band"); out["issue_price"] = num(kv.get("Issue Price")); out["lot"] = kv.get("Lot Size")
    out["sale_type"] = kv.get("Sale Type"); out["dates"] = kv.get("IPO Date"); out["listed_on"] = kv.get("Listed on")
    out["last_trade"] = num(kv.get("Last Trade")); out["shares_post"] = num((kv.get("Share Holding Post Issue") or "").split(" ")[0])
    out["issue_cr"] = cr(kv.get("Total Issue Size")); out["fresh_cr"] = cr(kv.get("Fresh Issue"))
    out["ofs_cr"] = cr(kv.get("Offer for Sale"))
    if out["issue_cr"] and out["fresh_cr"] is not None:
        out["fresh_pct"] = round(out["fresh_cr"] / out["issue_cr"] * 100, 1)
    elif out["issue_cr"] and out["ofs_cr"]:
        out["fresh_pct"] = round((1 - out["ofs_cr"] / out["issue_cr"]) * 100, 1)
    if kv.get("Retail (Min)"):
        pass
    for t in tables:
        h0 = t[0] if t else []
        if h0[:1] == ["Period Ended"]:
            cols = h0[1:]
            rows = {r[0]: r[1:] for r in t[1:] if len(r) > 1}
            fy = [i for i, c in enumerate(cols) if "Mar" in c]
            def series(*names):
                for n in names:
                    if n in rows:
                        return [num(rows[n][i]) if i < len(rows[n]) else None for i in range(len(cols))]
            rev = series("Revenue", "Total Income", "Revenue from Operations"); pat = series("Profit After Tax", "PAT")
            bor = series("Total Borrowing"); nw = series("NET Worth", "Net Worth")
            out["periods"] = cols
            out["revenue"] = rev; out["pat"] = pat; out["borrowing"] = bor; out["networth"] = nw
            if rev and len(fy) >= 2:
                a, b = fy[-1], fy[0]
                out["rev_cagr"] = cagr(rev[a], rev[b], len(fy) - 1)
            if pat and len(fy) >= 2:
                a, b = fy[-1], fy[0]
                out["pat_cagr"] = cagr(pat[a], pat[b], len(fy) - 1)
            if bor and nw and nw[0]:
                out["de_calc"] = round((bor[0] or 0) / nw[0], 2)
        if h0[:1] == ["KPI"]:
            out["kpi"] = {r[0]: r[1:] for r in t[1:] if len(r) > 1}
        if h0[:3] == ["Valuation Metric", "Pre IPO", "Post IPO"]:
            for r in t[1:]:
                if r[0].startswith("EPS"): out["eps_pre"], out["eps_post"] = num(r[1]), num(r[2])
                if r[0].startswith("P/E"): out["pe_pre"], out["pe_post"] = num(r[1]), num(r[2])
                if r[0].startswith("Market Cap"): out["mcap_pre"], out["mcap_post"] = cr(r[1]), cr(r[2])
        if h0[:3] == ["Category", "Pre IPO", "Post IPO"]:
            for r in t[1:]:
                if r[0].startswith("Promoter"): out["promoter_pre"], out["promoter_post"] = num(r[1]), num(r[2])
        if h0[:2] == ["#", "Issue Objects"]:
            out["objects"] = [[r[1], num(r[2])] for r in t[1:] if len(r) >= 3 and r[1] and r[1] != "Total" and "Issue Expenses" not in r[1]]
        if h0[:2] == ["Category", "Subscription (times)"]:
            for r in t[1:]:
                if r[0] == "Total": out["sub_total"] = num(r[1])
        if h0[:2] == ["Category", "Subscription (x)"]:
            for r in t[1:]:
                k = {"QIB (Ex Anchor)": "sub_qib", "NII": "sub_nii", "Retail": "sub_retail", "Total": "sub_total"}.get(r[0].replace("*", "").strip())
                if k: out[k] = num(r[1])
        if len(h0) >= 4 and h0[0] == "Category" and "Subscription (times)" in h0[1:2]:
            for r in t[1:]:
                if r and r[0] == "Total" and len(r) > 1: out["sub_total"] = num(r[1])
    for t in tables:
        for r in t:
            if r and r[0] == "No. of times subscribed" and len(r) > 1 and num(r[-1]):
                out.setdefault("sub_total", num(r[-1]))
            if r and r[0].startswith("Anchor Portion"): out["anchor_cr"] = num(r[1])
            if r and r[0] == "Last Trade" and len(r) > 1: out["last_trade"] = num(r[-1])
            if r and r[0].startswith("−") and "Anchor Investor" in r[0] and len(r) > 1: out["anchor_shares"] = num(r[1])
    return out


if __name__ == "__main__":
    ch = json.load(open(CACHE / "chitt.json"))
    only = sys.argv[1:]
    res = json.load(open(CACHE / "metrics.json")) if (CACHE / "metrics.json").exists() and only else {}
    for c, v in ch.items():
        if only and c not in only:
            continue
        try:
            res[c] = parse(v["url"])
            print(f"{c:28} pe_post={res[c].get('pe_post')} fresh%={res[c].get('fresh_pct')} sub={res[c].get('sub_total')} revCAGR={res[c].get('rev_cagr')} patCAGR={res[c].get('pat_cagr')}", flush=True)
        except Exception as e:
            print("ERR", c, e)
        time.sleep(0.6)
    json.dump(res, open(CACHE / "metrics.json", "w"), indent=1)
