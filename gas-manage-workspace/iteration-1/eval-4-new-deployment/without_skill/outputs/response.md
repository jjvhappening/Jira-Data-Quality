Great — with Run 3 complete, here's how to create a new versioned deployment so the stable web app URL starts serving your updated code.

## Creating a New Deployment Version

### Option A: Using the Apps Script Editor (UI)

1. Open your script at [script.google.com](https://script.google.com) and select your project.
2. Click **Deploy** (top-right) → **Manage deployments**.
3. Find your existing web app deployment and click the **pencil (edit) icon**.
4. In the **Version** dropdown, select **New version** (it will be at the top of the list).
5. Optionally add a description (e.g. "Run 3 complete").
6. Click **Deploy**.

The stable deployment URL does not change — it now points to the new version automatically.

---

### Option B: Using clasp (command line)

If you manage your project with [clasp](https://github.com/google/clasp), the equivalent workflow is:

```bash
# 1. Push your local files to the script project
clasp push

# 2. Create a new versioned deployment
#    Replace DEPLOYMENT_ID with your existing web app deployment ID
clasp deploy --deploymentId <DEPLOYMENT_ID> --description "Run 3 complete"
```

- `clasp push` uploads your local `.gs` / `.html` files to the HEAD of the script project.
- `clasp deploy --deploymentId` updates an **existing** deployment to point to a new version of HEAD. Omitting `--deploymentId` would create a brand-new deployment with a different URL, which is usually not what you want for a stable URL.

To find your existing deployment ID:

```bash
clasp deployments
```

This lists all deployments with their IDs and current version numbers.

---

### Verifying the update

After deploying, open the stable web app URL (the one that doesn't end in `/dev`) in an incognito window to confirm the new code is live. The `/dev` URL always serves the latest saved HEAD and is unaffected by versioned deployments.
