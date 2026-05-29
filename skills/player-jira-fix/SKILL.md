---
name: player-jira-fix
description: Fix and update field values on PLAYER Jira initiatives and Player Area bugs based on the P&T Roadmapping rules. Use this skill when the user wants to correct, populate, or bulk-update fields on PLAYER initiatives or bugs across Player Area projects (BCN, PLAYER, FPT, TRX, MANAGE) — such as setting missing Squad, Product Leads, Health Status, Roadmap Priority, or any other field. Trigger on phrases like "fix PLAYER initiatives", "fix bugs", "update Jira fields", "set the missing fields", "correct these initiatives", "bulk update", "apply fixes", "fill in the gaps". Always confirm with the user before writing any changes to Jira.
---

# PLAYER Jira Fix Skill

This skill corrects field values on PLAYER Jira initiatives and bugs, writing updates back via the Jira API. It always shows a preview of planned changes and requires explicit user confirmation before applying anything.

## Scope

This skill handles two issue types:

### Initiatives (PLAYER project)
Full roadmapping field compliance per the P&T Roadmapping rules. See Rules Reference below.

### Bugs (Player Area projects: BCN, PLAYER, FPT, TRX, MANAGE)
Primary fixable fields on bugs:
- **Squad** (`customfield_11250`) — derive from Team field using the confirmed mapping table (see Squad Auto-fill section)
- **Tribes Impacted** (`customfield_12109`) — derive from squad's tribe, only if currently empty
- **Team** (`customfield_10001`) — only backfill if explicitly requested

JQL for open bugs with Squad empty:
```
issuetype = Bug AND project in (BCN, PLAYER, FPT, TRX, MANAGE) AND statusCategory != Done AND Squad is EMPTY
```

**Note:** Gaming (GAM) is a separate area — exclude from Player Area bug fixes. Fraud Investigation team is an ops team, not Player — skip those bugs.

## Rules Reference

Full rules: `C:\Users\JonVince\Documents\GitHub\Jira-Data-Quality\references\Jira Roadmap Logic v2.md`

Read it before starting — it defines which fields are required at each PDLC stage and what values are valid.

**Bug fix reference** (team→squad mapping, Squad option IDs, project field availability, exclusions):
`C:\Users\JonVince\Documents\GitHub\Jira-Data-Quality\references\player_area_bug_squad_fix.md`

Read this when the task involves fixing Squad fields on Player Area bugs.

## Safety First

**Never write to Jira without explicit user confirmation.** Always present a clear preview of every change planned and wait for the user to say "yes", "go ahead", "apply", or equivalent before calling `editJiraIssue`. If the user says anything ambiguous, confirm again.

Present changes as a table:

| Issue Key | Initiative Name | Field | Current Value | Proposed Value |
|---|---|---|---|---|
| PLAYER-123 | Faster Withdrawal Flow | Health Status | (empty) | On Track |
| PLAYER-456 | Loyalty Revamp | Planned Release Date | (empty) | 2026-06-30 |

After the table, say: **"Shall I apply these X changes to Jira?"**

Only proceed when the user confirms.

## Supported Fix Operations

### Auto-fixable (value can be derived from context or rules)
- **Health Status** — can be set based on user instruction (e.g. "set all In Delivery initiatives without a health status to 'At Risk'")
- **Short Status Update** — can be set to a placeholder or user-provided text
- **End of Definition Date** — can be set to a date provided by the user or inferred from context
- **Squad (from Team field)** — when `customfield_11250` (Squad) is empty but `customfield_10001` (Team) is populated, derive a Squad candidate from the Team value (see Squad Auto-fill below)

### User-supplied value (user provides the value, you apply it)
- **Product Lead** (`customfield_12121`) — requires an Atlassian account ID; use `lookupJiraAccountId` to find it by name
- **Engineering Lead** (`customfield_12122`) — same as above
- **Roadmap Priority** (`customfield_12012`) — valid values: `0 - Critical`, `1 - Must have`, `2 - Should have`, `3 - Nice to have`, `4 - None`
- **Impact (PDT)** (`customfield_12178`) — valid values: `Very High (>€1M per month)`, `High (<€1M per month)`, `Medium (<€100k per month)`, `Low (<€10k per month)`, `Very Low (<€1k per month - Enabler)`
- **Country (PDT)** (`customfield_12112`) — multi-select; valid values: `🌐 All`, `🇧🇪 Belgium`, `🇧🇷 Brazil`, `🇧🇬 Bulgaria`, `🇭🇷 Croatia`, `🇬🇷 Greece`, `🇵🇱 Poland`, `🇷🇴 Romania`, `🇷🇸 Serbia`
- **Investment Category** (`customfield_10709`) — valid values: `KTLO`, `User Experience`, `Engineering Excellence`
- **Planned Release Date** (`customfield_12114`) — date in `YYYY-MM-DD` format
- **Due Date** (`duedate`) — date in `YYYY-MM-DD` format
- **Tribes Impacted** (`customfield_12109`) — array of tribe values
- **Squad** (`customfield_11250`) — squad name

