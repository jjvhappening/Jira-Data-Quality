"""
drive_sync.py — Upload trend_history.json to Google Drive.

Auth strategy (two-tier):
  1. Tries a saved drive_token.json that has full Drive write scope.
  2. If not present, runs a one-time browser OAuth flow using the client
     credentials from ~/.clasprc.json (no extra setup needed).
     The resulting token is saved to drive_token.json for future runs.

USAGE
-----
Test connection only (safe — no upload):
    python drive_sync.py --test

Upload trend_history.json to Drive (replaces the live file):
    python drive_sync.py

DEPENDENCIES
------------
    pip install google-api-python-client google-auth google-auth-oauthlib

INTEGRATION
-----------
Called automatically at the end of build_reports.py. If this script fails,
build_reports.py prints a manual-fallback message and continues.
"""
import json, os, sys, argparse
sys.stdout.reconfigure(encoding='utf-8')

CLASPRC             = os.path.expanduser('~/.clasprc.json')
DRIVE_TREND_FILE_ID = '1hlDO1oo2YOT6BenZa9vqbWxBT0bRW2PA'
TREND_FILE          = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'trend_history.json')
# Saved token with drive write scope — created on first run, reused thereafter.
TOKEN_FILE          = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'drive_token.json')
SCOPES              = ['https://www.googleapis.com/auth/drive']


def _client_config():
    """Extract client_id and client_secret from the clasp credentials file."""
    with open(CLASPRC, encoding='utf-8') as f:
        rc = json.load(f)
    t = rc.get('tokens', {}).get('default', rc)
    return {
        'client_id':     t['client_id'],
        'client_secret': t['client_secret'],
    }


def get_creds():
    """
    Return valid Drive credentials with write scope.

    Loads from drive_token.json if present and valid; otherwise runs a
    browser-based OAuth flow once and saves the result to drive_token.json.
    """
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None

    # ── Load saved token ──────────────────────────────────────────────────────
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, encoding='utf-8') as f:
            data = json.load(f)
        cfg = _client_config()
        creds = Credentials(
            token=data.get('access_token'),
            refresh_token=data.get('refresh_token'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=cfg['client_id'],
            client_secret=cfg['client_secret'],
            scopes=SCOPES,
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            _save_token(creds)

    # ── First-run: browser OAuth flow ─────────────────────────────────────────
    if not creds or not creds.valid:
        cfg = _client_config()
        client_config = {
            'installed': {
                'client_id':                  cfg['client_id'],
                'client_secret':              cfg['client_secret'],
                'auth_uri':                   'https://accounts.google.com/o/oauth2/auth',
                'token_uri':                  'https://oauth2.googleapis.com/token',
                'redirect_uris':              ['http://localhost', 'urn:ietf:wg:oauth:2.0:oob'],
            }
        }
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        print('  Opening browser for Drive authorisation (one-time only)...')
        creds = flow.run_local_server(port=0, prompt='select_account')
        _save_token(creds)
        print(f'  Token saved to {TOKEN_FILE}')

    return creds


def _save_token(creds):
    """Persist the token to drive_token.json for future runs."""
    with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            'access_token':  creds.token,
            'refresh_token': creds.refresh_token,
        }, f, indent=2)


def upload_trend_history():
    """Replace the Drive copy of trend_history.json with the local version."""
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    if not os.path.exists(TREND_FILE):
        raise FileNotFoundError(f'Local trend_history.json not found: {TREND_FILE}')

    svc    = build('drive', 'v3', credentials=get_creds())
    media  = MediaFileUpload(TREND_FILE, mimetype='application/json', resumable=False)
    result = svc.files().update(fileId=DRIVE_TREND_FILE_ID, media_body=media,
                                fields='id,modifiedTime').execute()
    print(f'  ✓ trend_history.json uploaded to Drive '
          f'(id={DRIVE_TREND_FILE_ID}, modified={result.get("modifiedTime", "?")})')


def test_connection():
    """Verify credentials work and the target Drive file is accessible."""
    from googleapiclient.discovery import build

    svc  = build('drive', 'v3', credentials=get_creds())
    meta = svc.files().get(fileId=DRIVE_TREND_FILE_ID,
                           fields='id,name,modifiedTime').execute()
    print(f'  ✓ Connection OK')
    print(f'    File   : {meta["name"]}')
    print(f'    ID     : {meta["id"]}')
    print(f'    Modified: {meta["modifiedTime"]}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(
        description='Sync local trend_history.json to Google Drive.')
    ap.add_argument('--test', action='store_true',
                    help='Verify credentials without uploading.')
    args = ap.parse_args()

    if args.test:
        print('Testing Drive connection...')
        test_connection()
    else:
        print('Uploading trend_history.json to Drive...')
        upload_trend_history()
