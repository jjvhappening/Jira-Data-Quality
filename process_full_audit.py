"""
Full PLAYER audit processing script.
Loads all paginated Jira result files, applies tier rules, groups by squad/tribe,
runs QC1A (Cochran sample) and QC1B (coverage check), then outputs JSON for
downstream spreadsheet and Slack steps.
"""
import json, sys, math, random, datetime, os
sys.stdout.reconfigure(encoding='utf-8')

# Timestamp of when this audit script started fetching from Jira.
# Carried through to every row so build_reports.py can record it in trend_history.json.
AUDIT_FETCHED_AT = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── File paths from command-line arguments ────────────────────────────────────
# Usage: python process_full_audit.py --audit f1 f2 ... --qc1b g1 g2 ...
# Both flags are required. Files may be full paths or names inside TOOL_DIR.
# If --tool-dir is passed, it overrides the default TOOL_DIR for resolving bare filenames.
#
# Example (bare names, legacy tool-results dir):
#   python process_full_audit.py \
#     --tool-dir "C:\...\.claude\...\tool-results" \
#     --audit mcp-...-p1.txt mcp-...-p2.txt \
#     --qc1b  mcp-...-qc1b-p1.txt
#
# Example (full paths, e.g. after Claude saves direct JSON files):
#   python process_full_audit.py \
#     --audit jira_a.json jira_b.json jira_c.json jira_d.json \
#     --qc1b  qc1b_p1.json qc1b_p2.json

import argparse
_parser = argparse.ArgumentParser(add_help=False)
_parser.add_argument('--tool-dir', default=None)
_parser.add_argument('--audit',  nargs='+', required=True)
_parser.add_argument('--qc1b',   nargs='+', required=True)
_args, _ = _parser.parse_known_args()

TOOL_DIR    = _args.tool_dir or OUT_DIR
AUDIT_FILES = _args.audit
QC1B_FILES  = _args.qc1b

# ─── Squad → Tribe mapping ─────────────────────────────────────────────────────
# Keys are lowercase for case-insensitive matching; supports partial matches
SQUAD_TRIBE = {
    # Player Engagement
    'greyskull': 'Player Engagement', 'grayskull': 'Player Engagement',
    'thundercats': 'Player Engagement',
    'bonus integration': 'Player Engagement',
    'mobius': 'Player Engagement',
    'gamification': 'Player Engagement',
    'sb club migration': 'Player Engagement',
    'player experience - gamification': 'Player Engagement',
    'player experience - growth': 'Player Engagement',
    'engagement integrations': 'Player Engagement',  # possibly stale; kept for legacy issues
    'engagement platform': 'Player Engagement',      # possibly stale; kept for legacy issues
    'loyalty': 'Player Engagement',                  # possibly stale; kept for legacy issues
    'hunch': 'Player Engagement',                    # possibly stale; kept for legacy issues
    # Transact
    'apm experience': 'Transact',
    'card experience': 'Transact',
    'payment experience': 'Transact',
    'payment platform': 'Transact',
    'wallet core': 'Transact',
    'wallet integrations': 'Transact',
    'cross transact': 'Transact',  # appears in native Team field
    # Fraud Prevention
    'fraud engineering': 'Fraud Prevention',
    'fraud': 'Fraud Prevention',
    # Retail/Multichannel
    'retail sports experience': 'Retail/Multichannel',
    'retail gaming experience': 'Retail/Multichannel',
    'retail operations experience': 'Retail/Multichannel',
    'retail platform foundation': 'Retail/Multichannel',
    'retail added value experience': 'Retail/Multichannel',
    'retail terminals platform': 'Retail/Multichannel',
    'rise': 'Retail/Multichannel',
    # Manage
    'player onboarding': 'Manage',
    'player identity': 'Manage',
    'player account': 'Manage',
    'manage platform': 'Manage',
    'player support': 'Manage',
}

