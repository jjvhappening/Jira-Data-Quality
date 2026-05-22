# PLAYER Jira Data Quality Workflow — Change Log

All changes to workflow scripts, skill definitions, and configuration files. Most recent first.

---

## 2026-05-18

### `build_tribe_messages.py` — new script; tribe messages now automated
**Why:** In Run #5, the Fraud Prevention tribe lead (Litha Hari) was silently omitted from the tribe message batch because tribe messages were built manually. No error was raised — the message simply wasn't sent. `build_squad_messages.py` already automating squad messages made this gap obvious.

**Changes:**
- New script: `build_tribe_messages.py` — mirrors `build_squad_messages.py` structure
- Covers all 5 tribes from `squad_leads.json` systematically; no tribe can be silently skipped
- Includes per-squad breakdown with JQL links (for squads with gaps), top missing fields, and staleness footer
- Retail/Multichannel: age-bucketed format for Tomislav (initiatives grouped by creation age: this week / 2 weeks ago / 3+ weeks ago; only post-April-2026 initiatives in scope)
- Transact (no tribe lead configured): falls back to summary_recipient (Jonathan) with ⚠️ prefix
- Saves output to `tribe_messages.json`
- `player-jira-data-quality-workflow.md` Step 7: updated to reference `build_tribe_messages.py` as the first action; manual message construction deprecated

---

### Tier rules — Due Date moved to Tier 4; Actual End Date added as Tier 5
**Why:** Due Date is a planning estimate (set alongside Planned Release Date when delivery begins, always after it). Actual End Date (`customfield_12180`) is the factual record of when the Definition of Done was met — it belongs at Tier 5, not Due Date. The handbook confirms: Due Date = planned end date, Actual End Date = actual date DoD was met.

**Changes (across `process_full_audit.py`, `build_reports.py`, `player-jira-audit` SKILL.md):**
- `duedate` (Due Date): moved from Tier 5 → Tier 4 (alongside Planned Release Date, Health Status, Short Status Update)
- `customfield_12180` (Actual End Date): added as the sole Tier 5 required field (replaces Due Date at Done)
- SKILL.md note updated: Actual End Date is now required at Done (was "optional — do not flag")
- `customfield_12115` (Released Date) remains optional — unchanged

---

