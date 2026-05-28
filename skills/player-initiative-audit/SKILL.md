---
name: player-initiative-audit
description: Audit a single PLAYER Jira initiative by issue key against the P&T Roadmapping field completion rules. Use this skill when given a specific issue key like PLAYER-1404, or when the user wants a detailed compliance check on one initiative. Trigger on phrases like "audit PLAYER-1404", "check PLAYER-XXX", "what's missing on PLAYER-XXX", "is PLAYER-XXX complete", or any request that names a specific PLAYER issue key.
---

# PLAYER Single Initiative Audit

Audits one PLAYER initiative against the P&T Roadmapping field completion rules and reports exactly what is missing, what is optional, and what Claude can fix automatically.

## Rules Reference

Full rules: `C:\Users\JonVince\Documents\GitHub\Jira-Data-Quality\references\Jira Roadmap Logic v2.md`

Read it at the start of every audit — it is the source of truth.

## Field Checking Matrix

Apply tiers cumulatively: all rules for the initiative's tier and every tier below it apply.

### Tier 0 — Any status except Backlog and Won't Do

| Field | Jira ID |
|---|---|
| Summary (naming convention) | `summary` |
| Parent (linked to strategy) | `parent` |
| Product Lead | `customfield_12121` |
| Engineering Lead | `customfield_12122` |
| Roadmap Priority (PDT) | `customfield_12012` |
| Impact (PDT) | `customfield_12178` |
| Country (PDT) | `customfield_12112` |
| Areas Impacted | `customfield_12110` |
| Investment Category | `customfield_10709` |

### Tier 1 — In Discovery or later
- Start Date (`customfield_10025`) — encouraged but not a hard requirement

### Tier 2 — Awaiting Approval or later
- Description / PRD: either `description` OR `customfield_12128` must be populated. Flag only if **both** are empty.

### Tier 3 — In Definition (end of) / Awaiting Approval or later
- Tribes Impacted (`customfield_12109`)
- End of Definition Date (`customfield_15460`)
- Squad (`customfield_11250`) — optional, note but do not flag as a hard gap

### Tier 4 — Awaiting Delivery / In Planning or later
- Health Status (`customfield_12111`)
- Planned Release Date (`customfield_12114`)
- Due Date (`duedate`)
- Short Status Update (`customfield_14447`)
- Dependencies (issue links) — flag as a recommendation if none exist

### Tier 5 — Done
- Actual End Date (`customfield_12180`)

## Status → Tier Mapping

| Status | Tiers to apply |
|---|---|
| Backlog | Skip — no audit |
| To Do | 0 |
| In Discovery | 0, 1 |
| In Definition | 0, 1 |
| Awaiting Approval | 0, 1, 2, 3 |
| Awaiting Delivery | 0, 1, 2, 3, 4 |
| In Planning | 0, 1, 2, 3, 4 |
| In Delivery | 0, 1, 2, 3, 4 |
| Pending Certification | 0, 1, 2, 3, 4 |
| In Production | 0, 1, 2, 3, 4 |
| Rollout / Experimentation | 0, 1, 2, 3, 4 |
| In Cleanup | 0, 1, 2, 3, 4 |
| Done | 0, 1, 2, 3, 4, 5 |
| Won't Do | Skip — no audit |
| On Hold | Tier 0 minimum; apply pre-hold tiers if known |

## Workflow

### Step 1 — Extract the issue key

Parse the issue key from the user's message (e.g. `PLAYER-1404`). If no key is present, ask for one.

### Step 2 — Fetch the initiative

Use `searchJiraIssuesUsingJql` with `key = PLAYER-1404`. Request all fields in one call:

```
summary, status, parent, customfield_12121, customfield_12122, customfield_12012,
customfield_12178, customfield_12112, customfield_12110, customfield_10709,
customfield_10025, description, customfield_12128, customfield_12109, customfield_15460,
customfield_11250, customfield_10001, customfield_12111, customfield_12114, customfield_14447,
customfield_15595, duedate, customfield_12115, customfield_12180, issuelinks
```

If the initiative is not found, report the error and stop.

### Step 3 — Evaluate fields

1. Get the current status
2. Look up which tiers apply
3. For each required field in those tiers, check if it is populated (non-null, non-empty, not an empty array)
4. Tier 2: satisfied if either `description` or `customfield_12128` has content
5. `issuelinks`: flag as a recommendation (not a hard gap) if empty for Tier 4+
6. `customfield_11250` (Squad): note as optional

### Step 4 — Check Claude-fixable flags

Flag these separately from hard gaps:

| Condition | Flag |
|---|---|
| Status = Backlog AND Roadmap Priority (`customfield_12012`) is populated | 🔧 Eligible for Backlog → To Do promotion |
| Roadmap Priority is empty AND Planned Release Date (`customfield_12114`) is set | 🔧 Data inconsistency — can clear release date |
| Short Status Update (`customfield_14447`) is empty AND status is Tier 4+ | 🔧 Auto-generatable from activity log |
| Child epics have delivery-stage statuses but initiative is pre-delivery | 🔧 Eligible for status advance to In Delivery |

### Step 5 — Report

**Header line:** `PLAYER-XXXX — [Initiative Name]`
**Status:** current status and tier

**Missing fields** (hard gaps):
```
✗ Product Lead (customfield_12121)
✗ Planned Release Date (customfield_12114)
```

**Optional / recommended:**
```
◌ Squad (customfield_11250) — not yet assigned
◌ Dependencies — none linked; recommend adding if blocked or blocking
```

**Summary naming flags** (soft, use ⚠):
Flag if the summary contains a tribe/squad name, jurisdiction code (BR, BE, PL…), phase name (Discovery, Delivery), quarter prefix ([Q22026]), or is longer than ~5 words.

**If fully compliant:**
```
PLAYER-XXXX — [Initiative Name] ✓ All required fields complete
```

**Claude-fixable items** (list after the main report):
```
Claude-fixable (X items):
  🔧 PLAYER-XXXX — Eligible for Backlog → To Do promotion (Roadmap Priority is set)
  🔧 PLAYER-XXXX — Planned Release Date set but Roadmap Priority empty — can clear date
  🔧 PLAYER-XXXX — Short Status Update empty — can draft from activity log
```

### Step 6 — Offer next steps

After reporting, offer:
1. Apply Claude-fixable items using the `player-jira-fix` skill
2. View this initiative's Jira link: `https://axilis.atlassian.net/browse/PLAYER-XXXX`
3. Audit a different issue key

## Notes

- `parent` check confirms the initiative is linked to a strategy. No parent = will not appear in any roadmap — flag prominently.
- `customfield_10001` (native Team field): use as fallback context if Squad is empty, but do not score it.
- `customfield_15595` (Target Release Date): only required when there is a hard external compliance deadline — do not flag its absence unless context suggests one.
- `customfield_12115` (Release Date): optional — do not flag.
- If a field returns an unexpected format, note "unable to verify" rather than marking it missing.
