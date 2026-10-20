"""Equity research report generator (7-section format) from Screener data + IPO metrics.

Usage: python scripts/report.py KARAMTARA "Karamtara Engineering"
Writes reports/<slug>.html (full document) and reports/<slug>.frag.html (embeddable fragment, CSS scoped to .rpt).
Company-specific qualitative content lives in CONTENT (keyed by company name); numbers are computed from Screener.
"""
import json, re, sys, statistics
from pathlib import Path

ROOT = Path(r"C:\ipo_repo")
AUTHOR = "CA Niraj Variava"


# ---------- helpers ----------
def num(s):
    if s is None:
        return None
    s = str(s).replace(",", "").replace("%", "").replace("₹", "").replace("Cr.", "").strip()
    if s in ("", "-"):
        return None
    try:
        return float(s)
    except ValueError:
        m = re.search(r"-?\d+(?:\.\d+)?", s)
        return float(m.group()) if m else None


def row(tbl, key):
    for k, v in tbl["rows"].items():
        if k.startswith(key):
            return [num(x) for x in v]
    return None


def cagr(a, b, yrs):
    return ((b / a) ** (1 / yrs) - 1) * 100 if a and b and a > 0 and b > 0 else None


def f(x, d=1):
    return "n/a" if x is None else f"{x:,.{d}f}"


def inr(x, d=0):
    return "n/a" if x is None else "₹" + f"{x:,.{d}f}"


def trend(vals, hib=True, tol=0.07):
    v = [x for x in vals if x is not None]
    if len(v) < 3:
        return ("Limited data", "neu")
    a = statistics.mean(v[:2]); b = statistics.mean(v[-2:])
    sign_flip = any(x < 0 for x in v) and any(x > 0 for x in v)
    rng = max(v) - min(v)
    base = max(abs(statistics.mean(v)), 1e-9)
    if sign_flip or rng / base > 1.5 and abs(b - a) / max(abs(a), 1e-9) < 0.15:
        return ("Volatile", "neu")
    ch = (b - a) / max(abs(a), 1e-9)
    if abs(ch) <= tol:
        return ("Stable", "neu")
    up = ch > 0
    last = v[-1] - v[-2]
    if (last > 0) != up and abs(last) / max(abs(v[-2]), 1e-9) > tol:
        return ("Mixed (reversed in latest year)", "neu")
    if up == hib:
        return ("Improving", "pos")
    return (("Declining" if hib else "Deteriorating"), "neg")


def table(head, rows, trend_col=True):
    h = "".join(f"<th>{c}</th>" for c in head)
    out = f"<table><thead><tr>{h}</tr></thead><tbody>"
    for r in rows:
        cells = []
        for i, c in enumerate(r):
            if isinstance(c, tuple):
                cells.append(f'<td class="tr {c[1]}">{c[0]}</td>')
            else:
                cells.append(f"<td>{c}</td>" if i else f'<td class="lb">{c}</td>')
        out += "<tr>" + "".join(cells) + "</tr>"
    return out + "</tbody></table>"


