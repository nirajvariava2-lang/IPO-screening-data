# IPO Screening Desk: daily runbook

Goal: every Indian mainboard IPO (open, upcoming, listed in the last 6 months) has all 8 filters filled. The dashboard shows only rows with no "?" (`unknown == 0`); incomplete rows are listed as pending.

## Where each filter comes from
| Filter | Source | Script |
|---|---|---|
| F1 fresh issue, F2 proceeds, F3 post-issue P/E, F6 growth | Chittorgarh IPO page + SEBI DRHP/abridged prospectus (objects, restated revenue/PAT) | manual by Claude, record page ref in `sources` |
| F4 subscription (after close only) | Chittorgarh `/ipo_subscription/<slug>/<id>/`. Listed IPOs show total only, so mark `soft.f4 = "total only"` | `scripts/f4.py` |
| F5 D/E <= 1 and operating cash flow > 0 | Screener (`/company/<NSE symbol>/consolidated/`, latest Mar column) for listed IPOs; SEBI DRHP otherwise (tag `stale.f5 = FYxx`) | `scripts/screener.py`, `scripts/derive.py` |
| F7 promoter >= 50% post-issue, no pledge | Chittorgarh "Promoter and Promoter Group" pre/post table; pledge from DRHP text | `scripts/chitt.py`, `derive.pledge_none` |
| F8 anchors + no auditor qualification | Anchor rows on Chittorgarh; auditor statement from DRHP ("no qualification"). Soft pass, confirm in RHP | `scripts/chitt.py`, `scripts/apply3.py` |

## Pipeline order
1. `python scripts/sebi.py` : find SEBI filings (`C:\ipo_cache\discovery.json`). Search keyword must keep hyphens (Hy-Tech, Indo-MIM).
2. `python scripts/fill.py` then `python scripts/post.py` : download PDFs, extract text, compute latest financial year (`fy_fixed`).
3. `python scripts/chitt.py`, `scripts/screener.py`, `scripts/f4.py`, `scripts/apply3.py`, `scripts/derive.py data.json` : fill U cells only. Never overwrite P/F.
4. Anything still U: resolve by hand and record source text/page in `sources.<fK>`.
5. `python scripts/metrics.py`, then `scripts/merge_metrics.py` and `scripts/merge_ocf.py` : refresh the decision numbers (row['m']) shown in the dashboard detail panel and ranking. Verdict is computed by `derive.verdict` (Rejected = 0-2 passes or row['gov_flag']).
6. `python scripts/flat.py` : writes `ipo_screen_v3.json` for the dashboard.

## Rules
- Values from a document older than FY26 get `stale.<fK> = "FY25"` and are drawn lighter.
- Verdict: Qualified needs 7-8 passes with no stale/soft cells; Provisional 5-6; Review 3-4; Rejected 0-2.
- Open/upcoming IPOs cannot have F4 or anchors before bidding closes, so they stay pending.
- Chittorgarh slug-only URL `/ipo/<slug>/` redirects to the page with the id.

## Publish
1. Commit `data.json` and scripts to `main`, push (Git Credential Manager is signed in on this PC).
2. Upload `ipo_screen_v3.json` as an asset to https://claude.ai/artifact/5oeTTPykEmVEUoj9CCT5rk and `update` the `datasets/screen` document's `source.url`, `description` and `updated`.


## Public website
Public page: https://nirajvariava2-lang.github.io/IPO-screening-data/ (GitHub Pages, branch main, root). After each data refresh also copy `ipo_screen_v3.json` into the repo root and commit it; the page fetches it. Rebuild `index.html` only if the dashboard page code changes: `python scripts/build_site.py <saved dashboard page>`.