# Tribe name suffixes that appear appended to squad names in the native Team field,
# e.g. "Payment Platform - Transact" → strip " - Transact" → "Payment Platform"
_TEAM_TRIBE_SUFFIXES = [
    ' - transact', ' - player engagement', ' - fraud prevention',
    ' - retail/multichannel', ' - retail', ' - manage',
]

def normalise_team_name(team_name):
    """Strip tribe-name suffixes appended to squad names in the native Jira Team field.

    Examples:
        "Payment Platform - Transact"  → "Payment Platform"
        "Card Experience - Transact"   → "Card Experience"
        "Cross Transact"               → "Cross Transact"  (no suffix to strip)
    Returns None if team_name is empty/None.
    """
    if not team_name:
        return None
    normalised = team_name.strip()
    lower = normalised.lower()
    for suffix in _TEAM_TRIBE_SUFFIXES:
        if lower.endswith(suffix):
            normalised = normalised[:len(normalised) - len(suffix)].strip()
            break
    return normalised or None

def squad_to_tribe(squad_name):
    if not squad_name:
        return 'Unassigned'
    lower = squad_name.lower()
    # Exact match
    if lower in SQUAD_TRIBE:
        return SQUAD_TRIBE[lower]
    # Partial match — check if any key is contained in the squad name
    for key, tribe in SQUAD_TRIBE.items():
        if key in lower:
            return tribe
    return 'Unassigned'

# Known tribe names for Tribes Impacted matching
KNOWN_TRIBES = {
    'player engagement', 'transact', 'fraud prevention',
    'retail/multichannel', 'retail', 'manage',
}

def tribes_impacted_values(fields):
    """Extract tribe names from customfield_12109 (Tribes Impacted)."""
    raw = fields.get('customfield_12109') or []
    return [v['value'] for v in raw if isinstance(v, dict) and v.get('value')]

def normalise_tribe(name):
    """Normalise tribe name to canonical form.

    Handles both full and abbreviated forms that appear in the Tribes Impacted
    field (customfield_12109), e.g. "Engagement" (shorthand for "Player Engagement"),
    "Multichannel" (shorthand for "Retail/Multichannel").
    Unknown tribe names are returned as-is and will resolve to 'Unassigned'.
    """
    TRIBE_ALIASES = {
        # Full canonical names
        'player engagement': 'Player Engagement',
        'transact': 'Transact',
        'fraud prevention': 'Fraud Prevention',
        'retail/multichannel': 'Retail/Multichannel',
        'manage': 'Manage',
        # Shorthand / abbreviated forms in the Jira field
        'engagement': 'Player Engagement',
        'multichannel': 'Retail/Multichannel',
        'retail': 'Retail/Multichannel',
    }
    return TRIBE_ALIASES.get(name.lower(), name)

