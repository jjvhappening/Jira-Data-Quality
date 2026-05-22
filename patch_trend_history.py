"""One-off: normalise squad name variants in trend_history.json across all historical runs."""
import json, os

SQUAD_NORM = {
    'Thundercats (Promo Journeys)': 'Thundercats',
    'Thundercats (Engagement Tribe)': 'Thundercats',
    'GraySkull (Bonus Platform)': 'GraySkull',
    'Retail Sports Experience (RISE)': 'Retail Sports Experience',
}

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'trend_history.json')
with open(path, encoding='utf-8') as f:
    history = json.load(f)

def merge_squads(squads_dict):
    """Merge squad entries whose names normalise to the same canonical name."""
    merged = {}
    for raw_name, data in squads_dict.items():
        canon = SQUAD_NORM.get(raw_name, raw_name)
        if canon not in merged:
            merged[canon] = data
        else:
            # Merge: combine totals, re-average score, merge gap_counts
            existing = merged[canon]
            total_new = existing['total'] + data['total']
            existing['avg_score'] = round(
                (existing['avg_score'] * existing['total'] + data['avg_score'] * data['total'])
                / total_new
            )
            existing['total'] = total_new
            existing['with_gaps'] = existing.get('with_gaps', 0) + data.get('with_gaps', 0)
            for field, count in data.get('gap_counts', {}).items():
                existing.setdefault('gap_counts', {})[field] = (
                    existing['gap_counts'].get(field, 0) + count
                )
            # Merge top_offenders (deduplicate by key, keep combined top 5)
            seen = {r['key'] for r in existing.get('top_offenders', [])}
            for r in data.get('top_offenders', []):
                if r['key'] not in seen:
                    existing.setdefault('top_offenders', []).append(r)
                    seen.add(r['key'])
            existing['top_offenders'] = sorted(
                existing.get('top_offenders', []),
                key=lambda r: r.get('missing_count', 0), reverse=True
            )[:5]
    return merged

changes = []
for run in history['runs']:
    for tribe_name, tribe_data in run.get('tribes', {}).items():
        if 'squads' in tribe_data:
            before = set(tribe_data['squads'].keys())
            tribe_data['squads'] = merge_squads(tribe_data['squads'])
            after = set(tribe_data['squads'].keys())
            removed = before - after
            if removed:
                changes.append(f'  Run #{run["run"]} {tribe_name}: merged {removed} -> {after}')

if changes:
    print('Changes made:')
    for c in changes:
        print(c)
else:
    print('No squad name variants found to merge.')

with open(path, 'w', encoding='utf-8') as f:
    json.dump(history, f, ensure_ascii=False, indent=2)
print('trend_history.json patched.')
