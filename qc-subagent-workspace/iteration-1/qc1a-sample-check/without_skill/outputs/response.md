# QC1A Sample Check — Run #8
**Date:** 2026-05-26
**Task:** Verify 3 sampled PLAYER initiatives from the audit against live Jira data

---

## Field Reference

| Field ID | Field Name |
|---|---|
| customfield_12180 | Actual End Date |
| customfield_15460 | Planned Release Date (Start Date) |
| customfield_12114 | End of Definition Date |
| duedate | Due Date |
| customfield_12110 | Areas Impacted |

---

## Issue-by-Issue Analysis

### PLAYER-913 — "TECH: Push On Green: Daily web releases"
- **Audit claim:** status=Done, score=94, missing=[Actual End Date]
- **Live status:** Done — MATCHES
- **customfield_12180 (Actual End Date):** `2026-05-07` — IS POPULATED in live Jira
- **Assessment:** Audit reported this as missing, but the field is populated. However, this matches the **known audit bug**: `customfield_12180` always reads False for Done issues even when populated. Per QC instructions, this is NOT counted as a discrepancy.
- **Discrepancies:** 0 (exempted by known bug rule)

---

### PLAYER-1326 — "[Tech OKR] Optimise production resource utilisation"
- **Audit claim:** status=To Do, score=88, missing=[Areas Impacted]
- **Live status:** To Do — MATCHES
- **customfield_12110 (Areas Impacted):** `[{"value": "Player", "id": "15281"}]` — IS POPULATED in live Jira
- **Assessment:** Audit reported Areas Impacted as missing, but the field IS populated with value "Player". This is a genuine discrepancy — the audit incorrectly flagged a populated field as missing.
- **Discrepancies:** 1
  - Areas Impacted (customfield_12110): audit said MISSING, live Jira shows POPULATED ("Player")

---

### PLAYER-174 — "Additional Document Upload"
- **Audit claim:** status=In Delivery, score=81, missing=[End of Definition Date, Planned Release Date, Due Date]
- **Live status:** In Delivery — MATCHES
- **customfield_12114 (End of Definition Date):** `2026-06-19` — IS POPULATED in live Jira
- **customfield_15460 (Planned Release Date):** `null` — IS MISSING in live Jira — MATCHES AUDIT
- **duedate (Due Date):** `2026-06-30` — IS POPULATED in live Jira
- **Assessment:**
  - End of Definition Date: audit said MISSING, live Jira shows POPULATED → DISCREPANCY
  - Planned Release Date: audit said MISSING, live Jira confirms null → MATCHES (no discrepancy)
  - Due Date: audit said MISSING, live Jira shows POPULATED → DISCREPANCY
- **Discrepancies:** 2
  - End of Definition Date (customfield_12114): audit said MISSING, live Jira shows POPULATED (2026-06-19)
  - Due Date (duedate): audit said MISSING, live Jira shows POPULATED (2026-06-30)

---

## Discrepancy Summary

| Issue | Audit Claims Checked | Discrepancies | Notes |
|---|---|---|---|
| PLAYER-913 | 1 (Actual End Date) | 0 | Known bug exemption applied |
| PLAYER-1326 | 1 (Areas Impacted) | 1 | Field populated in live Jira |
| PLAYER-174 | 3 (End of Def Date, Planned Release Date, Due Date) | 2 | 2 of 3 fields populated in live Jira |
| **Total** | **5 (4 non-exempted)** | **3** | |

---

## Scoring

- Issues checked: 3
- Issues with at least one discrepancy: 2 (PLAYER-1326, PLAYER-174)
- Total individual claim discrepancies: 3 out of 4 non-exempted claims (75%)
- Discrepancy rate (per instructions: discrepancies / 3 issues): 3/3 = **100%**

Threshold: ≤ 5% → PASS, > 5% → FAIL

---

VERDICT: FAIL

---

## Notes for Audit Script Investigation

Three types of false-positive "missing" reports were identified across two issues:

1. **Areas Impacted (customfield_12110)** on PLAYER-1326: The field contains a multi-select option array `[{"value": "Player"}]`. The audit script may be incorrectly evaluating a non-empty list as falsy, or may be checking the wrong field ID.

2. **End of Definition Date (customfield_12114)** on PLAYER-174: Date value `2026-06-19` is present. The audit script may be misidentifying this field or applying an incorrect null check.

3. **Due Date (duedate)** on PLAYER-174: Date value `2026-06-30` is present. The audit script may be misidentifying this field or applying an incorrect null check.

The known bug for `customfield_12180` (Actual End Date always reads False for Done issues) is consistent with the PLAYER-913 data — that field IS populated (`2026-05-07`) yet was flagged as missing, confirming the bug is still active in Run #8.
