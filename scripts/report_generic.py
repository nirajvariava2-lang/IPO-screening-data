"""Generic 7-section equity research report for listed IPOs (data-driven; qualitative text from reports/qual.json).

Usage: python scripts/report_generic.py "<Company>" [more companies...]   (or --all)
Same output files and CSS as report.py. Statements are conditional on the computed numbers.
"""
import json, re, sys, statistics
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import report as R
from report import num, cagr, f, inr, trend, table, svg_bars, svg_lines, CSS, AUTHOR, ROOT

CACHE = Path(r"C:\ipo_cache")
IND = json.load(open(CACHE / "industry.json", encoding="utf-8"))
MET = json.load(open(CACHE / "metrics.json", encoding="utf-8"))
ABOUT_DIR = CACHE / "about"
ROWS = {r["company"]: r for r in json.load(open(ROOT / "data.json", encoding="utf-8"))["rows"]}
QUAL = json.load(open(ROOT / "reports" / "qual.json", encoding="utf-8")) if (ROOT / "reports" / "qual.json").exists() else {}


def srow(t, *keys):
    if not t:
        return None
    for key in keys:
        for k, v in t["rows"].items():
            if k.startswith(key):
                return [num(x) for x in v]
    return None


def fy(c):
    return "FY" + c[-2:]


def load_series(d, m):
    """Annual arrays aligned to FY labels: the source (Screener or Chittorgarh restated data) with more years."""
    A1 = _screener(d)
    A2 = _chitt(m)
    n1 = len(A1["labels"]) if A1 else 0
    n2 = len(A2["labels"]) if A2 else 0
    return A1 if n1 >= n2 and n1 >= 1 else (A2 if n2 >= 1 else None)


def _screener(d):
    pl, bs, cf, rt = d["profit-loss"], d["balance-sheet"], d["cash-flow"], d["ratios"]
    A = {}
    if pl and len(pl["cols"]) >= 1 and srow(pl, "Sales", "Revenue", "Total Income"):
        A["src"] = "Screener.in (consolidated)"
        A["labels"] = [fy(c) for c in pl["cols"]]
        A["sales"] = srow(pl, "Sales", "Revenue", "Total Income")
        A["op"] = srow(pl, "Operating Profit", "Financing Profit"); A["opm"] = srow(pl, "OPM", "Financing Margin")
        A["npf"] = srow(pl, "Net Profit"); A["eps"] = srow(pl, "EPS"); A["intr"] = srow(pl, "Interest")
        A["payout"] = srow(pl, "Dividend Payout")
        eq, res = srow(bs, "Equity Capital"), srow(bs, "Reserves")
        A["bor"] = srow(bs, "Borrowings", "Borrowing"); A["ta"] = srow(bs, "Total Assets", "Total Liabilities")
        A["nw"] = [(a or 0) + (b or 0) for a, b in zip(eq, res)] if eq and res else None
        A["cfo"] = srow(cf, "Cash from Operating"); A["cfi"] = srow(cf, "Cash from Investing"); A["fcf"] = srow(cf, "Free Cash Flow")
        A["ccc"] = srow(rt, "Cash Conversion"); A["wcd"] = srow(rt, "Working Capital"); A["roce"] = srow(rt, "ROCE")
        A["debd"] = srow(rt, "Debtor"); A["invd"] = srow(rt, "Inventory"); A["payd"] = srow(rt, "Days Payable")
        return A
    return None


def _chitt(m):
    A = {}
    per = m.get("periods") or []
    idx = [i for i, p in enumerate(per) if "Mar" in p][::-1]
    if len(idx) < 1:
        return None
    A["src"] = "Restated figures in the offer document (via Chittorgarh); Screener has no annual history yet"
    A["labels"] = ["FY" + per[i][-2:] for i in idx]

    def pick(key):
        v = m.get(key)
        return [v[i] if v and i < len(v) else None for i in idx] if v else None
    A["sales"], A["npf"], A["bor"], A["nw"] = pick("revenue"), pick("pat"), pick("borrowing"), pick("networth")
    for k in ("op", "opm", "eps", "intr", "payout", "ta", "cfo", "cfi", "fcf", "ccc", "wcd", "roce", "debd", "invd", "payd"):
        A[k] = None
    return A


def series_or_none(n, v):
    return v if v and len(v) == n else [None] * n


def gov_text(name, q):
    if q.get("gov"):
        return q["gov"]
    r = ROWS.get(name, {}); src = r.get("sources") or {}
    parts = ["The company is promoter-led."]
    s8 = (src.get("f8") or "").lower()
    if "no auditor qualification" in s8 or "no qualification" in s8 or "no auditor" in s8:
        parts.append("Our offer-document review found no auditor qualification (to be confirmed in the RHP).")
    s7 = (src.get("f7") or "").lower()
    if "no pledge" in s7:
        parts.append("No promoter share pledge was disclosed in the offer document.")
    parts.append("Board independence, committee structure and related-party transactions should be read in the RHP before investing.")
    return " ".join(parts)


