Great — let's get clasp set up from scratch. Work through each step below in order; I'll pause where you need to do something before we can continue.

---

## Step 1 — Verify Node.js

Run this to check whether Node.js is already installed:

```powershell
node --version
npm --version
```

If either command is not found, install Node.js (LTS) from https://nodejs.org, then come back and confirm before continuing.

---

## Step 2 — Install clasp

```powershell
npm install -g @google/clasp
clasp --version
```

This installs clasp globally. The version number printed confirms it's ready.

---

## Step 3 — Enable the Apps Script API

Open this URL in your browser:

**https://script.google.com/home/usersettings**

Toggle **Google Apps Script API** to **On**. This is required — without it, every clasp command fails with a 403 error.

Confirm here once it's enabled before we proceed.

---

## Step 4 — Authenticate

```powershell
clasp login
```

This opens a browser OAuth flow. Sign in with **jonathan.vince@super.xyz**.

---

## Step 5 — Create .clasp.json

Write the following to the project root (`C:\Users\JonathanVince\Documents\Claude\Projects\Jira Data Quality\.clasp.json`):

```json
{
  "scriptId": "1a6Cau2qMAvxLbHBtQkig42wNX9A_A0I5p946CxXxBWNVdjYd0veGOBFh",
  "rootDir": "gas"
}
```

---

## Step 6 — Create the gas/ folder and pull live files

```powershell
New-Item -ItemType Directory -Path "C:\Users\JonathanVince\Documents\Claude\Projects\Jira Data Quality\gas" -Force
Set-Location "C:\Users\JonathanVince\Documents\Claude\Projects\Jira Data Quality"
clasp pull
```

This pulls the live script down and creates:
- `gas/Code.gs`
- `gas/dashboard.html`
- `gas/appsscript.json`

---

## Step 7 — Verify against existing root files

Compare the pulled files against the copies that currently sit at the project root:

- `gas/Code.gs` vs `gas_Code.gs`
- `gas/dashboard.html` vs `gas_dashboard.html`

If they differ, show me the diff and I'll help you decide which copy is authoritative before we delete the old ones.

---

## Step 8 — Remove old root files

Once Step 7 is confirmed, remove the old copies:

```powershell
Remove-Item "C:\Users\JonathanVince\Documents\Claude\Projects\Jira Data Quality\gas_Code.gs"
Remove-Item "C:\Users\JonathanVince\Documents\Claude\Projects\Jira Data Quality\gas_dashboard.html"
```

---

## Step 9 — Create push.ps1

Write this convenience script to the project root (`push.ps1`):

```powershell
param([switch]$Run)
Write-Host "Pushing to Apps Script..."
clasp push --force
if ($Run) {
    Write-Host "Running generateDashboard()..."
    clasp run generateDashboard
}
```

Usage going forward:
- `.\push.ps1` — push only
- `.\push.ps1 -Run` — push and regenerate the dashboard

---

## After setup: verify the connection

Run a quick pull to confirm everything is wired up correctly:

```powershell
clasp pull
```

No error = the connection is live and you're ready to go.

---

## Note on clasp run

`clasp run` (used by `.\push.ps1 -Run`) needs a GCP credentials file — standard `clasp login` does not grant the required scopes. If you want to enable that, let me know and I'll walk you through the Phase 2 setup (creating an OAuth Desktop app credential in Google Cloud Console and saving it as `gas/credentials.json`).

Start with Step 1 — let me know what `node --version` returns.
