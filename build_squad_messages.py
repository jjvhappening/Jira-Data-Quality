"""Build squad EM Slack messages — run metadata loaded dynamically from run_log.json."""
import json, os, sys, urllib.parse
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(_SCRIPT_DIR, 'audit_results.json'), encoding='utf-8') as fh:
    audit = json.load(fh)
with open(os.path.join(_SCRIPT_DIR, 'squad_leads.json'), encoding='utf-8') as fh:
    leads = json.load(fh)

# ── Dynamic run metadata from run_log.json ────────────────────────────────────
with open(os.path.join(_SCRIPT_DIR, 'run_log.json'), encoding='utf-8') as fh:
    _run_log = json.load(fh)
_latest = _run_log[-1]
RUN_NUMBER = _latest['run']
RUN_DATE   = _latest['date']
RUN_TS     = _latest['timestamp']
print(f'Building messages for Run #{RUN_NUMBER} ({RUN_DATE})')

# Staleness footer: appended to every message when data is >48h old.
_age_hours = (datetime.now() - datetime.fromisoformat(RUN_TS)).total_seconds() / 3600
_staleness = (
    f'\n\n⚠️ _Note: This data was extracted {int(_age_hours)}h ago. '
    f'Fields updated in Jira since then will appear in the next run._'
) if _age_hours > 48 else ''
DASHBOARD = 'https://jjvhappening.github.io/Jira-Data-Quality/'
HANDBOOK = 'https://www.notion.so/superbet/HANDBOOK-Setting-up-Jira-for-P-T-Roadmapping-318032f852c58057a66ce19cf7a22d9e'

SQUAD_MAP = {
    'GraySkull': 'GraySkull', 'GraySkull (Bonus Platform)': 'GraySkull',
    'Thundercats': 'Thundercats', 'Thundercats (Promo Journeys)': 'Thundercats',
    'Thundercats (Engagement Tribe)': 'Thundercats',
    'Bonus Integration': 'Bonus Integration', 'Mobius': 'Mobius',
    'Gamification': 'Gamification', 'Sb Club Migration': 'Sb Club Migration',
    'Player Experience - Gamification': 'Player Experience - Gamification',
    'Player Experience - Growth': 'Player Experience - Growth',
    'Hunch (F2P)': 'Hunch (F2P)',
    'APM Experience': 'APM Experience', 'Card Experience': 'Card Experience',
    'Payment Experience': 'Payment Experience', 'Payment Platform': 'Payment Platform',
    'Wallet Core': 'Wallet Core', 'Wallet Integrations': 'Wallet Integrations',
    'Fraud Engineering': 'Fraud Engineering',
    'Retail Sports Experience': 'Retail Sports Experience (RISE)',
    'Retail Sports Experience (RISE)': 'Retail Sports Experience (RISE)',
    'Retail Gaming Experience': 'Retail Gaming Experience',
    'Retail Operations Experience': 'Retail Operations Experience',
    'Retail Platform Foundation': 'Retail Platform Foundation',
    'Retail Added Value Experience': 'Retail Added Value Experience',
    'Retail Terminals Platform': 'Retail Terminals Platform',
    'Player Onboarding': 'Player Onboarding', 'Player Identity': 'Player Identity',
    'Player Account': 'Player Account', 'Manage Platform': 'Manage Platform',
    'Player Support': 'Player Support',
}

RO_LABELS = {
    'Player Identity': [
        {'key': 'PLAYER-1299', 'release': '2026-06-15', 'note': 'release date 15 Jun, all child epics Done — initiative needs closing out'},
        {'key': 'PLAYER-172', 'release': '2026-06-01', 'note': 'release date 1 Jun, all child epics Done — initiative needs closing out'},
    ],
    'Player Account': [
        {'key': 'PLAYER-220', 'release': '2026-03-31', 'note': 'release date 31 Mar, all child epics Done — initiative needs closing out'},
        {'key': 'PLAYER-218', 'release': '2026-03-31', 'note': 'release date 31 Mar, work complete — initiative not closed'},
    ],
}

def rag(score):
    if score >= 85: return chr(0x1F7E2)  # green
    elif score >= 70: return chr(0x1F7E1)  # yellow
    else: return chr(0x1F534)  # red

def field_jql_link(keys):
    key_list = ', '.join(keys)
    jql = 'project = PLAYER AND issuetype = Initiative AND issueKey in ({})'.format(key_list)
    return 'https://axilis.atlassian.net/issues/?jql=' + urllib.parse.quote(jql)

def jql_link(squad_jira_names):
    sq_list = ', '.join('"{}"'.format(s) for s in squad_jira_names)
    if len(squad_jira_names) == 1:
        jql = 'project = PLAYER AND issuetype = Initiative AND cf[11250] = "{}" AND status NOT IN (Backlog, "Won\'t Do")'.format(squad_jira_names[0])
    else:
        jql = 'project = PLAYER AND issuetype = Initiative AND cf[11250] in ({}) AND status NOT IN (Backlog, "Won\'t Do")'.format(sq_list)
    return 'https://axilis.atlassian.net/issues/?jql=' + urllib.parse.quote(jql)

# Group rows by squad_leads key
squad_rows = {}
for r in audit['rows']:
    sq_jira = r['squad'] if r['squad'] != 'No squad' else None
    sq_key = SQUAD_MAP.get(sq_jira) if sq_jira else None
    if sq_key:
        squad_rows.setdefault(sq_key, []).append(r)

# Build per-EM data
em_data = {}
skipped_squads = []