def build(name):
    ind = IND.get(name, {})
    code = ind.get("code")
    d = json.load(open(CACHE / "screener_full" / f"{code}.json", encoding="utf-8"))
    m = MET.get(name, {})
    ab = json.load(open(ABOUT_DIR / f"{code}.json", encoding="utf-8")).get("about", "") if (ABOUT_DIR / f"{code}.json").exists() else ""
    q = QUAL.get(name)
    if not q:
        print("SKIP (no qualitative content):", name); return None
    A = load_series(d, m)
    if not A or not A["sales"] or not A["npf"]:
        print("SKIP (no financials):", name); return None
    n = len(A["labels"])
    labels = A["labels"]
    S = {k: (series_or_none(n, A[k]) if k != "src" and k != "labels" else A[k]) for k in A}
    sales, npf, nw, bor, ta, op, intr = S["sales"], S["npf"], S["nw"], S["bor"], S["ta"], S["op"], S["intr"]
    opm = S["opm"]
    if all(v is None for v in opm) and any(v is not None for v in op):
        opm = [op[i] / sales[i] * 100 if op[i] is not None and sales[i] else None for i in range(n)]
    npm = [npf[i] / sales[i] * 100 if npf[i] is not None and sales[i] else None for i in range(n)]
    roe = [None] + [(npf[i] / ((nw[i] + nw[i - 1]) / 2) * 100) if (nw[i] and nw[i - 1] and npf[i] is not None) else None for i in range(1, n)]
    if all(v is None for v in roe) and nw[-1] and npf[-1] is not None:  # single-year: on closing net worth
        roe[-1] = npf[-1] / nw[-1] * 100
    de = [bor[i] / nw[i] if (bor[i] is not None and nw[i]) else None for i in range(n)]
    at = [None] + [(sales[i] / ((ta[i] + ta[i - 1]) / 2)) if (ta[i] and ta[i - 1] and sales[i]) else None for i in range(1, n)]
    icov = [op[i] / intr[i] if (op[i] is not None and intr[i]) else None for i in range(n)]
    eps = S["eps"]
    if all(v is None for v in eps) and ind:
        pass
    # ---- market data ----
    top = d["top"]
    mcap = num(top.get("Market Cap")); price = num(top.get("Current Price")); hi_lo = top.get("High / Low", "n/a")
    pe = num(top.get("Stock P/E"))
    price_note = ""
    if not price and m.get("last_trade"):
        price = m["last_trade"]; price_note = " Price is the last trade on the exchange (Chittorgarh); Screener has no quote yet."
        if m.get("shares_post"):
            mcap = price * m["shares_post"] / 1e7
        hi_lo = "n/a"
    epsL = eps[-1] if eps and eps[-1] is not None else None
    if pe is None and epsL and price:
        pe = price / epsL if epsL > 0 else None
    shares = mcap / price if mcap and price else None
    if pe is None and mcap and npf[-1] and npf[-1] > 0:
        pe = mcap / npf[-1]; price_note += f" P/E is market cap divided by {labels[-1]} restated profit."
    if epsL is None and npf[-1] is not None and shares:
        epsL = npf[-1] / shares
    ind_pe, ind_name = ind.get("median_pe"), ind.get("industry", "")
    issue_price, post_pe = m.get("issue_price"), m.get("pe_post")
    # growth
    def span(v):
        pts = [(i, x) for i, x in enumerate(v) if x is not None and x > 0]
        if len(pts) < 2: return None, None, None
        (i0, a), (i1, b) = pts[0], pts[-1]
        return cagr(a, b, i1 - i0), labels[i0], labels[i1]
    rev_c, rv0, rv1 = span(sales)
    pat_c, pt0, pt1 = span(npf)
    eps_c, ep0, ep1 = span(eps) if any(eps) else (None, None, None)
    def yoy(v):
        return (v[-1] / v[-2] - 1) * 100 if len(v) > 1 and v[-1] is not None and v[-2] and v[-2] > 0 and v[-1] > 0 else None
    rev_y, pat_y = yoy(sales), yoy(npf)
    eps_y = yoy(eps) if any(eps) else pat_y

    # ---- valuation ----
    g = None
    eps_val = (price / pe) if (price and pe and pe > 0) else epsL
    rating_ok = bool(eps_val and eps_val > 0 and price)
    if rating_ok:
        comps = [x for x in (eps_y, pat_c) if x is not None]
        base = (sum(comps) / len(comps)) if comps else 10
        g = max(0.08, min(0.35, 0.6 * base / 100))
        eps27 = eps_val * (1 + g)
        qual_factor = 1.0
        roce_l = S["roce"][-1]
        cfo_l = S["cfo"][-1]
        if (roce_l is not None and roce_l >= 20 and g >= 0.2): qual_factor = 1.15
        if (roce_l is not None and roce_l < 12) or (cfo_l is not None and cfo_l < 0): qual_factor = 0.85
        t_pe0 = (ind_pe or 25.0) * qual_factor
        t_pe = 0.4 * t_pe0 + 0.6 * (pe if pe else t_pe0)  # multiples converge only partly (40%) in 12 months
        v1 = eps27 * t_pe
        peg_pe = max(12.0, min(40.0, g * 100 * 1.5))
        v2 = eps27 * peg_pe
        target = round(0.5 * v1 + 0.5 * v2)
        upside = (target / price - 1) * 100
        capped = abs(upside) > 35
        if capped:
            target = round(price * (1.35 if upside > 0 else 0.65)); upside = (target / price - 1) * 100
        if upside > 15: rec_full, rec = "Buy", "BUY"
        elif upside >= -10: rec_full, rec = "Hold", "HOLD"
        else: rec_full, rec = "Sell", "SELL"
        downgraded = False
        if rec == "BUY":
            roe_l, de_l, dd_l = roe[-1], de[-1], S["debd"][-1]
            q_ok = ((roe_l or 0) >= 15 or (S["roce"][-1] or 0) >= 15) and (S["cfo"][-1] is None or S["cfo"][-1] > 0) and (de_l is None or de_l <= 1.5 or q.get("financial")) and (dd_l is None or dd_l <= 150)
            if not q_ok:
                rec_full, rec, downgraded = "Hold", "HOLD", True
    else:
        rec_full = rec = "NOT RATED"
    cls = {"BUY": "", "HOLD": "hold", "SELL": "sell", "NOT RATED": "hold"}[rec]
    hz = "12 months"
    if rating_ok:
        sign = "upside" if upside >= 0 else "downside"
        reco = f"""<div class="reco {cls}"><div class="r1">Investment Recommendation</div><div class="r2">{rec}</div>
<div class="r3"><span><b>Target Price:</b> <span class="hl">{inr(target)}</span> ({abs(upside):.0f}% {sign} to CMP {inr(price)})</span><span><b>Investment Horizon:</b> {hz}</span></div></div>"""
    else:
        reco = f"""<div class="reco hold"><div class="r1">Investment Recommendation</div><div class="r2">NOT RATED</div>
<div class="r3"><span>No target price: latest earnings are zero, negative or unavailable, so earnings-based valuation is not meaningful.</span></div></div>"""

    # table helpers
    W = min(5, n)
    Lc = slice(n - W, n)
    Hd = ["Metric"] + labels[Lc][::-1] + ["Trend"]

    def r5(label, vals, dp=1, suf="", hib=True):
        v = vals[Lc] if vals else [None] * W
        t = trend(v, hib) if sum(x is not None for x in v) >= 3 else ("Limited data", "neu")
        return [label] + [f"{f(x,dp)}{suf}" if x is not None else "n/a" for x in v[::-1]] + [t]

    def last(v):
        return v[-1] if v else None

    def tone(a, b, hi, lo=None):
        return "improved" if (a is not None and b is not None and a > b) else "weakened"

    chips = f"""<div class="chips"><div class="chip">Sector<b>{q.get('sector', ind_name or 'n/a')}</b></div><div class="chip">Market Cap<b>{inr(mcap)} Cr</b></div>
<div class="chip">CMP<b>{inr(price)}</b></div><div class="chip">P/E (TTM)<b>{f(pe)}x</b></div><div class="chip">52-wk High / Low<b>{hi_lo}</b></div></div>"""
    s = [f"""<div class="hd"><div class="brand">Equity Research · Indian Equities</div><h1>{name} Ltd - Equity Analysis Report</h1><div class="by">By {AUTHOR}</div>{chips}</div><div class="bd">"""]

    # 1 overview
    sents = re.split(r"(?<=[.!?])\s+", ab)
    intro = " ".join(sents[:3]).strip() or q.get("summary", "")
    ipo_bits = []
    if m.get("issue_cr"): ipo_bits.append(f"IPO of <b>₹{f(m['issue_cr'],0)} Cr</b>" + (f" (fresh issue {m['fresh_pct']:.0f}%)" if m.get("fresh_pct") is not None else "") + (f" at <b>₹{f(issue_price,0)}</b> per share" if issue_price else ""))
    if m.get("sub_total"): ipo_bits.append(f"subscribed <b>{f(m['sub_total'])}x</b>")
    if m.get("listed_on"): ipo_bits.append(f"listed on <b>{m['listed_on'].split(', ',1)[-1]}</b>")
    res_line = ""
    if sales[-1] is not None and npf[-1] is not None:
        res_line = f"<li><b>Latest annual results ({labels[-1]}):</b> revenue ₹{f(sales[-1],0)} Cr" + (f" ({rev_y:+.0f}% YoY)" if rev_y is not None else "") + f" and net profit ₹{f(npf[-1],0)} Cr" + (f" ({pat_y:+.0f}% YoY)" if pat_y is not None else "") + ".</li>"
    pro = ""
    if m.get("promoter_pre") is not None and m.get("promoter_post") is not None:
        pro = f"<li><b>Ownership:</b> promoter holding moved from {m['promoter_pre']:.2f}% before the IPO to {m['promoter_post']:.2f}% after it.</li>"
    s.append(f"<h2>1. Company Overview</h2><p>{intro}</p><ul><li><b>Recent events:</b> " + (", ".join(ipo_bits) if ipo_bits else "recently listed on the Indian exchanges") + ".</li>" + res_line + pro + "</ul>")
    s.append("<h3>Investment Recommendation</h3>" + reco)

    # 2 quantitative
    short = n < 5
    note = f"Annual data source: {A['src']}. Latest annual period shown: {labels[-1]}." + (" Fewer than five fiscal years are available because the company was recently listed; tables show every year available." if short else "")
    s.append('<h2 class="pb">2. Quantitative Analysis</h2><p class="kt"><b>Data basis:</b> ' + note + " Market data is the latest Screener quote." + price_note + "</p>")

    # a
    rng = None
    try:
        h_, l_ = [num(x) for x in hi_lo.split("/")]
        rng = (price - l_) / (h_ - l_) if h_ != l_ else None
    except Exception:
        pass
    vt = [["Market Capitalization", f"{inr(mcap)} Cr", ("Recently listed", "neu")],
          ["Current Stock Price", f"{inr(price)} (52-wk {hi_lo})", (("Lower half of range" if rng is not None and rng < 0.5 else "Upper half of range") if rng is not None else "n/a", "neu")]]
    if issue_price and price:
        up_ = (price / issue_price - 1) * 100
        vt.append(["IPO Issue Price", f"{inr(issue_price)} (CMP {abs(up_):.0f}% {'above' if up_ >= 0 else 'below'})", ("Gain since IPO" if up_ >= 0 else "Below IPO price", "pos" if up_ >= 0 else "neg")])
    vt.append(["Price-to-Earnings (P/E) Ratio", (f"{f(pe)}x (TTM)" if pe else "n/a") + (f" · {f(post_pe)}x at IPO price" if post_pe else ""),
               (("Above industry median" if pe and ind_pe and pe > ind_pe else "At or below industry median") if (pe and ind_pe) else "n/a", ("neg" if pe and ind_pe and pe > ind_pe else "pos"))])
    s.append("<h3>a) Market Valuation and Price Metrics</h3>" + table(["Metric", f"Current Value ({labels[-1]} / latest)", "Trend"], vt))
    prem = ((pe / ind_pe - 1) * 100) if (pe and ind_pe) else None
    atxt = f"The stock has only a short trading history since listing, so a five-year price trend is not available." + (f" It trades at {f(pe)}x trailing earnings versus {f(post_pe)}x at the IPO price." if pe and post_pe else "")
    ktxt = (f"At a market capitalisation of {inr(mcap)} Cr, the P/E of {f(pe)}x is {abs(prem):.0f}% {'above' if prem >= 0 else 'below'} the {ind_name} industry median of {f(ind_pe)}x" + (", so investors are already paying a premium for growth." if prem >= 0 else ", so the stock is valued at a discount to its industry.")) if prem is not None else "A like-for-like industry P/E comparison could not be computed."
    s.append(f'<p class="ta"><span class="lbl">Trend Analysis</span> {atxt}</p><p class="kt"><span class="lbl">Key Takeaways</span> {ktxt}</p>')

    # b
    s.append("<h3>b) Profitability and Returns</h3>" + table(Hd, [r5("Return on Equity (ROE)", roe, 1, "%"), r5("Return on Capital Employed (ROCE)", S["roce"], 1, "%"), r5("Net Profit Margin", npm, 1, "%"), r5("Operating Profit Margin", opm, 1, "%")]))
    ser = [("ROE", roe), ("Net margin", npm), ("Operating margin", opm), ("ROCE", S["roce"])]
    ser = [(a, b) for a, b in ser if sum(x is not None for x in b) >= 2]
    if len(ser) and n >= 3:
        cols_ = ["#12355b", "#1a7f4b", "#d98200", "#8e44ad"]
        pad = [[x for x in b] for a, b in ser]
        s.append(svg_lines(labels, [(a, [x if x is not None else None for x in b]) for a, b in ser], cols_[:len(ser)], "Returns and margins (%)"))
    def rng_txt(v, nm):
        vv = [x for x in v if x is not None]
        if len(vv) < 2: return f"{nm} is available for only one year ({f(vv[-1]) + '%' if vv else 'n/a'})."
        d_ = vv[-1] - vv[0]
        return f"{nm} {'rose' if d_ > 0 else 'fell'} from {f(vv[0])}% to {f(vv[-1])}%."
    btxt = " ".join([rng_txt(roe, "ROE"), rng_txt(npm, "Net margin"), rng_txt(opm, "Operating margin")]) + (f" ROCE moved from {f(next((x for x in S['roce'] if x is not None), None))}% to {f(S['roce'][-1])}%." if S["roce"][-1] is not None else "")
    ind_roce = None
    for r_ in (d.get("peers") or []):
        if len(r_) > 10 and r_[1].startswith("Median"): ind_roce = num(r_[10])
    kb = f"Latest ROCE of {f(S['roce'][-1])}% compares with an industry median of {f(ind_roce)}%." if (S["roce"][-1] is not None and ind_roce is not None) else "Industry return benchmarks are shown in the peer table below."
    kb += (" Operating margin below 10% leaves limited cushion against cost shocks." if opm[-1] is not None and opm[-1] < 10 else "") + (" Returns are high enough to support reinvestment at attractive rates." if (roe[-1] or 0) >= 18 else (" Returns are modest and need to improve to justify a premium valuation." if (roe[-1] is not None and roe[-1] < 12) else ""))
    s.append(f'<p class="ta"><span class="lbl">Trend Analysis</span> {btxt}</p><p class="kt"><span class="lbl">Key Takeaways</span> {kb}</p>')

    # c
    gl = lambda a, b: f"{a}-{b}" if a and b else "n/a"
    grow_rows = [["Revenue Growth Rate", f"{f(rev_c)}% ({gl(rv0, rv1)})", f"{f(rev_y)}%", ("Strong" if (rev_c or 0) >= 15 else ("Moderate" if (rev_c or 0) >= 8 else "Weak"), "pos" if (rev_c or 0) >= 15 else ("neu" if (rev_c or 0) >= 8 else "neg"))],
                 ["Net Profit Growth", f"{f(pat_c)}% ({gl(pt0, pt1)})", f"{f(pat_y)}%", ("Strong" if (pat_c or 0) >= 15 else ("Moderate" if (pat_c or 0) >= 8 else "Weak"), "pos" if (pat_c or 0) >= 15 else ("neu" if (pat_c or 0) >= 8 else "neg"))]]
    if eps_c is not None:
        grow_rows.append(["EPS Growth Rate", f"{f(eps_c)}% ({gl(ep0, ep1)})", f"{f(yoy(eps))}%", ("Strong" if eps_c >= 15 else "Moderate", "pos" if eps_c >= 15 else "neu")])
    s.append("<h3>c) Growth Metrics</h3>" + table(["Metric", "CAGR (period available)", f"Latest YoY ({labels[-1]})", "Trend"], grow_rows))
    s.append(svg_bars(labels, [("Revenue (₹ Cr)", sales), ("Net profit (₹ Cr)", npf)], ["#12355b", "#c8a24a"], "Revenue and net profit (₹ Cr)"))
    ctxt = f"Revenue moved from ₹{f(sales[0],0)} Cr in {labels[0]} to ₹{f(sales[-1],0)} Cr in {labels[-1]}" + (f", a CAGR of {f(rev_c)}%" if rev_c is not None else "") + f". Net profit moved from ₹{f(npf[0],0)} Cr to ₹{f(npf[-1],0)} Cr" + (f" ({f(pat_c)}% CAGR)" if pat_c is not None else "") + "."
    ck = ("Growth is strong and ahead of the 15% hurdle." if ((rev_c or 0) >= 15 and (pat_c or 0) >= 15) else "Growth is below the 15% hurdle on at least one of revenue or profit, which limits the case for a premium multiple.")
    if g is not None and pe:
        ck += f" With a P/E of {f(pe)}x and expected earnings growth of about {g*100:.0f}%, the PEG ratio is about {pe/(g*100):.1f}."
    s.append(f'<p class="ta"><span class="lbl">Trend Analysis</span> {ctxt}</p><p class="kt"><span class="lbl">Key Takeaways</span> {ck}</p>')

    # d
    fin_note = " Because this company lends or earns fee income, debt-to-equity is not a like-for-like leverage measure." if q.get("financial") else ""
    s.append("<h3>d) Balance Sheet Strength</h3>" + table(Hd, [r5("Debt-to-Equity Ratio", de, 2, "", False), r5("Borrowings (₹ Cr)", bor, 0, "", False), r5("Net Worth (₹ Cr)", nw, 0), r5("Interest Coverage (x)", icov, 1, "x")]))
    s.append(svg_bars(labels, [("Borrowings (₹ Cr)", bor), ("Net worth (₹ Cr)", nw)], ["#c0392b", "#1a7f4b"], "Borrowings vs net worth (₹ Cr)"))
    dl = de[-1]
    dcls = "low" if (dl is not None and dl < 0.5) else ("moderate" if (dl is not None and dl <= 1) else "high")
    dtxt = (f"Debt-to-equity is {f(dl,2)} at {labels[-1]}, which is {dcls}" + (f", versus {f(next((x for x in de if x is not None), None),2)} at {labels[0]}" if len([x for x in de if x is not None]) > 1 else "") + ".") if dl is not None else "Debt-to-equity could not be computed from the available data."
    dk = {"low": "Low leverage gives financial flexibility.", "moderate": "Leverage is manageable but should be watched.", "high": "Leverage is above 1.0x, which raises financial risk, particularly if earnings dip."}[dcls] + fin_note
    s.append(f'<p class="ta"><span class="lbl">Trend Analysis</span> {dtxt}</p><p class="kt"><span class="lbl">Key Takeaways</span> {dk}</p>')

    # e
    s.append("<h3>e) Cash Flow Analysis</h3>")
    if any(v is not None for v in S["cfo"]):
        s.append(table(Hd, [r5("Cash Flow from Operations (₹ Cr)", S["cfo"], 0), r5("Cash Flow from Investing (₹ Cr)", S["cfi"], 0, "", False)[:-1] + [("Capex / investment", "neu")], r5("Free Cash Flow (₹ Cr)", S["fcf"], 0)]))
        s.append(svg_bars(labels, [("Operating CF", S["cfo"]), ("Net profit", npf)], ["#12355b", "#c8a24a"], "Operating cash flow versus profit (₹ Cr)"))
        cf_l, np_l = S["cfo"][-1], npf[-1]
        etxt = f"Operating cash flow was ₹{f(cf_l,0)} Cr in {labels[-1]} against net profit of ₹{f(np_l,0)} Cr" + (f" (conversion of {cf_l/np_l*100:.0f}%)" if (cf_l is not None and np_l and np_l > 0) else "") + "."
        neg_years = sum(1 for x in S["cfo"] if x is not None and x < 0)
        ek = ("Cash generation supports reported profits." if (cf_l or 0) > (np_l or 0) * 0.7 else "Cash flow lags profit, so earnings quality needs monitoring.") + (f" Operating cash flow was negative in {neg_years} of {sum(1 for x in S['cfo'] if x is not None)} years." if neg_years else "")
    else:
        s.append("<p>Annual cash flow statements are not yet available for this company; the IPO restated figures show profit and balance sheet only.</p>")
        etxt = "Cash flow history is not available in the sources used. A qualitative view: asset-light or fast-growing businesses often show weak operating cash flow in early years; the RHP and first annual report should be checked."
        ek = "Treat cash conversion as an open question until audited cash flow statements are available."
    s.append(f'<p class="ta"><span class="lbl">Trend Analysis</span> {etxt}</p><p class="kt"><span class="lbl">Key Takeaways</span> {ek}</p>')

    # f
    pay = S["payout"]
    s.append("<h3>f) Dividend Analysis</h3>")
    if any(v is not None for v in pay):
        s.append(table(Hd, [r5("Dividend Payout Ratio", pay, 0, "%")]))
        pl_ = pay[-1]
        dyield = num(top.get("Dividend Yield")) or 0
        s.append(f'<p class="ta"><span class="lbl">Trend Analysis</span> Dividend payout in {labels[-1]} was {f(pl_,0)}% and the current dividend yield is {f(dyield,2)}%.</p><p class="kt"><span class="lbl">Key Takeaways</span> ' + ("Profits are retained for growth, so income investors should not expect dividends." if (pl_ or 0) < 5 else "The company returns part of its profit to shareholders.") + "</p>")
    else:
        s.append('<p class="ta"><span class="lbl">Trend Analysis</span> No dividend history is available because the company was only recently listed.</p><p class="kt"><span class="lbl">Key Takeaways</span> Dividend policy should be read in the RHP; most newly listed growth companies retain profits.</p>')

    # g
    s.append("<h3>g) Efficiency Ratios</h3>")
    if any(v is not None for v in at) or any(v is not None for v in S["ccc"]):
        rows_ = [r5("Asset Turnover Ratio (x)", at, 2, "x")]
        for lab, key in (("Cash Conversion Cycle (days)", "ccc"), ("Debtor Days", "debd"), ("Inventory Days", "invd")):
            if any(v is not None for v in S[key]): rows_.append(r5(lab, S[key], 0, "", False))
        s.append(table(Hd, rows_))
        gtxt = (f"Asset turnover is {f(last(at),2)}x in {labels[-1]}" if last(at) is not None else "Asset turnover is not available") + (f" and the cash conversion cycle is {f(last(S['ccc']),0)} days." if last(S["ccc"]) is not None else ".")
        gk = ("Debtor days above 90 point to slow collections and working capital risk. " if (last(S["debd"]) or 0) > 90 else "") + ("Working capital is managed efficiently." if (last(S["ccc"]) is not None and last(S["ccc"]) < 60) else "Working capital intensity is high and ties up cash as the company grows.")
    else:
        s.append("<p>Working-capital ratios are not available in the sources used.</p>")
        gtxt = "Asset turnover can be estimated only roughly from the offer document figures."
        gk = "Efficiency is a monitoring item for the first annual results after listing."
    s.append(f'<p class="ta"><span class="lbl">Trend Analysis</span> {gtxt}</p><p class="kt"><span class="lbl">Key Takeaways</span> {gk}</p>')

    # h peers
    peers = d.get("peers") or []
    plist = []
    for r_ in peers[1:]:
        if len(r_) > 10 and not r_[1].startswith("Median") and name.split()[0].lower() not in r_[1].lower():
            plist.append((r_[1], num(r_[3]), num(r_[10]), num(r_[4])))
    plist = [p for p in plist if p[1] is not None]
    plist.sort(key=lambda x: -(x[3] or 0))
    sel = plist[:4]
    prow = [[f"<b>{name}</b>", f(pe, 1), f(S['roce'][-1], 1) + "%" if S["roce"][-1] is not None else "n/a", f(dl, 2) if dl is not None else "n/a"]] + [[p[0], f(p[1], 1), f(p[2], 1) + "%", "-"] for p in sel]
    prow.append([f"Industry Median ({ind_name})", f(ind_pe, 1), f(ind_roce, 1) + "%" if ind_roce is not None else "-", "-"])
    hv = (f"{name} trades at {f(pe)}x versus an industry median of {f(ind_pe)}x" + (f", a {'premium' if pe > ind_pe else 'discount'} of {abs(pe/ind_pe-1)*100:.0f}%" if (pe and ind_pe) else "") + ".") if ind_pe else "Industry median P/E is not available."
    hk = "The peer set mixes companies of very different size and quality, so the comparison is indicative rather than exact. " + ("The IPO price of about " + f(post_pe) + "x was priced " + ("above" if (post_pe and ind_pe and post_pe > ind_pe) else "at or below") + " the industry median.") if (post_pe and ind_pe) else "The peer set mixes companies of very different size and quality, so the comparison is indicative rather than exact."
    s.append("<h3>h) Valuation Metrics Comparison with Industry Peers</h3>" + table(["Company", "P/E Ratio", "ROCE", "Debt/Equity"], prow))
    s.append(f'<p class="ta"><span class="lbl">Trend Analysis</span> {hv}</p><p class="kt"><span class="lbl">Key Takeaways</span> {hk}</p>')

    # flags
    flags = []
    if dl is not None and dl > 1: flags.append(f"Debt-to-equity of {f(dl,2)} is above 1.0x.")
    if sum(1 for x in S["cfo"] if x is not None and x < 0) >= 1: flags.append("Operating cash flow was negative in one or more years.")
    if opm[-1] is not None and opm[-1] < 8: flags.append(f"Operating margin of {f(opm[-1])}% is thin.")
    if (last(S["debd"]) or 0) > 90: flags.append(f"Debtor days of {f(last(S['debd']),0)} indicate slow collections.")
    if pat_y is not None and pat_y < 0: flags.append("Net profit declined in the latest year.")
    if prem is not None and prem > 20: flags.append(f"P/E is {prem:.0f}% above the industry median.")
    if m.get("promoter_post") is not None and m["promoter_post"] < 50: flags.append(f"Promoter holding is only {m['promoter_post']:.0f}% after the issue.")
    if short: flags.append("Short financial and trading history after listing.")
    for x in q.get("risks", []): flags.append(x)
    chg = []
    if rev_y is not None: chg.append(f"revenue {rev_y:+.0f}% and net profit {(f'{pat_y:+.0f}%' if pat_y is not None else 'n/a')} year on year in {labels[-1]}")
    s.append('<p class="ta"><span class="lbl">Red flags, significant changes and implications</span></p><ul>' + (f"<li><b>Significant changes:</b> {'; '.join(chg)}.</li>" if chg else "") + "".join(f"<li>{x}</li>" for x in (flags or ["No major red flags are visible in the data reviewed."])) + "</ul>")

    # 3 qualitative
    ls = lambda xs: "<ul>" + "".join(f"<li>{x}</li>" for x in xs) + "</ul>"
    obj = m.get("objects") or []
    growth_items = list(q.get("growth", []))
    if obj and m.get("fresh_cr"):
        growth_items.append("Use of IPO proceeds: " + "; ".join(f"{o[0][:70]} (₹{f(o[1],0)} Cr)" for o in obj[:3] if o[1]) + ".")
    s.append('<h2 class="pb">3. Qualitative Analysis</h2><h3>a) Business Model</h3><h4>Core Products/Services</h4>' + ls(q["core"]) + f"<h4>Revenue Streams</h4><p>{q['revenue']}</p><h4>Competitive Advantages</h4>" + ls(q["adv"]))
    s.append(f"<h3>b) Management Quality</h3><p><b>Experience and track record:</b> {q['mgmt']}</p><p><b>Corporate governance practices:</b> {gov_text(name, q)}</p>")
    s.append("<h3>c) Growth Strategy</h3><h4>Expansion Plans</h4>" + ls(growth_items or ["Expansion plans are described in the offer document."]) + f"<h4>Research and Development Initiatives</h4><p>{q.get('rnd', 'No material standalone R&amp;D programme is highlighted in the sources reviewed; competitiveness rests on manufacturing, sourcing and distribution execution.')}</p>")

    # 4 shareholding
    sh = d["shareholding"]; shr = sh["rows"] if sh else {}
    pre, post = m.get("promoter_pre"), m.get("promoter_post")
    lastc = sh["cols"][-1] if sh else "latest"
    g1 = lambda k: shr.get(k, ["n/a"])[-1] if shr else "n/a"
    s.append("<h2>4. Shareholding Pattern Analysis</h2>" + table(["Category", "Pre-IPO (DRHP)", "Post-IPO (at allotment)", f"{lastc} (latest)", "Trend"],
        [["Promoters", f"{f(pre,2)}%" if pre is not None else "n/a", f"{f(post,2)}%" if post is not None else "n/a", g1("Promoters"), ("Diluted by IPO", "neu")],
         ["Foreign Institutional Investors (FIIs)", "-", "-", g1("FIIs"), ("Post-listing starting point", "neu")],
         ["Domestic Institutional Investors (DIIs)", "-", "-", g1("DIIs"), ("Post-listing starting point", "neu")],
         ["Public", f"{f(100-pre,2)}%" if pre is not None else "n/a", f"{f(100-post,2)}%" if post is not None else "n/a", g1("Public"), ("Wide retail base" if True else "", "neu")]]))
    pn = num(g1("Promoters"))
    s.append(f"""<ul><li><b>Promoter holding:</b> {f(pre,2)}% before the IPO, {f(post,2)}% after allotment and {g1('Promoters')} in {lastc}.</li>
<li><b>Institutional holdings:</b> FIIs {g1('FIIs')} and DIIs {g1('DIIs')} in the first reported quarter after listing. There is no trend yet, only a starting point.</li>
<li><b>Public shareholding:</b> {g1('Public')} held by about {g1('No. of Shareholders')} shareholders.</li></ul>
<p class="kt"><span class="lbl">Key Takeaways</span> {'Promoters hold a controlling stake, which supports alignment but limits free float.' if (pn or 0) >= 60 else 'Promoter stake is below 60%, so governance depends more on institutional oversight.'} Institutional trends should be tracked over the coming quarters, and lock-in expiries of pre-IPO and anchor shares can create near-term supply.</p>""")

    # 5 thesis
    s.append('<h2 class="pb">5. Investment Thesis</h2><h3>Key Drivers for Future Growth</h3><ol>' + "".join(f"<li>{x}</li>" for x in q["drivers"]) + "</ol><h3>Potential Catalysts for Stock Price Movement</h3><ol>" + "".join(f"<li>{x}</li>" for x in q["catalysts"]) + "</ol><h3>Positioning for Industry Trends and Challenges</h3><ol>" + "".join(f"<li>{x}</li>" for x in q["positioning"]) + "</ol>")

    # 6 valuation
    s.append("<h2>6. Valuation and Recommendation</h2><h3>Fair Value Estimate</h3>")
    if rating_ok:
        s.append("<p>Two earnings-based methods are blended equally: (1) relative valuation at the industry median P/E, adjusted for quality, and (2) a growth-adjusted P/E (PEG of 1.5).</p>" + table(["Method", "Key assumptions", "Value per share", "Weight"],
            [["Industry-relative P/E", f"FY27E EPS {inr(eps27,2)} (trailing EPS {inr(eps_val,2)} +{g*100:.0f}%) × {t_pe:.1f}x (60% current {f(pe)}x and 40% industry-based {t_pe0:.1f}x = industry median {f(ind_pe) if ind_pe else '25 (default)'}x × quality factor {qual_factor:.2f})", inr(v1), "50%"],
             ["Growth-adjusted P/E", f"FY27E EPS {inr(eps27,2)} × {peg_pe:.1f}x (growth {g*100:.0f}% × 1.5, bounded 12-40x)", inr(v2), "50%"],
             ["<b>Blended fair value</b>", "", f'<span class="hl">{inr(target)}</span>', "100%"]]))
        s.append(f"<p>The growth assumption ({g*100:.0f}%) is set at 60% of the average of the latest year-on-year earnings growth and the period profit CAGR, bounded between 8% and 35%, to allow for a normalising base. Quality factor is 1.15 when ROCE is at least 20% with growth of 20% or more, 0.85 when ROCE is below 12% or operating cash flow is negative, otherwise 1.0. These are the author's estimates, not company guidance." + (" The model gap exceeded 35%, so the target is capped at 35% above or below the current price." if capped else "") + (" The valuation gap points to a Buy, but the rating is held at Hold because the quality screen failed (returns below 15%, negative operating cash flow, debt-to-equity above 1.5 or debtor days above 150)." if downgraded else "") + price_note + "</p>")
    else:
        s.append("<p>A target price is not given because the latest reported earnings are zero or negative, or the data needed is unavailable. Valuation would rest on revenue multiples and a path to profitability, which are too uncertain to estimate responsibly here.</p>")
    s.append("<h3>Investment Recommendation</h3>" + reco + "<p><b>Recommendation rating: " + rec_full + ".</b> Rating bands: Buy above +15%, Hold -10% to +15%, Sell below -10% versus the current price." + (" The estimated gap exceeds 30%, which signals high model uncertainty; treat the target as indicative and verify against the RHP and peers." if (rating_ok and abs(upside) > 30) else "") + (" For lenders, brokers and asset managers the P/E-based approach is only a rough guide." if q.get("financial") else "") + "</p>")
    rat = []
    if rating_ok:
        rat.append(f"<b>Valuation:</b> the blended fair value of {inr(target)} is {abs(upside):.0f}% {'above' if upside >= 0 else 'below'} the current price.")
    if rev_c is not None: rat.append(f"<b>Growth:</b> revenue CAGR of {f(rev_c)}% and profit CAGR of {f(pat_c)}%.")
    if S["roce"][-1] is not None: rat.append(f"<b>Returns:</b> ROCE of {f(S['roce'][-1])}% and ROE of {f(roe[-1])}%.")
    if dl is not None: rat.append(f"<b>Balance sheet:</b> debt-to-equity of {f(dl,2)}.")
    rat.append("<b>Key risks:</b> " + ("; ".join(q.get("risks", [])[:2]) or "see red flags above") + ".")
    s.append("<h3>Rationale for Recommendation</h3><ol>" + "".join(f"<li>{x}</li>" for x in rat) + "</ol>")
    concl = f"<p>{name} {q.get('concl', 'is a recently listed company with a business model described above.')}</p><p>On our estimates the stock {'has a blended fair value of <b>' + inr(target) + '</b> (' + f'{abs(upside):.0f}% ' + ('upside' if upside >= 0 else 'downside') + ' to the current price) over ' + hz + ', which supports a <b>' + rec + '</b> recommendation.' if rating_ok else 'is <b>not rated</b> because earnings-based valuation is not meaningful at present.'} Investors should confirm the numbers against the RHP and the first annual report, and keep position sizes appropriate to the risks outlined.</p>"
    s.append("<h2>7. Conclusion</h2>" + concl + "</div>")
    s.append(f"""<div class="ft"><b>Disclaimer:</b> This report is for information and education only. It is not investment advice, a solicitation or an offer to buy or sell any security. Figures are taken from Screener.in, the company's offer document and Chittorgarh and may contain errors or omissions; forecasts and the target price are the author's estimates based on stated assumptions and may not materialise. Equity investments carry risk of loss. Please consult a SEBI-registered adviser before acting.<br><b>Published by:</b> {AUTHOR} · IPO Screening Desk · Sources: Screener.in, SEBI offer documents, Chittorgarh.</div>""")
    frag = f'<style>{CSS}</style><div class="rpt">{"".join(s)}</div>'
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    (ROOT / "reports" / f"{slug}.frag.html").write_text(frag, encoding="utf-8")
    full = f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{name} - Equity Analysis Report</title><style>body{{margin:0;background:#e9edf2}}@media print{{body{{background:#fff}}}}</style></head><body>{frag}</body></html>'
    (ROOT / "reports" / f"{slug}.html").write_text(full, encoding="utf-8")
    print(f"{name:28} {rec_full:12} target={(target if rating_ok else '-')!s:>6} {(f'{upside:+.0f}%' if rating_ok else ''):>6} years={n} src={'S' if 'Screener' in A['src'] else 'C'}")
    return slug


if __name__ == "__main__":
    names = [x for x in sys.argv[1:] if not x.startswith("--")]
    if "--all" in sys.argv:
        names = [k for k in QUAL if k != "Karamtara Engineering"]
    for nm in names:
        try:
            build(nm)
        except Exception as e:
            import traceback; traceback.print_exc(); print("ERR", nm, e)
