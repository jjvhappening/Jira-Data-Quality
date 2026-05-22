---
name: JDQ GitHub & Pages Reference
description: GitHub repo URL, Pages dashboard URL, raw data URL, and run workflow for the Jira Data Quality project
type: reference
project: Jira Data Quality
---

# Jira Data Quality — GitHub Reference

## URLs

| Resource | URL |
|---|---|
| GitHub repo | https://github.com/jjvhappening/Jira-Data-Quality |
| Dashboard (GitHub Pages) | https://jjvhappening.github.io/Jira-Data-Quality/ |
| trend_history.json (raw) | https://raw.githubusercontent.com/jjvhappening/Jira-Data-Quality/main/trend_history.json |

## Key files

| File | Purpose |
|---|---|
| `index.html` | Static dashboard served by GitHub Pages — fetches trend_history.json client-side |
| `trend_history.json` | Time-series audit data — updated by build_reports.py, committed and pushed each run |
| `audit_results.json` | Latest Jira audit snapshot — written by process_full_audit.py |
| `build_reports.py` | Main pipeline: reads audit_results.json, updates trend_history.json, git pushes |
| `process_full_audit.py` | Fetches Jira data and writes audit_results.json |
| `build_tribe_messages.py` | Generates tribe lead Slack messages (links to GitHub Pages dashboard) |
| `build_squad_messages.py` | Generates squad EM Slack messages |
| `mk_index.py` | One-time build script used to transform gas/gas_dashboard.html into index.html |

## Run workflow (in order)

1. `python process_full_audit.py` — fetches Jira, writes audit_results.json
2. `python build_reports.py` — builds trend history, commits + pushes trend_history.json (dashboard live ~30s later)
3. `python build_tribe_messages.py` — writes tribe_messages.json
4. `python build_squad_messages.py` — writes squad_messages.json

## Former Google Drive integration (superseded 2026-05-22)

Previously the dashboard was a Google Apps Script web app at:
`https://script.google.com/a/macros/super.xyz/s/AKfycbz267VI_QpjOEoAR94h89sA1KJW3j3xmgk7IMK6nepNmoc8oQG7DS4ZxiBuZAr2DIaPgw/exec`

`drive_sync.py` uploaded trend_history.json to Drive file ID `1hlDO1oo2YOT6BenZa9vqbWxBT0bRW2PA`.
Both are now superseded. `drive_sync.py` remains in the repo but is no longer called.

Last updated: 2026-05-22