### `player-jira-data-quality-workflow.md` — Drive upload gate removed
**Why:** `build_reports.py` already auto-uploads `trend_history.json` to Google Drive at the end of Step 5 (confirmed during Run #5 when Jonathan pointed out the manual upload step was obsolete). The PLAYER Data Quality Dashboard reads from `trend_history.json`, so it is live immediately after Step 5 — no manual upload needed to unblock tribe messages.

**Changes:**
- Step 5b rewritten: no longer asks Jonathan to upload to Drive; now sends a simple "run complete" completion DM
- Step 6 rewritten: blocking Drive upload gate removed; replaced with "Proceed directly to Step 7"
- Removed `📂 <[Google Drive direct link...]>` lines from all three tribe message templates (standard, Retail, and "no gaps")
- Step 8 summary template: removed `Master report: [Google Drive link]`; replaced with dashboard link
- Intro: updated to remove "delivers a master summary spreadsheet to Google Drive"
- Checkpoint note: updated to "Step 6 (optional)"
- QC3/QC4/QC5 table: updated QC3 to say "blocks Step 7" (not Step 6); QC5 marked as removed
- Excel spreadsheets remain local only; Drive upload for stakeholder sharing is optional and unblocks nothing

---

## 2026-05-12

### `player-jira-audit` SKILL.md — Tribe lead messages now include per-squad JQL links
**Why:** Tribe leads were receiving a dashboard link but no way to quickly jump into a specific squad's initiative list. A single tribe-wide JQL link would be too broad (141 initiatives for Manage). Per-squad links give tribe leads one-click access to each team's gaps.

**Changes:**
- Added inline JQL link to each squad row in the tribe lead message breakdown: `• {Squad}: X/Y with gaps | Z% — View initiatives`
- JQL is scoped per squad: `cf[11250] = "{squad}" AND status NOT IN (Backlog, "Won't Do")`
- Links only shown for squads with gaps — omitted for squads at 100%

---

## 2026-05-11

### `player-jira-fix` SKILL.md — Improved comment quality rules and templates
**Why:** Comments were too generic (e.g. "Planned Release Date has passed") — not specific or actionable enough to prompt a real response.

**Changes:**
- Replaced the single free-form comment format with explicit quality rules:
  1. Always state actual field values (real dates, counts, status names)
  2. For overdue dates: always compute and state the number of days overdue
  3. Give two clear actions (what to do if complete vs if slipped)
  4. For auto-generated SSU: state confidence level and source
  5. No boilerplate padding — every sentence must be specific to that initiative
- Added four typed comment templates:
  - Overdue Planned Release Date
  - Data inconsistency (e.g. release date set but priority empty)
  - Auto-generated SSU — description available (higher confidence)
  - Auto-generated SSU — status only, no usable description (low confidence / placeholder)

---

### `player-jira-audit` SKILL.md — Slack notification format defined
**Why:** Tribe lead messages previously included Google Drive spreadsheet links. An HTML dashboard is now available that gives a better experience than spreadsheets.

**Changes:**
- Added `## Slack Notification Format` section to the audit skill
- Defined tribe lead DM template: dashboard link replaces all Google Drive file links
- Defined squad EM DM template: JQL link + P&T Handbook link + dashboard link
- Removed Google Drive report links from both message types
- Explicit rule: do not include any URLs other than the three above
- Dashboard URL: `https://script.google.com/a/macros/super.xyz/s/AKfycbz267VI_QpjOEoAR94h89sA1KJW3j3xmgk7IMK6nepNmoc8oQG7DS4ZxiBuZAr2DIaPgw/exec`
- "All clear" message format documented for both tribes and squads with 0 in-scope initiatives

---

## 2026-05-04 (Run #2)

### `generate_ssu.py` — Fixed SSU text generation artifacts
**Why:** Several generated SSU values contained bracket artifacts (`[.`), heading stubs (`PRD: Tech Refinement:.`), and other structural noise from Jira description fields.

**Changes:**
- `get_text()`: Added regex to strip closed-bracket artifacts: `re.sub(r'\[[^\]]{0,120}\]', '', text)`
- `first_useful_sentence()`: Added filters to skip sentences that:
  - Start with `What`, `Why`, `How`, `Note`, `TODO`, `-`, `*`, `•`, `[`
  - Contain `please check` (case-insensitive)
  - End with `:` (heading stubs)
- `first_useful_sentence()`: Changed fallback from `return text[:max_len]` to `return ''` — the fallback was bypassing all filters and producing raw truncated text
- `STATUS_PHRASE`: Added `'On hold'` (lowercase) mapping to handle case variation in Jira status values

---

## 2026-04-28

### `squad_leads.json` — Retail/Multichannel tribe lead updated
**Why:** Kristijan Franković was no longer the correct contact for Retail comms.

**Changes:**
- Replaced Kristijan Franković (UTWGM5L22) with Tomislav Pavic (U052U4CEZQQ) as Retail/Multichannel tribe lead
- Tomislav's role: Technical Program Manager

---

## 2026-04-26

### `squad_leads.json` — PM roles removed from tribe lead lists
**Why:** Tribe-level DMs should go to Engineering Managers only, not Product Managers.

**Changes:**
- Removed Antonio Goard (Head of Product) from Player Engagement tribe leads
- Removed Filip Gvardijan (Head of Product) from Fraud Prevention tribe leads
- Added `_tribe_leads_note` to both tribes documenting the removal reason

---

## 2026-04-24

### `squad_leads.json` — Initial refresh from Notion
**Why:** First structured pass to populate EM Slack IDs from the Notion Player Org page.

**Changes:**
- Populated engineering_manager entries for all squads across Player Engagement, Transact, Fraud Prevention, Retail/Multichannel, and Manage
- Added `_squad_messages: suppressed` for Retail/Multichannel — squads only recently started using Jira; only tribe lead notified until 2026-09-01 review
- Excluded D. Cem Gunduz (Director of Engineering) from Transact tribe leads — to be reviewed
- Set `Manage Platform` engineering_manager to null (TBH in Notion)
- Added `summary_recipient` entry for Jon Vince (U08HBGPPRNY) — receives master run summary and Transact fallback messages

---

## Format

Each entry should include:
- **Date** of change
- **File(s) changed**
- **Why** the change was made (the trigger or problem)
- **What** specifically changed