### Cannot fix automatically (manual action required)
Flag these but do not attempt to write them:
- **Summary** (naming convention) — renaming risks breaking references; advise manual update
- **Parent** (strategy link) — requires knowledge of which strategy is correct
- **Description** (PRD/One Pager link) — requires the actual document
- **Areas Impacted** (`customfield_12110`) — requires human judgment
- **Dependencies** (issue links) — requires knowledge of related work
- **Start Date** (`customfield_10025`) — usually retrospective; advise user

## Squad Auto-fill from Team Field

When `customfield_11250` (Squad) is empty, check `customfield_10001` (Team) as a fallback.

1. Read the Team value. If null or empty, skip.
2. Strip tribe-name suffix (two forms):
   - `"{Squad} - {TribeName}"` — remove everything from the first ` - ` onwards
   - `"{Squad} ({TribeName})"` — remove the parenthetical suffix (e.g. "Thundercats (Engagement Tribe)" → "Thundercats")
3. Apply the **confirmed team→squad mapping table** (checked against Notion Player Org 2026-05-29) before fuzzy-matching:

   | Team name (after stripping) | Squad field value | Tribe |
   |---|---|---|
   | Engagement Integrations | Engagement Integrations | Player Engagement |
   | Payment Experience | Payment Experience | Transact |
   | Payment Platform | Payment Platform | Transact |
   | Wallet Core | Wallet Core | Transact |
   | Wallet Integrations | Wallet Integrations | Transact |
   | Fraud Prevention | Fraud Engineering | Fraud Prevention |
   | Loyalty | Loyalty | Player Engagement |
   | GraySkull / Grayskull / Bonus Platform | GraySkull (Bonus Platform) | Player Engagement |
   | Thundercats | Thundercats | Player Engagement |
   | Mobius | Mobius Platform | Player Engagement |
   | Player Onboarding | Player Onboarding | Manage |
   | Player Identity | Player Identity | Manage |
   | Player Account / Player Manage / PAM | Player Account | Manage |
   | Manage Platform | Manage Platform | Manage |
   | Player Support | Player Support | Manage |
   | APM Experience | APM Experience | Transact |
   | Card Experience | Card Experience | Transact |

4. If not in the table above, fetch the complete Squad universe using `getJiraIssueTypeMetaWithFields` for the relevant project, Bug issue type (ID: `10004`). Extract `allowedValues` from `customfield_11250`. Fuzzy-match (priority order):
   - **Exact match** (case-insensitive) — confidence: high
   - **Starts-with match** — confidence: medium
   - **Substring match** — confidence: medium
   - **No match** — do not propose a value; note "Team value could not be matched to a known squad"
5. If the candidate matches more than one squad at the same confidence level, surface all options and ask the user to confirm.
6. API format: `[{"value": "Squad Name"}]`

**Note on Gamification:** The Squad field option "Gamification" does not currently exist in the Jira Squad field allowedValues. Bugs with Team = "Gamification (Player Engagement Tribe)" or "Player Experience - Gamification" cannot be auto-fixed until a Jira admin adds this Squad option.

## Fix Workflow

### Step 1 — Determine scope

If not provided, ask:
- Which initiatives to fix (issue keys, JQL, squad, or all with gaps)
- Which fields to fix (specific fields, or "run the audit and fix what's missing")
- Target values for user-supplied fields

If the user says "fix what the audit found", run `player-initiative-audit` (single) or `player-jira-audit` (bulk) first, then proceed with the fixable items.

### Step 2 — Fetch current field values

Use `searchJiraIssuesUsingJql` to get current values for all fields you intend to update. Always re-fetch immediately before proposing changes — never rely on stale audit data.

Always include `customfield_10001` (Team) — needed for Squad auto-fill even when Squad is not the explicit target.

### Step 2a — Child Epic Status Check

For every initiative where **Health Status (`customfield_12111`) OR Short Status Update (`customfield_14447`) is already populated**, check its child epics:

1. `searchJiraIssuesUsingJql`: `parent = {INITIATIVE_KEY} AND issuetype = Epic`
2. If any epic status is in the delivery set below AND the initiative's status is pre-delivery, flag it for transition to "In Delivery":

**Delivery statuses:** `In Planning`, `In Delivery`, `Pending Certification`, `In Production`, `Rollout / Experimentation`, `In Cleanup`, `On Hold`

3. Do not propose a transition if the initiative is already at `In Delivery` or later, `Done`, or `Won't Do`.
4. Use `getTransitionsForJiraIssue` to find the transition ID, then include the transition in the change plan.

### Step 3 — Build the change plan

