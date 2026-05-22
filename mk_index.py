#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re, os, sys

BASE = r'C:\Users\JonVince\Documents\Claude\Projects\Jira Data Quality'
src = os.path.join(BASE, 'gas', 'gas_dashboard.html')
dst = os.path.join(BASE, 'index.html')

with open(src, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Replace GAS scriptlet injection block (7 lines, identified by unique <?!= ... ?> tag)
content = re.sub(
    r'// [^\n]+ Injected data[^\n]*\n'
    r'const _D = <\?!= DATA_JSON \?>;\n'
    r'const TRIBES[^\n]*\n'
    r'const SQUADS[^\n]*\n'
    r'const RUNS[^\n]*\n'
    r'const GAP_FIELDS[^\n]*\n'
    r'const OFFENDERS[^\n]*\n',
    '// -- Data globals (populated async after fetch from GitHub) ---------------------\nlet _D, TRIBES, SQUADS, RUNS, GAP_FIELDS, OFFENDERS;\n',
    content
)
assert '<?!= DATA_JSON ?>' not in content, 'ABORT: scriptlet replacement failed'

# 2. Add activeGapField to state declarations
assert content.count('let trendChart, gapChart;\n') == 1, 'ABORT: trendChart line not found uniquely'
content = content.replace(
    'let trendChart, gapChart;\n',
    'let trendChart, gapChart;\nlet activeGapField = null;\n',
    1
)

# 3. Update footer
assert 'Powered by Google Apps Script' in content, 'ABORT: footer text not found'
content = content.replace('Powered by Google Apps Script', 'Hosted on GitHub Pages')

# 4. Replace init block + insert computeDashboardData, selectGapField, async init
old4_pattern = r'// [^\n]+ Initialise [^\n]*\nrenderHeader\(\);\ninitRunFilter\(\);\nrenderAll\(\);\n'
assert re.search(old4_pattern, content), 'ABORT: init block not found'

NEW_CODE = """// -- Data transform: client-side port of Code.js computeDashboardData() ----------
function computeDashboardData(history) {
  var runs = history.runs;
  var TRIBE_COLORS = {
    'Player Engagement':'#6a1b9a','Transact':'#1565C0',
    'Fraud Prevention':'#e65100','Retail/Multichannel':'#795548',
    'Manage':'#2e7d32','Unassigned':'#757575',
  };
  var MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  var runsData = runs.map(function(r) {
    var d = new Date(r.date);
    return { run:r.run, label:'Run '+r.run,
             date:d.getDate()+' '+MONTHS[d.getMonth()]+' '+d.getFullYear(),
             month:MONTHS[d.getMonth()], score:r.avg_score, total:r.total,
             compliant:r.compliant, gaps:r.with_gaps, data_fetched_at:r.data_fetched_at||null };
  });
  var TRIBE_ORDER = ['Player Engagement','Transact','Fraud Prevention','Retail/Multichannel','Manage'];
  var tribeSet = {};
  runs.forEach(function(r) { Object.keys(r.tribes).forEach(function(t) { tribeSet[t]=true; }); });
  var tribeNames = TRIBE_ORDER.filter(function(t) { return tribeSet[t]; });
  var tribesData = tribeNames.map(function(name) {
    return {
      name:name, color:TRIBE_COLORS[name]||'#607d8b', volatile:name==='Retail/Multichannel',
      scores:    runs.map(function(r) { return r.tribes[name] ? r.tribes[name].avg_score : null; }),
      totals:    runs.map(function(r) { return r.tribes[name] ? r.tribes[name].total     : 0; }),
      compliant: runs.map(function(r) { return r.tribes[name] ? r.tribes[name].compliant : 0; }),
      gapCounts: runs.map(function(r) { return r.tribes[name] ? (r.tribes[name].gap_counts||{}) : {}; }),
    };
  });
  var squadToTribe = {};
  runs.forEach(function(r) {
    Object.keys(r.tribes).forEach(function(tribeName) {
      var tribe = r.tribes[tribeName];
      if (tribe && tribe.squads) Object.keys(tribe.squads).forEach(function(sq) {
        if (!squadToTribe[sq]) squadToTribe[sq] = tribeName;
      });
    });
  });
  var squadsData = Object.keys(squadToTribe).sort().map(function(sq) {
    var tn = squadToTribe[sq];
    return [sq, tn,
      runs.map(function(r) { var t=r.tribes[tn]; return (t&&t.squads&&t.squads[sq])?t.squads[sq].avg_score:null; }),
      runs.map(function(r) { var t=r.tribes[tn]; return (t&&t.squads&&t.squads[sq])?t.squads[sq].total:0; }),
      runs.map(function(r) { var t=r.tribes[tn]; return (t&&t.squads&&t.squads[sq])?(t.squads[sq].gap_counts||{}):{} }),
      runs.map(function(r) { var t=r.tribes[tn]; return (!t||!t.squads||!t.squads[sq])?[]:(t.squads[sq].top_offenders||[]); }),
    ];
  });
  var latestRun = runs[runs.length-1]||{gap_counts:{}};
  var allFieldNames = {};
  runs.forEach(function(r) { Object.keys(r.gap_counts||{}).forEach(function(f) { allFieldNames[f]=true; }); });
  var sortedFields = Object.keys(allFieldNames).sort(function(a,b) {
    return (latestRun.gap_counts[b]||0)-(latestRun.gap_counts[a]||0);
  }).slice(0,10);
  var gapFields = sortedFields.map(function(f) { return [f, runs.map(function(r) { return r.gap_counts[f]||0; })]; });
  var offenders = runs.map(function(run) {
    return (run.top_offenders||[]).map(function(o) { return [o.key,o.summary,o.squad,o.tribe,o.score,o.missing]; });
  });
  return {tribes:tribesData, squads:squadsData, runs:runsData, gap_fields:gapFields, offenders:offenders};
}

function selectGapField(f) {
  activeGapField = activeGapField===f ? null : f;
  renderGapChart();
}

// -- Initialise: fetch trend_history.json from GitHub, then render -----------------
(async function init() {
  var DATA_URL = 'https://raw.githubusercontent.com/jjvhappening/Jira-Data-Quality/main/trend_history.json';
  try {
    var resp = await fetch(DATA_URL + '?_=' + Date.now());
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    var history = await resp.json();
    if (!history.runs || !history.runs.length) throw new Error('No run data in trend_history.json');
    _D        = computeDashboardData(history);
    TRIBES     = _D.tribes;
    SQUADS     = _D.squads;
    RUNS       = _D.runs;
    GAP_FIELDS = _D.gap_fields;
    OFFENDERS  = _D.offenders;
    var ov = document.getElementById('loadingOverlay');
    if (ov) ov.remove();
    renderHeader();
    initRunFilter();
    renderAll();
  } catch (e) {
    var ov = document.getElementById('loadingOverlay');
    if (ov) ov.innerHTML =
      '<div style="text-align:center;padding:60px;font-family:Segoe UI,sans-serif">' +
      '<div style="font-size:18px;color:#1a3a5c;font-weight:700">PLAYER — Jira Data Quality</div>' +
      '<div style="font-size:14px;color:#dc3545;margin-top:16px;font-weight:600">Failed to load dashboard data</div>' +
      '<div style="font-size:13px;color:#6c757d;margin-top:8px">' + e.message + '</div></div>';
  }
})();
"""

content = re.sub(old4_pattern, NEW_CODE, content, count=1)

# 5. Add loading overlay div just before </body>
OVERLAY = (
    '<div id="loadingOverlay" style="position:fixed;inset:0;background:#f0f4f8;'
    'display:flex;align-items:center;justify-content:center;z-index:9999">'
    '<div style="text-align:center;font-family:Segoe UI,sans-serif">'
    '<div style="font-size:18px;color:#1a3a5c;font-weight:700;margin-bottom:12px">PLAYER — Jira Data Quality</div>'
    '<div style="font-size:14px;color:#6c757d">Loading dashboard data…</div>'
    '</div></div>\n'
)
content = content.replace('</body>', OVERLAY + '</body>', 1)

with open(dst, 'w', encoding='utf-8') as f:
    f.write(content)
print('Done — index.html written to', dst)
