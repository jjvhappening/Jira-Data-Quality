# QC1A Sample Check — Run #8
**Date:** 2026-05-26  
**Verifier:** QC sub-agent (claude-sonnet-4-6)  
**Task:** Verify 3 sampled PLAYER initiatives from the Run #8 audit against live Jira data.

---

## Field Reference

| Field ID | Field Name |
|---|---|
| customfield_12180 | Actual End Date |
| customfield_15460 | Planned Release Date (Start of Definition / target) |
| customfield_12114 | End of Definition Date (target/planned date) |
| customfield_12110 | Areas Impacted |
| duedate | Due Date |
| customfield_12121 | PM Owner |
| customfield_12122 | Tech Lead |

---

## Issue Analysis

### PLAYER-913 (Done) — Audit: score=94, missing=[Actual End Date]

**Live Jira fields:**
| Field | Value |
|---|---|
| status | Done |
| customfield_12180 (Actual End Date) | **2026-05-07** (populated) |
| customfield_15460 | 2026-01-01 (populated) |
| customfield_12114 | 2026-04-10 (populated) |
| customfield_12110 | [Player] (populated) |
| duedate | 2026-04-10 (populated) |

**Assessment:**  
Audit claims `customfield_12180` (Actual End Date) is missing. Live data shows it is **populated** ("2026-05-07").

However, this matches the **known audit bug**: `customfield_12180` always reads False for Done issues even when populated. Per QC instructions, this is NOT counted as a discrepancy.

**Discrepancies for PLAYER-913: 0** (known bug exemption applied)

---

### PLAYER-1326 (To Do) — Audit: score=88, missing=[Areas Impacted]

**Live Jira fields:**
| Field | Value |
|---|---|
| status | To Do |
| customfield_12180 (Actual End Date) | null |
| customfield_15460 | null |
| customfield_12114 | null |
| customfield_12110 (Areas Impacted) | **[{"value": "Player"}]** (populated) |
| duedate | null |

**Assessment:**  
Audit claims `customfield_12110` (Areas Impacted) is missing. Live data shows it is **populated** with value "Player".

This is a genuine discrepancy — the audit incorrectly flagged Areas Impacted as missing when it has a value.

**Discrepancies for PLAYER-1326: 1**
- DISCREPANCY: Audit says Areas Impacted (customfield_12110) is missing, but live value = "Player"

---

### PLAYER-174 (In Delivery) — Audit: score=81, missing=[End of Definition Date, Planned Release Date, Due Date]

**Live Jira fields:**
| Field | Value |
|---|---|
| status | In Delivery |
| customfield_12180 (Actual End Date) | null |
| customfield_15460 (Planned Release Date) | **null** (absent — confirms audit) |
| customfield_12114 (End of Definition Date) | **2026-06-19** (populated) |
| customfield_12110 (Areas Impacted) | [Player] (populated) |
| duedate (Due Date) | **2026-06-30** (populated) |

**Assessment:**  
Audit claims three fields are missing: End of Definition Date, Planned Release Date, Due Date.

- `customfield_15460` (Planned Release Date) = null → audit claim CONFIRMED, no discrepancy
- `customfield_12114` (End of Definition Date) = "2026-06-19" → **DISCREPANCY**: audit says missing but field IS populated
- `duedate` (Due Date) = "2026-06-30" → **DISCREPANCY**: audit says missing but field IS populated

**Discrepancies for PLAYER-174: 2**
- DISCREPANCY 1: Audit says End of Definition Date (customfield_12114) is missing, but live value = "2026-06-19"
- DISCREPANCY 2: Audit says Due Date (duedate) is missing, but live value = "2026-06-30"

---

## Summary

| Issue | Audit Claimed Missing | Live Status | Discrepancies |
|---|---|---|---|
| PLAYER-913 | Actual End Date | Populated (known bug exemption) | 0 |
| PLAYER-1326 | Areas Impacted | Populated — DISCREPANCY | 1 |
| PLAYER-174 | End of Definition Date | Populated — DISCREPANCY | 1 |
| PLAYER-174 | Planned Release Date | Absent — confirmed | 0 |
| PLAYER-174 | Due Date | Populated — DISCREPANCY | 1 |

**Total discrepancies: 3**  
**Total field-claims checked: 5** (4 after exempting the known bug on PLAYER-913)  
**Issues checked: 3**

---

## Scoring

Discrepancy rate = discrepancies / issues checked = 3 / 3 = **100%**

Threshold: ≤ 5% → PASS, > 5% → FAIL

The discrepancy rate of 100% far exceeds the 5% threshold.

---

VERDICT: FAIL
