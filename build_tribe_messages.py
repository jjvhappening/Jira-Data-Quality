"""Build tribe lead Slack messages — run metadata loaded dynamically from run_log.json.

Produces tribe_messages.json covering ALL tribes from squad_leads.json.
Tribes with no configured tribe_leads fall back to summary_recipient (Jonathan).
Retail/Multichannel uses an age-bucketed initiative format for Tomislav.
"""
import json, os, sys, urllib.parse
from datetime import datetime, date
sys.stdout.reconfigure(encoding='utf-8')

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(_SCRIPT_DIR, 'audit_results.json'), encoding='utf-8') as fh:
    audit = json.load(fh)
with open(os.path.join(_SCRIPT_DIR, 'squad_leads.json'), encoding='utf-8') as fh:
    leads = json.load(fh)
with open(os.path.join(_SCRIPT_DIR, 'run_log.json'), encoding='utf-8') as fh:
    _run_log = json.load(fh)
with open(os.path.join(_SCRIPT_DIR, 'trend_history.json'), encoding='utf-8') as fh:
    trend_history = json.load(fh)

_latest = _run_log[-1]
RUN_NUMBER = _latest['run']
RUN_DATE   = _latest['date']
RUN_TS     = _latest['timestamp']
print(f'Building tribe messages for Run #{RUN_NUMBER} ({RUN_DATE})')

_policy = leads.get('notification_policy', {})
_DECLINING_TREND_RUNS = _policy.get('declining_trend_runs', 3)


def is_declining_trend(tribe_name, min_consecutive=_DECLINING_TREND_RUNS):
    """Return True if tribe avg_score declined in each of the last min_consecutive runs."""
    scores = [
        r['tribes'][tribe_name]['avg_score']
        for r in trend_history['runs']
        if tribe_name in r.get('tribes', {})
    ]
    if len(scores) < min_consecutive + 1:
        return False
    return all(scores[i] < scores[i - 1] for i in range(-min_consecutive, 0))

_age_hours = (datetime.now() - datetime.fromisoformat(RUN_TS)).total_seconds() / 3600
_staleness = (
    f'\n\n⚠️ _Note: This data was extracted {int(_age_hours)}h ago. '
    f'Fields updated in Jira since then will appear in the next run._'
) if _age_hours > 48 else ''

DASHBOARD = 'https://jjvhappening.github.io/Jira-Data-Quality/'
HANDBOOK = ('https://www.notion.so/superbet/'
            'HANDBOOK-Setting-up-Jira-for-P-T-Roadmapping-318032f852c58057a66ce19cf7a22d9e')


# Normalise raw Jira squad name variants to canonical display names
_SQUAD_NORM = {
    'Thundercats (Promo Journeys)': 'Thundercats',
    'Thundercats (Engagement Tribe)': 'Thundercats',
    'GraySkull (Bonus Platform)': 'GraySkull',
    'Retail Sports Experience (RISE)': 'Retail Sports Experience',
}


def normalise_squad(name):
    return _SQUAD_NORM.get(name, name)


def rag(score):
    if score >= 85: return chr(0x1F7E2)
    elif score >= 70: return chr(0x1F7E1)
    else: return chr(0x1F534)


def squad_jql_url(squad_name):
    jql = (f'project = PLAYER AND issuetype = Initiative '
           f'AND cf[11250] = "{squad_name}" '
           f'AND status NOT IN (Backlog, "Won\'t Do")')
    return 'https://axilis.atlassian.net/issues/?jql=' + urllib.parse.quote(jql)


def tribe_jql_url(squad_names):
    sq_list = ', '.join(f'"{s}"' for s in squad_names)
    jql = (f'project = PLAYER AND issuetype = Initiative '
           f'AND cf[11250] in ({sq_list}) '
           f'AND status NOT IN (Backlog, "Won\'t Do")')
    return 'https://axilis.atlassian.net/issues/?jql=' + urllib.parse.quote(jql)


def _days_ago(created_str, audit_date_str):
    try:
        c = date.fromisoformat(created_str[:10])
        a = date.fromisoformat(audit_date_str)
        return (a - c).days
    except Exception:
        return None


