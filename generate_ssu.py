"""
generate_ssu.py — Read re-fetched Jira data, identify initiatives still
needing Short Status Update, generate proposed SSU text, and write
fix_preview.json for review and application.
"""
import json, sys, re, os
sys.stdout.reconfigure(encoding='utf-8')

TOOL_RESULTS_DIR = r'C:\Users\JonathanVince\.claude\projects\C--Users-JonathanVince-Documents-Claude-Projects-Jira-Data-Quality\b91203ba-58c0-4f75-9d2e-f94abb7f4863\tool-results'
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

BATCH1 = 'mcp-b846195e-69b9-4ade-88d4-18e6a3f23890-searchJiraIssuesUsingJql-1777886279841.txt'
BATCH2 = 'mcp-b846195e-69b9-4ade-88d4-18e6a3f23890-searchJiraIssuesUsingJql-1777886284981.txt'

STATUS_PHRASE = {
    'In Delivery':               'currently in active delivery',
    'In Planning':               'in the planning phase',
    'In Discovery':              'in discovery',
    'In Definition':             'in definition',
    'Awaiting Delivery':         'discovery complete and awaiting delivery start',
    'Awaiting Approval':         'awaiting approval to proceed',
    'Pending Certification':     'in delivery and pending certification',
    'In Production':             'in production / live',
    'Rollout / Experimentation': 'in rollout and experimentation',
    'In Cleanup':                'in cleanup / post-delivery',
    'On Hold':                   'currently on hold',
    'On hold':                   'currently on hold',
    'Done':                      'complete',
    'To Do':                     'scheduled and not yet started',
}

def load_issues(fname):
    path = os.path.join(TOOL_RESULTS_DIR, fname)
    with open(path, encoding='utf-8') as fh:
        raw = json.load(fh)
    # Unwrap MCP list wrapper if present
    if isinstance(raw, list) and raw and 'text' in raw[0]:
        raw = json.loads(raw[0]['text'])
    # Format: {"issues": {"nodes": [...], "totalCount": N}}
    issues_val = raw.get('issues', raw)
    if isinstance(issues_val, dict):
        return issues_val.get('nodes', [])
    if isinstance(issues_val, list):
        return issues_val
    return []

def get_field(issue, field_id):
    fields = issue.get('fields') or issue.get('fieldValues') or {}
    return fields.get(field_id)

def get_text(val):
    """Extract clean plain text from ADF, plain string, or None."""
    if not val:
        return ''
    if isinstance(val, str):
        text = val
    elif isinstance(val, dict):
        # ADF document — walk content tree collecting text nodes
        parts = []
        def walk(node):
            if isinstance(node, dict):
                if node.get('type') == 'text':
                    parts.append(node.get('text', ''))
                for child in node.get('content', []):
                    walk(child)
        walk(val)
        text = ' '.join(parts)
    else:
        return ''
    # Strip markdown headings, bold, italic
    text = re.sub(r'#+\s*', '', text)
    text = re.sub(r'\*{1,2}(.*?)\*{1,2}', r'\1', text)
    text = re.sub(r'_{1,2}(.*?)_{1,2}', r'\1', text)
    # Strip URLs and smart link markup
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'<custom[^>]*>.*?</custom>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '', text)
    # Strip bracket link artifacts (e.g. [.] or [text] left after URL removal)
    text = re.sub(r'\[[^\]]{0,120}\]', '', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def first_useful_sentence(text, min_len=25, max_len=180):
    """Return the first sentence that looks like real prose (not a heading stub)."""
    if not text:
        return ''
    # Split on sentence-ending punctuation
    sentences = re.split(r'(?<=[.!?])\s+', text)
    for s in sentences:
        s = s.strip()
        # Skip very short fragments, list bullets, or pure punctuation
        if len(s) < min_len:
            continue
        if s.startswith(('What', 'Why', 'How', 'Note', 'TODO', '-', '*', '•', '[')):
            continue
        # Skip "please check" phrases and heading stubs ending with colon
        if re.search(r'\bplease check\b', s, re.IGNORECASE):
            continue
        if s.rstrip().endswith(':'):
            continue
        return s[:max_len]
    return ''

def get_squad(issue):
    f = (issue.get('fields') or {})
    vals = f.get('customfield_11250') or []
    if vals and isinstance(vals, list):
        return vals[0].get('value', '') if isinstance(vals[0], dict) else str(vals[0])
    return ''

def generate_ssu(summary, status, description_text, squad):
    phrase = STATUS_PHRASE.get(status, f'in {status.lower()} status')

    # Strip emoji and brackets from summary for cleaner prose
    clean = re.sub(r'[\U00010000-\U0010ffff]', '', summary).strip()
    clean = re.sub(r'^\[.*?\]\s*', '', clean).strip()
    clean = re.sub(r'\s+', ' ', clean)

    # Done / terminal statuses need no description context
    terminal = status in ('Done', 'In Production', 'Rollout / Experimentation', 'In Cleanup')
    hint = '' if terminal else first_useful_sentence(description_text) if description_text else ''

    # Only use hint if it reads like a clean sentence (no residual bullets/structure words)
    if hint and re.search(r'\*|#|\bWhat\b|\bWhy\b|\bHow\b|\bNote\b', hint):
        hint = ''

    if hint:
        ssu = f"{clean} is {phrase}. {hint}."
    else:
        ssu = f"{clean} is {phrase}."

    # Cap at 255 chars (Jira field limit for short text)
    return ssu[:255]

# ── Load both batches ─────────────────────────────────────────────────────────
print('Loading batch 1...')
b1 = load_issues(BATCH1)
print(f'  {len(b1)} issues')
print('Loading batch 2...')
b2 = load_issues(BATCH2)
print(f'  {len(b2)} issues')

all_issues = b1 + b2
print(f'Total loaded: {len(all_issues)}')

# ── Build fix plan ────────────────────────────────────────────────────────────
still_empty = []
already_populated = []

for issue in all_issues:
    key = issue.get('key', '')
    f = issue.get('fields') or {}
    summary = f.get('summary', '')
    status_obj = f.get('status') or {}
    status = status_obj.get('name', '') if isinstance(status_obj, dict) else str(status_obj)
    current_ssu = get_text(f.get('customfield_14447'))
    description = get_text(f.get('description'))
    squad = get_squad(issue)

    if current_ssu:
        already_populated.append(key)
    else:
        proposed = generate_ssu(summary, status, description, squad)
        still_empty.append({
            'key': key,
            'summary': summary,
            'status': status,
            'squad': squad,
            'proposed_ssu': proposed,
        })

print(f'\nStill need SSU:    {len(still_empty)}')
print(f'Already populated: {len(already_populated)} (skipping)')
if already_populated:
    print(f'  Populated since audit: {", ".join(already_populated)}')

# ── Write preview file ────────────────────────────────────────────────────────
out_path = os.path.join(OUT_DIR, 'fix_preview.json')
with open(out_path, 'w', encoding='utf-8') as fh:
    json.dump({'fixes': still_empty, 'skipped': already_populated}, fh,
              indent=2, ensure_ascii=False)
print(f'\nFix preview written -> {out_path}')

# ── Print sample (first 5) ────────────────────────────────────────────────────
print('\n=== SAMPLE (first 5 proposed SSUs) ===')
for item in still_empty[:5]:
    print(f"\n{item['key']} — {item['summary'][:60]}")
    print(f"  Status: {item['status']}  |  Squad: {item['squad']}")
    print(f"  Proposed SSU: {item['proposed_ssu']}")
print('\nDONE')
