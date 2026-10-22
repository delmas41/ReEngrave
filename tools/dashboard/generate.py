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

# ── artefacts the pipeline flow graph reads (all committed; each is optional,
#    and a missing one degrades that cell to "unmeasured" rather than crashing)
READING = ROOT / "benchmarks" / "omr-reading-vs-reproduction-2026-09" / "results.json"
SCAN_GATE = ROOT / "benchmarks" / "omr-scan-e2e-2026-09" / "results-reconciliation.json"
ENGRAVED_1TO1 = ROOT / "benchmarks" / "omr-headline-validity-2026-09" / "engraved-1to1.json"
NORMALISED = ROOT / "benchmarks" / "omr-headline-validity-2026-09" / "results-normalised-arm.json"
HAIRPIN_CV = ROOT / "benchmarks" / "omr-hairpin-cv-2026-09" / "results-scored-pages.json"

BAR_MAX_PX = 200  # the worst work's bar length; others scale linearly

# ── the colour rule, stated once and printed in the legend from these constants
#    so the page can never claim a threshold the code does not use.
RATE_GREEN = 0.90   # higher-is-better rates (F1, recall, "n of m correct")
RATE_AMBER = 0.60
NED_GREEN = 0.15    # OMR-NED — lower is better
NED_AMBER = 0.50

# The reading benchmark pools at this centre tolerance, in staff spaces.
READING_TOL = "0.5"
# Families the reading harness flags rather than pools: `accidental` is a
# Verovio render artefact (one glyph per <alter>, not per <accidental>), and
# `barline`/`beam` are classical-CV and cell-relative, so they never appear in
# page coordinates on the prediction side. Excluding exactly these three
# reproduces the harness's published pooled F1 of 0.919.
READING_UNPOOLED = ("accidental", "barline", "beam")

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


# ── pipeline flow graph ──────────────────────────────────────────────────────
#
# Sean's ask: see the pieces, labelled with what technology reads each one, and
# colour-coded by how well it currently works.
#
# ⚠️ The design constraint that decides whether this is useful or misleading:
# ONE colour per stage would be a lie. Engraved and scanned pages differ
# enormously at the SAME stage, sometimes in opposite directions — hairpins read
# at F1 1.000 against engraved page truth and 1 of 99 on scans; noteheads 856 of
# 856 engraved while half-notes are the documented scan weakness. So every stage
# carries TWO cells and they are never averaged.
#
# Every figure here is either read from a committed artefact (preferred — it
# cannot rot) or carried in the content JSON with an explicit `source` string.
# A stage with no isolated measurement is GREY and says so: this project's house
# standard is that an unmeasured claim is worse than an absent one.


