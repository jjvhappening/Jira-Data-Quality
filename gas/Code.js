/**
 * PLAYER Jira Data Quality — Trend Dashboard
 * Google Apps Script — Code.gs
 *
 * SETUP (one-time):
 * 1. script.google.com → New project → name "PLAYER DQ Dashboard"
 * 2. Paste this file as Code.gs
 * 3. Create an HTML file named "gas_dashboard" and paste gas_dashboard.html into it
 * 4. Services → Add Drive API
 * 5. Project Settings → Script Properties → add:
 *      FOLDER_ID     = 1L8oU7wvw9ROTJmCtooTod_UcXpnt9Uk0
 *      TREND_FILE_ID = 1hlDO1oo2YOT6BenZa9vqbWxBT0bRW2PA
 * 6. Deploy → New deployment → Web app → Execute as Me → Anyone with link → Copy URL
 *
 * ARCHITECTURE (as of 2026-05-14):
 * Python (build_reports.py + drive_sync.py) is the sole source of truth for
 * trend_history.json. This script reads that Drive file and serves the dashboard.
 * The Excel-processing pipeline (extractFromMaster, extractTopOffenders,
 * processNewRun, checkForNewRuns) has been removed — it was the root cause of
 * the score/missing-count inconsistency bug (UTF-8 ✓ corruption on conversion).
 *
 * If you see a checkForNewRuns time-driven trigger in Apps Script → Triggers,
 * delete it — it is no longer needed.
 */

var props = PropertiesService.getScriptProperties();

