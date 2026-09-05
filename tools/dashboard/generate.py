"""Regenerate docs/progress-dashboard.html from live numbers + curated content.

The numbers side is read fresh on every run and can never go stale:
  - benchmarks/omr-ned-2026-08/current-accuracy.json  (headline + per-work table)
  - git log                                           (recent-commits strip)
The narrative side (active projects, queue, shipping log, dead ends) lives in
docs/progress-dashboard.content.json — edit it, re-run this, done.

    python3 -m tools.dashboard.generate            # write docs/progress-dashboard.html
    python3 -m tools.dashboard.generate --check    # exit 1 if the HTML is stale
    python3 -m tools.dashboard.generate --serve    # regenerate + serve on localhost:8600

Stdlib only; runs on the 3.9 host.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / "benchmarks" / "omr-ned-2026-08" / "current-accuracy.json"
INDUSTRY = ROOT / "benchmarks" / "omr-vs-industry-2026-09" / "results.json"
INDUSTRY_SCAN = ROOT / "benchmarks" / "omr-vs-industry-2026-09" / "results-audiveris-scan.json"
SCAN_COMPARISON = ROOT / "benchmarks" / "omr-vs-industry-2026-09" / "scan-comparison.json"
CONTENT = ROOT / "docs" / "progress-dashboard.content.json"
OUT = ROOT / "docs" / "progress-dashboard.html"

BAR_MAX_PX = 200  # the worst work's bar length; others scale linearly

ROMAN = {1: "i", 2: "ii", 3: "iii", 4: "iv", 5: "v"}


def work_display_name(work_id: str) -> str:
    """beethoven-sym5-mvt1 -> 'Beethoven 5 i'. Falls back to the raw id."""
    parts = work_id.split("-")
    try:
        composer = parts[0].capitalize()
        if composer == "Dvorak":
            composer = "Dvořák"
        num = int(parts[1].replace("sym", ""))
        mvt = ROMAN.get(int(parts[2].replace("mvt", "")), parts[2])
        return "%s %d %s" % (composer, num, mvt)
    except (IndexError, ValueError):
        return work_id


def recent_commits(n: int = 6) -> list:
    try:
        out = subprocess.run(
            ["git", "log", "--no-merges", "-%d" % n,
             "--pretty=%ad\x1f%h\x1f%s", "--date=short"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=10,
        )
        if out.returncode != 0:
            return []
        rows = []
        for line in out.stdout.strip().splitlines():
            date, sha, subject = line.split("\x1f", 2)
            rows.append({"date": date, "sha": sha, "subject": subject})
        return rows
    except Exception:
        return []


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ── HTML pieces ──────────────────────────────────────────────────────────────

CSS = """\
  :root {
    --paper: #F7F6F2; --surface: #FFFFFF; --ink: #1D1F27; --muted: #676B76;
    --faint: #9A9DA6; --hairline: #E4E2DA; --hairline-strong: #CFCDC3;
    --accent: #3352C4; --accent-soft: #E7ECFA;
    --good: #2E7D4F; --good-soft: #E4F0E8;
    --warn: #A97A14; --warn-soft: #F5EDD9;
    --crit: #B3382E; --crit-soft: #F6E4E2;
    --shadow: 0 1px 2px rgba(29,31,39,.05);
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --paper: #14161C; --surface: #1C1F28; --ink: #E9E8E3; --muted: #A0A3AD;
      --faint: #6E7280; --hairline: #2C303B; --hairline-strong: #3A3F4D;
      --accent: #8CA3F2; --accent-soft: #232B44;
      --good: #6DBE8F; --good-soft: #1E3328;
      --warn: #D9AE4E; --warn-soft: #362E17;
      --crit: #E08076; --crit-soft: #3B211E;
      --shadow: none;
    }
  }
  :root[data-theme="dark"] {
    --paper: #14161C; --surface: #1C1F28; --ink: #E9E8E3; --muted: #A0A3AD;
    --faint: #6E7280; --hairline: #2C303B; --hairline-strong: #3A3F4D;
    --accent: #8CA3F2; --accent-soft: #232B44;
    --good: #6DBE8F; --good-soft: #1E3328;
    --warn: #D9AE4E; --warn-soft: #362E17;
    --crit: #E08076; --crit-soft: #3B211E;
    --shadow: none;
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--paper); color: var(--ink);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 15px; line-height: 1.5; -webkit-font-smoothing: antialiased; }
  .wrap { max-width: 1120px; margin: 0 auto; padding: 40px 28px 72px; }
  header h1 { font-family: "Source Serif 4", Georgia, "Times New Roman", serif; font-weight: 600;
    font-size: 34px; margin: 0; letter-spacing: -.01em; text-wrap: balance; }
  .masthead-row { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
  .stamp { font-family: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace; font-size: 12.5px; color: var(--muted); }
  .stamp b { color: var(--ink); font-weight: 600; }
  .stafflines { margin: 18px 0 0; display: grid; gap: 5px; }
  .stafflines i { display: block; height: 1px; background: var(--hairline-strong); }
  .stafflines i:nth-child(3) { background: var(--accent); opacity: .7; }
  .subtitle { color: var(--muted); margin: 14px 0 0; max-width: 68ch; }
  section { margin-top: 44px; }
  .kicker { font-size: 11.5px; font-weight: 700;
    letter-spacing: .14em; text-transform: uppercase; color: var(--accent);
    margin: 0 0 14px; display: flex; align-items: center; gap: 12px; }
  .kicker::after { content: ""; flex: 1; height: 1px; background: var(--hairline); }
  .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }
  .metric { background: var(--surface); border: 1px solid var(--hairline); border-radius: 6px;
    padding: 16px 18px 14px; box-shadow: var(--shadow); }
  .metric .label { font-size: 12px; color: var(--muted); letter-spacing: .04em; text-transform: uppercase; font-weight: 600; }
  .metric .value { font-family: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace; font-size: 30px; font-weight: 600;
    line-height: 1.15; margin-top: 6px; font-variant-numeric: tabular-nums; }
  .metric .note { font-size: 12.5px; color: var(--muted); margin-top: 4px; }
  .metric .value .unit { font-size: 14px; color: var(--faint); font-weight: 400; }
  .tablewrap { overflow-x: auto; background: var(--surface); border: 1px solid var(--hairline);
    border-radius: 6px; box-shadow: var(--shadow); }
  table { border-collapse: collapse; width: 100%; min-width: 720px; }
  th, td { text-align: left; padding: 9px 14px; border-bottom: 1px solid var(--hairline); font-size: 13.5px; }
  th { font-size: 11.5px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); font-weight: 600; }
  tbody tr:last-child td { border-bottom: none; }
  td.num, th.num { text-align: right; font-family: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace; font-variant-numeric: tabular-nums; }
  .bar { display: inline-block; vertical-align: middle; height: 8px; border-radius: 2px;
    background: var(--accent); opacity: .85; margin-right: 10px; }
  .work { font-weight: 500; white-space: nowrap; }
  .flagnote { color: var(--warn); cursor: help; border-bottom: 1px dotted var(--warn); }
  .table-caption { font-size: 12.5px; color: var(--muted); margin: 10px 2px 0; max-width: 90ch; }
  .board { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
  @media (max-width: 860px) { .board { grid-template-columns: 1fr; } }
  .card { background: var(--surface); border: 1px solid var(--hairline); border-radius: 6px;
    padding: 4px 0; box-shadow: var(--shadow); }
  .item { padding: 13px 18px; border-bottom: 1px solid var(--hairline); }
  .item:last-child { border-bottom: none; }
  .item h3 { font-size: 14.5px; font-weight: 600; margin: 0 0 3px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .item p { margin: 0; font-size: 13.5px; color: var(--muted); }
  .item p b { color: var(--ink); font-weight: 600; }
  .pill { display: inline-block; font-size: 10.5px;
    font-weight: 600; letter-spacing: .06em; text-transform: uppercase; padding: 2px 8px;
    border-radius: 999px; white-space: nowrap; }
  .pill.active  { background: var(--accent-soft); color: var(--accent); }
  .pill.shipped { background: var(--good-soft); color: var(--good); }
  .pill.waiting { background: var(--warn-soft); color: var(--warn); }
  .pill.blocked { background: var(--crit-soft); color: var(--crit); }
  .pill.queue   { background: var(--hairline); color: var(--muted); }
  .log { border-left: 2px solid var(--hairline-strong); margin-left: 6px; padding-left: 22px; display: grid; gap: 16px; }
  .log-entry { position: relative; }
  .log-entry::before { content: ""; position: absolute; left: -27.5px; top: 6px;
    width: 9px; height: 9px; border-radius: 50%; background: var(--good);
    border: 2px solid var(--paper); }
  .log-entry.neg::before { background: var(--crit); }
  .log-date { font-family: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace; font-size: 12px; color: var(--muted); }
  .log-entry h3 { font-size: 14.5px; margin: 1px 0 2px; font-weight: 600; }
  .log-entry p { margin: 0; font-size: 13.5px; color: var(--muted); max-width: 82ch; }
  .log-entry p b { color: var(--ink); }
  .deadends { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 10px; }
  .dead { border: 1px solid var(--hairline); border-left: 3px solid var(--crit);
    border-radius: 4px; background: var(--surface); padding: 10px 14px;
    font-size: 13px; color: var(--muted); }
  .dead b { color: var(--ink); font-weight: 600; display: block; margin-bottom: 2px; }
  .commits { font-family: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace; font-size: 12.5px;
    display: grid; gap: 6px; color: var(--muted); }
  .commits .sha { color: var(--accent); }
  footer { margin-top: 56px; padding-top: 18px; border-top: 1px solid var(--hairline);
    font-size: 12.5px; color: var(--faint); display: flex; justify-content: space-between;
    gap: 12px; flex-wrap: wrap; }
  code { font-family: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace; font-size: .92em;
    background: var(--accent-soft); color: var(--accent); padding: 1px 5px; border-radius: 3px; }
"""


def build_metrics(record: dict, content: dict) -> str:
    runs = record["runs"]
    cards = []
    dt = runs.get("direction_text")
    if dt:
        cards.append(
            '<div class="metric"><div class="label">Engraved benchmark</div>'
            '<div class="value">%.4f</div>'
            '<div class="note">pooled OMR-NED, %d works · %s edits · direction reader on</div></div>'
            % (dt["pooled"], len(dt["works"]), "{:,}".format(dt["edits"]))
        )
    nd = runs.get("no_direction_text")
    if nd:
        cards.append(
            '<div class="metric"><div class="label">Without OCR rung</div>'
            '<div class="value">%.4f</div>'
            '<div class="note">same commit, <code>--no-direction-text</code> · %s edits</div></div>'
            % (nd["pooled"], "{:,}".format(nd["edits"]))
        )
    for m in content.get("extra_metrics", []):
        cards.append(
            '<div class="metric"><div class="label">%s</div><div class="value">%s</div>'
            '<div class="note">%s</div></div>'
            % (m["label"], m["value"], m["note"])
        )
    return "\n      ".join(cards)


def build_table(record: dict, content: dict) -> str:
    works = sorted(record["runs"]["direction_text"]["works"], key=lambda w: w["omr_ned"])
    max_ned = max(w["omr_ned"] for w in works)
    flags = content.get("work_flags", {})
    rows = []
    for w in works:
        name = esc(work_display_name(w["work_id"]))
        flag = flags.get(w["work_id"])
        if flag:
            name += ' <span class="flagnote" title="%s">†</span>' % esc(flag).replace('"', "&quot;")
        px = max(6, round(w["omr_ned"] / max_ned * BAR_MAX_PX))
        rows.append(
            '<tr><td class="work">%s</td>'
            '<td><span class="bar" style="width:%dpx"></span><span class="num">%.4f</span></td>'
            '<td class="num">%d</td><td class="num">%.3f</td><td class="num">%.3f</td>'
            '<td class="num">%.3f</td></tr>'
            % (name, px, w["omr_ned"], w["edits"], w["pitch_recall"],
               w["pitch_precision"], w["duration_rate"])
        )
    return "\n          ".join(rows)


def build_items(items: list) -> str:
    out = []
    for it in items:
        out.append(
            '<div class="item"><h3>%s <span class="pill %s">%s</span></h3><p>%s</p></div>'
            % (it["title"], it["pill_class"], it["pill"], it["body"])
        )
    return "\n          ".join(out)


def build_log(entries: list) -> str:
    out = []
    for e in entries:
        cls = "log-entry neg" if e.get("negative") else "log-entry"
        out.append(
            '<div class="%s"><div class="log-date">%s</div><h3>%s</h3><p>%s</p></div>'
            % (cls, e["date"], e["title"], e["body"])
        )
    return "\n      ".join(out)


def build_deadends(items: list) -> str:
    return "\n      ".join(
        '<div class="dead"><b>%s</b>%s</div>' % (d["title"], d["body"]) for d in items
    )


def build_industry(record: dict) -> str:
    """ReEngrave vs Audiveris — the industrial standard to beat.

    Two columns: the engraved benchmark (results.json) and the scan benchmark
    (results-audiveris-scan.json vs the scan bench's own results.json).
    Rendered only when the engraved comparison exists. oemer/homr were measured
    once (2026-09-04) and ruled out — architectural failures on orchestral
    pages; they live in the dead-ends ledger, not this table.
    """
    if not INDUSTRY.exists():
        return ""
    data = json.loads(INDUSTRY.read_text())
    audi = (data.get("engines") or {}).get("audiveris") or {}
    ok = [r for r in audi.values() if r.get("status") == "ok"]
    if not ok:
        return ""
    a_ed = sum(r["omr_ed"] for r in ok)
    a_denom = sum(r["truth_symbols"] + r["pred_symbols"] for r in ok)
    ours = record["runs"]["direction_text"]

    def cell(v, edits, note):
        return ('<div class="value" style="font-size:24px">%.4f</div>'
                '<div class="note">%s edits · %s</div>'
                % (v, "{:,}".format(edits), note))

    dash = '<div class="note">not yet measured</div>'
    scan_cells = {"ReEngrave": dash, "Audiveris 5.11": dash}
    scan_note = ""
    if SCAN_COMPARISON.exists():
        sc = json.loads(SCAN_COMPARISON.read_text())
        scan_cells["ReEngrave"] = cell(
            sc["ours_current"]["omr_ned"], sc["ours_current"]["omr_ed"],
            "current scan weights (graft09 arm; recorded pre-hollow run: %.4f)"
            % sc["ours_recorded"]["omr_ned"])
        scan_cells["Audiveris 5.11"] = cell(
            sc["audiveris"]["omr_ned"], sc["audiveris"]["omr_ed"],
            "%d/5 pages — 2 needed hand-holding (raised step timeout, music21 pass-through)"
            % sc["audiveris"]["n_rows"])
        scan_note = (" The scan column is the five-page scan benchmark — real "
                     "IMSLP pages, no dossier, Audiveris fed page renders at "
                     "its 20 MP cap; our row is the newest scan weights, "
                     "pinned (the canonical recorded figure is the pre-hollow "
                     "run).")
    body = []
    for name, pooled_v, edits, note in (
        ("ReEngrave", ours["pooled"], ours["edits"],
         "%d works · recorded on %s" % (len(ours["works"]), ours["commit"])),
        ("Audiveris 5.11", a_ed / a_denom, a_ed,
         "%d/%d works · same fixtures + scorer" % (len(ok), len(audi))),
    ):
        body.append(
            '<tr><td class="work">%s</td><td>%s</td><td>%s</td></tr>'
            % (esc(name), cell(pooled_v, edits, note), scan_cells[name]))
    return """
  <section>
    <p class="kicker">Vs Audiveris &middot; the standard to beat</p>
    <div class="tablewrap">
      <table>
        <thead><tr><th>System</th><th>Engraved benchmark (11 works)</th><th>Scan benchmark (5 pages)</th></tr></thead>
        <tbody>
          %s
        </tbody>
      </table>
    </div>
    <p class="table-caption">Audiveris ran on the same fixtures and was scored by the same musicdiff bridge — the only valid comparison; published paper numbers are from other corpora.%s Lower is better. Full reading: <code>benchmarks/omr-vs-industry-2026-09/FINDINGS.md</code>.</p>
  </section>
""" % ("\n          ".join(body), scan_note)


def build_commits(rows: list) -> str:
    if not rows:
        return ""
    lines = "\n      ".join(
        '<div><span class="sha">%s</span> %s · %s</div>'
        % (esc(r["sha"]), esc(r["date"]), esc(r["subject"])) for r in rows
    )
    return (
        '\n  <section>\n    <p class="kicker">Recent commits</p>\n'
        '    <div class="commits">\n      %s\n    </div>\n  </section>\n' % lines
    )


def render() -> str:
    record = json.loads(RECORD.read_text())
    content = json.loads(CONTENT.read_text())
    stamp = record.get("benchmark") or {}
    if not stamp:
        print("WARN: accuracy record carries no benchmark stamp (pre-boundary record?)",
              file=sys.stderr)
    commit = record["runs"]["direction_text"]["commit"]
    today = _dt.date.today().isoformat()

    return """<title>ReEngrave Status Board</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,500;8..60,600&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
%(css)s</style>

<div class="wrap">
  <header>
    <div class="masthead-row">
      <h1>ReEngrave Status Board</h1>
      <div class="stamp">generated <b>%(today)s</b> · benchmark commit <b>%(commit)s</b></div>
    </div>
    <div class="stafflines" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></div>
    <p class="subtitle">%(subtitle)s</p>
  </header>

  <section>
    <p class="kicker">Headline numbers</p>
    <div class="metrics">
      %(metrics)s
    </div>
    <p class="table-caption">%(era_note)s</p>
  </section>

  <section>
    <p class="kicker">Per-work OMR-NED · engraved orchestral e2e</p>
    <div class="tablewrap">
      <table>
        <thead><tr>
          <th>Work</th><th>OMR-NED (lower = better)</th><th class="num">edits</th><th class="num">note recall</th><th class="num">precision</th><th class="num">duration</th>
        </tr></thead>
        <tbody>
          %(table_rows)s
        </tbody>
      </table>
    </div>
    <p class="table-caption">%(table_caption)s</p>
  </section>

  <section>
    <div class="board">
      <div>
        <p class="kicker">Active projects</p>
        <div class="card">
          %(active)s
        </div>
      </div>
      <div>
        <p class="kicker">Next up · ranked</p>
        <div class="card">
          %(queue)s
        </div>
      </div>
    </div>
  </section>

%(industry)s
  <section>
    <p class="kicker">Shipping log · September</p>
    <div class="log">
      %(log)s
    </div>
  </section>

  <section>
    <p class="kicker">Closed · do not retry</p>
    <div class="deadends">
      %(deadends)s
    </div>
  </section>
%(commits)s
  <footer>
    <span>Generated by <code>python3 -m tools.dashboard.generate</code> — numbers from current-accuracy.json + git, narrative from docs/progress-dashboard.content.json</span>
    <span>Do not hand-edit the HTML</span>
  </footer>
</div>
""" % {
        "css": CSS,
        "today": today,
        "commit": esc(commit),
        "subtitle": content["subtitle"],
        "metrics": build_metrics(record, content),
        "era_note": content["era_note"],
        "table_rows": build_table(record, content),
        "table_caption": content["table_caption"],
        "active": build_items(content["active"]),
        "queue": build_items(content["queue"]),
        "log": build_log(content["log"]),
        "deadends": build_deadends(content["deadends"]),
        "industry": build_industry(record),
        "commits": build_commits(recent_commits()),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if the written HTML is stale against a fresh render "
                         "(the generated-date stamp and commit strip are ignored)")
    ap.add_argument("--serve", action="store_true",
                    help="regenerate, then serve docs/ on http://localhost:8600")
    args = ap.parse_args()

    html = render()

    if args.check:
        if not OUT.exists():
            print("STALE: %s does not exist" % OUT)
            return 1
        import re
        def normalize(s: str) -> str:
            s = re.sub(r"generated <b>[\d-]+</b>", "generated <b>DATE</b>", s)
            s = re.sub(r'(?s)\n  <section>\n    <p class="kicker">Recent commits</p>.*?</section>\n', "", s)
            return s
        if normalize(OUT.read_text()) != normalize(html):
            print("STALE: docs/progress-dashboard.html differs from a fresh render — re-run the generator")
            return 1
        print("OK: dashboard is current")
        return 0

    OUT.write_text(html)
    print("wrote %s" % OUT.relative_to(ROOT))

    if args.serve:
        import http.server, functools
        handler = functools.partial(
            http.server.SimpleHTTPRequestHandler, directory=str(ROOT / "docs"))
        print("serving http://localhost:8600/progress-dashboard.html  (Ctrl-C to stop)")
        http.server.HTTPServer(("127.0.0.1", 8600), handler).serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
