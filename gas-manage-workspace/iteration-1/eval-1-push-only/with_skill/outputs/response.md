On it. I'll push `gas/Code.gs` to the live Apps Script using clasp.

```powershell
Set-Location "C:\Users\JonathanVince\Documents\Claude\Projects\Jira Data Quality"
clasp push --force
```

`clasp` isn't installed yet — Node.js (v24.15.0) and npm are present, so it's a one-line fix:

```powershell
npm install -g @google/clasp
clasp --version
```

Then there are two more one-time steps before the push will work:

**1. Enable the Apps Script API**
Open **https://script.google.com/home/usersettings** and toggle **Google Apps Script API** to On. Without this, every clasp command returns a 403. Confirm here when it's enabled.

**2. Authenticate**
```powershell
clasp login
```
Sign in with `jonathan.vince@super.xyz` when the browser opens.

Once those are done, the push is:

```powershell
Set-Location "C:\Users\JonathanVince\Documents\Claude\Projects\Jira Data Quality"
clasp push --force
```

`--force` skips the interactive confirmation prompt. After it completes, run `clasp open` to verify the bug fix appears in the script editor.