// ── Web app entry point ──────────────────────────────────────────────────────
// Generates the dashboard on-the-fly by injecting trend data into the
// gas_dashboard HTML template. Uses createTemplateFromFile to avoid the
// nested-<html> blank-page issue caused by createHtmlOutput().
function doGet() {
  var history = loadTrendHistory();
  if (!history || !history.runs || !history.runs.length) {
    return HtmlService.createHtmlOutput(
      '<div style="font-family:Segoe UI,sans-serif;padding:60px;text-align:center;color:#1a3a5c">' +
      '<h1 style="font-size:22px">PLAYER — Jira Data Quality</h1>' +
      '<p style="color:#6c757d;font-size:14px;margin-top:12px">No data yet.<br>' +
      'Run <code style="background:#f0f4f8;padding:2px 6px;border-radius:4px">backfillHistory()</code> ' +
      'in the Apps Script editor.</p></div>'
    ).setTitle('PLAYER Jira Data Quality');
  }
  var tmpl = HtmlService.createTemplateFromFile('gas_dashboard');
  tmpl.DATA_JSON = JSON.stringify(computeDashboardData(history));
  return tmpl.evaluate()
    .setTitle('PLAYER Jira Data Quality')
    .setSandboxMode(HtmlService.SandboxMode.IFRAME)
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

// ── Trend history: load ──────────────────────────────────────────────────────
// Reads trend_history.json from Drive. Written by Python (build_reports.py +
// drive_sync.py) — this script never modifies it.
function loadTrendHistory() {
  var fileId = props.getProperty('TREND_FILE_ID');
  if (!fileId) return { schema_version: 1, runs: [] };
  try {
    return JSON.parse(DriveApp.getFileById(fileId).getBlob().getDataAsString());
  } catch (e) {
    Logger.log('loadTrendHistory error: ' + e);
    return { schema_version: 1, runs: [] };
  }
}

// ── Dashboard computation ────────────────────────────────────────────────────
function computeDashboardData(history) {
  var runs    = history.runs;

  var TRIBE_COLORS = {
    'Player Engagement':   '#6a1b9a',
    'Transact':            '#1565C0',
    'Fraud Prevention':    '#e65100',
    'Retail/Multichannel': '#795548',
    'Manage':              '#2e7d32',
    'Unassigned':          '#757575',
  };

  // RUNS array — one entry per audit run
  var MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  var runsData = runs.map(function(r) {
    var d = new Date(r.date);
    return {
      run:             r.run,
      label:           'Run ' + r.run,
      date:            d.getDate() + ' ' + MONTHS[d.getMonth()] + ' ' + d.getFullYear(),
      month:           MONTHS[d.getMonth()],
      score:           r.avg_score,
      total:           r.total,
      compliant:       r.compliant,
      gaps:            r.with_gaps,
      // Timestamp of when Jira data was fetched (set by process_full_audit.py).
      // Used by the dashboard to show "Data fetched: YYYY-MM-DD HH:MM UTC".
      data_fetched_at: r.data_fetched_at || null,
    };
  });

  // Collect tribe names in canonical order, excluding Unassigned
  var TRIBE_ORDER = ['Player Engagement','Transact','Fraud Prevention','Retail/Multichannel','Manage'];
  var tribeSet    = {};
  runs.forEach(function(r) { Object.keys(r.tribes).forEach(function(t) { tribeSet[t] = true; }); });
  var tribeNames  = TRIBE_ORDER.filter(function(t) { return tribeSet[t]; });

  // TRIBES array
  var tribesData = tribeNames.map(function(name) {
    var scores    = runs.map(function(r) { return r.tribes[name] ? r.tribes[name].avg_score : null; });
    var totals    = runs.map(function(r) { return r.tribes[name] ? r.tribes[name].total     : 0; });
    var compliant = runs.map(function(r) { return r.tribes[name] ? r.tribes[name].compliant : 0; });
    var gapCounts = runs.map(function(r) { return r.tribes[name] ? (r.tribes[name].gap_counts || {}) : {}; });
    return {
      name:      name,
      color:     TRIBE_COLORS[name] || '#607d8b',
      scores:    scores,
      totals:    totals,
      compliant: compliant,
      volatile:  name === 'Retail/Multichannel',
      gapCounts: gapCounts,
    };
  });

  // Build squad → tribe mapping across all runs
  var squadToTribe = {};
  runs.forEach(function(r) {
    Object.keys(r.tribes).forEach(function(tribeName) {
      var tribe = r.tribes[tribeName];
      if (tribe && tribe.squads) {
        Object.keys(tribe.squads).forEach(function(sq) {
          if (!squadToTribe[sq]) squadToTribe[sq] = tribeName;
        });
      }
    });
  });

  // SQUADS array: [name, tribe, [scores per run], [totals per run], [gapCounts per run], [squadOffenders per run]]
  var squadsData = Object.keys(squadToTribe).sort().map(function(sq) {
    var tribeName = squadToTribe[sq];
    var scores = runs.map(function(r) {
      var tribe = r.tribes[tribeName];
      return (tribe && tribe.squads && tribe.squads[sq]) ? tribe.squads[sq].avg_score : null;
    });
    var totals = runs.map(function(r) {
      var tribe = r.tribes[tribeName];
      return (tribe && tribe.squads && tribe.squads[sq]) ? tribe.squads[sq].total : 0;
    });
    var gapCounts = runs.map(function(r) {
      var tribe = r.tribes[tribeName];
      return (tribe && tribe.squads && tribe.squads[sq]) ? (tribe.squads[sq].gap_counts || {}) : {};
    });
    // Per-squad top offenders for squad-level filtering in the dashboard
    var squadOffenders = runs.map(function(r) {
      var tribe = r.tribes[tribeName];
      if (!tribe || !tribe.squads || !tribe.squads[sq]) return [];
      return tribe.squads[sq].top_offenders || [];
    });
    return [sq, tribeName, scores, totals, gapCounts, squadOffenders];
  });

  // GAP_FIELDS array: [label, [count per run]] — top 10 by latest run
  var latestRun     = runs[runs.length - 1] || { gap_counts: {} };
  var allFieldNames = {};
  runs.forEach(function(r) { Object.keys(r.gap_counts || {}).forEach(function(f) { allFieldNames[f] = true; }); });
  var sortedFields  = Object.keys(allFieldNames).sort(function(a, b) {
    return (latestRun.gap_counts[b] || 0) - (latestRun.gap_counts[a] || 0);
  }).slice(0, 10);

  var gapFields = sortedFields.map(function(f) {
    return [f, runs.map(function(r) { return r.gap_counts[f] || 0; })];
  });

  // OFFENDERS array-of-arrays: one entry per run
  // Each element: [key, summary, squad, tribe, score, [missing_fields]]
  var offenders = runs.map(function(run) {
    return (run.top_offenders || []).map(function(o) {
      return [o.key, o.summary, o.squad, o.tribe, o.score, o.missing];
    });
  });

  return {
    tribes:     tribesData,
    squads:     squadsData,
    runs:       runsData,
    gap_fields: gapFields,
    offenders:  offenders,
  };
}

// ── Dashboard generation (static Drive HTML copy) ────────────────────────────
// Updates the static Drive HTML copy of the dashboard (used as a fallback and
// for email-based sharing). The live web app always serves from doGet() directly.
function generateDashboard() {
  var history  = loadTrendHistory();
  var html     = buildDashboardHtml(history);
  var fileId   = props.getProperty('DASHBOARD_FILE_ID');
  if (fileId) {
    DriveApp.getFileById(fileId).setContent(html);
  } else {
    var folder = DriveApp.getFolderById(props.getProperty('FOLDER_ID'));
    var file   = folder.createFile('PLAYER_DataQuality_Dashboard.html', html, 'text/html');
    props.setProperty('DASHBOARD_FILE_ID', file.getId());
    Logger.log('Created dashboard: ' + file.getId());
  }
  Logger.log('Dashboard generated (' + history.runs.length + ' runs).');
}

function buildDashboardHtml(history) {
  var template = HtmlService.createHtmlOutputFromFile('gas_dashboard').getContent();
  var data     = computeDashboardData(history);
  return template.replace('/* __DATA__ */null', JSON.stringify(data));
}

// ── One-time backfill (legacy) ────────────────────────────────────────────────
// The Excel-based backfill pipeline has been replaced by the Python pipeline.
// To re-populate trend_history.json from scratch, run:
//   python build_reports.py   (writes local trend_history.json)
//   python drive_sync.py      (uploads to Drive file ID 1hlDO1oo2YOT6BenZa9vqbWxBT0bRW2PA)
// This stub is kept so the function name still appears in the Apps Script UI.
function backfillHistory() {
  Logger.log('backfillHistory() is now a no-op.');
  Logger.log('Use the Python pipeline instead: build_reports.py + drive_sync.py');
  Logger.log('See the ARCHITECTURE note at the top of Code.gs for details.');
}

// ── Manual regenerate (utility) ──────────────────────────────────────────────
// Run from the editor to force-regenerate the static Drive HTML copy without
// uploading new data. The live web app does not need this — it reads Drive JSON
// on every request via doGet().
function regenerateDashboard() {
  generateDashboard();
  Logger.log('Dashboard regenerated. DASHBOARD_FILE_ID: ' + props.getProperty('DASHBOARD_FILE_ID'));
}
