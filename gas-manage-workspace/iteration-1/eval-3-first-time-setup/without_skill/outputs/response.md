# Setting Up clasp for the First Time

clasp (Command Line Apps Script Projects) lets you develop Google Apps Script projects locally and push/pull code via the command line. Here's how to get set up from scratch.

---

## Step 1: Install Node.js

clasp requires Node.js. If you don't have it:

- Download and install from https://nodejs.org (LTS version recommended)
- Verify installation: `node -v` and `npm -v`

---

## Step 2: Install clasp globally

```bash
npm install -g @google/clasp
```

Verify the install:

```bash
clasp --version
```

---

## Step 3: Enable the Google Apps Script API

Before authenticating, you need to enable the Apps Script API on your Google account:

1. Go to https://script.google.com/home/usersettings
2. Toggle **Google Apps Script API** to **On**

Without this step, clasp commands will fail with a permissions error even after login.

---

## Step 4: Authenticate with Google

```bash
clasp login
```

This opens a browser window asking you to sign in with your Google account and grant clasp the necessary permissions. After authorising, your credentials are saved locally (typically at `~/.clasprc.json`) and you won't need to log in again unless you explicitly log out.

---

## Step 5: Set up your project directory

Create or navigate to the local folder where you want to keep your script files:

```bash
mkdir my-script-project
cd my-script-project
```

You now have two options depending on whether the Apps Script project already exists or you want to create a new one.

### Option A: Clone an existing Apps Script project

If the project already exists in Google Drive or the Apps Script editor, find its Script ID (in the Apps Script editor: **Project Settings** → **Script ID**), then run:

```bash
clasp clone <SCRIPT_ID>
```

This pulls down the existing files and creates a `.clasp.json` config file in your directory.

### Option B: Create a brand-new project

```bash
clasp create --title "My Project Name" --type standalone
```

Common `--type` values: `standalone`, `sheets`, `docs`, `forms`, `slides`, `webapp`. This creates the project in Google Drive and generates a `.clasp.json` locally.

---

## Step 6: Understand the key files

After cloning or creating, your directory will contain:

| File | Purpose |
|---|---|
| `.clasp.json` | Links this folder to your Apps Script project (contains the `scriptId`) |
| `appsscript.json` | The project manifest (time zone, OAuth scopes, etc.) |
| `*.gs` / `*.js` | Your script files |

> By default, clasp works with `.gs` files. If you prefer TypeScript, add `--rootDir` and a `tsconfig.json` — clasp will transpile before pushing.

---

## Step 7: Push and pull code

**Push local changes to Google:**

```bash
clasp push
```

**Pull the latest version from Google:**

```bash
clasp pull
```

**Open the project in the browser-based editor:**

```bash
clasp open
```

---

## Step 8: Deploying (optional)

To create a new versioned deployment (e.g. a web app or add-on):

```bash
clasp deploy --description "v1.0 initial release"
```

List existing deployments:

```bash
clasp deployments
```

---

## Typical workflow summary

1. Edit `.gs` files locally in your editor of choice (VS Code works well)
2. `clasp push` to sync changes up to Google
3. Test in the Apps Script editor or via your web app URL
4. `clasp pull` if you ever make changes directly in the browser editor

---

## Troubleshooting tips

- **"Script API not enabled"** — revisit Step 3 and make sure the toggle is on for the correct Google account
- **"Could not read API credentials"** — run `clasp login` again
- **Multiple Google accounts** — use `clasp login --no-localhost` or manage credentials with `clasp logout` and re-login with the correct account
- **`.claspignore`** — works like `.gitignore`; add it to exclude files (e.g. `node_modules/`, `README.md`) from being pushed to Apps Script