def _build_retail_message(tribe_name, rows, with_gaps, avg_score, top_gaps):
    """Age-bucketed format for Retail/Multichannel (Tomislav only)."""
    cutoff = date(2026, 4, 1)
    in_scope = [r for r in rows if r.get('created') and
                date.fromisoformat(r['created'][:10]) >= cutoff]
    gap_rows = [r for r in in_scope if r['missing']]

    def bucket(r):
        d = _days_ago(r['created'], RUN_DATE)
        if d is None: return 99
        if d < 7: return 0
        if d < 14: return 1
        return 2

    buckets = {0: [], 1: [], 2: []}
    for r in gap_rows:
        buckets[bucket(r)].append(r)

    bucket_labels = {
        0: '\U0001f5d3 Created this week (< 7 days)',
        1: '\U0001f4c5 Created 2 weeks ago (7–13 days)',
        2: '⏳ Created 3+ weeks ago (14+ days)',
    }

    age_blocks = []
    for b in [0, 1, 2]:
        if not buckets[b]:
            continue
        lines = [f'*{bucket_labels[b]}*']
        for r in buckets[b]:
            missing_str = ', '.join(r['missing'][:3])
            lines.append(
                f'• <https://axilis.atlassian.net/browse/{r["key"]}|{r["key"]} — {r["summary"]}>'
                f' — missing: {missing_str}'
            )
        age_blocks.append('\n'.join(lines))

    all_squads = list({r.get('squad') for r in in_scope if r.get('squad')})
    jql_url = tribe_jql_url(all_squads) if all_squads else 'https://axilis.atlassian.net'

    n_gap = len(gap_rows)
    n_total = len(in_scope)
    sc = round(sum(r['score'] for r in in_scope) / n_total) if n_total else 0

    header = (
        f'Hi {{name}} \U0001f44b Here\'s the PLAYER Jira data quality report for '
        f'{tribe_name} (Run #{RUN_NUMBER}).\n\n'
        f'_Note: this report only covers initiatives created from April 2026 onwards — '
        f'older items are excluded as they predate the process. '
        f'You only need to worry about the initiatives listed below._\n\n'
        f'{n_gap} initiative{"s" if n_gap != 1 else ""} need{"" if n_gap != 1 else "s"} attention. '
        f'Average compliance score: {sc}% {rag(sc)} \U0001f4ca\n\n'
        f'*Initiatives requiring attention — by age:*\n\n'
    )
    footer = (
        f'\n\n\U0001f517 <{jql_url}|View all {tribe_name} initiatives in Jira>\n\n'
        f'This is a new process and we\'re actively improving it — '
        f'feedback and ideas are very welcome \U0001f64f'
    )
    if not age_blocks:
        return (header.rstrip('\n\n') +
                f'\n\nNo initiatives with missing fields this run. \U0001f389' + footer)
    return header + '\n\n'.join(age_blocks) + footer


# Group audit rows by tribe
tribe_rows = {}
for r in audit['rows']:
    t = r.get('tribe') or 'Unassigned'
    tribe_rows.setdefault(t, []).append(r)

messages = []
fallback_tribes = []

