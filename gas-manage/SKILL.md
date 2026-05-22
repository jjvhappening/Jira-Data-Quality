---
name: gas-manage
description: Manage the PLAYER Data Quality Google Apps Script project using clasp (Google's official CLI). Use this skill whenever Jon wants to: push code changes to gas/Code.gs or gas/dashboard.html to the live Apps Script, run generateDashboard() or any Apps Script function, create a new web app deployment, sync local files from the live script, or perform initial clasp setup. Also trigger for phrases like "update the script", "deploy a new version", "run the dashboard generation", "push my changes", "get the latest from the script editor", or anything involving the PLAYER DQ dashboard's underlying Apps Script code.
---

# PLAYER DQ Apps Script — clasp Management

Manages the Google Apps Script project that powers the PLAYER Data Quality dashboard, using `clasp` — Google's official CLI for Apps Script.

## Project Configuration

| Setting | Value |
|---|---|
| Script ID | `1a6Cau2qMAvxLbHBtQkig42wNX9A_A0I5p946CxXxBWNVdjYd0veGOBFh` |
| Source files | `gas/Code.gs`, `gas/dashboard.html` |
| clasp rootDir | `gas/` |
| `.clasp.json` location | Project root |
| Credentials (clasp run) | `gas/credentials.json` — never commit |
| Platform | Windows / PowerShell |
| Project dir | `C:\Users\JonathanVince\Documents\Claude\Projects\Jira Data Quality` |

---

## Detecting Intent

Map the user's request to an operation:

| User says… | Operation |
|---|---|
| "push", "update the script", "get my changes live" | **push** |
| "push and run", "push then regenerate dashboard", "push-run" | **push-run** |
| "pull", "sync from Google", "get latest from browser editor" | **pull** |
| "deploy", "new deployment", "new version", "release" | **deploy** |
| "run [function]", "trigger [function]", "execute [function]" | **run** |
| "open the editor", "open in browser" | **open** |
| "set up clasp", "first time", "install clasp" | **setup** |

---

## Operations

### push

Push local `gas/` files to the live Apps Script project.

```powershell
Set-Location "C:\Users\JonathanVince\Documents\Claude\Projects\Jira Data Quality"
clasp push --force
```

`--force` skips the interactive "Are you sure?" prompt.

---

### push-run

Push changes then immediately regenerate the dashboard.

> **Phase 2 not yet configured** — `clasp run` requires GCP Desktop App credentials which are not set up. Use **push** instead, then trigger `generateDashboard()` from the Apps Script browser editor if needed. The hourly trigger also regenerates the Drive copy automatically.

```powershell
Set-Location "C:\Users\JonathanVince\Documents\Claude\Projects\Jira Data Quality"
clasp push --force
clasp run generateDashboard
```

---

### pull

Download the current live script files into `gas/`. Use when edits were made directly in the browser script editor and need to be synced locally.

```powershell
Set-Location "C:\Users\JonathanVince\Documents\Claude\Projects\Jira Data Quality"
clasp pull
```

---

### deploy

Push and create a new versioned deployment. The web app URL stays stable; the version number increments. Description is date-stamped for tracking.

```powershell
Set-Location "C:\Users\JonathanVince\Documents\Claude\Projects\Jira Data Quality"
clasp push --force
clasp deploy --description "Run $(Get-Date -Format 'yyyy-MM-dd')"
```

---

### run

Execute a named Apps Script function directly from the CLI.

> **Phase 2 not yet configured** — `clasp run` is blocked until GCP Desktop App credentials are set up. As a fallback, open the script in the browser (`clasp open`) and use the function dropdown to run manually.

Common functions in this project:

| Function | Purpose |
|---|---|
| `generateDashboard` | Regenerate the HTML dashboard from trend data |
| `checkForNewRuns` | Manually trigger the hourly new-run scan |
| `backfillHistory` | One-time seed of historical trend data |
| `regenerateDashboard` | Regenerate dashboard without processing a new upload |

```powershell
clasp run <functionName>
```

---

### open

Open the Apps Script project in the browser editor.

```powershell
clasp open
```

---

### setup

First-time configuration. Run each step in order, pausing where user input is needed.

**Step 1 — Verify Node.js**
```powershell
node --version
npm --version
```
If Node.js is missing, direct the user to https://nodejs.org (LTS version). Wait for installation before continuing.

**Step 2 — Install clasp**
```powershell
npm install -g @google/clasp
clasp --version
```

**Step 3 — Enable Apps Script API**

Tell the user:
> "Open **https://script.google.com/home/usersettings** and toggle **Google Apps Script API** to On. This is required — without it, every clasp command fails with a 403. Confirm here when it's enabled."

Wait for confirmation before proceeding.

**Step 4 — Authenticate**
```powershell
clasp login
```
Opens a browser OAuth flow. Jon should sign in with `jonathan.vince@super.xyz`.

**Step 5 — Create .clasp.json**

Write this to the project root:
```json
{
  "scriptId": "1a6Cau2qMAvxLbHBtQkig42wNX9A_A0I5p946CxXxBWNVdjYd0veGOBFh",
  "rootDir": "gas"
}
```

**Step 6 — Create gas/ folder and pull live files**
```powershell
New-Item -ItemType Directory -Path "C:\Users\JonathanVince\Documents\Claude\Projects\Jira Data Quality\gas" -Force
Set-Location "C:\Users\JonathanVince\Documents\Claude\Projects\Jira Data Quality"
clasp pull
```
This creates `gas/Code.gs`, `gas/dashboard.html`, and `gas/appsscript.json` from the live script.

**Step 7 — Verify against existing files**

Compare the pulled files against the root copies that currently exist:
- `gas/Code.gs` ↔ `gas_Code.gs` (project root)
- `gas/dashboard.html` ↔ `gas_dashboard.html` (project root)

If they differ, show the diff and ask Jon which copy is authoritative before proceeding.

**Step 8 — Remove old root files** (after Step 7 confirmed)
```powershell
Remove-Item "C:\Users\JonathanVince\Documents\Claude\Projects\Jira Data Quality\gas_Code.gs"
Remove-Item "C:\Users\JonathanVince\Documents\Claude\Projects\Jira Data Quality\gas_dashboard.html"
```

**Step 9 — Create push.ps1**

Write this convenience script to the project root:
```powershell
param([switch]$Run)
Write-Host "Pushing to Apps Script..."
clasp push --force
if ($Run) {
    Write-Host "Running generateDashboard()..."
    clasp run generateDashboard
}
```

Usage: `.\push.ps1` (push only) or `.\push.ps1 -Run` (push + regenerate dashboard).

---

## Phase 2: Enabling clasp run

Standard `clasp login` doesn't grant the scopes needed to execute functions — it only supports push/pull/deploy. To unlock `clasp run`, you need a GCP credentials file.

**Steps:**

1. Open [Google Cloud Console](https://console.cloud.google.com) → **APIs & Services** → **Credentials**.
2. Find the GCP project linked to this script: in `script.google.com` → ⚙ **Project settings** → **Google Cloud Platform project**.
3. Click **+ Create Credentials** → **OAuth 2.0 Client ID** → Application type: **Desktop app** → name it "clasp-local".
4. Download the JSON → save it as `gas/credentials.json` in the project directory.
5. Note: `gas/credentials.json` contains secrets — do not commit it anywhere.
6. Re-authenticate using the credentials file:
   ```powershell
   clasp login --creds "C:\Users\JonathanVince\Documents\Claude\Projects\Jira Data Quality\gas\credentials.json"
   ```
7. `clasp run <functionName>` now works.

---

## Verification

| After this action | Verify by |
|---|---|
| Setup or any auth change | Run `clasp pull` — no error = connection is live |
| Push | Run `clasp open`, confirm the change appears in the script editor |
| `clasp run generateDashboard` | Check Drive file `PLAYER_DataQuality_Dashboard.html` — modified timestamp should be fresh |
| Deploy | Run `clasp deployments` — new version appears in the list |
