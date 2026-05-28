# QC3 — Manage Tribe Spreadsheet Check
**Run:** 8 — 2026-05-26
**File:** `PLAYER_DataQuality_Manage_2026-05-26.xlsx`

## Check Results

### 1. Sort Order (Compliance Score ascending)
- First row score: **35**
- Last row score: **100**
- First <= Last: **TRUE**
- Result: **PASS**

### 2. Hyperlinks / Issue Key values (col B, first 3 rows)
- Row 1: `PLAYER-964`
- Row 2: `PLAYER-1459`
- Row 3: `PLAYER-1387`
- All three match PLAYER-XXXX pattern: **TRUE**
- Result: **PASS**

### 3. Row Count Sanity (expected 100–200, known value 152)
- Actual row count: **152**
- Within range [100, 200]: **TRUE**
- Result: **PASS**

## Summary

| Check | Result |
|---|---|
| Sort order ascending | PASS |
| Issue Key values present | PASS |
| Row count sanity | PASS |

VERDICT: PASS