def _load(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _f1(truth: int, pred: int, matched: int):
    if not truth or not pred:
        return None
    prec = matched / pred
    rec = matched / truth
    if prec + rec == 0:
        return None
    return 2 * prec * rec / (prec + rec), prec, rec


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def pipeline_metrics() -> dict:
    """Every number the flow graph can compute, keyed by the name the content
    JSON refers to. Each value is {display, detail, source} plus at most one of
    `rate` (higher is better) or `ned` (lower is better) — the colour comes from
    that, never from a hand-assigned status."""
    m = {}

    # ── stage 4/5/8: per-family reading F1 against exact Verovio page truth
    reading = _load(READING)
    if reading:
        agg = {}
        works = reading.get("stage1_reading") or {}
        for w in works.values():
            per = ((w.get("tolerances") or {}).get(READING_TOL) or {}).get("per_family") or {}
            for fam, v in per.items():
                a = agg.setdefault(fam, [0, 0, 0])
                a[0] += v["truth"]; a[1] += v["pred"]; a[2] += v["matched"]
        src = "benchmarks/omr-reading-vs-reproduction-2026-09/results.json"
        note = " · %d engraved works, page truth at %s staff spaces" % (len(works), READING_TOL)
        pool = [0, 0, 0]
        for fam, (t, p, mt) in agg.items():
            r = _f1(t, p, mt)
            if r:
                f1, prec, rec = r
                m["reading:" + fam] = {
                    "display": "F1 %.3f" % f1, "rate": f1,
                    "detail": "%d printed / %d read / %d matched · precision %.3f recall %.3f"
                              % (t, p, mt, prec, rec),
                    "source": src,
                }
            if fam not in READING_UNPOOLED:
                pool[0] += t; pool[1] += p; pool[2] += mt
        r = _f1(*pool)
        if r:
            f1, prec, rec = r
            m["reading:POOLED"] = {
                "display": "F1 %.3f" % f1, "rate": f1,
                "detail": "%d scoreable symbols / %d read · precision %.3f recall %.3f%s"
                          % (pool[0], pool[1], prec, rec, note),
                "source": src,
            }

    # ── the two headline scores, one per input family
    record = _load(RECORD)
    if record:
        dt = record["runs"]["direction_text"]
        m["engraved:omr_ned"] = {
            "display": "%.4f" % dt["pooled"], "ned": dt["pooled"],
            "detail": "pooled OMR-NED, %d works, %s edits · recorded on %s"
                      % (len(dt["works"]), "{:,}".format(dt["edits"]), dt["commit"]),
            "source": "benchmarks/omr-ned-2026-08/current-accuracy.json",
        }
        pr = _mean([w["pitch_recall"] for w in dt["works"]])
        dr = _mean([w["duration_rate"] for w in dt["works"]])
        m["engraved:pitch"] = {
            "display": "%.3f" % pr, "rate": pr,
            "detail": "mean note recall over %d works (worst %.3f, best %.3f)"
                      % (len(dt["works"]),
                         min(w["pitch_recall"] for w in dt["works"]),
                         max(w["pitch_recall"] for w in dt["works"])),
            "source": "benchmarks/omr-ned-2026-08/current-accuracy.json",
        }
        m["engraved:duration"] = {
            "display": "%.3f" % dr, "rate": dr,
            "detail": "mean duration rate over %d works — of matched notes, the share "
                      "whose value is also right" % len(dt["works"]),
            "source": "benchmarks/omr-ned-2026-08/current-accuracy.json",
        }

    # ── stage 1/2/3/6/7: the scan gate's own structural + note columns
    gate = _load(SCAN_GATE)
    if gate:
        rows = gate["rows"]
        src = "benchmarks/omr-scan-e2e-2026-09/results-reconciliation.json"
        m["scan:omr_ned"] = {
            "display": "%.4f" % gate["pooled"]["omr_ned"], "ned": gate["pooled"]["omr_ned"],
            "detail": "pooled OMR-NED, %d hand-verified rows, %s edits · ⚠️ a large share is "
                      "structural charge, see the note below"
                      % (len(rows), "{:,}".format(gate["pooled"]["omr_ed"])),
            "source": src,
        }
        st_ok = sum(1 for r in rows if r["printed"]["staves"] == r["detected"]["staves"])
        m["scan:staves"] = {
            "display": "%d/%d rows" % (st_ok, len(rows)), "rate": st_ok / len(rows),
            "detail": "%d printed staves, %d detected — every row exact"
                      % (sum(r["printed"]["staves"] for r in rows),
                         sum(r["detected"]["staves"] for r in rows))
                      if st_ok == len(rows) else
                      "%d printed staves, %d detected"
                      % (sum(r["printed"]["staves"] for r in rows),
                         sum(r["detected"]["staves"] for r in rows)),
            "source": src,
        }
        sy_ok = sum(1 for r in rows if r["printed"]["systems"] == r["detected"]["systems"])
        m["scan:systems"] = {
            "display": "%d/%d rows" % (sy_ok, len(rows)), "rate": sy_ok / len(rows),
            "detail": "systems per page, hand-read against the print",
            "source": src,
        }
        # ⚠️ the summary `detected.measures` field undercounts MULTI-system pages
        # (recorded in BASELINE_20ROW_2026-09-05.md), so this reads only the
        # single-system rows, where it is trustworthy.
        single = [r for r in rows if r["printed"]["systems"] == 1]
        if single:
            ok = sum(1 for r in single if r["truth"]["measures"] == r["detected"]["measures"])
            bad = [r["row_id"].split(".")[0] for r in single
                   if r["truth"]["measures"] != r["detected"]["measures"]]
            m["scan:measures"] = {
                "display": "%d/%d pages" % (ok, len(single)), "rate": ok / len(single),
                "detail": "single-system rows only — the summary field undercounts "
                          "multi-system pages%s"
                          % ((" · off by one on " + ", ".join(bad)) if bad else ""),
                "source": src,
            }
        acc = {}
        for key in ("exact", "step", "with_duration"):
            t = p = mt = 0
            for r in rows:
                n = (r.get("notes") or {}).get("pooled")
                if n:
                    t += n[key]["truth"]; p += n[key]["omr"]; mt += n[key]["matched"]
            acc[key] = (t, p, mt)
        n_scored = sum(1 for r in rows if (r.get("notes") or {}).get("pooled"))
        if acc["step"][0]:
            step_rec = acc["step"][2] / acc["step"][0]
            exact_rec = acc["exact"][2] / acc["exact"][0]
            m["scan:pitch"] = {
                "display": "%.3f" % step_rec, "rate": step_rec,
                "detail": "staff-position recall over %s truth notes on the %d rows carrying a "
                          "hand-confirmed staff map · spelled-pitch recall %.3f — the gap is the "
                          "accidental and key-signature layer"
                          % ("{:,}".format(acc["step"][0]), n_scored, exact_rec),
                "source": src,
            }
        if acc["exact"][2]:
            drate = acc["with_duration"][2] / acc["exact"][2]
            m["scan:duration"] = {
                "display": "%.3f" % drate, "rate": drate,
                "detail": "of the %s notes matched on pitch, the share whose duration is also "
                          "right (%d rows)" % ("{:,}".format(acc["exact"][2]), n_scored),
                "source": src,
            }

    # ── stage 1-3 on engraved pages: does the output have the page's structure
    one = _load(ENGRAVED_1TO1)
    if one:
        works = one["works"]
        ok = sum(1 for w in works if w["our_parts"] == w["truth_parts"])
        m["engraved:structure"] = {
            "display": "%d/%d works" % (ok, len(works)), "rate": ok / len(works),
            "detail": "parts emitted vs parts in the truth · these fixtures are 1:1 by "
                      "construction (every truth part gets its own printed staff), so this is "
                      "an easier question than a conductor's page asks",
            "source": "benchmarks/omr-headline-validity-2026-09/engraved-1to1.json",
        }

    # ── the caveat the scan colour cannot be read without
    norm = _load(NORMALISED)
    if norm:
        raw = norm["pooled_over_normalisable_rows_only"]["raw"]
        nz = norm["pooled_over_normalisable_rows_only"]["normalised"]
        removed = raw["omr_ed"] - nz["omr_ed"]
        m["scan:structural_charge"] = {
            "display": "%.1f%%" % (100.0 * removed / raw["omr_ed"]),
            "detail": "on the %d rows where the condensation convention can be normalised away, "
                      "%.4f → %.4f and %s of %s edits disappear — the page prints "
                      "<code>Flauti</code> on one staff, the encoding holds two flute parts, and "
                      "we are charged for reading the page right"
                      % (raw["n_rows"], raw["omr_ned"], nz["omr_ned"],
                         "{:,}".format(removed), "{:,}".format(raw["omr_ed"])),
            "source": "benchmarks/omr-headline-validity-2026-09/results-normalised-arm.json",
        }

    # ── stage 4 on scans: the one per-class detector figure that exists
    hp = _load(HAIRPIN_CV)
    if hp:
        truth = sum(v["truth_hairpins"] for v in hp.values())
        yolo = sum(v["yolo"] for v in hp.values())
        if truth:
            m["scan:hairpin_detect"] = {
                "display": "%d/%d" % (yolo, truth), "rate": yolo / truth,
                "detail": "hairpins the DETECTOR finds on %d scanned pages — against F1 1.000 "
                          "on engraved page truth. The classical-CV reader added later carries "
                          "118 of the 198 <code>&lt;wedge&gt;</code> into the file"
                          % len(hp),
                "source": "benchmarks/omr-hairpin-cv-2026-09/results-scored-pages.json",
            }
    return m


def _status(cell: dict) -> tuple:
    """(css class, label). Derived from the number, never asserted."""
    if cell.get("rate") is not None:
        v = cell["rate"]
        if v >= RATE_GREEN:
            return "good", "good"
        if v >= RATE_AMBER:
            return "warn", "partial"
        return "crit", "weak"
    if cell.get("ned") is not None:
        v = cell["ned"]
        if v <= NED_GREEN:
            return "good", "good"
        if v <= NED_AMBER:
            return "warn", "partial"
        return "crit", "weak"
    return "grey", "unmeasured"


def _resolve_cell(spec, metrics: dict) -> dict:
    """A content-JSON cell is either {"metric": key} (computed, cannot rot) or a
    literal carrying its own `source`. An unresolvable metric degrades to grey
    rather than raising — a missing artefact must not break the build."""
    if not spec:
        return {"display": "—", "detail": "no measurement", "source": ""}
    if spec.get("metric"):
        base = dict(metrics.get(spec["metric"]) or {})
        if not base:
            base = {"display": "—",
                    "detail": "artefact missing: <code>%s</code>" % esc(spec["metric"]),
                    "source": ""}
        for k in ("detail", "display", "source"):
            if spec.get(k):
                base[k] = spec[k]
        if spec.get("detail_suffix"):
            base["detail"] = base.get("detail", "") + " " + spec["detail_suffix"]
        return base
    return dict(spec)


def build_pipeline(content: dict, metrics: dict) -> str:
    pipe = content.get("pipeline")
    if not pipe:
        return ""
    rows = []
    stages = pipe["stages"]
    for i, st in enumerate(stages):
        cells = []
        for family, label in (("engraved", "engraved"), ("scan", "scan")):
            c = _resolve_cell(st.get(family), metrics)
            cls, word = _status(c)
            src = ('<span class="psrc">%s</span>' % esc(c["source"])) if c.get("source") else ""
            cells.append(
                '<div class="pcell %s"><span class="plab">%s <em>%s</em></span>'
                '<span class="pval">%s</span><span class="pdet">%s</span>%s</div>'
                % (cls, label, word, c.get("display", "—"), c.get("detail", ""), src))
        note = ('<p class="pnote">%s</p>' % st["note"]) if st.get("note") else ""
        cls = ""
        if i == 0:
            cls += " first"
        if i == len(stages) - 1:
            cls += " last"
        rows.append(
            '<div class="pstage%s">'
            '<div class="pnum"><span>%s</span></div>'
            '<div class="pmain"><h4>%s</h4><span class="tech">%s</span>%s</div>'
            '%s%s</div>'
            % (cls, st["n"], st["name"], st["tech"], note, cells[0], cells[1]))
    legend = (
        '<div class="plegend">'
        '<span><i class="sw good"></i>good — rate ≥ %.2f, or OMR-NED ≤ %.2f</span>'
        '<span><i class="sw warn"></i>partial — rate %.2f–%.2f, or OMR-NED %.2f–%.2f</span>'
        '<span><i class="sw crit"></i>weak — rate &lt; %.2f, or OMR-NED &gt; %.2f</span>'
        '<span><i class="sw grey"></i>unmeasured — no isolated figure exists</span>'
        '</div>' % (RATE_GREEN, NED_GREEN, RATE_AMBER, RATE_GREEN, NED_GREEN, NED_AMBER,
                    RATE_AMBER, NED_AMBER))
    charge = metrics.get("scan:structural_charge")
    charge_html = ""
    if charge:
        charge_html = (
            '<p class="table-caption">⚠️ <b>Read the scan column with this in hand:</b> %s '
            '(<span class="psrc">%s</span>) So the scan colours are a floor on how well the '
            'stage reads the page — part of that gap is the metric billing a printing '
            'convention, not a misreading.</p>' % (charge["detail"], esc(charge["source"])))
    return """
  <section>
    <p class="kicker">The pipeline, stage by stage</p>
    <p class="table-caption" style="margin:0 0 14px">%s</p>
    %s
    <div class="pflowwrap">
      <div class="pflow">
        <div class="phead"><div></div><div>stage &middot; what reads it</div><div>digitally engraved input</div><div>scanned input</div></div>
        %s
      </div>
    </div>
    %s
  </section>
""" % (pipe["intro"], legend, "\n        ".join(rows), charge_html)


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

  /* ── pipeline flow graph ─────────────────────────────────────────────── */
  .plegend { display: flex; flex-wrap: wrap; gap: 8px 20px; font-size: 12.5px;
    color: var(--muted); margin: 0 0 16px; }
  .plegend span { display: inline-flex; align-items: center; gap: 7px; }
  .sw { width: 11px; height: 11px; border-radius: 3px; display: inline-block; flex: none; }
  .sw.good { background: var(--good); } .sw.warn { background: var(--warn); }
  .sw.crit { background: var(--crit); } .sw.grey { background: var(--faint); }
  .pflowwrap { overflow-x: auto; }
  .pflow { min-width: 700px; background: var(--surface); border: 1px solid var(--hairline);
    border-radius: 6px; box-shadow: var(--shadow); }
  .phead, .pstage { display: grid; grid-template-columns: 46px minmax(190px, 1.15fr)
    minmax(190px, 1fr) minmax(190px, 1fr); }
  .phead > div { font-size: 11px; text-transform: uppercase; letter-spacing: .08em;
    color: var(--muted); font-weight: 600; padding: 11px 14px 9px;
    border-bottom: 1px solid var(--hairline-strong); }
  .pstage { border-bottom: 1px solid var(--hairline); }
  .pstage.last { border-bottom: none; }
  /* the rail: a numbered node per stage, joined by a line down the gutter */
  .pnum { position: relative; font-family: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace;
    font-size: 11.5px; font-weight: 600; color: var(--muted); padding: 16px 0 0;
    text-align: center; }
  .pnum::before { content: ""; position: absolute; left: 50%; top: 0; bottom: 0; width: 1px;
    margin-left: -.5px; background: var(--hairline-strong); }
  .pstage.first .pnum::before { top: 18px; }
  .pstage.last .pnum::before { bottom: auto; height: 18px; }
  .pnum span { position: relative; display: inline-block; background: var(--surface);
    padding: 2px 0; width: 20px; }
  .pmain { padding: 13px 14px; }
  .pmain h4 { margin: 0 0 4px; font-size: 14px; font-weight: 600; line-height: 1.3; }
  .tech { display: inline-block; font-size: 10.5px; font-weight: 600; letter-spacing: .05em;
    text-transform: uppercase; padding: 2px 8px; border-radius: 999px;
    background: var(--accent-soft); color: var(--accent); }
  .pnote { margin: 7px 0 0; font-size: 12.5px; color: var(--muted); }
  .pcell { padding: 13px 14px; border-left: 1px solid var(--hairline);
    display: flex; flex-direction: column; gap: 2px; }
  .pcell .plab { font-size: 10.5px; text-transform: uppercase; letter-spacing: .07em;
    font-weight: 600; color: var(--faint); }
  .pcell .plab em { font-style: normal; font-weight: 700; }
  .pcell .pval { font-family: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace;
    font-size: 19px; font-weight: 600; font-variant-numeric: tabular-nums; line-height: 1.25; }
  .pcell .pdet { font-size: 12px; color: var(--muted); line-height: 1.45; }
  .pcell .psrc { font-family: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace;
    font-size: 10.5px; color: var(--faint); margin-top: 4px; overflow-wrap: anywhere; }
  .pcell.good { background: var(--good-soft); }
  .pcell.good .pval, .pcell.good .plab em { color: var(--good); }
  .pcell.warn { background: var(--warn-soft); }
  .pcell.warn .pval, .pcell.warn .plab em { color: var(--warn); }
  .pcell.crit { background: var(--crit-soft); }
  .pcell.crit .pval, .pcell.crit .plab em { color: var(--crit); }
  .pcell.grey .pval { color: var(--faint); font-size: 15px; }
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
            sc["ours_current"].get("label", ""))
        scan_cells["Audiveris 5.11"] = cell(
            sc["audiveris"]["omr_ned"], sc["audiveris"]["omr_ed"],
            "%d/11 rows — cannot process Bach (internal NPE); several rows needed hand-holding"
            % sc["audiveris"]["n_rows"])
        scan_note = (" The scan column is the re-stamped 11-row scan benchmark "
                     "(2026-09-04), pooled over the 10 rows both systems "
                     "scored; real IMSLP pages, no dossier.")
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
%(pipeline)s
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
        "pipeline": build_pipeline(content, pipeline_metrics()),
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

        class _Utf8Handler(http.server.SimpleHTTPRequestHandler):
            """The written page is a FRAGMENT — no <head>, so no <meta charset>;
            the artifact host supplies one. A bare SimpleHTTPRequestHandler does
            not, and the preview then renders every ⚠️, → and — as mojibake, which
            reads like a generator bug. Declare it on the wire instead."""
            def guess_type(self, path):
                ctype = http.server.SimpleHTTPRequestHandler.guess_type(self, path)
                if ctype in ("text/html", "text/plain") or str(path).endswith(".html"):
                    return "text/html; charset=utf-8"
                return ctype

        handler = functools.partial(_Utf8Handler, directory=str(ROOT / "docs"))
        print("serving http://localhost:8600/progress-dashboard.html  (Ctrl-C to stop)")
        http.server.HTTPServer(("127.0.0.1", 8600), handler).serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
