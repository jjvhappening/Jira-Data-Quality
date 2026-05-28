# PLAYER Jira Data Quality

Automated audit, reporting, and stakeholder notification system for PLAYER initiative data quality in Jira.

## What this does

Each run audits all active PLAYER Jira initiatives against a tiered field-completion standard, auto-fixes what it can (Backlog promotion, stale release dates, missing status updates), then sends compliance reports to Squad and Tribe leads via Slack. Results feed a live dashboard on GitHub Pages.

Compliance is scored per initiative based on which fields are required at each status tier — To Do through Done each carry progressively more required fields.

## Dashboard

**[PLAYER Data Quality Dashboard](https://jjvhappening.github.io/Jira-Data-Quality/)** — served from `index.html` via GitHub Pages. Reads `trend_history.json` from this repo at runtime. Updates automatically within ~30 seconds of each run completing.

## Key scripts

| Script | Purpose |
|---|---|
| `process_full_audit.py` | Merges paginated Jira results, applies tier scoring, maps squads→tribes, runs QC1A sampling and QC1B coverage check. Outputs `audit_results.json`. |
| `build_reports.py` | Reads `audit_results.json`, appends run metrics to `run_log.json` and `trend_history.json`, and pushes to GitHub (which updates the dashboard). |
| `build_tribe_messages.py` | Generates `tribe_messages.json` for all 5 tribes from `audit_results.json`. |
| `build_squad_messages.py` | Generates squad-level Slack message content. |
| `generate_ssu.py` | Generates Short Status Update text from Jira descriptions for auto-fill. |
| `backfill_history.py` | One-time utility: reconstructs `trend_history.json` from historical audit data. |

## Skills

See `skills/` for Claude Code skills used in this workflow.

| Skill | Purpose |
|---|---|
| `gas-manage` | Manage the PLAYER DQ Google Apps Script project via `clasp` — push code, deploy, run functions, set up from scratch. |

## Run workflow

The full workflow (audit → QC → fixes → Slack → tribe messages) is documented in [player-jira-data-quality-workflow.md](player-jira-data-quality-workflow.md).

The audit + notification skills (`player-jira-audit`, `player-jira-fix`) are registered separately as the `player-jira@local` plugin, not stored in this repo.

## Key data files

| File | Description |
|---|---|
| `squad_leads.json` | Slack IDs for all Squad EMs and Tribe leads. Refresh periodically against [Notion Player Org](https://www.notion.so/superbet/Player-Org-29b032f852c5807fab59c839b9710512). |
| `audit_results.json` | Output of `process_full_audit.py` — all initiatives with per-field scores. |
| `trend_history.json` | Per-run compliance metrics — source data for the dashboard. |
| `run_log.json` | Append-only log of every workflow run. |

## References

| File | Description |
|---|---|
| `references/Jira Roadmap Logic v2.md` | Field completion rules — which fields are required at each status tier. |
| `references/qc_known_bugs.md` | Known bugs and workarounds in the audit pipeline. |
| `references/audit_pagination_reference.md` | Notes on Jira pagination handling. |
| `DASHBOARD_SETUP.md` | One-time setup guide for the Google Apps Script dashboard. |
| `WORKFLOW_CHANGELOG.md` | History of changes to workflow scripts and skill definitions. |

## Google Apps Script dashboard

The Apps Script project (`gas/`) powers a secondary web app dashboard served from Google Apps Script. Setup instructions are in [DASHBOARD_SETUP.md](DASHBOARD_SETUP.md). Managed via the `gas-manage` skill.