for tribe_name, tribe_data in leads['tribes'].items():
    retail_suppressed = tribe_data.get('_squad_messages') == 'suppressed'
    for sq_key, sq_info in tribe_data.get('squads', {}).items():
        em = sq_info.get('engineering_manager')
        if retail_suppressed:
            continue
        if not em:
            skipped_squads.append(sq_key + ' (null EM)')
            continue
        slack_id = em['slack_id']
        if slack_id not in em_data:
            em_data[slack_id] = {
                'name': em['name'].split()[0],
                'full_name': em['name'],
                'squad_keys': [],
                'rows': [],
                'squad_jira_names': set(),
            }
        em_data[slack_id]['squad_keys'].append(sq_key)
        em_data[slack_id]['rows'].extend(squad_rows.get(sq_key, []))
        for r in squad_rows.get(sq_key, []):
            if r['squad'] != 'No squad':
                em_data[slack_id]['squad_jira_names'].add(r['squad'])

messages = []
for slack_id, data in em_data.items():
    name = data['name']
    rows = data['rows']
    sq_keys = data['squad_keys']
    sq_jira_names = list(data['squad_jira_names'])

    if len(sq_keys) == 1:
        sq_display = sq_keys[0]
    elif len(sq_keys) == 2:
        sq_display = ' & '.join(sq_keys)
    else:
        sq_display = ', '.join(sq_keys)

    ro_for_squad = []
    for sk in sq_keys:
        ro_for_squad.extend(RO_LABELS.get(sk, []))

    if not rows and not ro_for_squad:
        continue

    total = len(rows)
    with_gaps = sum(1 for r in rows if r['missing'])
    avg_score = round(sum(r['score'] for r in rows) / total) if total else 0

    gap_counts = {}
    gap_keys = {}
    for r in rows:
        for m in r['missing']:
            gap_counts[m] = gap_counts.get(m, 0) + 1
            gap_keys.setdefault(m, []).append(r['key'])
    top_gaps = sorted(gap_counts.items(), key=lambda x: -x[1])[:6]

    has_eod = any(f == 'End of Definition Date' for f, _ in top_gaps)
    has_ssu = any(f == 'Short Status Update' for f, _ in top_gaps)
    show_hint = has_eod or has_ssu

    jql_url = jql_link(sq_jira_names) if sq_jira_names else 'https://axilis.atlassian.net'

    if with_gaps == 0 and not ro_for_squad:
        msg = (
            'Hi {} {} Great news for {} — Run #{}.\n\n'
            'All {} of your squad\'s PLAYER initiatives in Jira are fully compliant — no missing fields! \U0001f389\n\n'
            'Keep it up, and thanks for staying on top of this.'
        ).format(name, '\U0001f44b', sq_display, RUN_NUMBER, total)

    elif with_gaps == 0 and ro_for_squad:
        ro_lines = '\n'.join('• {} — {}'.format(x['key'], x['note']) for x in ro_for_squad)
        msg = (
            'Hi {} {} Here\'s a data quality update for {} — Run #{}.\n\n'
            'All {} of your squad\'s PLAYER initiatives are field-compliant — no missing fields! \U0001f389\n\n'
            '⚠️ *From RO Migration programme audit:*\n{}\n'
            '_Action: close these initiatives in Jira._\n\n'
            'This is a new process and we\'re actively improving it — feedback and ideas are very welcome.'
        ).format(name, '\U0001f44b', sq_display, RUN_NUMBER, total, ro_lines)

    else:
        gap_lines = '\n'.join(
            '• <{}|{}: {} initiative{}>'.format(
                field_jql_link(gap_keys[f]), f, c, 's' if c > 1 else ''
            )
            for f, c in top_gaps
        )
        ro_block = ''
        if ro_for_squad:
            ro_items = '\n'.join('• {} — {}'.format(x['key'], x['note']) for x in ro_for_squad)
            ro_block = '\n⚠️ *From RO Migration programme audit:*\n{}\n_Action: close these initiatives in Jira._\n'.format(ro_items)
        hint_line = ''
        if show_hint:
            hint_line = '\n_\U0001f4a1 End of Definition Date = the date Discovery actually ended. Short Status Update = 1–2 sentence current state summary._'
        msg = (
            'Hi {} {} Here\'s a data quality update for {}\'s PLAYER initiatives in Jira (Run #{}).\n\n'
            '{} initiative{} have missing fields. Average compliance score: {}% {}\n\n'
            '{}\n'
            '{}'
            '<{}|View your initiatives here>\n\n'
            '_Please update these fields at your earliest convenience. See the <{}|P&T Jira Roadmapping Handbook> for guidance on what each field means._'
            '{}\n\n'
            ':bar_chart: <{}|PLAYER Data Quality Dashboard>\n\n'
            'This is a new process and we\'re actively improving it — feedback and ideas are very welcome.'
        ).format(
            name, '\U0001f44b', sq_display, RUN_NUMBER,
            with_gaps, 's' if with_gaps != 1 else '',
            avg_score, rag(avg_score),
            gap_lines,
            ro_block + '\n' if ro_block else '\n',
            jql_url,
            HANDBOOK,
            hint_line,
            DASHBOARD,
        )

    msg += _staleness

    messages.append({
        'slack_id': slack_id,
        'name': data['full_name'],
        'squad': sq_display,
        'message': msg,
        'total': total,
        'gaps': with_gaps,
        'avg': avg_score,
    })

print('Messages to send: {}'.format(len(messages)))
print('Skipped (null EM): {}'.format(skipped_squads))
print()
for m in messages:
    print('  {} ({}): {} initiatives, {} gaps, {}% avg'.format(
        m['name'], m['squad'], m['total'], m['gaps'], m['avg']))

with open('squad_messages.json', 'w', encoding='utf-8') as fh:
    json.dump(messages, fh, ensure_ascii=False, indent=2)
print('Saved squad_messages.json')
