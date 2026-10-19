# IPO Screening Desk: handoff for Claude Code

Owner: Niraj Variava, CA (GST/Income Tax audit, internal audit, outsourced accounting). Style: professional, cite sources, compute with Python, tables/charts, short paragraphs.

## Goal
A database of every Indian mainboard IPO (listed in the last 6 months, open, and upcoming) with all 8 filters filled from primary documents (DRHP/RHP/abridged prospectus), refreshed daily, shown in a dashboard HTML that reads data.json from GitHub raw. No "?" except F4 (subscription) before the issue closes.

## Filters
F1 fresh issue >=90% | F2 proceeds productive | F3 post-issue P/E <=25x (loss-making/above fails) | F4 subscription >=3x with QIB demand (only after issue closes) | F5 D/E <=1 and positive operating cash flow | F6 revenue and PAT CAGR >=15% | F7 post-issue promoter holding >=50% and pledge 0% | F8 anchors present AND no auditor qualification found (soft pass, confirm in RHP).
Verdicts: Qualified 7-8 verified passes; Provisional 5-6; Review 3-4; Rejected 0-2 or any governance red flag.

## Current state (19 Oct 2026 data)
53 IPOs. Unknown counts: F4 30, F5 35, F7 41, F8 49, F2 1, F3 1, F6 3. Provisional: German Green Steel 7/8 (F7 open), SRIT India, Glass Wall Systems, ESDS Software (6/8 each).
Why "?" exist: earlier data came from Chittorgarh/Screener summaries, which lack pledge, auditor opinion and sometimes cash flow. These are in the offer documents and must be read from them.

## Document sources (tested)
- Works: WebFetch on sebi.gov.in/sebi_data/commondocs/... PDFs (DRHP/abridged prospectus); NSE/BSE result filings (nsearchives.nseindia.com); Screener company pages; Chittorgarh; Investorgain.
- Fails: bseindia.com PDFs, curl/shell to sebi.gov.in (proxy 403), screener search API, Screener peers table.
- Abridged prospectus gives promoter pre-issue %, auditors and qualification statement; post-issue % and pledge may need RHP or the BSE/NSE shareholding pattern.

## Build plan
1. Python script (scripts/fill.py) that, per IPO, stores extracted fields and source page in data.json and verified.json.
2. For each of the 53 rows, locate the SEBI prospectus and fill F5, F6, F7, F8 with section references.
3. Schedule: daily task trig_015GetpmL5ZdKcWwaLHz4Jei (07:51 IST) must add new IPOs, fill all filters, push data.json, notify on >=5 passes.
4. Known bug: the 19 Oct scheduled run updated the artifact but did not push data.json. Verify it pushes.

## Repo files
data.json (rows, as_of), verified.json (overrides + rules), README.md. Raw URL: https://raw.githubusercontent.com/nirajvariava2-lang/IPO-screening-data/main/data.json
Dashboard: https://claude.ai/artifact/5oeTTPykEmVEUoj9CCT5rk ; standalone IPO_Screening_Desk.html (fetches the raw URL).
Commits end with: Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
