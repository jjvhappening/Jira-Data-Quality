Great — here's how to push your changes and regenerate the dashboard.

## 1. Push your changes with clasp

From the root of your project (where `.clasp.json` lives), run:

```bash
clasp push
```

This uploads all local files to the Apps Script project. If your project uses TypeScript or has a `rootDir` configured in `.clasp.json`, make sure you're running the command from the correct directory.

If you want to confirm what will be pushed before sending it, you can do a dry run first:

```bash
clasp push --watch
```

(Use Ctrl+C to stop watching once the initial push is confirmed.)

## 2. Regenerate the dashboard

Once the push is complete, you need to run the function that builds the dashboard output. You can do this from the command line with clasp:

```bash
clasp run generateDashboard
```

Replace `generateDashboard` with the actual name of your generation function if it differs.

> **Note:** `clasp run` requires that your script has been deployed with an API-accessible deployment and that you've authorised the CLI with the correct Google account (`clasp login`). If you haven't set that up, you can instead open the Apps Script editor (`clasp open`), select the function from the dropdown, and click **Run** manually.

## 3. Verify the live output

After the function completes, reload whichever URL or file serves the live dashboard to confirm your top offenders table fix is showing correctly.

---

**Quick checklist:**
- [ ] `clasp push` completed without errors
- [ ] `clasp run generateDashboard` (or equivalent) finished successfully
- [ ] Live dashboard reloaded and fix is visible
