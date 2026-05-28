---
name: squad-leads-refresh
description: Refresh squad_leads.json from the Notion Player Org page to pick up Engineering Manager changes, new squads, and updated Slack IDs. Use this skill every 5 runs (check run_log.json for the current run number), or whenever there are known org changes. Trigger on phrases like "refresh squad leads", "update squad_leads.json", "sync squad EMs from Notion", "who are the current EMs", or when the workflow prompts a refresh reminder.
---

# Squad Leads Refresh

Keeps `squad_leads.json` in sync with the Notion Player Org page. Run every 5 workflow runs, or whenever org changes are known.

## Files

| File | Path |
|---|---|
| Squad leads data | `C:\Users\JonVince\Documents\GitHub\Jira-Data-Quality\squad_leads.json` |
| Notion Player Org | https://www.notion.so/superbet/Player-Org-29b032f852c5807fab59c839b9710512 |
| Run log | `C:\Users\JonVince\Documents\GitHub\Jira-Data-Quality\run_log.json` |

## When to run

Check `run_log.json` — if the current run number is a multiple of 5 (Run #5, #10, #15…), prompt a refresh. Also run on demand when org changes are mentioned.

## Workflow

### Step 1 — Load current state

Read `squad_leads.json`. Build a flat comparison table of all current squad → EM mappings:

| Tribe | Squad | Current EM | Slack ID | Notion User ID | Last Refreshed |
|---|---|---|---|---|---|
| Player Engagement | GraySkull | Maria Diaz | U09V8TPJCQ1 | 2aed… | 2026-05-11 |
| … | … | … | … | … | … |

Include squads where `engineering_manager` is null (TBH roles) — these are specifically worth checking.

Also note tribe lead entries from each tribe's `tribe_leads` array.

### Step 2 — Fetch the Notion Player Org page

Use `notion-fetch` with the Player Org URL. Extract:
- All squad names listed
- The Engineering Manager assigned to each squad
- Any squads that appear in Notion but are missing from `squad_leads.json`
- Any squads in `squad_leads.json` that no longer appear in Notion

If the page has sub-pages or linked databases, fetch those too to get the full picture.

### Step 3 — Diff against current squad_leads.json

Produce a change table:

| Change type | Tribe | Squad | Old value | New value |
|---|---|---|---|---|
| EM changed | Transact | APM Experience | Ruchita Ram | [new name] |
| EM filled (was TBH) | Manage | Manage Platform | null | [new name] |
| New squad | Player Engagement | [New Squad] | — | [EM name] |
| Squad removed | … | … | [EM] | — |
| No change | … | … | — | — |

If there are no changes, report: `squad_leads.json is up to date as of [Notion page last_edited_time]. No changes needed.` and stop.

### Step 4 — Resolve Slack IDs for changed entries

For each changed or new EM:

1. Use `notion-get-users` with their `notion_user_id` (from the Notion page) to retrieve their email address.
2. Use `slack_search_users` with the email to get their Slack ID.
3. If Slack lookup returns multiple results, show options and ask the user to confirm.
4. If no Slack result is found, set `slack_id` to `null` and flag it in the summary — the workflow will skip Slack messages for squads with a null slack_id.

### Step 5 — Confirm changes with the user

Present the proposed updates:

```
Squad leads refresh — proposed changes (N total):

UPDATES:
  Transact / APM Experience
    EM: Ruchita Ram → [New Name]
    Email: ruchita.ram@happening.xyz → [new email]
    Slack ID: U09G7JMLYUF → [new slack_id]
    Notion ID: 27dd… → [new notion_user_id]

NEW SQUADS:
  Player Engagement / [New Squad]
    EM: [Name], Slack: [ID], Notion: [ID]

TBH ROLES STILL UNFILLED:
  Manage / Manage Platform — still null in Notion

Shall I apply these changes to squad_leads.json?
```

Wait for explicit confirmation before writing.

### Step 6 — Apply changes

For each confirmed change:
- Update the relevant squad's `engineering_manager` object in `squad_leads.json`
- Add new squads under the correct tribe
- For removed squads: do **not** delete them automatically — flag them and ask the user to confirm removal separately (a squad may have been temporarily removed from Notion but still has active initiatives)
- Set `_meta.last_refreshed` to today's date (`YYYY-MM-DD`)

Write the updated file.

### Step 7 — Summarise

```
squad_leads.json updated:
  ✓ X EMs updated
  ✓ Y new squads added
  ◌ Z squads still TBH (no EM)
  ⚠ N squads flagged for manual review (potential removals)

last_refreshed set to [date].
```

If any Slack IDs could not be resolved, list them explicitly so they can be chased.

## Notes

- Never overwrite a `_note` field without preserving its content — append rather than replace.
- If a squad has the same EM as another squad (shared EM), add a `_note` documenting this to avoid confusion at run time.
- Tribe leads (`tribe_leads` arrays) should also be checked for changes during each refresh — the same diff and Slack resolution process applies.
- `summary_recipient` (Jon Vince) does not need refreshing via this skill.
- The `notification_policy.declining_trend_runs` field controls message suppression logic — do not modify it during a refresh.