# ─── Tier rules ────────────────────────────────────────────────────────────────
STATUS_TIERS = {
    # Backlog is explicitly Tier 0 only — unscheduled work has no date requirements.
    # The main audit JQL does not exclude Backlog, so these initiatives can appear in
    # the results. Tier 0 means only core identity fields are checked; date fields
    # (Start Date, End of Definition Date, Planned Release Date, Due Date, Actual End Date) are NOT
    # required. This is intentional — Backlog items haven't been scheduled yet.
    'Backlog': [0],
    'To Do': [0], 'In Discovery': [0,1], 'In Definition': [0,1],
    'Awaiting Approval': [0,1,2,3], 'Awaiting Delivery': [0,1,2,3,4],
    'In Planning': [0,1,2,3,4], 'In Delivery': [0,1,2,3,4],
    'Pending Certification': [0,1,2,3,4], 'In Production': [0,1,2,3,4],
    'Rollout / Experimentation': [0,1,2,3,4], 'In Cleanup': [0,1,2,3,4],
    'Done': [0,1,2,3,4,5], 'On Hold': [0,1,2,3,4], 'On hold': [0,1,2,3,4],
}
TIER_FIELDS = {
    # Note: 'summary' (the Jira issue title) was removed — it is enforced by Jira
    # itself and can never legitimately be empty, so including it would always
    # produce a false-negative that inflates the "missing" count.
    0: ['parent','customfield_12121','customfield_12122','customfield_12012',
        'customfield_12178','customfield_12112','customfield_12110','customfield_10709'],
    1: ['customfield_10025'],
    2: ['desc_or_prd'],
    3: ['customfield_12109','customfield_15460'],
    4: ['customfield_12111','customfield_12114','customfield_14447','duedate'],
    5: ['customfield_12180'],
}
FIELD_LABELS = [
    # ('Summary', 'summary') removed — Jira enforces this field; always populated.
    ('Parent',                   'parent'),
    ('Product Lead',             'customfield_12121'),
    ('Engineering Lead',         'customfield_12122'),
    ('Roadmap Priority',         'customfield_12012'),
    ('Impact (PDT)',             'customfield_12178'),
    ('Country (PDT)',            'customfield_12112'),
    ('Areas Impacted',           'customfield_12110'),
    ('Investment Category',      'customfield_10709'),
    ('Start Date',               'customfield_10025'),
    ('Description / PRD',        'desc_or_prd'),
    ('Tribes Impacted',          'customfield_12109'),
    ('End of Definition Date',   'customfield_15460'),
    ('Health Status',            'customfield_12111'),
    ('Planned Release Date',     'customfield_12114'),
    ('Short Status Update',      'customfield_14447'),
    ('Due Date',                 'duedate'),
    ('Actual End Date',          'customfield_12180'),
]
TIER_FOR_FIELD = {fld: t for t, flds in TIER_FIELDS.items() for fld in flds}

def is_pop(val):
    if val is None: return False
    if val == '': return False
    if isinstance(val, list): return len(val) > 0
    if isinstance(val, dict): return bool(val)
    return True

def evaluate(f, status):
    tiers = STATUS_TIERS.get(status, [0])
    req_fields = [fld for t in tiers for fld in TIER_FIELDS[t]]
    field_results = {}
    populated = 0
    for fld in req_fields:
        if fld == 'desc_or_prd':
            v = is_pop(f.get('description')) or is_pop(f.get('customfield_12128'))
        else:
            v = is_pop(f.get(fld))
        field_results[fld] = v
        if v: populated += 1
    score = round(populated / len(req_fields) * 100) if req_fields else 100
    return field_results, score, tiers

JIRA_MAX_RESULTS = 100  # Jira API hard cap; a file with this many results may be truncated

def resolve(fname):
    """Return an absolute path: pass-through if already absolute, else join with TOOL_DIR."""
    return fname if os.path.isabs(fname) else os.path.join(TOOL_DIR, fname)

def load_file(path):
    with open(path, encoding='utf-8') as fh:
        data = json.load(fh)
    # MCP tool-result format: list with a 'text' field containing serialised JSON
    if isinstance(data, list) and data and 'text' in data[0]:
        return json.loads(data[0]['text'])['issues']
    # Plain list of issues (pre-merged format)
    if isinstance(data, list):
        return data
    # Direct Jira response format: {'issues': [...]}
    return data['issues']

# ─── Load all audit data ───────────────────────────────────────────────────────
print('Loading audit data...')
all_issues_raw = []
seen_keys = set()
pagination_warnings = []
for fname in AUDIT_FILES:
    issues = load_file(resolve(fname))
    if len(issues) == JIRA_MAX_RESULTS:
        pagination_warnings.append(fname)
    for i in issues:
        if i['key'] not in seen_keys:
            all_issues_raw.append(i)
            seen_keys.add(i['key'])