def svg_bars(labels, series, colors, title, unit="", w=520, h=210):
    """Grouped bar chart; series = [(name, [vals])]."""
    vals = [v for _, s in series for v in s if v is not None]
    if not vals:
        return ""
    lo, hi = min(0, min(vals)), max(vals)
    span = (hi - lo) or 1
    pad_l, pad_b, pad_t = 8, 28, 26
    ch = h - pad_b - pad_t
    n = len(labels); k = len(series)
    gw = (w - pad_l * 2) / n
    bw = gw * 0.7 / k
    y0 = pad_t + ch * (hi / span)
    g = [f'<text x="{pad_l}" y="14" class="ct">{title}</text>']
    g.append(f'<line x1="{pad_l}" x2="{w-pad_l}" y1="{y0:.1f}" y2="{y0:.1f}" class="ax"/>')
    for i, lab in enumerate(labels):
        gx = pad_l + gw * i + gw * 0.15
        for j, (nm, s) in enumerate(series):
            v = s[i]
            if v is None:
                continue
            bh = abs(v) / span * ch
            y = y0 - bh if v >= 0 else y0
            g.append(f'<rect x="{gx+j*bw:.1f}" y="{y:.1f}" width="{bw-1:.1f}" height="{max(bh,1):.1f}" fill="{colors[j]}" rx="2"/>')
            ty = y - 3 if v >= 0 else y + bh + 10
            g.append(f'<text x="{gx+j*bw+bw/2:.1f}" y="{ty:.1f}" class="vl">{f(v,0 if abs(v)>=100 else 1)}</text>')
        g.append(f'<text x="{pad_l+gw*i+gw/2:.1f}" y="{h-12}" class="xl">{lab}</text>')
    lg = "".join(f'<tspan fill="{colors[j]}">■</tspan> {nm}   ' for j, (nm, _) in enumerate(series))
    g.append(f'<text x="{w-pad_l}" y="14" class="lg" text-anchor="end">{lg}{unit}</text>')
    return f'<svg viewBox="0 0 {w} {h}" class="ch" role="img" aria-label="{title}">' + "".join(g) + "</svg>"


