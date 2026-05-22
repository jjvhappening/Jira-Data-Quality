# PLAYER Project — Jira Roadmapping Rules

Rules for completing initiative fields in the PLAYER Jira project, structured by the point in the PDLC at which each field is required. Based on the [P&T Jira Roadmapping Handbook](https://www.notion.so/superbet/HANDBOOK-Setting-up-Jira-for-P-T-Roadmapping-318032f852c58057a66ce19cf7a22d9e).

> **⚠️ This document is the single source of truth for all PLAYER Jira field IDs.** All other files (`process_full_audit.py`, `build_reports.py`, `player-jira-data-quality-workflow.md`) must derive their field IDs from here — not the other way around.

---

## Maintenance Rules

### Changing a custom field ID

Before proposing or applying any change to a `customfield_XXXXX` value in this document:

1. **Fetch a live initiative** — use the Jira MCP (`searchJiraIssuesUsingJql` or `getJiraIssue`) to retrieve a known PLAYER initiative that has the field in question populated.
2. **Confirm the mismatch** — inspect the raw API response and verify that the field ID currently in this document does not match the value returned for the expected field name. Quote both the current doc value and the live API value in the change rationale.
3. **Only then update** — apply the corrected field ID here first, then propagate to any downstream files.

No field ID in this document may be changed without live API evidence.

---

## Status Workflow Reference

| Phase | Statuses |
|---|---|
| Pre-Delivery | Backlog → To Do → In Discovery → In Definition → Awaiting Approval |
| Delivery | Awaiting Delivery → In Planning → In Delivery → Pending Certification → In Production |
| Post-Delivery | Rollout / Experimentation → In Cleanup |
| Terminal | Done / Won't Do |
| Special | On Hold *(can occur at any point)* |

> Initiatives with **Status = Backlog** are filtered out of all roadmaps.
> Initiatives with **Status = Done for more than 90 days** are also filtered out.

---

## Field Completion Rules by Status

### At Initiative Creation
*Before any work begins, regardless of starting status.*

- **Summary** — follow the naming convention: customer-facing language, no tribe/phase prefix, max ~5 words
- **Parent** — link to a Horizontal or Vertical Strategy immediately; the initiative will not appear in any roadmap without it
- **Product Lead** (`customfield_12121`) — assign the responsible PM
- **Engineering Lead** (`customfield_12122`) — assign the responsible EM
- **Roadmap Priority (PDT)** (`customfield_12012`) — Critical / Must Have / Should Have / Nice to Have. *Priority assigned during the PDT (Product, Design & Tech) roadmap planning process. Determines whether an initiative is committed to a roadmap cycle.*
- **Impact (PDT)** (`customfield_12178`) — expected GGR per month (1 = Very High, 1M+ EUR)
- **Country (PDT)** (`customfield_12112`) — target deployment countries
- **Areas Impacted** (`customfield_12110`) — all areas affected by the change, or from which support is required
- **Investment Category** (`customfield_10709`) — KTLO / User Experience / Engineering Excellence. *The strategic bucket this initiative falls into, used for portfolio-level reporting.*

---

### By In Discovery
*When the initiative transitions into active pre-delivery work.*

- **Start Date** (`customfield_10025`) — set when the initiative moves to In Discovery

> 💡 **Start Date is now auto-populated by a Jira automation rule** (live as of 2026-04-28). When an initiative transitions to In Discovery (or any Tier 1+ status) and Start Date is empty, Jira automatically sets it to today's date. Future Start Date gaps should be rare. If a gap is flagged for a recently created initiative, this likely means the automation had not yet fired when the audit ran.

---

### By Awaiting Approval
*Hard deadline for pre-delivery field completion.*

- **Description** (`description`) or **Product Requirement document** (`customfield_12128`) — the PRD or One Pager must be linked here; this is a hard deadline from the handbook, required as part of the pre-delivery phase

> **Description / PRD rule:** Either `description` OR `customfield_12128` satisfies this requirement. If either field has content, this gap is considered resolved — only flag if **both** are empty.

---

### By End of In Definition / Awaiting Approval
*Once scope is understood and the owning squad is confirmed.*

- **Squad** (`customfield_11250`) *(optional)* — assign as soon as the owning squad is confirmed; multi-squad initiatives should be split into separate initiatives where possible
- **Tribes Impacted** (`customfield_12109`) — all tribes affected by the change, or from which support is required
- **End of Definition Date** (`customfield_15460`) — the date Discovery actually ended — i.e. when the initiative completed its discovery/definition phase and was ready to move into delivery.

---

### From In Planning / Awaiting Delivery Onwards
*Once delivery begins.*

- **Health Status** (`customfield_12111`) — not expected in Backlog, To Do, or Discovery; required once the initiative is moving into delivery. *RAG indicator — Red / Amber / Green — reflecting the squad's own assessment of whether the initiative is on track.*
- **Planned Release Date** (`customfield_12114`) — the planned production release date; the committed date for when the initiative reaches Rollout / Experimentation
- **Due Date** (`duedate`) — the planned end date for the initiative; set when delivery begins so there is a target to track against throughout delivery
- **Short Status Update** (`customfield_14447`) — a short free-text update on current progress, blockers, or key recent developments; kept current throughout delivery. *In plain terms: a 1–2 sentence summary of the initiative's current state — what's happening, any blockers, whether it's on track. Should be updated at least weekly for active initiatives.*
- **Dependencies (Is Blocked by / Blocks)** — recommended as soon as dependencies are identified, including on epics where possible

---

### Optional Fields *(not audited)*
*Set whenever the information is known.*

- **Target Release Date** (`customfield_15595`) *(not audited)* — only needed where there is a hard external deadline (regulatory, compliance); typically later than Planned Release Date

---

### At Done

- **Actual End Date** (`customfield_12180`) — the date the Definition of Done was met, regardless of the Due Date
- **Released Date** (`customfield_12115`) *(not audited)* — actual production release date when functionality became available to customers

---

### Won't Do / On Hold

No new fields are required. Existing field data should be kept accurate and up to date for any initiative that may return to active work.

---

## Additional Rules

### Initiative Naming Convention

- Names should be clear and non-technical, focusing on **value to the customer** rather than an internal/engineering perspective
- Do not encode metadata as a prefix (e.g. tribe name, jurisdiction, phase) if it is already captured in other fields
- Keep names concise — try to avoid more than 5 words
- Avoid tribe/squad names, jurisdictions (BR, BE, etc.) and phase names (Discovery, Delivery) in the title

### Roadmap Visibility

- The **Assignee** field is not used for roadmapping purposes; use Product Lead and Engineering Lead instead
- Any grouping or filtering changes you make in a roadmap view are visible only to you — contact a Jira Champion (Admin) to alter a shared default view
- Initiatives not linked to a parent strategy will not appear in any roadmap at all

### Capacity Planning Fields *(not audited — optional but encouraged)*

These fields support quarterly planning and help leads identify bottlenecks and make informed prioritisation decisions. There is no penalty for rough or imprecise estimates — approximate data is significantly more useful than no data.

- **Effort (T-shirt size)** (`customfield_12135`) *(not audited)* — overall size estimate: XS (0–4 wks), S (5–9 wks), M (10–19 wks), L (20–39 wks), XL (40+ wks). Size up rather than down when uncertain.
- **Effort BE** (`customfield_11220`) *(not audited)* / **Effort Web** (`customfield_11234`) *(not audited)* / **Effort QA** (`customfield_12141`) *(not audited)* / **Effort iOS** (`customfield_11235`) *(not audited)* / **Effort Android** (`customfield_11237`) *(not audited)* — role-level effort in weeks. Enter **0** (not blank) where a role has no involvement.

---

## Cross-Project Fields

Fields used across multiple Jira projects (not PLAYER-specific). Included here as the canonical field ID reference.

### Program (`customfield_14342`)

A **multi-select** field that tags an initiative as part of a named cross-team program. Used for portfolio-level filtering and discovery across all P&T boards (PLAYER, DAP, GAM, IP, and others).

| Option ID | Value |
|---|---|
| `17893` | 🇬🇷 Greece launch |
| `17894` | 🇷🇴 Romania migration |
| `17937` | Product performance & stability |
| `17630` | 🏆 World Cup |

**JQL usage:**
```
cf[14342] = "🇷🇴 Romania migration"
```

> Note: `customfield_14342 is not EMPTY` is valid JQL for this field. The field stores option objects (with `id`, `value`, `self`) — when checking programmatically, match against the option `value` string or `id`.

---

## Appendix — Tier-at-a-Glance

This table shows which fields are required at each status tier in the PLAYER audit. Fields from lower tiers remain required at all higher tiers — each tier is cumulative.

| Tier | Applies at status | Fields required |
|---|---|---|
| **0** | All statuses (including Backlog, To Do) | Summary, Parent, Product Lead, Engineering Lead, Roadmap Priority (PDT), Impact (PDT), Country (PDT), Areas Impacted, Investment Category |
| **1** | In Discovery, In Definition, and above | + Start Date |
| **2** | Awaiting Approval and above | + Description or PRD (either field satisfies this) |
| **3** | Awaiting Approval and above | + Tribes Impacted, End of Definition Date |
| **4** | Awaiting Delivery / In Planning / In Delivery and above (incl. On Hold) | + Health Status, Planned Release Date, Due Date, Short Status Update |
| **5** | Done only | + Actual End Date |

> **Backlog = Tier 0 only.** Initiatives in Backlog are not penalised for missing date fields — dates are genuinely not applicable to unscheduled work.

> **Fields marked *(not audited)*** — Target Release Date, Released Date, Actual End Date, and all Capacity Planning fields — are optional and not included in compliance scoring. They will not appear in gap reports or Slack notifications.
