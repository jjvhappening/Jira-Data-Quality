# PLAYER Data Quality Dashboard — One-Time Setup Guide

Estimated time: **15–20 minutes**

---

## What you'll end up with

A Google Apps Script web app at a stable `script.google.com` URL that:
- Shows compliance trends, tribe scorecards, squad tables, and top offenders
- Auto-updates every time you upload a new Master Excel to Drive
- Is accessible to anyone you share the URL with — no login required

---

## Step 1 — Create the Apps Script project

1. Go to [script.google.com](https://script.google.com) → **New project**
2. Rename it: click "Untitled project" → type **`PLAYER DQ Dashboard`** → click OK

---

## Step 2 — Paste the code

### Code.gs (main script)
1. The editor opens with a default `Code.gs` file
2. **Delete all existing content** in `Code.gs`
3. Open `gas_Code.gs` from `C:\Users\JonathanVince\Documents\Claude\Projects\Jira Data Quality\`
4. Copy the entire contents and paste into `Code.gs`
5. Click the **Save** button (floppy disk icon)

### gas_dashboard (HTML template)
1. In the left sidebar, click **+** next to Files → select **HTML**
2. Name the file exactly: **`gas_dashboard`** (no `.html` extension — Apps Script adds it)
3. **Delete all existing content** in the new file
4. Open `gas_dashboard.html` from the project folder
5. Copy the entire contents and paste into the Apps Script HTML file
6. Click **Save**

---

## Step 3 — Enable the Drive API

1. In the left sidebar, click **Services** (+ icon)
2. Find **Drive API** in the list → select it → click **Add**
3. Confirm it appears under Services as `Drive`

---

## Step 4 — Set Script Properties

1. Click **Project Settings** (gear icon, left sidebar)
2. Scroll down to **Script Properties** → click **Add script property**
3. Add this property:

| Property | Value |
|---|---|
| `FOLDER_ID` | `1L8oU7wvw9ROTJmCtooTod_UcXpnt9Uk0` |

4. Click **Save script properties**

---

## Step 5 — Run the backfill (first time only)

This reads the Run 1 and Run 2 Excel files already in Drive and creates the initial `trend_history.json` and `dashboard.html` files in the Drive folder.

1. In the editor, open the function dropdown at the top (it may say `myFunction`) → select **`backfillHistory`**
2. Click **▶ Run**
3. First run will ask for permissions — click **Review permissions** → choose your account → click **Allow**
4. Run `backfillHistory` again after authorising
5. Check the **Execution log** at the bottom — you should see:
   ```
   Backfilling: 2026-04-25
     Run 1: 490 initiatives, avg XX%
   Backfilling: 2026-05-04
     Run 2: 302 initiatives, avg 76%
   Backfill complete. Runs: 2
   TREND_FILE_ID:     [some ID]
   DASHBOARD_FILE_ID: [some ID]
   ```
6. Verify `trend_history.json` and `PLAYER_DataQuality_Dashboard.html` have appeared in the [Player Jira Data Quality Drive folder](https://drive.google.com/drive/folders/1L8oU7wvw9ROTJmCtooTod_UcXpnt9Uk0)

> **If backfill fails:** Check the execution log for the error. The most common cause is Drive API not enabled (Step 3) or FOLDER_ID not set (Step 4).

---

## Step 6 — Set up the hourly trigger

This makes the dashboard auto-update within ~1 hour of uploading a new Master Excel.

> **Note:** Google deprecated the "From Google Drive" onChange trigger — it no longer appears in the UI. The time-driven approach below is the reliable replacement.

1. In the left sidebar, click **Triggers** (clock icon)
2. Click **+ Add Trigger** (bottom right)
3. Configure:

| Setting | Value |
|---|---|
| Function to run | `checkForNewRuns` |
| Which runs at deployment | `Head` |
| Event source | `Time-driven` |
| Type of time based trigger | `Hour timer` |
| Select hour interval | `Every hour` |

4. Click **Save**
5. Grant permissions when prompted

`checkForNewRuns` scans the Drive folder for any `PLAYER_DataQuality_Master_*.xlsx` file whose date isn't already in `trend_history.json`. First time it finds one, it processes it and regenerates the dashboard. Subsequent hourly runs do nothing until a new file appears.

---

## Step 7 — Deploy as web app

1. Click **Deploy** (top right) → **New deployment**
2. Click the gear icon next to "Type" → select **Web app**
3. Configure:

| Setting | Value |
|---|---|
| Description | `PLAYER DQ Dashboard v1` |
| Execute as | `Me` |
| Who has access | `Anyone` *(or "Anyone with the link" if that option is shown)* |

4. Click **Deploy**
5. **Copy the web app URL** — it looks like `https://script.google.com/macros/s/AKfycb.../exec`
6. Open it in an incognito window to verify the dashboard loads

> **Share this URL** with Tribe Leads, Directors, and VPs. It's stable — it won't change unless you create a new deployment.

---

## Ongoing use — each new run

When you run the PLAYER data quality workflow and `build_reports.py` completes:

1. Upload the run folder (tribe Excels + Master) to the [Player Jira Data Quality Drive folder](https://drive.google.com/drive/folders/1L8oU7wvw9ROTJmCtooTod_UcXpnt9Uk0)
2. The hourly `checkForNewRuns` trigger detects the new `PLAYER_DataQuality_Master_*.xlsx` file
3. Apps Script reads the Master Excel, updates `trend_history.json`, and regenerates the dashboard — **within ~1 hour of upload**
4. Anyone visiting the web app URL sees the updated data immediately

No further action needed.

---

## Manual controls (from the Apps Script editor)

| Function | When to use |
|---|---|
| `backfillHistory()` | First-time setup only — seeds Run 1 & 2 data |
| `regenerateDashboard()` | Force-regenerate the dashboard without uploading new files |
| `processNewRun('2026-05-04', 'MASTER_FILE_ID')` | Manually trigger processing for a specific date if the onChange trigger missed it |

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Dashboard shows "not yet generated" | Run `backfillHistory()` from the editor |
| Dashboard doesn't update after upload | Wait up to 1 hour for `checkForNewRuns` to fire. Or run `checkForNewRuns()` manually from the editor to trigger immediately. |
| `backfillHistory` fails with "Drive API not enabled" | Add Drive API via Services (Step 3) |
| "FOLDER_ID not set" in logs | Set Script Property in Project Settings (Step 4) |
| Old data still showing | Wait 30 seconds and refresh. Drive indexing can lag slightly. |
