The deploy operation pushes the latest local code and creates a new versioned deployment. The stable web app URL will automatically serve the new version.

Run the following two commands in sequence:

```powershell
Set-Location "C:\Users\JonathanVince\Documents\Claude\Projects\Jira Data Quality"
clasp push --force
clasp deploy --description "Run $(Get-Date -Format 'yyyy-MM-dd')"
```

This will:
1. Push your local `gas/` files to the live Apps Script project (`--force` skips the interactive prompt)
2. Create a new versioned deployment with today's date as the description (e.g. `"Run 2026-05-11"`)

The stable web app URL does not change — it automatically points to the newest deployment.

**To verify:** run `clasp deployments` afterwards — the new version should appear at the top of the list.