for tribe_name, tribe_data in leads['tribes'].items():
    tribe_leads = tribe_data.get('tribe_leads', [])
    rows = tribe_rows.get(tribe_name, [])

    # Recipients: tribe leads, or fallback to Jonathan
    if tribe_leads:
        recipients = [
            {'name': tl['name'].split()[0], 'slack_id': tl['slack_id'], 'fallback': False}
            for tl in tribe_leads
        ]
    else:
        recipients = [{
            'name': leads['summary_recipient']['name'].split()[0],
            'slack_id': leads['summary_recipient']['slack_id'],
            'fallback': True,
        }]
        fallback_tribes.append(tribe_name)

    total = len(rows)
    with_gaps = sum(1 for r in rows if r['missing'])
    avg_score = round(sum(r['score'] for r in rows) / total) if total else 0

    # Per-squad breakdown (normalised squad names to merge variants)
    squad_stats = {}
    for r in rows:
        raw_sq = r.get('squad') or 'No squad'
        sq = normalise_squad(raw_sq)
        if sq not in squad_stats:
            squad_stats[sq] = {'total': 0, 'gaps': 0, 'scores': [], 'raw_names': set()}
        squad_stats[sq]['total'] += 1
        squad_stats[sq]['raw_names'].add(raw_sq)
        if r['missing']:
            squad_stats[sq]['gaps'] += 1
        squad_stats[sq]['scores'].append(r['score'])

    # Top missing fields
    gap_counts = {}
    for r in rows:
        for m in r['missing']:
            gap_counts[m] = gap_counts.get(m, 0) + 1
    top_gaps = sorted(gap_counts.items(), key=lambda x: -x[1])[:6]

    # Build message body
    is_retail = tribe_name == 'Retail/Multichannel'

    if total == 0:
        body = (
            f'Hi {{name}} \U0001f44b Great news for {tribe_name} — Run #{RUN_NUMBER}.\n\n'
            f'No in-scope initiatives this run — nothing to action! \U0001f389'
        )
    elif is_retail:
        body = _build_retail_message(tribe_name, rows, with_gaps, avg_score, top_gaps)
    elif with_gaps == 0:
        sq_lines = []
        for sq, s in sorted(squad_stats.items(), key=lambda x: -x[1]['total']):
            sq_avg = round(sum(s['scores']) / s['total']) if s['total'] else 0
            sq_lines.append(f'• {sq}: 0/{s["total"]} with gaps | {sq_avg}% {rag(sq_avg)}')
        body = (
            f'Hi {{name}} \U0001f44b Here\'s the {tribe_name} tribe summary from Run #{RUN_NUMBER} '
            f'of the PLAYER Jira data quality audit.\n\n'
            f'{total} initiatives audited | Average score: {avg_score}% {rag(avg_score)} | '
            f'0 with gaps \U0001f389\n\n'
            f'Squad breakdown:\n' + '\n'.join(sq_lines) + '\n\n'
            f'Each squad EM has been notified individually with their specific gap lists.\n\n'
            f':bar_chart: <{DASHBOARD}|PLAYER Data Quality Dashboard>\n\n'
            f'This is a new process and we\'re actively improving it — feedback on format or coverage is very welcome.'
        )
    else:
        sq_lines = []
        for sq, s in sorted(squad_stats.items(), key=lambda x: -x[1]['total']):
            sq_avg = round(sum(s['scores']) / s['total']) if s['total'] else 0
            raw_names = list(s['raw_names'])
            jql_url = (squad_jql_url(raw_names[0]) if len(raw_names) == 1
                       else tribe_jql_url(raw_names))
            if s['gaps'] > 0:
                sq_lines.append(
                    f'• {sq}: {s["gaps"]}/{s["total"]} with gaps | {sq_avg}% {rag(sq_avg)}'
                    f' — <{jql_url}|View initiatives>'
                )
            else:
                sq_lines.append(f'• {sq}: 0/{s["total"]} with gaps | {sq_avg}% {rag(sq_avg)}')
        gap_lines = '\n'.join(
            f'• {f}: {c} initiative{"s" if c > 1 else ""}' for f, c in top_gaps
        )
        body = (
            f'Hi {{name}} \U0001f44b Here\'s the {tribe_name} tribe summary from Run #{RUN_NUMBER} '
            f'of the PLAYER Jira data quality audit.\n\n'
            f'{total} initiatives audited | Average score: {avg_score}% {rag(avg_score)} | '
            f'{with_gaps} with gaps\n\n'
            f'Squad breakdown:\n' + '\n'.join(sq_lines) + '\n\n'
            f'Top missing fields across the tribe:\n{gap_lines}\n\n'
            f'Each squad EM has been notified individually with their specific gap lists.\n\n'
            f':bar_chart: <{DASHBOARD}|PLAYER Data Quality Dashboard>\n\n'
            f'This is a new process and we\'re actively improving it — feedback on format or coverage is very welcome.'
        )

    declining = is_declining_trend(tribe_name)
    suppressed = not declining
    if suppressed:
        recent = [
            r['tribes'].get(tribe_name, {}).get('avg_score')
            for r in trend_history['runs']
            if tribe_name in r.get('tribes', {})
        ][-(_DECLINING_TREND_RUNS + 1):]
        suppress_reason = (
            f'no sustained decline over last {_DECLINING_TREND_RUNS} runs '
            f'(recent scores: {recent})'
        )
    else:
        suppress_reason = ''

    for rec in recipients:
        prefix = (
            f'⚠️ No tribe lead is configured for {tribe_name} — '
            f'sending to you as fallback.\n\n'
        ) if rec['fallback'] else ''
        msg = (prefix + body.format(name=rec['name'])) + _staleness
        messages.append({
            'slack_id': rec['slack_id'],
            'name': rec['name'],
            'tribe': tribe_name,
            'message': msg,
            'total': total,
            'gaps': with_gaps,
            'avg': avg_score,
            'fallback': rec['fallback'],
            'suppressed': suppressed,
            'suppress_reason': suppress_reason,
        })


to_send = [m for m in messages if not m['suppressed']]
suppressed = [m for m in messages if m['suppressed']]
print(f'Messages to send: {len(to_send)} | Suppressed: {len(suppressed)} (no sustained decline)')
if fallback_tribes:
    print(f'Fallback tribes (no tribe lead configured): {fallback_tribes}')
print()
for m in to_send:
    fb = ' [FALLBACK]' if m.get('fallback') else ''
    print(f'  ✅ {m["name"]} ({m["tribe"]}){fb}: {m["total"]} initiatives, '
          f'{m["gaps"]} gaps, {m["avg"]}% avg')
for m in suppressed:
    print(f'  ⏸️  {m["name"]} ({m["tribe"]}): suppressed — {m["suppress_reason"]}')

with open(os.path.join(_SCRIPT_DIR, 'tribe_messages.json'), 'w', encoding='utf-8') as fh:
    json.dump(messages, fh, ensure_ascii=False, indent=2)
print('Saved tribe_messages.json')
