# Context

This workflow audits all active PLAYER Jira initiatives, notifies Squad and Tribe leads of gaps they need to fix, produces tribe-level Excel reports, and delivers data quality metrics to the PLAYER Data Quality Dashboard and Slack.

**Key scripts** (all in `C:\Users\JonVince\Documents\GitHub\Jira-Data-Quality\`):
- `process_full_audit.py` — merges paginated Jira results, applies tier scoring, maps squads→tribes, runs QC1. Outputs `audit_results.json`.
- `build_reports.py` — reads `audit_results.json`, builds all 6 spreadsheets (5 tribe + 1 master) in one pass, writes run entry to `run_log.json`.

**Claude skills** (from the `player-jira@local` plugin — registered in `~/.claude/plugins/installed_plugins.json`, cached at `~/.claude/plugins/cache/local/player-jira/1.0.0/`):
- `/player-jira-audit` — invoked at Step 1 to fetch all active PLAYER initiatives from Jira
- `/player-jira-fix` — invoked at Step 2 to apply Claude-fixable rules (Backlog promotion, clear release date, auto status update)

The spreadsheet generation (Steps 5–6) is handled entirely by the Python scripts — no skill invocation required.

---

## Pre-requisites

1. **player-jira plugin** — Must be registered in `~/.claude/plugins/installed_plugins.json` as `player-jira@local` pointing to `~/.claude/plugins/cache/local/player-jira/1.0.0/`. If the skills fail to load at Step 1, check this file first and re-add the entry if missing (the plugin files themselves live permanently in the cache folder).

2. **Squad → Tribe mapping** — Sourced from Notion: https://www.notion.so/superbet/Player-Org-29b032f852c5807fab59c839b9710512

| Tribe | Squads |
|---|---|
| Player Engagement | GraySkull, Thundercats, Bonus Integration, Mobius, Gamification, Sb Club Migration, Player Experience - Gamification, Player Experience - Growth, Hunch (F2P) |
| Transact | APM Experience, Card Experience, Payment Experience, Payment Platform, Wallet Core, Wallet Integrations, Cross Transact |
| Fraud Prevention | Fraud Engineering |
| Retail/Multichannel | Retail Sports Experience, Retail Gaming Experience, Retail Operations Experience, Retail Platform Foundation, Retail Added Value Experience, Retail Terminals Platform |
| Manage | Player Onboarding, Player Identity, Player Account, Manage Platform, Player Support |

> **Squad field fallback**: `process_full_audit.py` falls back to the native Jira Team field (`customfield_10001`) when the Squad custom field (`customfield_11250`) is empty. Team names with tribe suffixes (e.g. "Payment Platform - Transact") are normalised by stripping the suffix before lookup. Initiatives where neither field is set appear as `[No squad]` and need manual assignment in Jira.

3. **Squad Lead / Tribe Lead identification** — Read from `C:\Users\JonVince\Documents\GitHub\Jira-Data-Quality\squad_leads.json`. The Engineering Manager for each squad is the Slack message recipient. Tribe leads are under `tribe_leads` for each tribe. Slack IDs are pre-resolved — no Notion or Slack lookups required at runtime. If a squad has `engineering_manager: null`, skip the Slack message for that squad and note it in the final summary. To refresh the mapping, see `_meta.refresh_instructions` in the file.

   > **Mapping refresh prompt:** At the start of Run #5, and every 5 runs thereafter (Run #10, #15, …), remind Jonathan to review `squad_leads.json` against the Notion org page — new squads, EM changes, and TBH roles that have since been filled. Check `run_log.json` for the current run number to determine whether a prompt is due.

   > **Adding a new squad — two-file update required:** When a squad is added to `squad_leads.json`, also update `SQUAD_MAP` in `build_squad_messages.py`. The map key must exactly match the Jira squad field value; the value must match the key used in `squad_leads.json`. A `None` value in SQUAD_MAP means the squad is known but intentionally excluded — change it to the string key to activate routing.

---

## Context management

This workflow is long. Interruptions (connectivity loss, compaction) are disruptive. Follow these rules to keep context lean and the workflow resumable:

**1. Write data to disk immediately, never hold it in context.**
After every Jira response, write the `issues` array to a named file and discard the raw JSON from context. The Python scripts are the analysis engine — Claude's role is orchestration, not data processing. Never quote or re-summarise raw Jira data mid-workflow.

**2. Use sub-agents for heavy verification steps.**
QC1A, QC3, and QC4 each spawn an isolated sub-agent. Pass only: the relevant file path(s), the sample or tribe name, and the rules reference path. Do not pass audit data inline. Sub-agents return a pass/fail verdict and a brief discrepancy list — that is all the main workflow needs to continue.

**3. Checkpoint state after each major phase.**
After each of the following, the workflow can safely restart from that point using only disk files:
- Step 1 complete → `jira_a.json` … `jira_d.json` + `audit_results.json` written
- Step 5 complete → spreadsheets written + `run_log.json` updated
- Step 6 (optional) → Excel spreadsheets available locally; upload to Drive for stakeholder sharing at any time

If the conversation is compacted between phases, read the relevant output files to reconstruct state. Do not re-fetch from Jira unless `audit_results.json` is missing or stale.

**4. Squad message Slack calls are the only step that should hold message content in context.**
Compose all squad messages from `audit_results.json` in a single pass and fire all `slack_send_message` calls as one parallel batch. Do not compose messages one at a time in sequential turns.

---

## Workflow

### Step 1 — Audit all active PLAYER initiatives

> **Skill:** `/player-jira-audit` — invoke this skill to load the audit logic and field rules before fetching.

Fire four status-segmented queries **simultaneously** (not sequentially). Each segment fits in 1–2 pages, avoiding page-token expiry between fetches. Results are merged and deduplicated by `process_full_audit.py`.

| Query | JQL |
|---|---|
| A — To Do | `project = PLAYER AND issuetype = Initiative AND status = "To Do" ORDER BY key ASC` |
| B — Pre-delivery | `project = PLAYER AND issuetype = Initiative AND status in ("In Discovery","In Definition","Awaiting Approval") ORDER BY key ASC` |
| C — Delivery | `project = PLAYER AND issuetype = Initiative AND status in ("Awaiting Delivery","In Planning","In Delivery","Pending Certification","In Production","Rollout / Experimentation","In Cleanup","On Hold") ORDER BY key ASC` |
| D — Done | `project = PLAYER AND issuetype = Initiative AND status = "Done" AND status changed to "Done" after "-90d" ORDER BY key ASC` |

> **Why not a single query?** A single `status NOT IN (Backlog, "Won't Do")` query returns 400–500 issues across 5–6 pages. Each page fetch requires the `nextPageToken` from the previous response — enforcing sequential calls and risking token expiry between steps. The four-query approach keeps each segment to 1–2 pages and makes all four fetches independent.

> **Pagination rule — treat exactly 100 results as a mandatory page-2 check:** The Jira MCP tool caps responses at 100 results per call. A response with exactly 100 issues is almost certainly truncated — `nextPageToken` may be absent even when more results exist. After each query: if `len(issues) == 100`, immediately fire a follow-up call with that query's `nextPageToken` (or `startAt=100` if no token), regardless of whether a token was returned. The Python script also enforces this: it raises `SystemExit` if any input file has exactly 100 records, so a truncated file will never silently produce a low total.

> **Page 2 handling:** Handle page 2 inline immediately — do not batch or defer. For page 2 calls, use the `nextPageToken` from the page 1 response. If the page 2 response also returns exactly 100 results, continue paginating until a page returns fewer than 100.

Fetch fields for each query:
```
summary,status,parent,assignee,customfield_12121,customfield_12122,customfield_12012,
customfield_12178,customfield_12112,customfield_12110,customfield_10709,
customfield_10025,description,customfield_12128,customfield_12109,
customfield_15460,customfield_12111,customfield_12114,customfield_14447,
customfield_11250,duedate,created
```

**After receiving each query response, immediately write the `issues` array to a named JSON file** in the working directory — do not keep the raw JSON in conversation context. Use consistent, predictable names so `process_full_audit.py` can be invoked without editing the script:

| Query | File(s) |
|---|---|
| A — To Do (p1) | `jira_a.json` |
| B — Pre-delivery (p1) | `jira_b.json` |
| C — Delivery (p1) | `jira_c.json` |
| D — Done (p1) | `jira_d.json` |
| Any page 2 | `jira_X_p2.json` (e.g. `jira_c_p2.json`) |

After saving, invoke `process_full_audit.py` with `--audit` pointing to all audit files and `--qc1b` pointing to QC1B files:

```
python process_full_audit.py --audit jira_a.json jira_b.json jira_c.json jira_d.json --qc1b qc1b_p1.json qc1b_p2.json
```

Full paths are not required if the script is run from the working directory. The script will raise `SystemExit` if any file returns exactly 100 records.

### Step 2 — Classify gaps and apply Claude-fixable rules

> **Skill:** `/player-jira-fix` — invoke this skill to load the fix rules and valid field values before applying changes.

**Claude-fixable rules (applied automatically before notifying squads):**

| Rule | Condition | Action |
|---|---|---|
| Backlog → To Do promotion | Initiative is in Backlog AND Roadmap Priority (PDT) is populated | Transition status to To Do via `transitionJiraIssue` |
| Clear Planned Release Date | Roadmap Priority (PDT) is empty AND Planned Release Date is set | Clear `customfield_12114` via `editJiraIssue` |
| Auto-generate Short Status Update | Short Status Update (`customfield_14447`) is empty | Fetch initiative activity/changelog via Jira API, summarise into a short status update, write via `editJiraIssue` |

**Non-blocking:** Claude builds the fix proposal table and saves it locally, then sends Jonathan a Slack message listing the proposed changes. The main workflow continues immediately — no waiting. To apply the fixes, Jonathan replies: `"Apply player-jira fixes"` at any time after the workflow completes.

Example preview:
| Issue Key | Initiative | Rule | Change |
|---|---|---|---|
| PLAYER-123 | Fast Withdrawal | Backlog → To Do | Status: Backlog → To Do |
| PLAYER-456 | Loyalty Revamp | Clear release date | Planned Release Date: 2026-06-30 → (empty) |
| PLAYER-789 | RO Migration | Auto status update | Short Status Update: (empty) → "In active delivery, on track for Q2..." |

**Tier mapping by status:**

| Status | Tier(s) | Date fields required? | Notes |
|---|---|---|---|
| Backlog | 0 | No | Unscheduled — no dates expected. Core identity fields only. |
| To Do | 0 | No | Core identity fields only. |
| In Discovery / In Definition | 0–1 | Start Date only | |
| Awaiting Approval | 0–3 | Start Date + End of Definition Date | |
| Awaiting Delivery / In Planning / In Delivery / Pending Certification / In Production / Rollout / Experimentation / In Cleanup / On Hold | 0–4 | Start Date + End of Definition Date + Planned Release Date | |
| Done | 0–5 | All date fields including Due Date | |

> **Backlog = Tier 0:** Initiatives in Backlog are not penalised for missing date fields. Dates are genuinely not applicable to unscheduled work. This is enforced explicitly in `STATUS_TIERS` in `process_full_audit.py` — `'Backlog': [0]` is a named entry, not a fallback. QC1B also lists Backlog in `EXPECTED_EXCLUDED`, so any Backlog initiative absent from the main audit is treated as an expected exclusion, not a gap.

> **Pending Jira automation — Start Date (PLYRTPM-32):** Start Date (`customfield_10025`) is consistently one of the top gaps in the audit. A Jira automation rule has been proposed (see PLYRTPM-32) that would auto-populate Start Date at the moment an initiative first transitions to "In Discovery" (or any Tier 1+ status), provided the field is currently empty. Rule: Trigger = Issue transitioned to [In Discovery / In Definition / Awaiting Approval / …], Condition = Start Date is empty, Action = set `customfield_10025` to `{{now.jiraDate}}`. This requires project admin access to configure in PLAYER Project Settings → Automation. Once live, the majority of future Start Date gaps would be resolved automatically without squad action. **Status: pending Jira admin configuration.**

**Squad-action required (all remaining gaps):**

| Fields requiring human input |
|---|
| Product Lead, Engineering Lead, Roadmap Priority, Impact, Country, Areas Impacted, Investment Category, Description / PRD, Tribes Impacted, Planned Release Date, Due Date, Dependencies, Start Date, Parent, Health Status, End of Definition Date |

**Description / PRD rule:** Tier 2 requires either `description` OR `customfield_12128` (Product Requirement document) to be populated. If either field has content, this gap is considered resolved — only flag if **both** are empty.

**Retail/Multichannel exclusion rules:** Retail squads only adopted Jira in April 2026. A Retail/Multichannel initiative is **excluded entirely** from the audit (not scored, not included in any spreadsheet, not sent to Tomislav) if **either** of the following is true:
- Its `created` date is before `2026-04-01` — these items predate the process entirely.
- Its status is `Done` — there is no value in flagging data quality gaps on completed work while the team is still new to the process.

Initiatives with no `created` date are also excluded as a safety default. Both rules are enforced in `process_full_audit.py` before tier scoring.

**Field definitions** — canonical reference for fields that have generated recipient questions:

| Field | Jira field ID | Definition |
|---|---|---|
| End of Definition Date | `customfield_15460` | The date Discovery actually ended — i.e. when the initiative completed its discovery/definition phase and was ready to move into delivery. |
| Short Status Update | `customfield_14447` | A 1–2 sentence plain-English summary of the initiative's current state: what's happening, any blockers, whether it's on track. Should be updated at least weekly for active initiatives. |
| Health Status | `customfield_12111` | RAG indicator for the initiative overall — Red / Amber / Green. Reflects the squad's own assessment of whether the initiative is on track. |
| Investment Category | `customfield_10709` | The strategic bucket this initiative falls into — KTLO / User Experience / Engineering Excellence. Used for portfolio-level reporting. |
| Roadmap Priority (PDT) | `customfield_12012` | Priority assigned during the PDT (Product & Design & Tech) roadmap planning process — Critical / Must Have / Should Have / Nice to Have. Determines whether an initiative is committed to a roadmap cycle. |

### Step 2b — Read RO Migration 'not closed out' labels

Query Jira for all PLAYER initiatives carrying the label `ro-not-closed-out`:

```
project = PLAYER AND issuetype = Initiative AND labels = "ro-not-closed-out"
```

Fetch fields: `key, summary, customfield_12114` (Planned Release Date), `customfield_11250` (Squad).

Store as `ro_not_closed_out`. If the query returns zero results, skip this step — no changes to squad messages are required.

> This label is stamped by the RO Migration Risk Crawler each Monday as part of its Epic Context Check. It identifies PLAYER initiatives where the release date has passed and all child epics are Done or Won't Do, but the initiative itself is still open in Jira. These are not compliance gaps — they need closing out by the squad.

---

### Step 3 — Build squad and tribe views

**Tribe attribution — Tribes Impacted first, Squad second:**

1. **Primary source: Tribes Impacted** (`customfield_12109`) — if this field is populated, use its values as the tribe(s) for the initiative. An initiative can appear in multiple tribes' reports if multiple tribes are listed.
2. **Secondary source: Squad** (`customfield_11250`) — if Tribes Impacted is empty, fall back to the Squad field and map it to its parent tribe via the squad→tribe mapping table in the Pre-requisites section.

This ordering means `tribe_source` in `audit_results.json` will be either `"tribes_impacted"` or `"squad"` for each row.

**Squad attribution gaps** — Initiatives where Tribes Impacted is populated but Squad is empty have a squad attribution gap: the tribe is known, but there is no squad-level owner. These are flagged separately in `squad_attribution_gaps` in `audit_results.json` and included in the Step 8 summary to Jonathan.

**Unattributed initiatives** — Initiatives with no Squad value and no Tribes Impacted value cannot be routed to any squad or tribe. Flag these in the Step 8 summary to Jonathan so they can be investigated.

**Squad JQL filter** — for each squad, build a filter scoped to that squad's initiatives:
```
project = PLAYER AND issuetype = Initiative AND cf[11250] = "Squad Name"
AND status NOT IN (Backlog, "Won't Do")
```

**Tribe JQL filter** — for each tribe, the filter must cover both routing sources. Construct it as:
```
project = PLAYER AND issuetype = Initiative
AND (cf[11250] in ("[Squad1]", "[Squad2]", ...) OR cf[12109] in ("[TribeName]"))
AND status NOT IN (Backlog, "Won't Do")
```

> **Note:** `cf[12109]` (Tribes Impacted) JQL support should be verified at runtime — if the filter is rejected by Jira, fall back to `cf[11250]` squad-based filtering only for the JQL link and add a note in the Step 8 summary. The tribe report itself should still include Tribes Impacted initiatives regardless of JQL filter support.

> **Column pre-selection — known limitation:** Jira Cloud's issue navigator (`/issues/?jql=…`) does **not** support pre-specifying columns via URL parameters. There is no `&columnNames=` or equivalent query string argument — column configuration is stored server-side per user and cannot be overridden from a URL. As a result, recipients who open a JQL link will see their own default Jira columns, not the mandatory fields. The workaround is to include a short "suggested columns" instruction in every squad Slack message and tribe Slack message so recipients can add the right columns in one step. See the Step 4 and Step 7 message templates for the exact wording.

### Step 4 — Send Slack messages to Squad Leads

For each squad (with or without gaps):
- Compose a message using the appropriate format below
- Send via `slack_send_message` to the Engineering Manager's `slack_id` from `squad_leads.json` (`tribes.[Tribe].squads.[Squad].engineering_manager.slack_id`)
- If two squads share the same EM (e.g. Card Experience and Payment Experience both map to Emanuele Manco), send a **single combined message** covering both squads rather than two separate messages

> **Retail/Multichannel — squad messages suppressed:** Check `tribes.Retail/Multichannel._squad_messages` in `squad_leads.json`. While this is set to `"suppressed"`, do **not** send individual squad messages for any Retail squad. Retail only receives a tribe-level message via Tomislav Pavic (Step 7). On the first run after `_squad_messages_review_after` (2026-09-01), prompt Jonathan: *"Retail squad messages are currently suppressed — Tomislav Pavic receives the tribe summary only. Would you like to enable squad-level messages for Retail now?"*

> **Performance:** Compose all messages first, then fire all `slack_send_message` calls in a **single parallel batch** — one tool call block containing all messages. Do not send in sequential batches of 5. Slack's rate limit for DMs is well above the ~17–20 messages generated by this workflow.

**RAG thresholds (apply to all messages — squad and tribe):**
| Score | Status |
|---|---|
| ≥ 85% | 🟢 |
| 70–84% | 🟡 |
| < 70% | 🔴 |

**If the squad has gaps** — standard message format:
```
Hi [Name] 👋 Here's a data quality update for your squad's PLAYER initiatives in Jira (Run #[N]).

X initiatives have missing fields. Average compliance score: X% [🟢/🟡/🔴]

• Product Lead: 3 initiatives
• Planned Release Date: 5 initiatives

[If ro_not_closed_out contains initiatives for this squad — insert block here:]
⚠️ *From RO Migration programme audit:*
• PLAYER-172 — release date 31 Mar, all child epics Done — initiative needs closing out
• PLAYER-218 — release date 15 Apr, work complete — initiative not closed
_Action: close these initiatives in Jira._

<[Jira JQL link]|View your initiatives here>

_Please update these fields at your earliest convenience. See the <https://www.notion.so/superbet/HANDBOOK-Setting-up-Jira-for-P-T-Roadmapping-318032f852c58057a66ce19cf7a22d9e|P&T Jira Roadmapping Handbook> for guidance on what each field means._

This is a new process and we're actively improving it — feedback and ideas are very welcome.
```

> **Conditional footer — field hint:** If End of Definition Date (`customfield_15460`) or Short Status Update (`customfield_14447`) appear in the gap list for that squad, append the following line immediately before the closing italics line:
> `_💡 End of Definition Date = the date Discovery actually ended. Short Status Update = 1–2 sentence current state summary._`
>
> Do not append the line if neither field is missing for the squad.

**If the squad has zero gaps and no RO labels** — celebration message format:
```
Hi [Name] 👋 Great news for [Squad Name] — Run #[N].

All [X] of your squad's PLAYER initiatives in Jira are fully compliant — no missing fields! 🎉

Keep it up, and thanks for staying on top of this.
```

**If the squad has zero gaps but has `ro-not-closed-out` initiatives** — do NOT send the full celebration message. Use this format instead:
```
Hi [Name] 👋 Here's a data quality update for [Squad Name] — Run #[N].

All [X] of your squad's PLAYER initiatives are field-compliant — no missing fields! 🎉

⚠️ *From RO Migration programme audit:*
• PLAYER-172 — release date 31 Mar, all child epics Done — initiative needs closing out
_Action: close these initiatives in Jira._

This is a new process and we're actively improving it — feedback and ideas are very welcome.
```

### Step 5 — Build all spreadsheets

Run `python build_reports.py` from the Jira Data Quality folder. It reads `audit_results.json` and produces all 6 xlsx files in one pass, then appends an entry to `run_log.json` and appends the run's compliance metrics to `trend_history.json`, then commits and pushes it to GitHub so the dashboard updates automatically.

**Tribe spreadsheets** (one per tribe) — two tabs each:
- **Detail tab**: one row per initiative sorted by Compliance Score ascending. Columns: Compliance Score, Issue Key (hyperlinked), Initiative Name, Status, Squad, one column per required field (✓/✗).
- **Summary tab**: one row per squad — squad name, total initiatives, avg compliance score, gap counts per field, hyperlinked JQL.

**Master spreadsheet** — three tabs:
- **Overview**: one row per tribe — avg score, total initiatives, total gaps, % complete by field
- **By Squad**: one row per squad across all tribes — sorted by compliance score ascending
- **By Field**: gap frequency across all PLAYER sorted by most common

File naming: `PLAYER_DataQuality_[TribeName]_[YYYY-MM-DD].xlsx` / `PLAYER_DataQuality_Master_[YYYY-MM-DD].xlsx`

### Step 5b — Notify Jonathan that the run is complete

Immediately after `build_reports.py` completes, send a Slack DM to Jonathan confirming the run is done and the dashboard is live.

> **No manual step required:** `build_reports.py` automatically commits and pushes `trend_history.json` to GitHub during its run — the PLAYER Data Quality Dashboard is live within ~30 seconds. Proceeding to tribe messages does not require any manual confirmation.

**Slack DM** (via `slack_send_message` to Jonathan's Slack ID `U08HBGPPRNY`):
```
📊 PLAYER Data Quality — Run #[N] complete.

All spreadsheets are ready in the local run folder:
PLAYER Data Quality — Run [N] — [YYYY-MM-DD]

The dashboard has been updated automatically. Proceeding to send tribe lead messages now.

[Include squad_leads.json refresh reminder if applicable — see Pre-requisite 3]
```

### Step 6 — Proceed to tribe messages (no gate)

> **Dashboard is live after Step 5:** `build_reports.py` commits and pushes `trend_history.json` to GitHub automatically — the dashboard updates within ~30 seconds. No manual action is required before sending tribe messages.

The Excel tribe spreadsheets are saved locally in the run folder (`local_folder` in `run_log.json`).

**Proceed directly to Step 7.**

### Step 7 — Message Tribe Leads

**Run `build_tribe_messages.py` first** — this generates `tribe_messages.json` covering all 5 tribes automatically. Do not build tribe messages manually; the script prevents silent omissions (Fraud Prevention was missed in Run #5 when built ad hoc).

```
python build_tribe_messages.py
```

The script handles:
- All tribes from `squad_leads.json` (Player Engagement, Transact, Fraud Prevention, Retail/Multichannel, Manage)
- Fallback to Jonathan when no tribe lead is configured (Transact currently)
- Retail/Multichannel age-bucketed format for Tomislav
- Staleness footer when data is >48 hours old

After running, read `tribe_messages.json` and **filter to messages where `suppressed == false`** before sending. A tribe is suppressed when its score has not declined in 3 or more consecutive runs — rewarding improvement and stability with silence. Suppressed messages are written to the file for audit purposes but must not be sent.

Send all non-suppressed messages in a single parallel batch via `slack_send_message`.

For each tribe, send a Slack message to **both** the Engineering Manager and the Director of Engineering (where one exists) — look up both from `tribes.[Tribe].tribe_leads` in `squad_leads.json`. Send as separate DMs (not a group message).

> **Fallback — no tribe leads:** If a tribe's `tribe_leads` array is empty (e.g. Transact currently has no active leads), send the tribe message to Jonathan instead (`summary_recipient.slack_id` = `U08HBGPPRNY`). Prefix the message with: `⚠️ No tribe lead is configured for [Tribe] — sending to you as fallback.` Note the fallback in the Step 8 summary.

**If the tribe has gaps** — standard message format:
```
Hi [Name] 👋 Here's the PLAYER Jira data quality report for [Tribe] (Run #[N]).

[Tribe] has X initiatives across Y squads with missing fields. Average compliance score: X% [🟢/🟡/🔴] 📊

Top gaps:
• [Field]: X initiatives
• [Field]: X initiatives

🔗 <[Jira JQL link for all tribe initiatives]|View all [Tribe] initiatives in Jira>

Squad leads have been notified individually.

This is a new process and we're actively improving it — feedback and ideas are very welcome 🙏
```

> **Retail/Multichannel — age-grouped format (Tomislav only):** Because Retail squads are new to Jira, send Tomislav a modified message that groups initiatives requiring attention by how long ago they were created, so he can prioritise older items. Squad-level messages are suppressed for Retail — Tomislav is the sole recipient. Use this format instead:

```
Hi Tomislav 👋 Here's the PLAYER Jira data quality report for Retail/Multichannel (Run #[N]).

_Note: this report only covers initiatives created from April 2026 onwards — older items are excluded as they predate the process. You only need to worry about the initiatives listed below._

X initiatives need attention. Average compliance score: X% [🟢/🟡/🔴] 📊

*Initiatives requiring attention — by age:*

*🗓 Created this week (< 7 days)*
• <https://axilis.atlassian.net/browse/PLAYER-XXX|PLAYER-XXX — Initiative Name> — missing: Field, Field
• ...

*📅 Created 2 weeks ago (7–13 days)*
• <https://axilis.atlassian.net/browse/PLAYER-XXX|PLAYER-XXX — Initiative Name> — missing: Field, Field
• ...

*⏳ Created 3+ weeks ago (14+ days)*
• <https://axilis.atlassian.net/browse/PLAYER-XXX|PLAYER-XXX — Initiative Name> — missing: Field, Field
• ...

🔗 <[Jira JQL link for all Retail initiatives]|View all Retail initiatives in Jira>

This is a new process and we're actively improving it — feedback and ideas are very welcome 🙏
```

> Age bucketing: use the `created` date from each row. Calculate age in days from the audit date. < 7 days = "this week", 7–13 days = "2 weeks ago", ≥ 14 days = "3+ weeks ago". Omit a bucket entirely if it has no initiatives. Compliant initiatives (score = 100) are not listed in the age groups — only those with gaps.

The Jira JQL for a tribe message covers all squads in that tribe:
```
project = PLAYER AND issuetype = Initiative AND cf[11250] in ("[Squad1]", "[Squad2]", ...) AND status NOT IN (Backlog, "Won't Do")
```

**If the tribe has zero gaps** — celebration message format:
```
Hi [Name] 👋 Brilliant news for [Tribe] — Run #[N]. 🎉

All [X] PLAYER Jira initiatives across [Y] squads are fully compliant — no missing fields!

[Tribe] is leading the way on PLAYER data quality. Outstanding work from the whole tribe. 🏆

🔗 <[Jira JQL link for all tribe initiatives]|View all [Tribe] initiatives in Jira>
```

### Step 8 — Send summary Slack message to user (Jonathan)

Jonathan's Slack ID is `U08HBGPPRNY` (stored as `summary_recipient.slack_id` in `squad_leads.json`). Send a summary message:

```
✅ PLAYER Data Quality — Run #[N] — [Date]

X initiatives audited across Y squads and Z tribes.

Overall completeness: XX%

Top 3 gaps across PLAYER:
1. [Field]: X initiatives missing (XX%)
2. [Field]: X initiatives missing (XX%)
3. [Field]: X initiatives missing (XX%)

Squad leads notified: X
Tribe leads notified: X

[If squad attribution gaps exist:]
⚠️ Squad attribution gaps: X initiatives have Tribes Impacted set but no Squad assigned — these have tribe visibility but no squad owner. Keys: PLAYER-XXX, ...

[If unattributed initiatives exist:]
⚠️ Unattributed: X initiatives have neither Squad nor Tribes Impacted set — not routed to any squad or tribe.

[If ro_not_closed_out is non-empty:]
🏷️ RO Migration labels cleared: X initiatives

:bar_chart: <DASHBOARD_URL|PLAYER Data Quality Dashboard>

This is a new process — feedback and ideas very welcome.
```

### Step 9 — Remove RO Migration labels

> Only runs if `ro_not_closed_out` is non-empty (Step 2b returned results).

For each initiative in `ro_not_closed_out`, call `editJiraIssue` to remove the label `ro-not-closed-out` from its labels array (fetch current labels, remove the target, write back). Fire all calls in a single parallel batch.

This ensures labels do not persist into the following week and become stale. The RO crawler re-stamps fresh on the next Monday run.

> **Step 9 is non-blocking** — it runs after the Step 8 summary message and does not gate any earlier step. If a label removal call fails, log the key and continue — do not retry or halt.

---

## Critical files

| File | Purpose |
|---|---|
| `~/.claude/plugins/cache/local/player-jira/1.0.0/skills/player-jira-audit/SKILL.md` | Audit logic, tier rules, field IDs |
| `~/.claude/plugins/cache/local/player-jira/1.0.0/skills/player-jira-fix/SKILL.md` | Fix logic, valid field values, API formats |
| `~/.claude/plugins/cache/local/player-jira/1.0.0/references/README.md` | Source-of-truth rules reference |
| `~/.claude/plugins/installed_plugins.json` | Needs player-jira@local re-added |
| `C:\Users\JonVince\Documents\GitHub\Jira-Data-Quality\squad_leads.json` | Engineering Manager Slack IDs per squad and tribe — input for Steps 4–6. Refresh periodically from Notion page in `_meta.notion_page_url`. |
| `C:\Users\JonVince\Documents\GitHub\Jira-Data-Quality\process_full_audit.py` | Loads all paginated Jira result files, deduplicates, applies tier rules, maps squads→tribes, runs QC1A stratified sampling, runs QC1B coverage check. Outputs `audit_results.json`. |
| `C:\Users\JonVince\Documents\GitHub\Jira-Data-Quality\build_reports.py` | Reads `audit_results.json` and builds all output spreadsheets in a single pass: 5 tribe workbooks (Detail + Summary tabs each) and 1 master workbook (Overview, By Squad, By Field tabs). Single JSON load; all constants defined once. |
| `C:\Users\JonVince\Documents\GitHub\Jira-Data-Quality\audit_results.json` | Intermediate output from `process_full_audit.py`. Contains all 490 rows with per-field scores, tribe assignments, QC1 sample keys, and QC1B results. Input to `build_reports.py` and the Slack messaging step. |
| `C:\Users\JonVince\Documents\GitHub\Jira-Data-Quality\run_log.json` | Append-only log of every workflow run. Each entry stores run number, date, timestamp, total audited, per-tribe counts, and files generated. Written by `build_reports.py` at the end of each run. |
| `C:\Users\JonVince\Documents\GitHub\Jira-Data-Quality\trend_history.json` | Per-run compliance metrics (tribe + squad avg scores, gap counts, top offenders). Written by `build_reports.py`, then committed and pushed to GitHub — the dashboard at https://jjvhappening.github.io/Jira-Data-Quality/ reads it directly. |
| `C:\Users\JonVince\Documents\GitHub\Jira-Data-Quality\index.html` | Static dashboard served by GitHub Pages — fetches trend_history.json client-side from the raw GitHub URL. |
| `C:\Users\JonVince\Documents\GitHub\Jira-Data-Quality\backfill_history.py` | One-time utility: reads existing tribe Excel Detail tabs and reconstructs `trend_history.json` entries. Only needed to recover missed runs. |
| `C:\Users\JonVince\Documents\GitHub\Jira-Data-Quality\references\Jira Roadmap Logic v2.md` | Field completion rules reference. Kept in sync with `~/.claude/plugins/cache/local/player-jira/1.0.0/references/README.md` (plugin file retains its README.md name as the skills reference it directly). If the plugin README changes, copy its content here and increment the version suffix. |

---

## Quality Checkpoints

QC2 requires user confirmation (writes to Jira). All other data checks use a separate verifier sub-agent. No checks on Slack messages.

| # | After | Verified by | What it checks |
|---|---|---|---|
| QC1 | Step 1 — Audit complete | **Verifier sub-agent** | Two parallel checks: **QC1A** — statistically significant sample re-verified against live Jira, score recalculation checked, tier gating confirmed. **QC1B** — coverage check via Areas Impacted query to catch any PLAYER initiatives missed by the main audit. Full detail below. |
| QC2 | Step 2 — Claude-fix preview | **Deferred — does not block workflow** | Claude saves the full fix proposal to a file and sends Jonathan a Slack message with the list. The main workflow continues immediately (audit, notifications, spreadsheets). Jonathan triggers the fixes separately when ready using: `"Apply player-jira fixes"` |
| QC3 | Step 5 — Spreadsheets built | **Verifier sub-agent — mandatory, blocks Step 7** | Picks one tribe spreadsheet, re-fetches Jira data for that tribe, and checks: compliance scores are correct, hyperlinks resolve, sort order is correct, row count matches audit. Workflow does not proceed to Slack until this passes. |
| QC4 | Step 5 — Master spreadsheet | **Verifier sub-agent** | Confirms Overview tab tribe totals match the sum of tribe-level spreadsheet data. Flags any mismatch. |
| QC5 | ~~Step 6 — Drive upload~~ | ~~Manual confirmation~~ | _Removed 2026-05-18 — `build_reports.py` auto-uploads `trend_history.json`; Excel upload to Drive is optional and does not gate Slack messages._ |

---

### QC1 — Detailed specification

QC1 runs two checks in parallel immediately after the audit completes — QC1A (sample verification) and QC1B (coverage check). Both must pass before the workflow continues.

#### QC1A — Sample verification

**Sample size calculation (Cochran formula with finite population correction):**

```
n₀ = (Z² × p × (1 - p)) / e²
n  = n₀ / (1 + (n₀ - 1) / N)
```

Parameters:
- Z = 1.96 (95% confidence)
- p = 0.5 (maximum variability — most conservative)
- e = 0.10 (±10% margin of error, appropriate for QC auditing)
- N = total initiatives returned by the audit

This gives n₀ = 96. The finite correction then scales down for small populations:

| N (audit size) | Sample size n |
|---|---|
| 20 | 17 |
| 47 | 32 |
| 75 | 43 |
| 100 | 49 |
| 150 | 59 |
| 200 | 66 |
| 300 | 75 |
| 500+ | ~88 |

Apply a minimum of 8 and a maximum of N (audit all if N ≤ 20).

**Stratified sampling:** Divide the sample proportionally across the status tiers present in the audit results, ensuring at least 1 initiative is sampled from each tier. Tiers:
- Pre-delivery (Backlog, To Do, In Discovery, In Definition, Awaiting Approval)
- Delivery (Awaiting Delivery, In Planning, In Delivery, Pending Certification, In Production)
- Post-delivery (Rollout / Experimentation, In Cleanup)
- Terminal (Done)

**What the verifier checks for each sampled initiative:**

1. **Field presence** — re-fetch from live Jira. For each field required at the initiative's status tier (per `C:\Users\JonVince\Documents\GitHub\Jira-Data-Quality\references\Jira Roadmap Logic v2.md`), confirm Claude's missing/present assessment is correct. The verifier must read the rules file directly — do not re-derive the tier logic independently.

2. **Score recalculation** — independently compute `fields_populated / fields_required × 100` and confirm it matches the reported compliance score (±1% tolerance for rounding).

3. **Tier gating** — confirm that fields from higher tiers are not being required for lower-status initiatives (e.g. Short Status Update must not be flagged missing on a To Do initiative).

4. **Status change detection** — if an initiative's live status differs from the audited status, flag it as a staleness warning. This is expected if fixes were applied between audit and QC1 — note it but do not count it as a discrepancy.

**Pass criteria:** ≤5% of sampled initiatives have a discrepancy. Report all discrepancies with issue key, field name, expected vs actual assessment.

**Important — data freshness:** QC1A must run against the same workflow execution's audit data, not a cached file from a previous run. If fixes were applied to Jira between the audit fetch and the QC1 check (e.g. Short Status Updates written), the live data will differ from the audit snapshot — these are staleness warnings, not audit errors. Always note the time elapsed between audit fetch and QC1 verification.

#### QC1A — Performance guidance

QC1A is the slower of the two sub-steps. Apply these optimisations:

1. **Single bulk fetch via JQL** — use `searchJiraIssuesUsingJql` with `key in (PLAYER-XXX, ...)` for all sampled keys in one call. Do not use `getJiraIssue` per initiative.

2. **Request only required fields** — pass an explicit fields list to minimise payload size:
   ```
   summary,status,parent,customfield_12121,customfield_12122,customfield_12012,
   customfield_12178,customfield_12112,customfield_12110,customfield_10709,
   customfield_10025,description,customfield_12128,customfield_12109,
   customfield_15460,customfield_12111,customfield_12114,customfield_14447,duedate
   ```

3. **Split large samples across two parallel agents** — if n > 20, divide the stratified sample into two halves and launch two sub-agents simultaneously, each processing half. Merge results before reporting.

4. **Pre-compute and pass the sample** — calculate the sample and stratification before spawning the agent. Pass the exact list of keys and their audit claims in the prompt so the agent does not need to derive them.

#### QC1B — Coverage check

> **Note:** The original design used `"Areas Impacted" in ("Player")` as a cross-project coverage query. This field (`customfield_12110`) does not support JQL filtering in any tested syntax — all variants (`cf[12110] = "Player"`, `cf[12110] in ("Player")`, `"Areas Impacted" = "Player"`) are rejected by Jira. The approach below replaces it with a broad category-based query spanning all related project categories.

Fire **nine separate queries simultaneously** — one per project category — instead of one paginated multi-category query. This eliminates sequential page-token fetching: most categories return under 100 results and fit in a single page.

```
issuetype = Initiative AND category = "Data Foundations"   ORDER BY key ASC
issuetype = Initiative AND category = "Data Products"      ORDER BY key ASC
issuetype = Initiative AND category = "Platform"           ORDER BY key ASC
issuetype = Initiative AND category = "Gaming"             ORDER BY key ASC
issuetype = Initiative AND category = "Player"             ORDER BY key ASC
issuetype = Initiative AND category = "Social"             ORDER BY key ASC
issuetype = Initiative AND category = "Sports"             ORDER BY key ASC
issuetype = Initiative AND category = "Core Experience"    ORDER BY key ASC
issuetype = Initiative AND category = "International Program" ORDER BY key ASC
```

Request **only** `key,summary,status` — no other fields needed.

After receiving the nine responses, merge all results and write the combined deduplicated list to `qc1b_p1.json` (and `qc1b_p2.json` if any category returned exactly 100 results and required a follow-up page). Pass these to `process_full_audit.py` via `--qc1b`.

Merge the results from all nine queries, deduplicate by key, then filter for `PLAYER-` keys as before.

From the results, **filter for all issues whose key begins with `PLAYER-`**. This cross-project sweep catches any PLAYER initiative that exists in the Jira instance but was excluded from the main audit (by status filter, issuetype mismatch, or any other reason). Cross-reference this list against the original audit results (the full set, not just the QC1A sample).

**Classify each PLAYER- issue not in the audit set by reason:**

| Excluded reason | Expected? |
|---|---|
| Status = Backlog | ✓ Expected — filtered by design |
| Status = Won't Do | ✓ Expected — filtered by design |
| Status = Done, transitioned to Done > 90 days ago | ✓ Expected — filtered by design |
| Any other status | ✗ Unexpected — investigate |
| Status = Done but transition date unclear / can't verify | ⚠ Flag for manual check |

**Flag any initiative where exclusion reason is unexpected.** Each flagged issue must be investigated before the workflow continues — it may indicate a status filter gap, issuetype mismatch, or a genuine data quality issue.

Report format:
```
QC1B — Coverage check: X PLAYER- issues found across category sweep  |  Y in audit  |  Z excluded
  Expected exclusions:
    - Backlog: N
    - Won't Do: N
    - Done > 90d: N
  ✓ No unexpected exclusions   (or)
  ✗ Unexpected exclusions:
    - PLAYER-XXX: [summary] — status: [status], reason: [explain]
```

#### QC1 overall pass criteria

Both QC1A and QC1B must pass. If either fails, halt the workflow and report findings to Jonathan before proceeding.

---

## Test Command

To spot-check any step without running the full workflow, use:

> **"Test player workflow: [scope]"**

Supported scopes:

| Command | What it runs |
|---|---|
| `test player workflow: audit squad Transact` | Runs the audit for Transact squad only and prints the gap report |
| `test player workflow: spreadsheet tribe Manage` | Creates the tribe spreadsheet for Manage only (no upload, no Slack) |
| `test player workflow: fixes squad APM Experience` | Shows the Claude-fixable preview for APM Experience only |
| `test player workflow: slack message squad Wallet Core` | Sends the squad Slack message to **Jonathan only** instead of the Squad Lead |
| `test player workflow: master` | Creates the master spreadsheet from cached audit data (no Slack, no upload) |

**Test mode rules:**
- All Slack messages (squad, tribe, summary) are redirected to Jonathan's Slack handle — no messages sent to actual leads
- No files uploaded to Google Drive
- No writes to Jira
- Scoped to the specified squad/tribe only
