---
name: QC Known Bugs Reference
description: Documents confirmed systematic bugs found in the audit script via QC verification runs. Use before fixing audit_results or interpreting compliance scores.
type: reference
project: Jira Data Quality
---

# Known Audit Script Bugs

## BUG-001: customfield_12180 (Actual End Date) always reads as False

**Discovered:** 2026-05-26 (QC1A Run #8, Half 2 — 39-initiative sample)

**Symptom:**
The audit records `customfield_12180 = False` for every single Done-status initiative in the full dataset. Out of 93 Done issues audited, zero show Actual End Date as present.

**Impact:**
- All Done-status initiatives are under-scored by exactly 6 percentage points (1 field out of 17 required)
- The `fields_missing` list for every Done issue incorrectly includes `"Actual End Date"`
- Tier 5 is treated as non-existent for all Done issues

**Evidence from QC1A Half 2:**
5 discrepancies all shared this root cause:

| Issue | Audit score | Correct score | Live ActEnd value |
|---|---|---|---|
| PLAYER-913 | 94 | 100 | 2026-05-07 |
| PLAYER-970 | 82 | 88 | 2026-05-20 |
| PLAYER-853 | 65 | 71 | 2026-05-13 |
| PLAYER-1481 | 53 | 59 | 2026-01-26 |
| PLAYER-234 | 65 | 71 | 2026-05-21 |

All five ActEnd dates pre-date the audit run (2026-05-26T07:17:32Z), confirming the field was populated at audit time and was not added after the fact.

**Root cause (hypothesis):**
The audit script likely fails to parse `customfield_12180` because:
- The field may return in a non-string format (e.g. nested dict, or null-like object)
- Or the field ID may differ for the PLAYER project vs what the script expects
- Check the raw Jira response for a Done issue — compare how the script parses cf12180 vs how it is actually structured

**Fix needed:**
1. Run `getJiraIssue` on any Done initiative that has a known ActEnd date (e.g. PLAYER-913)
2. Inspect the raw `customfield_12180` field structure in the response
3. Update the audit script's field-presence check to correctly detect population
4. Re-run the audit and verify Done-issue scores increase by 6pp for issues that have the field

**Do not mark compliance KPIs as definitive** until this bug is resolved. Done-status initiatives are systematically under-reported.

---

## Non-bugs confirmed

The following were investigated during QC1A and confirmed NOT to be bugs:

- All other field readings (parent, PL, EL, RP, Impact, Country, Areas, InvCat, StartDate, desc_or_prd, Tribes, EoDD, Health, PRD_date, SSU, Due) matched live Jira exactly across both halves of the QC sample.
- Status readings were accurate — no staleness detected across 39 issues in Half 2.

Last updated: 2026-05-26