if pagination_warnings:
    print(f'  ⚠ PAGINATION REQUIRED — the following files returned exactly {JIRA_MAX_RESULTS} results')
    print(f'    and are likely truncated. Fetch the next page using nextPageToken and add')
    print(f'    the new file to AUDIT_FILES before continuing:')
    for w in pagination_warnings:
        print(f'    • {w}')
    raise SystemExit('Aborted: paginate the above files and re-run.')
print(f'  Total unique audit issues: {len(all_issues_raw)}')

# ─── Apply tier rules ──────────────────────────────────────────────────────────
rows = []
unassigned_squads = set()
squad_attribution_gaps = []  # initiatives with Tribes Impacted but no Squad
for issue in all_issues_raw:
    key = issue['key']
    f = issue['fields']
    status = f['status']['name']
    squad_vals = [v['value'] for v in (f.get('customfield_11250') or [])]
    squad = squad_vals[0] if squad_vals else None

    # ── Fallback: native Jira Team field (customfield_10001) ────────────────
    # Used when the Squad custom field (customfield_11250) is empty.
    # The Team field often contains "<Squad> - <Tribe>" strings; normalise_team_name
    # strips the tribe suffix so the value resolves correctly in SQUAD_TRIBE.
    if not squad:
        team_obj = f.get('customfield_10001')
        if team_obj and isinstance(team_obj, dict) and team_obj.get('name'):
            squad = normalise_team_name(team_obj['name'])

    # ── Tribe attribution: Tribes Impacted first, Squad second ──────────────
    # Primary: use Tribes Impacted (customfield_12109) if populated.
    # Secondary: fall back to Squad → tribe mapping.
    # This means an initiative can belong to multiple tribes (one row per tribe).
    # An initiative with Tribes Impacted but no Squad is flagged as a squad
    # attribution gap — it has tribe visibility but no squad-level owner.
    ti_values = tribes_impacted_values(f)
    if ti_values:
        # Use Tribes Impacted as the primary tribe source
        tribe = normalise_tribe(ti_values[0])  # primary tribe for row grouping
        all_tribes = [normalise_tribe(t) for t in ti_values]
        # Squad attribution gap: Tribes Impacted is set but Squad is not
        if not squad:
            squad_attribution_gaps.append({'key': key, 'summary': f['summary'],
                                            'tribes_impacted': ti_values})
    else:
        # Fall back to squad → tribe mapping
        tribe = squad_to_tribe(squad)
        all_tribes = [tribe] if tribe != 'Unassigned' else []

    if tribe == 'Unassigned' and squad:
        unassigned_squads.add(squad)
    elif tribe == 'Unassigned':
        unassigned_squads.add('(no squad)')

    created_raw = f.get('created') or issue.get('created')
    created = created_raw[:10] if created_raw else None  # YYYY-MM-DD
    # Exclude Retail/Multichannel initiatives in two cases:
    #   1. Created before 2026-04-01 — Retail only adopted Jira in April 2026;
    #      older items predate the process and shouldn't be audited.
    #   2. Status is Done — no value in flagging data quality gaps on completed
    #      work while the team is still new to the process.
    # Initiatives with no created date are also excluded as a safety default.
    RETAIL_CUTOFF = '2026-04-01'
    if tribe == 'Retail/Multichannel' and (
        not created or created < RETAIL_CUTOFF or status == 'Done'
    ):
        continue
    field_results, score, tiers = evaluate(f, status)
    missing = [FIELD_LABELS[i][0] for i, (lbl, fld) in enumerate(FIELD_LABELS)
               if TIER_FOR_FIELD.get(fld) in tiers and not field_results.get(fld, True)]
    # Claude-fixable flags
    fixable = []
    rp = f.get('customfield_12012'); prd = f.get('customfield_12114'); ssu = f.get('customfield_14447')
    if status == 'Backlog' and is_pop(rp): fixable.append('Backlog → To Do promotion')
    if not is_pop(rp) and is_pop(prd): fixable.append('Clear Planned Release Date')
    if not is_pop(ssu) and 4 in tiers: fixable.append('Auto-generate Short Status Update')
    rows.append({'key':key,'summary':f['summary'],'status':status,'squad':squad or 'No squad',
                 'tribe':tribe,'all_tribes':all_tribes,'tribe_source': 'tribes_impacted' if ti_values else 'squad',
                 'score':score,'missing':missing,'fixable':fixable,
                 'fields':field_results,'tiers':tiers,'created':created,
                 'fetched_at':AUDIT_FETCHED_AT})

