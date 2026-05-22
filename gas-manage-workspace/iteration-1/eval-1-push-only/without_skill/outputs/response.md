To push your updated `gas/Code.gs` to Apps Script, you can use **clasp** (the official Google Apps Script CLI).

## Prerequisites

Make sure you have clasp installed and authenticated:

```bash
npm install -g @google/clasp
clasp login
```

## Check your `.clasp.json`

Your project needs a `.clasp.json` file in the root (or in the `gas/` directory, depending on your setup) that maps to your Script ID. It should look something like:

```json
{
  "scriptId": "YOUR_SCRIPT_ID_HERE",
  "rootDir": "gas"
}
```

If you don't have one yet, you can create it manually (get your Script ID from the Apps Script editor URL: `script.google.com/home/projects/YOUR_SCRIPT_ID/edit`) or run:

```bash
clasp clone YOUR_SCRIPT_ID
```

## Push your changes

From the directory containing `.clasp.json`, run:

```bash
clasp push
```

If your `.clasp.json` is in the project root and `rootDir` points to `gas/`, clasp will push everything in that folder. If it's inside `gas/` itself, run the command from there:

```bash
cd gas
clasp push
```

## Verify the push

After pushing, open the Apps Script editor to confirm the updated code is there:

```bash
clasp open
```

## Watch mode (optional)

If you're iterating quickly, you can use watch mode to push automatically on every file save:

```bash
clasp push --watch
```

## Common issues

- **"Could not find `.clasp.json`"** — run `clasp push` from the directory containing that file, or pass `--project path/to/.clasp.json`.
- **Auth errors** — re-run `clasp login` to refresh your credentials.
- **File type mismatch** — clasp expects `.gs` files (or `.js` if configured); make sure your local filenames match what's in `appsscript.json`.

Once the push succeeds, test your trend chart fix directly in the Apps Script editor or via your deployed web app.
