"""Deterministic market evidence only; no portfolio conclusions or orders."""
from dataclasses import asdict
import sqlite3
from .market import canonical, digest, validate_snapshot, DataError
from .vendor.market_data import build_market_data
from .vendor.wyckoff import analyze_wyckoff
from .vendor.smc import analyze_smc
from .vendor.confluence import analyze_confluence

UPSTREAM = 'ca6dce03685317e980d435d22539cc8d0bf45e15'
ENGINE = 'decision-check.market-evidence.v1'
SETTINGS = {'wyckoff_timeframe': '4h', 'wyckoff_lookback': 30, 'smc_timeframe': '1h', 'parameters': 'upstream-defaults-at-pinned-revision'}


def analyze(snapshot):
    validate_snapshot(snapshot)
    b = snapshot['bars']
    m = build_market_data(snapshot['symbol'], b['15m'][-1][4], b['1d'], b['4h'], b['1h'], b['15m'])
    w, s = analyze_wyckoff(m), analyze_smc(m, timeframe='1h')
    c = analyze_confluence(w, s)
    return {'wyckoff': asdict(w), 'smc': asdict(s), 'confluence': asdict(c)}


def make_report(snapshot):
    return {'schema': 'decision-check.report.v1', 'engine': ENGINE, 'upstream_revision': UPSTREAM,
        'settings': SETTINGS.copy(), 'snapshot_sha256': digest(snapshot), 'snapshot': snapshot,
        'analysis': analyze(snapshot), 'scope': 'MARKET_EVIDENCE_ONLY_NO_ORDER',
        'tapeout': {'status': 'NOT_REQUESTED', 'circuit_id': None}}


def verify_report(report):
    if (report.get('schema') != 'decision-check.report.v1' or report.get('engine') != ENGINE
        or report.get('upstream_revision') != UPSTREAM or report.get('settings') != SETTINGS
        or report.get('scope') != 'MARKET_EVIDENCE_ONLY_NO_ORDER'
        or report.get('tapeout') != {'status': 'NOT_REQUESTED', 'circuit_id': None}):
        raise DataError('UNSUPPORTED_REPORT_OR_RULE_VERSION')
    snapshot = report.get('snapshot')
    validate_snapshot(snapshot)
    if report.get('snapshot_sha256') != digest(snapshot):
        raise DataError('SNAPSHOT_HASH_MISMATCH')
    if canonical(report.get('analysis')) != canonical(analyze(snapshot)):
        raise DataError('ANALYSIS_REPLAY_MISMATCH')
    return True


def store_report(path, report):
    verify_report(report)
    # Local single-owner storage. Not a public multi-user account database.
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY, cutoff_ms INTEGER NOT NULL, symbol TEXT NOT NULL, market TEXT NOT NULL, payload TEXT NOT NULL)')
        report_id = digest(report)
        s = report['snapshot']
        db.execute('INSERT OR IGNORE INTO reports VALUES (?, ?, ?, ?, ?)',
                   (report_id, s['cutoff_ms'], s['symbol'], s['market'], canonical(report)))
    return report_id
