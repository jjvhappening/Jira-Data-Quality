---
name: Audit Pagination Reference
description: Pagination workaround for process_full_audit.py and QC1B category distribution for PLAYER project
type: reference
project: Jira Data Quality
---

# Audit Pagination Reference

Last updated: 2026-05-18

---

## process_full_audit.py — 100-result abort behaviour

The script aborts if **any single audit file contains exactly 100 results**, treating it as a truncation signal. This fires even when subsequent pages are already included in the `--audit` file list.

**Workaround:** Pre-merge all paginated files for each query into a single JSON list before passing to the script. Use `merge_tool_results.py` (or equivalent) to read the tool-result `.txt` files, extract the `issues` arrays, deduplicate by key, and write a merged list. Then pass the merged file — it won't trigger the check.

```bash
python merge_tool_results.py
python process_full_audit.py --audit jira_audit_merged.json --qc1b qc1b_merged.json
```

---

## Cursor token expiry

Jira `nextPageToken` values are **session-scoped** and expire in minutes. Across a context summarization boundary (when the conversation is compacted), all tokens become invalid. If a `nextPageToken` is used after expiry, Jira returns:

```
{"errorMessages":["The provided next page token is invalid or expired."],"errors":{}}
```

**Recovery:** Re-fetch from page 1 for each query and chain the new tokens. This costs 5–6 extra API calls for the Player category (which spans 6 pages of 100 results each). There is no `startAt` offset available through the MCP tool.

---

## QC1B — Category distribution

The QC1B coverage sweep fires nine category queries:

| Category | Contains PLAYER- keys? | Typical page count |
|---|---|---|
| Player | **Yes — all PLAYER- keys** | 6 pages (560+ issues) |
| Data Foundations | No | 1 page (56 issues) |
| Data Products | No | 1 page (76 issues) |
| Platform | No | 2 pages (174 issues) |
| Gaming | No | 4 pages+ (400+ issues) |
| Social | No | 1 page (103 issues) |
| Sports | No | 5 pages+ (500+ issues) |
| International Program | No | 3 pages (231 issues) |
| Core Experience | No | 1 page (37 issues) |

**Key insight:** All PLAYER project initiatives have `category = "Player"`. The other 8 categories contain initiatives from other Jira projects; they contribute zero PLAYER- keys to the coverage check. To complete a QC1B sweep, only the "Player" category pagination needs to be fully resolved.

---

## Query file structure (Run #6 reference)

| Query | Files (tool-result timestamps) | Issues |
|---|---|---|
| A — To Do | `...-1779120481277.txt` | 92 |
| B — Pre-delivery | `...-1779120485591.txt` | 33 |
| C — Delivery p1+p2 | `...-1779120490463.txt` + `...-1779120594646.txt` | 100+97 |
| D — Done 90d p1+p2 | `...-1779120497210.txt` + `...-1779120598794.txt` | 100+16 |
| QC Player p1–p6 | `...-1779120908030.txt` through `...-1779121059755.txt` | 100×5+64 |

Merged audit total: **438 issues** (deduplicated)
Merged QC1B total: **564 issues** (Player category only)
Audited (after Retail exclusion): **365 initiatives**