rows.sort(key=lambda x: x['score'])
print(f'  Audited: {len(rows)} | With gaps: {sum(1 for r in rows if r["missing"])} | Compliant: {sum(1 for r in rows if not r["missing"])}')
if unassigned_squads:
    print(f'  Unassigned squads: {sorted(unassigned_squads)}')
if squad_attribution_gaps:
    print(f'\n  ⚠ Squad attribution gaps ({len(squad_attribution_gaps)}) — Tribes Impacted set but no Squad:')
    for g in squad_attribution_gaps:
        print(f'    {g["key"]}: {g["summary"][:60]} — tribes: {", ".join(g["tribes_impacted"])}')
else:
    print(f'  ✓ No squad attribution gaps')

# ─── Status distribution ───────────────────────────────────────────────────────
status_dist = {}
for r in rows:
    status_dist[r['status']] = status_dist.get(r['status'], 0) + 1
print(f'\nStatus distribution:')
for s, c in sorted(status_dist.items(), key=lambda x: -x[1]):
    print(f'  {s}: {c}')

# ─── Tribe/squad grouping ──────────────────────────────────────────────────────
tribes = {}
for r in rows:
    tribes.setdefault(r['tribe'], {}).setdefault(r['squad'], []).append(r)

print(f'\nTribe/squad breakdown:')
for tribe in sorted(tribes.keys()):
    squads = tribes[tribe]
    total = sum(len(v) for v in squads.values())
    avg = round(sum(r['score'] for sq_rows in squads.values() for r in sq_rows) / total)
    print(f'  {tribe}: {total} initiatives, avg {avg}%')
    for sq, sq_rows in sorted(squads.items()):
        sq_avg = round(sum(r['score'] for r in sq_rows) / len(sq_rows))
        gaps = sum(1 for r in sq_rows if r['missing'])
        print(f'    {sq}: {len(sq_rows)} ({gaps} with gaps, avg {sq_avg}%)')

# ─── Gap summary ──────────────────────────────────────────────────────────────
gap_counts = {}
for r in rows:
    for m in r['missing']:
        gap_counts[m] = gap_counts.get(m, 0) + 1
print(f'\nTop gaps across PLAYER:')
for fld, cnt in sorted(gap_counts.items(), key=lambda x: -x[1])[:10]:
    print(f'  {fld}: {cnt} ({round(cnt/len(rows)*100)}%)')

# ─── QC1A — Cochran sample ────────────────────────────────────────────────────
N = len(rows)
n0 = (1.96**2 * 0.5 * 0.5) / (0.10**2)  # = 96.04
n = math.ceil(n0 / (1 + (n0 - 1) / N))
n = max(8, min(n, N))
print(f'\nQC1A: N={N}, n₀={round(n0)}, sample n={n}')

# Stratified sampling by tier
TIER_GROUPS = {
    'Pre-delivery':  ['To Do','In Discovery','In Definition','Awaiting Approval'],
    'Delivery':      ['Awaiting Delivery','In Planning','In Delivery','Pending Certification','In Production'],
    'Post-delivery': ['Rollout / Experimentation','In Cleanup'],
    'Terminal':      ['Done'],
}
tier_buckets = {tg: [r for r in rows if r['status'] in statuses] for tg, statuses in TIER_GROUPS.items()}
# Proportional allocation
sample = []
remaining = n
tiers_present = {tg: bucket for tg, bucket in tier_buckets.items() if bucket}
for i, (tg, bucket) in enumerate(tiers_present.items()):
    if i == len(tiers_present) - 1:
        alloc = remaining
    else:
        alloc = max(1, round(n * len(bucket) / N))
        remaining -= alloc
    take = min(alloc, len(bucket))
    random.seed(42)
    sample.extend(random.sample(bucket, take))