For each initiative and field:
- If already populated, skip (do not overwrite unless user explicitly asks)
- If empty and fixable, add to the change plan
- For Squad: run the auto-fill algorithm; add high/medium-confidence unambiguous matches; surface ambiguous matches for confirmation

### Step 4 — Preview and confirm

Show the full change table. If >20 items, offer to show a sample first. Wait for confirmation before proceeding.

### Step 5 — Apply changes

Call `editJiraIssue` for field updates, `transitionJiraIssue` for status transitions. Process in batches of 10 with progress updates:
```
Applying changes... (10/47 done)
```

If any update fails, capture the error and continue. Report all failures at the end.

#### Comments for flagged items

When applying a fix where a flag or concern exists, **also add a Jira comment** using `addCommentToJiraIssue`. Apply comments in parallel with field edits.

Add a comment when any of these are true:
- Planned Release Date has passed but initiative is still In Delivery
- Data inconsistency detected
- Auto-generated SSU was based on minimal data
- Any other data quality concern

**Comment quality rules:**
1. Always state actual values — real dates, field names, counts. Never generic.
2. For overdue dates: always state the number of days overdue.
3. Give two clear actions — what to do if complete, what to do if slipped.
4. For auto-generated SSU: state confidence level and source.
5. No boilerplate — every sentence must be specific to this initiative.

**Comment templates:**

Overdue Planned Release Date:
```
🤖 Data quality note: Planned Release Date was {DD MMM YYYY} — {N} days ago — and this initiative remains {status}. If delivery is complete, please transition to Done. If it has slipped, update the Planned Release Date to reflect the current forecast.
```

Data inconsistency:
```
🤖 Data quality note: {Field A} is set to "{value}" but {Field B} is empty — these fields are typically populated together. Please either populate {Field B} or confirm whether {Field A} is still accurate.
```

Auto-generated SSU — description available:
```
🤖 Data quality note: Short Status Update was auto-generated from the initiative description. Please review and update if the wording doesn't reflect the current state.
```

Auto-generated SSU — status only (low confidence):
```
🤖 Data quality note: Short Status Update was auto-generated from the initiative status only — no description was found to draw from. The current text is a placeholder: "{generated_text}". Please replace with a 1–2 sentence summary of the actual current state.
```

### Step 6 — Summarise

```
✓ X fields updated successfully
✗ Y updates failed (list issue keys and errors)
◌ Z fields skipped (already populated)
```

Offer to re-run `player-initiative-audit` to confirm the updated state.

## Field Value Reference

### API format by field type

| Field type | API format |
|---|---|
| Single-select | `{"value": "On Track"}` |
| Multi-select | `[{"value": "Poland"}, {"value": "Romania"}]` |
| User picker | `{"accountId": "712020:abc123..."}` |
| Date | `"2026-06-30"` |
| Number | `4.5` |

**Single-select:** `customfield_12012`, `customfield_12111`, `customfield_12178`, `customfield_10709`, `customfield_12135`
**Multi-select:** `customfield_11250`, `customfield_12109`, `customfield_12110`, `customfield_12112`
**User picker:** `customfield_12121`, `customfield_12122`
**Date:** `customfield_10025`, `customfield_12114`, `customfield_15460`, `customfield_15595`, `customfield_12115`, `customfield_12180`, `duedate`

### Health Status (`customfield_12111`)
- `🟢 On Track`
- `🟡 At Risk`
- `🔴 Off Track`

### Roadmap Priority (`customfield_12012`)
- `0 - Critical`, `1 - Must have`, `2 - Should have`, `3 - Nice to have`, `4 - None`

### Impact (PDT) (`customfield_12178`)
- `Very High (>€1M per month)`, `High (<€1M per month)`, `Medium (<€100k per month)`, `Low (<€10k per month)`, `Very Low (<€1k per month - Enabler)`

### Investment Category (`customfield_10709`)
- `KTLO`, `User Experience`, `Engineering Excellence`

### Country (PDT) (`customfield_12112`)
- `🌐 All`, `🇧🇪 Belgium`, `🇧🇷 Brazil`, `🇧🇬 Bulgaria`, `🇭🇷 Croatia`, `🇬🇷 Greece`, `🇵🇱 Poland`, `🇷🇴 Romania`, `🇷🇸 Serbia`

### Effort T-shirt Size (`customfield_12135`)
- `XS (0-4 weeks)`, `S (5-9 weeks)`, `M (10-19 weeks)`, `L (20-39 weeks)`, `XL (40-79 weeks)`, `XXL (>79 weeks)`

### People Fields
Use `lookupJiraAccountId` to convert a name to an Atlassian account ID. Confirm with the user before applying — especially for common names with multiple results.

## Notes

- Never guess field values — if unknown or ambiguous, ask the user.
- Log each successful write to report accurately even across long sessions.
- If asked to fix a field listed as "cannot fix automatically", explain why and provide a direct Jira link.