def svg_lines(labels, series, colors, title, w=520, h=210):
    vals = [v for _, s in series for v in s if v is not None]
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    pad_l, pad_r, pad_b, pad_t = 30, 14, 28, 30
    cw, chh = w - pad_l - pad_r, h - pad_b - pad_t
    xs = [pad_l + cw * i / (len(labels) - 1) for i in range(len(labels))]
    g = [f'<text x="8" y="14" class="ct">{title}</text>']
    for t in range(4):
        yv = lo + span * t / 3
        y = pad_t + chh * (1 - (yv - lo) / span)
        g.append(f'<line x1="{pad_l}" x2="{w-pad_r}" y1="{y:.1f}" y2="{y:.1f}" class="gr"/><text x="{pad_l-4}" y="{y+3:.1f}" class="yl">{yv:.0f}%</text>')
    for j, (nm, s) in enumerate(series):
        pts = [(xs[i], pad_t + chh * (1 - (v - lo) / span)) for i, v in enumerate(s) if v is not None]
        g.append('<polyline fill="none" stroke="%s" stroke-width="2.2" points="%s"/>' % (colors[j], " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)))
        for (x, y), v in zip(pts, [v for v in s if v is not None]):
            g.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.8" fill="{colors[j]}"/>')
        if pts:
            g.append(f'<text x="{pts[-1][0]:.1f}" y="{pts[-1][1]-6:.1f}" class="vl" text-anchor="end">{[v for v in s if v is not None][-1]:.0f}%</text>')
    for i, lab in enumerate(labels):
        g.append(f'<text x="{xs[i]:.1f}" y="{h-12}" class="xl">{lab}</text>')
    lg = "".join(f'<tspan fill="{colors[j]}">●</tspan> {nm}   ' for j, (nm, _) in enumerate(series))
    g.append(f'<text x="{w-8}" y="14" class="lg" text-anchor="end">{lg}</text>')
    return f'<svg viewBox="0 0 {w} {h}" class="ch" role="img" aria-label="{title}">' + "".join(g) + "</svg>"


CSS = """
.rpt{font-family:Georgia,"Times New Roman",serif;color:#1d2530;line-height:1.55;max-width:900px;margin:0 auto;background:#fff;padding:0 0 24px;font-size:14.5px}
.rpt *{box-sizing:border-box}
.rpt .hd{background:#12355b;color:#fff;padding:22px 28px 18px;border-bottom:5px solid #c8a24a}
.rpt .brand{font:600 11px/1 system-ui,sans-serif;letter-spacing:.18em;text-transform:uppercase;color:#c8a24a}
.rpt h1{font:700 26px/1.2 Georgia,serif;margin:8px 0 4px}
.rpt .by{font:500 13px system-ui,sans-serif;opacity:.9}
.rpt .chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.rpt .chip{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.25);border-radius:4px;padding:4px 10px;font:12px system-ui,sans-serif}
.rpt .chip b{display:block;font-size:14px}
.rpt .bd{padding:6px 28px}
.rpt h2{font:700 19px Georgia,serif;color:#12355b;border-bottom:2px solid #c8a24a;padding-bottom:4px;margin:26px 0 10px}
.rpt h3{font:700 15.5px Georgia,serif;color:#12355b;margin:18px 0 6px}
.rpt h4{font:700 14px Georgia,serif;margin:12px 0 4px}
.rpt p{margin:6px 0}.rpt ul,.rpt ol{margin:6px 0 6px 20px;padding:0}.rpt li{margin:3px 0}
.rpt table{width:100%;border-collapse:collapse;margin:8px 0 10px;font:13px system-ui,sans-serif;font-variant-numeric:tabular-nums}
.rpt th{background:#eaf0f7;color:#12355b;text-align:right;padding:6px 8px;border:1px solid #cfd8e3;font-weight:700}
.rpt th:first-child,.rpt td.lb{text-align:left}
.rpt td{padding:6px 8px;border:1px solid #dde3ea;text-align:right}
.rpt td.lb{font-weight:600;background:#fafbfc}
.rpt tr:nth-child(even) td{background:#fbfcfd}.rpt tr:nth-child(even) td.lb{background:#f5f7f9}
.rpt .tr{font-weight:700;white-space:nowrap}.rpt .pos{color:#1a7f4b}.rpt .neg{color:#c0392b}.rpt .neu{color:#d98200}
.rpt .reco{border:2px solid #12355b;border-left:10px solid #1a7f4b;border-radius:6px;padding:12px 16px;margin:14px 0;background:#f4f8fc;font-family:system-ui,sans-serif}
.rpt .reco.hold{border-left-color:#d98200}.rpt .reco.sell{border-left-color:#c0392b}
.rpt .reco .r1{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#5b6b7d}
.rpt .reco .r2{font-size:26px;font-weight:800;color:#1a7f4b}.rpt .reco.hold .r2{color:#d98200}.rpt .reco.sell .r2{color:#c0392b}
.rpt .reco .r3{display:flex;gap:28px;flex-wrap:wrap;margin-top:4px;font-size:14px}
.rpt .kt{background:#f7f3e6;border-left:4px solid #c8a24a;padding:8px 12px;margin:8px 0;font-size:14px}
.rpt .ta{background:#f0f4f8;border-left:4px solid #12355b;padding:8px 12px;margin:8px 0}
.rpt .lbl{font:700 12px system-ui,sans-serif;letter-spacing:.06em;text-transform:uppercase;color:#12355b}
.rpt .hl{background:#fff3b8;padding:0 3px;font-weight:700}
.rpt .ch{width:100%;height:auto;margin:6px 0;border:1px solid #e3e8ee;border-radius:4px;background:#fff}
.rpt .ch text{font-family:system-ui,sans-serif}.rpt .ct{font-size:12px;font-weight:700;fill:#12355b}.rpt .vl{font-size:9.5px;fill:#33404f;text-anchor:middle}.rpt .xl{font-size:10px;fill:#5b6b7d;text-anchor:middle}.rpt .yl{font-size:9px;fill:#7b8794;text-anchor:end}.rpt .lg{font-size:10px;fill:#5b6b7d}.rpt .ax{stroke:#8a96a3}.rpt .gr{stroke:#e3e8ee}
.rpt .two{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.rpt .ft{margin:22px 28px 0;padding-top:10px;border-top:1px solid #cfd8e3;font:11px/1.5 system-ui,sans-serif;color:#5b6b7d}
.rpt .pb{page-break-before:always}
@media(max-width:700px){.rpt .two{grid-template-columns:1fr}.rpt .bd{padding:6px 14px}.rpt .hd{padding:18px 14px}.rpt table{font-size:11.5px}}
@media print{.rpt{max-width:none;font-size:12.5px}.rpt .pb{page-break-before:always}.rpt h2,.rpt h3{page-break-after:avoid}.rpt table,.rpt .reco,.rpt .ch{page-break-inside:avoid}.rpt .hd{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
"""


def build(code, name, content):
    d = json.load(open(rf"C:\ipo_cache\screener_full\{code}.json", encoding="utf-8"))
    m = json.load(open(r"C:\ipo_cache\metrics.json", encoding="utf-8")).get(name, {})
    ind = json.load(open(r"C:\ipo_cache\industry.json", encoding="utf-8")).get(name, {})
    pl, bs, cf, rt, sh = d["profit-loss"], d["balance-sheet"], d["cash-flow"], d["ratios"], d["shareholding"]
    yrs = [c.replace("Mar ", "FY")[:2] + c[-2:] if False else "FY" + c[-2:] for c in pl["cols"]]  # FY21..FY26
    sales, op, opm, npf, eps = row(pl, "Sales"), row(pl, "Operating Profit"), row(pl, "OPM"), row(pl, "Net Profit"), row(pl, "EPS")
    pbt, intr, dep = row(pl, "Profit before tax"), row(pl, "Interest"), row(pl, "Depreciation")
    eq, res, bor, ta = row(bs, "Equity Capital"), row(bs, "Reserves"), row(bs, "Borrowings"), row(bs, "Total Assets")
    cfo, cfi, fcf = row(cf, "Cash from Operating"), row(cf, "Cash from Investing"), row(cf, "Free Cash Flow")
    ccc, wcd, roce = row(rt, "Cash Conversion"), row(rt, "Working Capital"), row(rt, "ROCE")
    debd, invd, payd = row(rt, "Debtor"), row(rt, "Inventory"), row(rt, "Days Payable")
    networth = [(a or 0) + (b or 0) for a, b in zip(eq, res)]
    roe = [None] + [npf[i] / ((networth[i] + networth[i - 1]) / 2) * 100 for i in range(1, len(npf))]
    npm = [npf[i] / sales[i] * 100 for i in range(len(sales))]
    de = [bor[i] / networth[i] for i in range(len(bor))]
    at = [None] + [sales[i] / ((ta[i] + ta[i - 1]) / 2) for i in range(1, len(sales))]
    icov = [op[i] / intr[i] if intr[i] else None for i in range(len(op))]
    L = slice(1, 6)  # FY22..FY26
    Y5 = yrs[L]
    top = d["top"]
    mcap = num(top["Market Cap"]); price = num(top["Current Price"]); pe = num(top["Stock P/E"])
    hi_lo = top["High / Low"]
    shares = mcap / price  # crore
    issue_price = m.get("issue_price"); post_pe = m.get("pe_post")
    rev5, rev3 = cagr(sales[0], sales[-1], 5), cagr(sales[2], sales[-1], 3)
    eps5, eps3 = cagr(eps[0], eps[-1], 5), cagr(eps[2], eps[-1], 3)
    pat5 = cagr(npf[0], npf[-1], 5)
    q = d.get("quarters")
    qs = row(q, "Sales") if q else None; qp = row(q, "Net Profit") if q else None
    ind_pe = ind.get("median_pe"); ind_name = ind.get("industry", "")

    # ---- valuation (explicit assumptions) ----
    g = content["growth_fy27"]
    eps27 = eps[-1] * (1 + g)
    pe_t = content["target_pe"]
    v_pe = eps27 * pe_t
    ebitda27 = op[-1] * (1 + content["ebitda_growth_fy27"])
    ev_m = content["target_ev_ebitda"]
    netdebt = bor[-1] - content["debt_repaid_ipo"]
    v_ev = (ebitda27 * ev_m - netdebt) / shares
    target = round(0.6 * v_pe + 0.4 * v_ev, -0)
    upside = (target / price - 1) * 100
    rec = "BUY" if upside > 15 else ("SELL" if upside < -10 else "HOLD")
    if upside > 30: rec_full = "Strong Buy"
    elif upside > 15: rec_full = "Buy"
    elif upside >= -10: rec_full = "Hold"
    elif upside >= -25: rec_full = "Sell"
    else: rec_full = "Strong Sell"
    cls = {"BUY": "", "HOLD": "hold", "SELL": "sell"}[rec]
    sign = "upside" if upside >= 0 else "downside"
    reco_html = f"""<div class="reco {cls}"><div class="r1">Investment Recommendation</div><div class="r2">{rec}</div>
<div class="r3"><span><b>Target Price:</b> <span class="hl">{inr(target)}</span> ({abs(upside):.0f}% {sign} to CMP {inr(price)})</span><span><b>Investment Horizon:</b> {content['horizon']}</span></div></div>"""

    def mrow(label, vals, dp=1, suf="", hib=True, tcol=True):
        t = trend(vals[L] if len(vals) == 6 else vals, hib)
        cells = [label] + [f"{f(v,dp)}{suf}" if v is not None else "n/a" for v in (vals[L] if len(vals) == 6 else vals)]
        return cells[::1] + [t]

    H5 = ["Metric"] + Y5[::-1] + ["Trend"]

    def r5(label, vals, dp=1, suf="", hib=True):
        v = vals[L]
        t = trend(v, hib)
        return [label] + [f"{f(x,dp)}{suf}" if x is not None else "n/a" for x in v[::-1]] + [t]

    # ---- sections ----
    s = []
    s.append(f"""<div class="hd"><div class="brand">Equity Research · Indian Equities</div>
<h1>{name} Ltd - Equity Analysis Report</h1><div class="by">By {AUTHOR}</div>
<div class="chips"><div class="chip">Sector<b>{content['sector']}</b></div><div class="chip">Market Cap<b>{inr(mcap)} Cr</b></div>
<div class="chip">CMP<b>{inr(price)}</b></div><div class="chip">P/E (TTM)<b>{f(pe)}x</b></div><div class="chip">52-wk High / Low<b>{hi_lo}</b></div></div></div><div class="bd">""")

    s.append("<h2>1. Company Overview</h2>")
    s.append(content["overview"])
    s.append("<h3>Investment Recommendation</h3>" + reco_html)

    s.append('<h2 class="pb">2. Quantitative Analysis</h2>')
    s.append(f'<p class="kt"><b>Data basis:</b> Annual financials from Screener.in (consolidated) with <b>FY26 (year ended 31 March 2026) as the latest annual period</b>; market data as of the latest Screener quote. {content["history_note"]}</p>')

    # a) market valuation
    s.append("<h3>a) Market Valuation and Price Metrics</h3>")
    vt = [["Market Capitalization", f"{inr(mcap)} Cr", ("Listed Sep 2026", "neu")],
          ["Current Stock Price", f"{inr(price)} (52-wk {hi_lo})", ("Near lower half of range" if (price - num(hi_lo.split('/')[1])) / (num(hi_lo.split('/')[0]) - num(hi_lo.split('/')[1])) < 0.5 else "Upper half of range", "neu")],
          ["IPO Issue Price", f"{inr(issue_price)}" + (f" (CMP {abs((price/issue_price-1)*100):.0f}% {'above' if price>=issue_price else 'below'})" if issue_price else ""), (("Gain since IPO" if price >= (issue_price or price) else "Below IPO price"), "pos" if price >= (issue_price or price) else "neg")],
          ["Price-to-Earnings (P/E) Ratio", f"{f(pe)}x (TTM) · {f(post_pe)}x at IPO price" if post_pe else f"{f(pe)}x", ("Above industry median" if ind_pe and pe > ind_pe else "Below industry median", "neg" if ind_pe and pe > ind_pe else "pos")]]
    s.append(table(["Metric", "Current Value (FY26 / latest)", "Trend"], vt))
    s.append(content["a_text"].format(ind_pe=f(ind_pe), ind_name=ind_name, pe=f(pe), post_pe=f(post_pe), price=inr(price), mcap=inr(mcap), issue=inr(issue_price)))

    # b) profitability
    s.append("<h3>b) Profitability and Returns</h3>")
    s.append(table(H5, [r5("Return on Equity (ROE)", roe, 1, "%"), r5("Return on Capital Employed (ROCE)", roce, 1, "%"),
                        r5("Net Profit Margin", npm, 1, "%"), r5("Operating Profit Margin", opm, 1, "%")]))
    s.append(svg_lines(yrs, [("ROE", roe), ("ROCE", roce), ("Net margin", npm), ("Operating margin", opm)], ["#12355b", "#1a7f4b", "#d98200", "#8e44ad"], "Returns and margins (%)"))
    s.append(content["b_text"].format(roe=f(roe[-1]), roce=f(roce[-1]), npm=f(npm[-1]), opm=f(opm[-1]), npm22=f(npm[1]), opm22=f(opm[1]), roe22=f(roe[1]), roce22=f(roce[1])))

    # c) growth
    s.append("<h3>c) Growth Metrics</h3>")
    s.append(table(["Metric", "5-Year CAGR (FY21-FY26)", "3-Year CAGR (FY23-FY26)", "Latest YoY (FY26)", "Trend"],
                   [["Revenue Growth Rate", f"{f(rev5)}%", f"{f(rev3)}%", f"{f((sales[-1]/sales[-2]-1)*100)}%", ("Strong, sustained", "pos")],
                    ["Net Profit Growth", f"{f(pat5)}%", f"{f(cagr(npf[2],npf[-1],3))}%", f"{f((npf[-1]/npf[-2]-1)*100)}%", ("Accelerating", "pos")],
                    ["EPS Growth Rate", f"{f(eps5)}%", f"{f(eps3)}%", f"{f((eps[-1]/eps[-2]-1)*100)}%", ("Strong growth", "pos")]]))
    s.append(svg_bars(yrs, [("Revenue (₹ Cr)", sales), ("Net profit (₹ Cr)", npf)], ["#12355b", "#c8a24a"], "Revenue and net profit (₹ Cr)"))
    s.append(content["c_text"].format(rev5=f(rev5), rev3=f(rev3), eps5=f(eps5), eps3=f(eps3), q1s=f(qs[-1], 0) if qs else "n/a", q1sp=f(qs[0], 0) if qs else "n/a", q1p=f(qp[-1], 0) if qp else "n/a", q1pp=f(qp[0], 0) if qp else "n/a", sales26=f(sales[-1], 0), sales21=f(sales[0], 0), peg=f(pe / (g * 100))))

    # d) balance sheet
    s.append("<h3>d) Balance Sheet Strength</h3>")
    s.append(table(H5, [r5("Debt-to-Equity Ratio", de, 2, "", False), r5("Borrowings (₹ Cr)", bor, 0, "", False), r5("Net Worth (₹ Cr)", networth, 0, ""),
                        r5("Interest Coverage (Op. profit / Interest, x)", icov, 1, "x")]))
    s.append(svg_bars(yrs, [("Borrowings (₹ Cr)", bor), ("Net worth (₹ Cr)", networth)], ["#c0392b", "#1a7f4b"], "Borrowings vs net worth (₹ Cr)"))
    s.append(content["d_text"].format(de26=f(de[-1], 2), de22=f(de[1], 2), de25=f(de[-2], 2), bor26=f(bor[-1], 0), bor25=f(bor[-2], 0), nw26=f(networth[-1], 0), icov=f(icov[-1]), icov22=f(icov[1]), repay=content["debt_repaid_ipo"]))

    # e) cash flow
    s.append("<h3>e) Cash Flow Analysis</h3>")
    s.append(table(H5, [r5("Cash Flow from Operations (₹ Cr)", cfo, 0), r5("Cash Flow from Investing (₹ Cr)", cfi, 0, "", False)[:-1] + [("Heavy investment phase", "neu")], r5("Free Cash Flow (₹ Cr)", fcf, 0)]))
    s.append(svg_bars(yrs, [("Operating CF", cfo), ("Free CF", fcf), ("Net profit", npf)], ["#12355b", "#d98200", "#c8a24a"], "Cash flow versus profit (₹ Cr)"))
    s.append(content["e_text"].format(cfo26=f(cfo[-1], 0), cfo25=f(cfo[-2], 0), cfo24=f(cfo[-3], 0), fcf26=f(fcf[-1], 0), cfi26=f(cfi[-1], 0), npf26=f(npf[-1], 0)))

    # f) dividends
    s.append("<h3>f) Dividend Analysis</h3>")
    s.append(table(H5, [r5("Dividend Yield", [0.0] * 6, 2, "%"), r5("Dividend Payout Ratio", row(pl, "Dividend Payout"), 0, "%")]))
    s.append(content["f_text"])

    # g) efficiency
    s.append("<h3>g) Efficiency Ratios</h3>")
    s.append(table(H5, [r5("Asset Turnover Ratio (Sales / avg. assets, x)", at, 2, "x"), r5("Cash Conversion Cycle (days)", ccc, 0, "", False),
                        r5("Working Capital Days", wcd, 0, "", False), r5("Debtor Days", debd, 0, "", False), r5("Inventory Days", invd, 0, "", False)]))
    s.append(content["g_text"].format(at26=f(at[-1], 2), at22=f(at[1], 2), ccc26=f(ccc[-1], 0), ccc22=f(ccc[1], 0), deb26=f(debd[-1], 0), pay26=f(payd[-1], 0)))

    # h) peers
    peers = d.get("peers") or []
    hdr = peers[0] if peers else []
    plist = []
    for r_ in peers[1:]:
        if len(r_) > 10 and not r_[1].startswith("Median") and r_[1] != d["name"].replace(" Ltd", "") and "Karamtara" not in r_[1]:
            plist.append((r_[1], num(r_[3]), num(r_[10]), num(r_[4])))
    medrow = [r_ for r_ in peers if len(r_) > 10 and r_[1].startswith("Median")]
    ind_roce = num(medrow[0][10]) if medrow else None
    plist.sort(key=lambda x: -(x[3] or 0))
    sel = plist[:5]
    s.append("<h3>h) Valuation Metrics Comparison with Industry Peers</h3>")
    prow = [[f"<b>{d['name'].replace(' Ltd','')}</b>", f(pe, 1), f(roce[-1], 1) + "%", f(de[-1], 2)]] + [[p[0], f(p[1], 1), f(p[2], 1) + "%", "-"] for p in sel]
    prow.append(["Industry Median (" + ind_name + ")", f(ind_pe, 1), f(ind_roce, 1) + "%" if ind_roce else "-", "-"])
    s.append(table(["Company", "P/E Ratio", "ROCE", "Debt/Equity"], prow))
    s.append(content["h_text"].format(pe=f(pe), ind_pe=f(ind_pe), ind_name=ind_name, ind_roce=f(ind_roce), roce=f(roce[-1]), post_pe=f(post_pe)))
    s.append('<p class="ta"><span class="lbl">For every metric</span> Significant year-over-year changes, comparison with industry benchmarks, potential red flags and implications for investors are summarised below.</p>')
    s.append(content["flags"])

    # 3 qualitative
    s.append('<h2 class="pb">3. Qualitative Analysis</h2>')
    s.append(content["qual"])
    # 4 shareholding
    pre = m.get("promoter_pre"); post = m.get("promoter_post")
    s.append("<h2>4. Shareholding Pattern Analysis</h2>")
    shr = sh["rows"]
    s.append(table(["Category", "Pre-IPO (DRHP)", "Post-IPO (at allotment)", sh["cols"][-1] + " (latest)", "Trend"],
                   [["Promoters", f"{f(pre,2)}%" if pre else "n/a", f"{f(post,2)}%" if post else "n/a", shr["Promoters"][-1], ("Diluted by IPO, now stable", "neu")],
                    ["Foreign Institutional Investors (FIIs)", "-", "-", shr["FIIs"][-1], ("New entrants", "pos")],
                    ["Domestic Institutional Investors (DIIs)", "-", "-", shr["DIIs"][-1], ("New entrants", "pos")],
                    ["Public", f"{f(100-pre,2)}%" if pre else "n/a", f"{f(100-post,2)}%" if post else "n/a", shr["Public"][-1], ("Institutions entered post-IPO", "neu")]]))
    s.append(content["sh_text"].format(prom=shr["Promoters"][-1], fii=shr["FIIs"][-1], dii=shr["DIIs"][-1], pub=shr["Public"][-1], holders=shr["No. of Shareholders"][-1], pre=f(pre, 2), post=f(post, 2)))
    # 5 thesis
    s.append('<h2 class="pb">5. Investment Thesis</h2>')
    s.append(content["thesis"])
    # 6 valuation
    s.append("<h2>6. Valuation and Recommendation</h2><h3>Fair Value Estimate</h3>")
    s.append(f"""<p>Two methods are blended: a forward <b>P/E</b> approach (60% weight) and an <b>EV/EBITDA</b> approach (40% weight).</p>""")
    s.append(table(["Method", "Key assumptions", "Value per share", "Weight"],
                   [["Forward P/E", f"FY27E EPS {inr(eps27,2)} (FY26 EPS {inr(eps[-1],2)} +{g*100:.0f}%) × {pe_t:.0f}x", inr(v_pe), "60%"],
                    ["EV/EBITDA", f"FY27E EBITDA {inr(ebitda27)} Cr (+{content['ebitda_growth_fy27']*100:.0f}%) × {ev_m:.0f}x, less pro-forma net debt {inr(netdebt)} Cr, {f(shares,2)} Cr shares", inr(v_ev), "40%"],
                    ["<b>Blended fair value</b>", "", f'<span class="hl">{inr(target)}</span>', "100%"]]))
    s.append(content["val_text"].format(pe_t=pe_t, ind_pe=f(ind_pe), post_pe=f(post_pe), ev_m=ev_m, g=int(g * 100)))
    s.append("<h3>Investment Recommendation</h3>" + reco_html)
    s.append(f"<p><b>Recommendation rating: {rec_full}.</b> Rating bands used: Strong Buy above +30%, Buy +15% to +30%, Hold -10% to +15%, Sell -10% to -25%, Strong Sell below -25% versus the current price.</p>")
    s.append("<h3>Rationale for Recommendation</h3>" + content["rationale"])
    s.append("<h2>7. Conclusion</h2>" + content["conclusion"].format(target=inr(target), up=f"{abs(upside):.0f}% {sign}", rec=rec, horizon=content["horizon"]))
    s.append("</div>")
    s.append(f"""<div class="ft"><b>Disclaimer:</b> This report is for information and education only. It is not investment advice, a solicitation or an offer to buy or sell any security. Figures are taken from Screener.in, the company's offer document and Chittorgarh and may contain errors or omissions; forecasts and the target price are the author's estimates based on stated assumptions and may not materialise. Equity investments carry risk of loss. Please consult a SEBI-registered adviser before acting.<br><b>Published by:</b> {AUTHOR} · IPO Screening Desk · Sources: Screener.in, SEBI offer documents, Chittorgarh.</div>""")
    body = "".join(s)
    frag = f"<style>{CSS}</style><div class=\"rpt\">{body}</div>"
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / f"{slug}.frag.html").write_text(frag, encoding="utf-8")
    full = f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>{name} - Equity Analysis Report</title><style>body{{margin:0;background:#e9edf2}}@media print{{body{{background:#fff}}}}</style></head><body>{frag}</body></html>"
    (ROOT / "reports" / f"{slug}.html").write_text(full, encoding="utf-8")
    print(f"{name}: target {target} ({upside:+.1f}%) {rec_full}; v_pe {v_pe:.0f}, v_ev {v_ev:.0f}; shares {shares:.2f} cr; eps27 {eps27:.2f}; len {len(full)}")
    return slug


if __name__ == "__main__":
    code, name = sys.argv[1], sys.argv[2]
    sys.path.insert(0, str(ROOT / "scripts"))
    mod = __import__("report_content_" + re.sub(r"[^a-z0-9]+", "_", name.lower()))
    build(code, name, mod.CONTENT)