print(f'  Stratified sample: {len(sample)} initiatives')
for tg, bucket in tiers_present.items():
    in_sample = sum(1 for r in sample if r['status'] in TIER_GROUPS.get(tg,[]))
    print(f'    {tg}: {len(bucket)} in audit, {in_sample} sampled')

# ─── QC1B — Coverage check ────────────────────────────────────────────────────
print(f'\nQC1B: Loading all-PLAYER coverage data...')
qc1b_issues = []
qc1b_seen = set()
for fname in QC1B_FILES:
    path = resolve(fname)
    if not os.path.exists(path):
        print(f'  WARNING: {fname} not found, skipping')
        continue
    for i in load_file(path):
        if i['key'] not in qc1b_seen:
            qc1b_issues.append(i)
            qc1b_seen.add(i['key'])

audit_keys = {r['key'] for r in rows}
qc1b_statuses = {}
for i in qc1b_issues:
    s = i['fields']['status']['name']
    qc1b_statuses[s] = qc1b_statuses.get(s,0)+1

EXPECTED_EXCLUDED = {'Backlog', "Won't Do"}

unexpected = []
expected_backlog = expected_wontdo = expected_done_old = 0
for i in qc1b_issues:
    if i['key'] in audit_keys:
        continue  # In audit — good
    status = i['fields']['status']['name']
    if status == 'Backlog':
        expected_backlog += 1
    elif status == "Won't Do":
        expected_wontdo += 1
    elif status == 'Done':
        # Done initiatives older than 90 days are excluded at the JQL level in Query D
        # (status changed to "Done" after "-90d"), so missing Done items here are expected.
        expected_done_old += 1
    else:
        unexpected.append({'key': i['key'], 'summary': i['fields']['summary'], 'status': status})

print(f'  Total PLAYER initiatives: {len(qc1b_issues)}')
print(f'  In audit: {len(audit_keys)}')
print(f'  Excluded: {len(qc1b_issues)-len(audit_keys)}')
print(f'    Backlog: {expected_backlog}  |  Won\'t Do: {expected_wontdo}  |  Done >90d (excluded by JQL): {expected_done_old}')
if unexpected:
    print(f'  UNEXPECTED EXCLUSIONS ({len(unexpected)}):')
    for u in unexpected:
        print(f'    ✗ {u["key"]}: {u["summary"][:50]} — status: {u["status"]}')
else:
    print(f'  ✓ No unexpected exclusions')

# ─── Save processed audit data for spreadsheet/Slack steps ───────────────────
output = {
    'audit_date': datetime.date.today().isoformat(),
    'total': len(rows),
    'with_gaps': sum(1 for r in rows if r['missing']),
    'compliant': sum(1 for r in rows if not r['missing']),
    'gap_counts': gap_counts,
    'squad_attribution_gaps': squad_attribution_gaps,
    'sample_keys': [r['key'] for r in sample],
    'qc1b': {
        'total_player': len(qc1b_issues),
        'in_audit': len(audit_keys),
        'expected_backlog': expected_backlog,
        'expected_wontdo': expected_wontdo,
        'expected_done_old': expected_done_old,
        'unexpected': unexpected,
    },
    'rows': rows,
    'tribes': {tribe: {sq: sq_rows for sq, sq_rows in squads.items()}
               for tribe, squads in tribes.items()},
}
out_path = os.path.join(OUT_DIR, 'audit_results.json')
with open(out_path, 'w', encoding='utf-8') as fh:
    json.dump(output, fh, ensure_ascii=False, default=str)
print(f'\nSaved audit results → {out_path}')
print('DONE')
