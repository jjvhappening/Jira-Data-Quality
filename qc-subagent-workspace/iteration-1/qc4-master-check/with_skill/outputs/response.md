# QC4 — Master Overview vs Tribe Spreadsheets

**Run:** 8 — 2026-05-26  
**Check:** Master Overview "Total Initiatives" matches Detail tab row counts in each tribe spreadsheet.

## Tribe Total Comparison

| Tribe | Master Overview (Total Initiatives) | Tribe Detail Tab (Row Count) | Expected | Match? |
|---|---|---|---|---|
| Player Engagement | 121 | 121 | 121 | YES |
| Transact | 55 | 55 | 55 | YES |
| Fraud Prevention | 21 | 21 | 21 | YES |
| Retail/Multichannel | 1 | 1 | 1 | YES |
| Manage | 152 | 152 | 152 | YES |

## Notes

- All five tribe totals match exactly between the Master Overview tab and the respective tribe-level Detail tabs.
- The Master Overview also contains an "Unassigned" row (Total Initiatives = 1), which is not represented in any tribe spreadsheet — this is expected behaviour and does not affect the verdict.
- The By Field tab was not checked in this QC step; per the check specification, higher counts there (due to Unassigned rows) are expected and are NOT a failure condition.

VERDICT: PASS
