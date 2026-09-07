#!/usr/bin/env python3
"""Render `metric-registry.json` as one page: **% of achievable, higher is better.**

    python3 -m tools.dashboard.registry_report                  # write HTML + MD
    python3 -m tools.dashboard.registry_report --check          # report staleness
    python3 -m tools.dashboard.registry_report --serve          # preview on :8601

STANDALONE, and deliberately so. `tools/dashboard/generate.py` and
`docs/progress-dashboard.*` are NOT touched — that page is a generated artefact
with a `--check` staleness gate, and rewiring it belongs in a reviewed change,
not beside a renderer written the same night. The proposed integration diff is
in `benchmarks/omr-pipeline-audit-2026-09/REGISTRY_REPORT.md`.

────────────────────────────────────────────────────────────────────────────────
WHY THIS EXISTS, in Sean's words (2026-09-07): *"a single internal measurement
system … a quick read on the dashboard. Currently sometimes 1.000 is what we are
aiming for and other times it would be a horrible score."*

So: **one unit, one direction, every row.** The native value is kept beside it —
the transform is reversible and the registry stores both — but the number a
reader's eye lands on always means the same thing.

FIVE RULES, EACH ENFORCED IN CODE RATHER THAN OBSERVED BY CONVENTION, because
each exists to stop the unit lying:

  1. **Direction is uniform.** Higher is better, everywhere. That is the point.

  2. **`scoreable: false` NEVER renders as a number, and never as 100.** It gets
     no bar element at all — a zero-length bar reads as 0%, and a fabricated 100
     is the worst outcome available here. `_assert_invariants` refuses to render
     a registry that would allow either.

  3. **Engraved and scan never merge.** Separate sections, separate ceilings,
     separate eras. There is NO page-level single number, by construction —
     `generate.py`'s own standing warning ("one colour per stage would be a lie")
     promoted from a comment to a property of the renderer.

  4. **Every row carries its own trustworthiness** — n, era key, noise floor,
     ceiling kind, and whether that ceiling was MEASURED or ASSUMED. A row scored
     against a guessed ceiling is drawn hatched; one scored against measured or
     externally corroborated evidence is drawn solid. They must not look alike.

  5. **`comparable_as` is honoured.** `time_series` (may be differenced) and
     `head_to_head` (may be compared, is NOT a delta) are different relations —
     the round-1 rule that collapsed them forbade the very comparison the
     registry prints. The Audiveris rows render in their own panel, labelled.

THE SHOWCASE is the ledger-zone pair, rendered as TWO ROWS and never one:
`screening_rate` 6.9% is a WORKLOAD figure and is marked unscoreable; the
adjudicated `defect_rate` is 0.98% → **99.02%**. Printing either alone is wrong
in a named direction — 6.9% overstates the defect sevenfold, 0.9% understates
the reviewer's workload sevenfold.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "benchmarks" / "omr-pipeline-audit-2026-09" / "metric-registry.json"
OUT_HTML = ROOT / "benchmarks" / "omr-pipeline-audit-2026-09" / "registry-report.html"
OUT_MD = ROOT / "benchmarks" / "omr-pipeline-audit-2026-09" / "registry-report.md"

#: One threshold pair, on ONE axis. Today `generate.py:_status` branches on
#: `rate` (RATE_GREEN 0.90, higher better) or `ned` (NED_GREEN 0.15, lower
#: better) — two hand-set constants doing the work a ceiling should do. Under
#: the registry there is one number, so there is one pair.
GREEN = 90.0
AMBER = 60.0

#: A ceiling backed by evidence. Anything else is drawn hatched.
TRUSTED_CEILINGS = {
    "measured", "measured_directly", "measured_and_corroborated",
    "measured_single_source", "pre_registered",
}

#: The pair that must never be printed alone. Order matters: screen, then defect.
SHOWCASE = ("labeling:ledger_zone:screening_rate", "labeling:ledger_zone:defect_rate")

FAMILY_ORDER = ["engraved", "scan", "both"]
FAMILY_TITLE = {
    "engraved": "Digitally engraved input",
    "scan": "Scanned input",
    "both": "Cross-cutting",
}
FAMILY_NOTE = {
    "engraved": "Fixtures we render ourselves, so the ink is known by construction. "
                "Says nothing about scan robustness.",
    "scan": "Real printed pages. ⚠️ Every scan row is <b>% of achievable under page "
            "fidelity</b> — the metric's unconstrained floor is zero, reachable by "
            "emitting the encoding instead of the page, which this project calls an "
            "anti-feature.",
    "both": "Rows that belong to neither family alone.",
}


def esc(s) -> str:
    return html.escape(str(s), quote=True)


# ── loading and refusals ─────────────────────────────────────────────────────

def load_registry(path: Path = REGISTRY) -> dict:
    if not path.exists():
        print(f"MISSING REGISTRY: {path}\n"
              f"  Regenerate with probe/build_metric_registry.py — see "
              f"benchmarks/omr-pipeline-audit-2026-09/README-metric-registry.md",
              file=sys.stderr)
        raise SystemExit(2)
    return json.loads(path.read_text())


def assert_invariants(reg: dict) -> list[str]:
    """Refuse to render a registry that could put a fabricated number on screen.

    ⚠️ These are HARD failures, not staleness. `--check` is deliberately not a
    gate on the *figures* (they are supposed to move), but a scoreable row with
    no percentage is not a moving figure — it is a row that would render as
    something, and the only somethings available are 0 and 100.
    """
    bad = []
    for r in reg["rows"]:
        rid = r.get("id", "<no id>")
        if r.get("scoreable") and r.get("pct_of_achievable") is None:
            bad.append(f"{rid}: scoreable:true with no pct_of_achievable — "
                       f"this is the fabricated-100 hazard, refused")
        if not r.get("scoreable") and r.get("pct_of_achievable") is not None:
            bad.append(f"{rid}: scoreable:false but carries a percentage "
                       f"({r['pct_of_achievable']}) — one of the two is wrong")
        if not r.get("scoreable") and not r.get("why_not"):
            bad.append(f"{rid}: unscoreable with no `why_not` — an unscoreable "
                       f"row without a reason is indistinguishable from a bug")
        p = r.get("pct_of_achievable")
        if p is not None and not (0 <= p <= 100):
            bad.append(f"{rid}: pct_of_achievable {p} outside 0-100")
    for rid in SHOWCASE:
        if not any(r["id"] == rid for r in reg["rows"]):
            bad.append(f"showcase row {rid} absent — the screen/defect pair is "
                       f"the clearest case this unit exists to fix and the page "
                       f"asserts it; do not silently drop it")
    return bad


def missing_evidence(reg: dict) -> list[tuple[str, str]]:
    """Rows whose `ceiling.evidence` names a file that is not on disk.

    ⚠️ Reported, NOT fatal. README §6 asks for a build-time refusal; that is
    right for the wired-in dashboard and wrong here, because an evidence file
    may legitimately be absent from a worktree. Silence is what must not happen,
    so the page shows the count and flags the row.
    """
    out = []
    for r in reg["rows"]:
        for e in (r["ceiling"].get("evidence") or []):
            for tok in re.split(r"[·\s]+", e):
                if "/" in tok and tok.endswith((".json", ".md", ".py", ".musicxml")):
                    if not (ROOT / tok).exists():
                        out.append((r["id"], tok))
    return out


# ── per-row derivations ──────────────────────────────────────────────────────

def band(pct: float | None) -> str:
    if pct is None:
        return "grey"
    return "good" if pct >= GREEN else ("warn" if pct >= AMBER else "crit")


def trusted(row: dict) -> bool:
    return row["ceiling"].get("status") in TRUSTED_CEILINGS


def native_str(row: dict) -> str:
    """The raw metric in its own units and its own direction — kept because the
    transform is reversible and losing it would make the page unauditable."""
    v = row.get("value")
    if v is None:
        return "—"
    d = row.get("native_direction") or ""
    arrow = "↓ better" if d == "lower_is_better" else ("↑ better" if d else "")
    return f"{v:.4f} <span class='dim'>({esc(row.get('raw_metric') or '')}{', ' + arrow if arrow else ''})</span>"


def noise_str(row: dict) -> str:
    nf = row.get("noise_floor")
    if not isinstance(nf, dict):
        return "<span class='dim'>no repeat-run figure — this row may not carry a delta</span>"
    if nf.get("status") != "measured":
        return f"<span class='dim'>{esc(nf.get('status') or 'unmeasured')}" + \
               (f" — {esc(nf.get('note'))}" if nf.get("note") else "") + "</span>"
    bits = []
    if nf.get("value_edits") is not None:
        bits.append(f"±{nf['value_edits']} edits")
    if nf.get("value_pct_points") is not None:
        bits.append(f"±{nf['value_pct_points']} pts pooled")
    return esc(" · ".join(bits) or "measured") + \
        (f" <span class='dim'>{esc(nf.get('note'))}</span>" if nf.get("note") else "")


def comparability_chips(row: dict) -> str:
    ca = row.get("comparable_as") or {}
    out = []
    if ca.get("time_series"):
        out.append('<span class="chip ts" title="%s">may be differenced over time</span>'
                   % esc(ca["time_series"]))
    if ca.get("head_to_head"):
        out.append('<span class="chip h2h" title="%s">head-to-head only — NOT a delta</span>'
                   % esc(ca["head_to_head"]))
    if not out:
        out.append('<span class="chip none">standalone — may not be put in a '
                   'sentence with an arrow</span>')
    return "".join(out)


# ── HTML fragments ───────────────────────────────────────────────────────────

def bar(row: dict) -> str:
    """⚠️ A row with no percentage gets NO BAR ELEMENT — not an empty one.

    An empty track reads as 0%, and "the harness cannot see this stage" is a
    ceiling of zero *information*, not a score of zero. The registry says so in
    `ceiling_kinds.visibility`; the renderer has to say it too.
    """
    pct = row.get("pct_of_achievable")
    if pct is None:
        return '<div class="nobar">not on this axis</div>'
    cls = band(pct) + ("" if trusted(row) else " assumed")
    return ('<div class="track"><i class="fill %s" style="width:%.1f%%"></i></div>'
            '<div class="pct %s">%.2f<span class="unit">%%</span></div>'
            % (cls, max(pct, 0.6), band(pct), pct))


def row_html(row: dict) -> str:
    rid = row["id"]
    c = row["ceiling"]
    unscore = not row.get("scoreable")
    ev = ", ".join(esc(x) for x in (c.get("evidence") or [])) or "—"
    ceil_val = "—" if c.get("value") is None else f"{c['value']:g}"
    detail = []
    if row.get("transform"):
        detail.append(f"<code>{esc(row['transform'])}</code>")
    if c.get("control"):
        detail.append("<b>control ·</b> " + c["control"])
    comp = row.get("companions") or {}
    if comp:
        detail.append("<b>companions ·</b> " +
                      ", ".join(f"{esc(k)} {esc(v)}" for k, v in comp.items()))
    for f in (row.get("flags") or []):
        detail.append('<span class="flag">⚠️ %s</span>' % f)

    body = ('<div class="why"><b>unscoreable —</b> %s</div>' % row["why_not"]) if unscore \
        else ('<div class="native">native · %s</div>' % native_str(row))

    return """
    <div class="mrow%(extra)s" id="%(anchor)s">
      <div class="mhead">
        <div>
          <div class="mid">%(id)s</div>
          <div class="mstage">%(stage)s</div>
        </div>
        <div class="mbar">%(bar)s</div>
      </div>
      %(body)s
      <div class="meta">
        <span><b>n</b> %(n)s %(n_unit)s</span>
        <span><b>ceiling</b> %(ck)s = %(cv)s · <i class="%(cs_cls)s">%(cs)s</i></span>
        <span><b>noise floor</b> %(noise)s</span>
        <span class="era"><b>era</b> <code>%(era)s</code></span>
      </div>
      <div class="chips">%(chips)s</div>
      <details><summary>evidence &amp; controls</summary>
        <div class="detail">%(detail)s<div class="ev"><b>evidence ·</b> %(ev)s</div>
        <div class="ev"><b>source ·</b> %(src)s</div></div>
      </details>
    </div>""" % {
        "extra": " unscore" if unscore else "",
        "anchor": esc(rid.replace(":", "-")),
        "id": esc(rid),
        "stage": esc(row.get("stage") or ""),
        "bar": bar(row),
        "body": body,
        "n": esc(row.get("n")),
        "n_unit": esc(row.get("n_unit") or ""),
        "ck": esc(c.get("kind") or "—"),
        "cv": esc(ceil_val),
        "cs": esc(c.get("status") or "—"),
        "cs_cls": "cs-ok" if trusted(row) else "cs-assumed",
        "noise": noise_str(row),
        "era": esc(row.get("era_key") or "—"),
        "chips": comparability_chips(row),
        "detail": "".join(f"<p>{d}</p>" for d in detail) or "<p class='dim'>—</p>",
        "ev": ev,
        "src": esc(row.get("source") or "—"),
    }


def showcase_html(by_id: dict) -> str:
    """The screen/defect pair. TWO ROWS, side by side, with the 7× between them."""
    scr, dfc = by_id[SHOWCASE[0]], by_id[SHOWCASE[1]]
    return """
  <section class="showcase">
    <p class="kicker">The pair that must never be printed alone</p>
    <div class="pairwrap">
      <div class="pair screen">
        <div class="ptag">a SCREEN · workload</div>
        <div class="pnum">%(s_native).1f<span class="unit">%%</span></div>
        <div class="plab">%(s_metric)s</div>
        <div class="pverdict">unscoreable — a screening rate is not an
          achievement number, and never goes on this axis</div>
      </div>
      <div class="pgap"><span>7×</span><small>and both are percentages</small></div>
      <div class="pair defect">
        <div class="ptag">a DEFECT · quality</div>
        <div class="pnum">%(d_pct).2f<span class="unit">%%</span></div>
        <div class="plab">of achievable &nbsp;·&nbsp; native %(d_native).2f%% wrong,
          hand-adjudicated</div>
        <div class="pverdict good-verdict">scoreable — this is the quality figure</div>
      </div>
    </div>
    <p class="showcase-note">⚠️ <b>Printing either alone is wrong in a NAMED
      direction.</b> The auditor flags 7 of 102 ledger-zone labels; hand
      adjudication found <b>one</b> real error. So <b>6.9%% overstates the defect
      sevenfold</b>, and <b>0.9%% understates the reviewer's workload
      sevenfold</b>. Six of the seven flags share one mechanism — a printed
      ledger line print-merging into the notehead's connected component, pulling
      the centroid up to a half-step. Two rows, different <code>stage</code>
      semantics, never one. <span class="dim">n = %(n)s labels,
      <code>%(era)s</code></span></p>
  </section>""" % {
        "s_native": (scr["value"] or 0) * 100,
        "s_metric": esc(scr.get("raw_metric") or ""),
        "d_pct": dfc["pct_of_achievable"],
        "d_native": (dfc["value"] or 0) * 100,
        "n": esc(dfc.get("n")),
        "era": esc(dfc.get("era_key") or ""),
    }


def head_to_head_html(reg: dict) -> str:
    """Rows sharing a `head_to_head` key. Rendered as a COMPARISON, not a delta."""
    groups: dict[str, list] = {}
    for r in reg["rows"]:
        k = (r.get("comparable_as") or {}).get("head_to_head")
        if k:
            groups.setdefault(k, []).append(r)
    pairs = {k: v for k, v in groups.items() if len(v) > 1}
    if not pairs:
        # the registry names the competitive rows explicitly even where the key
        # is one-sided; fall back to those rather than printing nothing.
        comp = [r for r in reg["rows"] if r["ceiling"].get("kind") == "competitive"]
        if not comp:
            return ""
        blocks = []
        for r in comp:
            ours = (r.get("companions") or {}).get("ours")
            blocks.append(
                '<div class="h2hrow"><div class="h2hlab">%s</div>'
                '<div class="h2hnums"><span class="us">ours %s</span>'
                '<span class="vs">vs</span><span class="them">%s %.2f%%</span></div>'
                '<div class="h2hnote">%s</div></div>'
                % (esc(r["id"]),
                   ("%.2f%%" % ours) if isinstance(ours, (int, float)) else "—",
                   esc(r.get("raw_metric") or "external"), r["pct_of_achievable"],
                   esc((r["ceiling"].get("control") or ""))))
        body = "".join(blocks)
    else:
        blocks = []
        for k, rs in pairs.items():
            rs = sorted(rs, key=lambda r: -(r.get("pct_of_achievable") or 0))
            nums = "".join(
                '<span class="%s">%s %.2f%%</span>'
                % ("us" if r["ceiling"].get("kind") != "competitive" else "them",
                   esc(r["id"]), r["pct_of_achievable"]) for r in rs)
            blocks.append('<div class="h2hrow"><div class="h2hlab"><code>%s</code></div>'
                          '<div class="h2hnums">%s</div></div>' % (esc(k), nums))
        body = "".join(blocks)
    return """
  <section>
    <p class="kicker">Head-to-head · same fixtures, same scorer, different system</p>
    <div class="h2h">%s</div>
    <p class="table-caption">⚠️ <b>THIS IS NOT A DELTA AND MUST NOT BE READ AS
      ONE.</b> Two systems can never share a <code>time_series</code> key, so
      nothing here says anything about direction over time — only that on these
      fixtures, through this scorer, one scores above the other. The round-1
      comparability rule was a single era-key equality test and it FORBADE this
      comparison; round 2 split the relation in two, which is why the panel can
      exist at all. Published figures from papers are pooled over other corpora
      and are context, never comparison.</p>
  </section>""" % body


def family_html(reg: dict, family: str) -> str:
    rows = [r for r in reg["rows"] if r["family"] == family]
    if not rows:
        return ""
    rows.sort(key=lambda r: (not r["scoreable"],
                             -(r.get("pct_of_achievable") or -1),
                             r["id"]))
    n_s = sum(1 for r in rows if r["scoreable"])
    return """
  <section>
    <p class="kicker">%s</p>
    <p class="table-caption">%s <span class="dim">· %d rows, %d scoreable, %d not</span></p>
    <div class="mrows">%s</div>
  </section>""" % (esc(FAMILY_TITLE.get(family, family)), FAMILY_NOTE.get(family, ""),
                   len(rows), n_s, len(rows) - n_s,
                   "".join(row_html(r) for r in rows))


CSS = """
  :root {
    --paper:#F7F6F2; --surface:#FFFFFF; --ink:#1D1F27; --muted:#676B76;
    --faint:#9A9DA6; --hairline:#E4E2DA; --hairline-strong:#CFCDC3;
    --accent:#3352C4; --accent-soft:#E7ECFA;
    --good:#2E7D4F; --good-soft:#E4F0E8;
    --warn:#A97A14; --warn-soft:#F5EDD9;
    --crit:#B3382E; --crit-soft:#F6E4E2;
    --shadow:0 1px 2px rgba(29,31,39,.05);
  }
  @media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
    --paper:#14161C; --surface:#1C1F28; --ink:#E9E8E3; --muted:#A0A3AD;
    --faint:#6E7280; --hairline:#2C303B; --hairline-strong:#3A3F4D;
    --accent:#8CA3F2; --accent-soft:#232B44;
    --good:#6DBE8F; --good-soft:#1E3328;
    --warn:#D9AE4E; --warn-soft:#362E17;
    --crit:#E08076; --crit-soft:#3B211E; --shadow:none; } }
  :root[data-theme="dark"] {
    --paper:#14161C; --surface:#1C1F28; --ink:#E9E8E3; --muted:#A0A3AD;
    --faint:#6E7280; --hairline:#2C303B; --hairline-strong:#3A3F4D;
    --accent:#8CA3F2; --accent-soft:#232B44;
    --good:#6DBE8F; --good-soft:#1E3328;
    --warn:#D9AE4E; --warn-soft:#362E17;
    --crit:#E08076; --crit-soft:#3B211E; --shadow:none; }

  * { box-sizing:border-box; }
  body { margin:0; background:var(--paper); color:var(--ink);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
    font-size:15px; line-height:1.5; -webkit-font-smoothing:antialiased; }
  .wrap { max-width:1120px; margin:0 auto; padding:40px 28px 72px; }
  header h1 { font-family:"Source Serif 4",Georgia,"Times New Roman",serif; font-weight:600;
    font-size:34px; margin:0; letter-spacing:-.01em; text-wrap:balance; }
  .masthead-row { display:flex; align-items:baseline; justify-content:space-between;
    gap:16px; flex-wrap:wrap; }
  .stamp { font-family:"IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace;
    font-size:12.5px; color:var(--muted); }
  .stamp b { color:var(--ink); font-weight:600; }
  .stafflines { margin:18px 0 0; display:grid; gap:5px; }
  .stafflines i { display:block; height:1px; background:var(--hairline-strong); }
  .subtitle { color:var(--muted); margin:16px 0 0; max-width:76ch; }
  section { margin-top:40px; }
  .kicker { font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace; font-size:11.5px;
    letter-spacing:.09em; text-transform:uppercase; color:var(--muted); margin:0 0 10px; }
  .table-caption { color:var(--muted); font-size:13.5px; margin:0 0 16px; max-width:88ch; }
  code { font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace; font-size:12px;
    background:var(--accent-soft); padding:1px 5px; border-radius:4px; }
  .dim { color:var(--faint); }

  /* the unit banner */
  .unitbar { display:flex; gap:18px; align-items:center; flex-wrap:wrap;
    background:var(--surface); border:1px solid var(--hairline);
    border-left:3px solid var(--accent); border-radius:10px; padding:16px 20px;
    box-shadow:var(--shadow); margin-top:26px; }
  .unitbar .big { font-family:"Source Serif 4",Georgia,serif; font-size:21px; font-weight:600; }
  .unitbar .sub { color:var(--muted); font-size:13.5px; max-width:70ch; }

  /* rows */
  .mrows { display:grid; gap:12px; }
  .mrow { background:var(--surface); border:1px solid var(--hairline); border-radius:10px;
    padding:14px 16px; box-shadow:var(--shadow); }
  .mrow.unscore { background:transparent; border-style:dashed;
    border-color:var(--hairline-strong); box-shadow:none; }
  .mhead { display:grid; grid-template-columns:minmax(0,1fr) minmax(200px,340px);
    gap:18px; align-items:center; }
  .mid { font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace; font-size:13px;
    font-weight:600; word-break:break-all; }
  .mstage { color:var(--faint); font-size:12.5px; margin-top:2px; }
  .mbar { display:grid; grid-template-columns:1fr auto; gap:10px; align-items:center; }
  .track { height:9px; border-radius:5px; background:var(--hairline); overflow:hidden; }
  .fill { display:block; height:100%; border-radius:5px; background:var(--good); }
  .fill.warn { background:var(--warn); } .fill.crit { background:var(--crit); }
  /* ⚠️ HATCHED = the ceiling is ASSUMED. A row graded against a guess and one
     graded against measured evidence must not look identical. */
  .fill.assumed { background-image:repeating-linear-gradient(135deg,
      rgba(255,255,255,.55) 0 3px, transparent 3px 7px); }
  .pct { font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace; font-size:17px;
    font-weight:600; min-width:78px; text-align:right; }
  .pct.good { color:var(--good); } .pct.warn { color:var(--warn); } .pct.crit { color:var(--crit); }
  .pct .unit { font-size:11px; font-weight:400; color:var(--muted); margin-left:2px; }
  .nobar { grid-column:1/-1; text-align:right; font-size:12.5px; color:var(--faint);
    font-style:italic; }
  .native { margin-top:9px; font-size:13px; color:var(--muted); }
  .why { margin-top:9px; font-size:13.5px; color:var(--ink); background:var(--warn-soft);
    border-radius:7px; padding:9px 12px; }
  .meta { margin-top:10px; display:flex; flex-wrap:wrap; gap:6px 18px; font-size:12.5px;
    color:var(--muted); }
  .meta b { color:var(--ink); font-weight:600; }
  .meta .era code { font-size:11px; }
  .cs-ok { color:var(--good); font-style:normal; font-weight:600; }
  .cs-assumed { color:var(--warn); font-style:normal; font-weight:600; }
  .chips { margin-top:8px; display:flex; gap:6px; flex-wrap:wrap; }
  .chip { font-size:11.5px; padding:2px 8px; border-radius:999px; border:1px solid var(--hairline-strong);
    color:var(--muted); }
  .chip.ts { border-color:var(--good); color:var(--good); background:var(--good-soft); }
  .chip.h2h { border-color:var(--accent); color:var(--accent); background:var(--accent-soft); }
  details { margin-top:8px; }
  summary { cursor:pointer; font-size:12.5px; color:var(--accent); }
  .detail { font-size:12.5px; color:var(--muted); margin-top:6px; }
  .detail p { margin:5px 0; }
  .ev { font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace; font-size:11px;
    color:var(--faint); word-break:break-all; }
  .flag { color:var(--warn); }

  /* showcase */
  .showcase .pairwrap { display:grid; grid-template-columns:1fr auto 1fr; gap:12px;
    align-items:stretch; }
  .pair { background:var(--surface); border:1px solid var(--hairline); border-radius:10px;
    padding:18px 20px; box-shadow:var(--shadow); }
  .pair.screen { border-style:dashed; border-color:var(--warn); background:transparent; }
  .pair.defect { border-left:3px solid var(--good); }
  .ptag { font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace; font-size:11px;
    letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }
  .pair .pnum { font-family:"Source Serif 4",Georgia,serif; font-size:40px; font-weight:600;
    line-height:1.1; margin:6px 0 2px; }
  .pair.screen .pnum { color:var(--warn); } .pair.defect .pnum { color:var(--good); }
  .pair .pnum .unit { font-size:18px; color:var(--muted); }
  .plab { font-size:13px; color:var(--muted); }
  .pverdict { margin-top:10px; font-size:12.5px; color:var(--warn); font-weight:600; }
  .pverdict.good-verdict { color:var(--good); }
  .pgap { display:flex; flex-direction:column; align-items:center; justify-content:center;
    padding:0 6px; }
  .pgap span { font-family:"Source Serif 4",Georgia,serif; font-size:26px; font-weight:600;
    color:var(--crit); }
  .pgap small { color:var(--faint); font-size:10.5px; text-align:center; max-width:96px; }
  .showcase-note { margin-top:14px; font-size:13.5px; color:var(--muted); max-width:92ch; }
  .showcase-note b { color:var(--ink); }

  /* head to head */
  .h2h { display:grid; gap:10px; }
  .h2hrow { background:var(--surface); border:1px solid var(--hairline); border-radius:10px;
    padding:14px 16px; box-shadow:var(--shadow); }
  .h2hlab { font-size:12.5px; color:var(--muted); word-break:break-all; }
  .h2hnums { margin-top:6px; display:flex; gap:14px; align-items:baseline; flex-wrap:wrap;
    font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace; font-size:15px; }
  .h2hnums .us { color:var(--good); font-weight:600; }
  .h2hnums .them { color:var(--accent); font-weight:600; }
  .h2hnums .vs { color:var(--faint); font-size:12px; }
  .h2hnote { margin-top:6px; font-size:12px; color:var(--faint); }

  .legend { display:flex; gap:16px; flex-wrap:wrap; font-size:12.5px; color:var(--muted);
    margin:0 0 18px; }
  .sw { display:inline-block; width:22px; height:9px; border-radius:5px; margin-right:6px;
    vertical-align:middle; }
  .sw.good { background:var(--good); } .sw.warn { background:var(--warn); }
  .sw.crit { background:var(--crit); } .sw.grey { background:var(--hairline-strong); }
  .sw.hatch { background:var(--good); background-image:repeating-linear-gradient(135deg,
      rgba(255,255,255,.55) 0 3px, transparent 3px 7px); }
  .warnbox { background:var(--crit-soft); border-left:3px solid var(--crit); border-radius:8px;
    padding:14px 18px; font-size:13.5px; margin-top:20px; }
  @media (max-width:820px) {
    .mhead { grid-template-columns:1fr; }
    .showcase .pairwrap { grid-template-columns:1fr; }
    .pgap { flex-direction:row; gap:10px; padding:4px 0; }
  }
"""


def render(reg: dict) -> str:
    by_id = {r["id"]: r for r in reg["rows"]}
    cov = reg.get("coverage", {})
    unit = reg.get("unit", {})
    miss = missing_evidence(reg)

    warn = ""
    if miss:
        warn = ('<div class="warnbox"><b>⚠️ %d ceiling-evidence path(s) named by the '
                'registry are not on disk in this tree.</b> Reported rather than fatal — '
                'an evidence file may legitimately be absent from a worktree — but a '
                'ceiling whose evidence cannot be opened is not a measured ceiling. '
                '<code>%s</code></div>'
                % (len(miss), esc("; ".join(f"{a} → {b}" for a, b in miss[:6]))))

    legend = (
        '<div class="legend">'
        '<span><i class="sw good"></i>≥ %.0f%% of achievable</span>'
        '<span><i class="sw warn"></i>%.0f–%.0f%%</span>'
        '<span><i class="sw crit"></i>&lt; %.0f%%</span>'
        '<span><i class="sw hatch"></i>hatched — ceiling <b>ASSUMED</b>, not measured</span>'
        '<span><i class="sw grey"></i>no bar at all — not on this axis</span>'
        '</div>' % (GREEN, AMBER, GREEN, AMBER))

    families = "".join(family_html(reg, f) for f in FAMILY_ORDER)

    return """<title>ReEngrave · %% of Achievable</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,500;8..60,600&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>%(css)s</style>
<div class="wrap">
  <header>
    <div class="masthead-row">
      <h1>%% of Achievable</h1>
      <div class="stamp">registry <b>v%(ver)s</b> · round <b>%(round)s</b> ·
        rendered <b>%(today)s</b></div>
    </div>
    <div class="stafflines" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></div>
    <p class="subtitle">Every measurement this project makes, in <b>one unit and one
      direction</b>. %(why)s</p>
    <div class="unitbar">
      <div>
        <div class="big">%(unit_name)s &nbsp;·&nbsp; 0–100 &nbsp;·&nbsp; higher is better</div>
        <div class="sub"><b>%(n_rows)s rows · %(n_score)s scoreable · %(n_un)s not.</b>
          A row that is not scoreable renders as a <i>reason</i>, never as a number and
          never as 100 — a fabricated 100 is the worst outcome available here. There is
          <b>no single top-line figure on this page</b>: engraved and scan have
          different ceilings, different noise floors and different eras, and pooling
          them would be the lie the dashboard already warns about.</div>
      </div>
    </div>
    %(warn)s
  </header>
%(showcase)s
  <section>
    <p class="kicker">How to read a row</p>
    %(legend)s
    <p class="table-caption">The <b>bar</b> is %% of achievable. <b>Hatched</b> means the
      ceiling was <i>assumed</i> at the value that minimises the score (F = 0 for an
      error metric, C = 1 for a rate) because no evidence exists — so such a row is
      understated by construction and can never manufacture a high number. Every row
      carries <b>n</b>, its <b>era key</b>, its <b>noise floor</b> and the <b>kind</b> of
      ceiling it is graded against; a delta is only meaningful inside one era key, above
      that row's own noise floor, and with the edit count moving the same way as the
      ratio — otherwise it is dilution, not improvement.</p>
  </section>
%(families)s
%(h2h)s
  <section>
    <p class="kicker">The rules this page enforces</p>
    <div class="mrow">
      <div class="detail" style="font-size:13.5px">
        <p><b>independence ·</b> %(r_ind)s</p>
        <p><b>assumption direction ·</b> %(r_asm)s</p>
        <p><b>no fabricated 100 ·</b> %(r_fab)s</p>
        <p><b>pooling ·</b> %(r_pool)s</p>
        <p><b>dilution ·</b> %(r_dil)s</p>
        <p><b>noise floor ·</b> %(r_noise)s</p>
      </div>
    </div>
    <p class="table-caption">Generated from
      <code>benchmarks/omr-pipeline-audit-2026-09/metric-registry.json</code> by
      <code>tools/dashboard/registry_report.py</code>. <b>Do not hand-edit.</b>
      This page is standalone and does not touch
      <code>docs/progress-dashboard.html</code>.</p>
  </section>
</div>
""" % {
        "css": CSS,
        "ver": esc(reg.get("schema_version")),
        "round": esc(reg.get("round")),
        "today": _dt.date.today().isoformat(),
        "why": esc(unit.get("why") or ""),
        "unit_name": esc(unit.get("name") or "% of achievable"),
        "n_rows": esc(cov.get("n_rows")),
        "n_score": esc(cov.get("n_scoreable")),
        "n_un": esc(cov.get("n_unscoreable")),
        "warn": warn,
        "showcase": showcase_html(by_id),
        "legend": legend,
        "families": families,
        "h2h": head_to_head_html(reg),
        "r_ind": esc(reg["rules"]["independence_guard"]),
        "r_asm": esc(reg["rules"]["assumption_direction"]),
        "r_fab": esc(reg["rules"]["no_fabricated_100"]),
        "r_pool": esc(reg["rules"]["pooling"]),
        "r_dil": esc(reg["rules"]["dilution_guard"]),
        "r_noise": esc(reg["rules"]["noise_floor"]),
    }


def render_md(reg: dict) -> str:
    by_id = {r["id"]: r for r in reg["rows"]}
    cov = reg.get("coverage", {})
    scr, dfc = by_id[SHOWCASE[0]], by_id[SHOWCASE[1]]
    out = [
        "# % of achievable — every measurement, one unit, one direction",
        "",
        f"Generated from `metric-registry.json` v{reg.get('schema_version')} "
        f"(round {reg.get('round')}) by `tools/dashboard/registry_report.py`. "
        "**Do not hand-edit.**",
        "",
        f"**{cov.get('n_rows')} rows · {cov.get('n_scoreable')} scoreable · "
        f"{cov.get('n_unscoreable')} not.** Higher is better, everywhere.",
        "",
        "⚠️ **There is no single top-line number here, deliberately.** Engraved and "
        "scan have different ceilings, different noise floors and different eras.",
        "",
        "## The pair that must never be printed alone",
        "",
        f"| | native | % of achievable | verdict |",
        "|---|--:|--:|---|",
        f"| **screen** — {scr.get('raw_metric')} | {(scr['value'] or 0)*100:.1f}% | "
        f"— | unscoreable: a workload figure, not an achievement |",
        f"| **defect** — {dfc.get('raw_metric')} | {(dfc['value'] or 0)*100:.2f}% | "
        f"**{dfc['pct_of_achievable']:.2f}%** | scoreable |",
        "",
        "They differ by **7×** and both are percentages. Printing either alone is wrong "
        "in a named direction: 6.9% overstates the defect sevenfold, 0.9% understates "
        "the reviewer's workload sevenfold.",
        "",
    ]
    for fam in FAMILY_ORDER:
        rows = [r for r in reg["rows"] if r["family"] == fam]
        if not rows:
            continue
        rows.sort(key=lambda r: (not r["scoreable"],
                                 -(r.get("pct_of_achievable") or -1), r["id"]))
        out += [f"## {FAMILY_TITLE.get(fam, fam)}", "",
                "| row | % achievable | native | ceiling | n | trust |",
                "|---|--:|--:|---|--:|---|"]
        for r in rows:
            pct = ("**%.2f**" % r["pct_of_achievable"]) if r["scoreable"] else "_unscoreable_"
            nat = "—" if r.get("value") is None else f"{r['value']:.4f}"
            trust = r["ceiling"].get("status") or "—"
            trust = f"**{trust}**" if trusted(r) else f"_{trust}_"
            out.append(f"| `{r['id']}` | {pct} | {nat} | {r['ceiling'].get('kind') or '—'} "
                       f"| {r.get('n')} | {trust} |")
        out.append("")
        un = [r for r in rows if not r["scoreable"]]
        if un:
            out.append("**Why the unscoreable rows are unscoreable**")
            out.append("")
            for r in un:
                why = re.sub(r"<[^>]+>", "", r["why_not"] or "")
                out.append(f"- `{r['id']}` — {why[:400]}")
            out.append("")
    comp = [r for r in reg["rows"] if r["ceiling"].get("kind") == "competitive"]
    if comp:
        out += ["## Head-to-head — NOT a delta", ""]
        for r in comp:
            ours = (r.get("companions") or {}).get("ours")
            out.append(f"- `{r['id']}` **{r['pct_of_achievable']:.2f}%** vs ours "
                       f"{('%.2f%%' % ours) if isinstance(ours,(int,float)) else '—'} "
                       f"— same fixtures, same scorer, different system. Says nothing "
                       f"about direction over time.")
        out.append("")
    return "\n".join(out)


# ── entry point ──────────────────────────────────────────────────────────────

def _normalise(s: str) -> str:
    return re.sub(r"rendered <b>[\d-]+</b>", "rendered <b>DATE</b>", s)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="REPORT staleness against a fresh render and exit 0. "
                         "Deliberately not a gate: these figures are supposed to "
                         "move. Schema violations still exit 1 — those are not "
                         "moving figures.")
    ap.add_argument("--strict", action="store_true",
                    help="with --check, exit 1 on staleness too (opt in)")
    ap.add_argument("--serve", action="store_true", help="preview on :8601")
    ap.add_argument("--registry", type=Path, default=REGISTRY)
    args = ap.parse_args(argv)

    reg = load_registry(args.registry)

    bad = assert_invariants(reg)
    if bad:
        print("REGISTRY REFUSED — rendering would put a fabricated number on screen:",
              file=sys.stderr)
        for b in bad:
            print("  · " + b, file=sys.stderr)
        return 1

    for rid, path in missing_evidence(reg):
        print(f"WARN: {rid} names ceiling evidence that is not on disk: {path}",
              file=sys.stderr)

    html_out, md_out = render(reg), render_md(reg)

    if args.check:
        stale = []
        for p, fresh in ((OUT_HTML, html_out), (OUT_MD, md_out)):
            if not p.exists():
                stale.append(f"{p.relative_to(ROOT)} does not exist")
            elif _normalise(p.read_text()) != _normalise(fresh):
                stale.append(f"{p.relative_to(ROOT)} differs from a fresh render")
        if stale:
            print("STALE (reporting, not gating — re-run without --check):")
            for s in stale:
                print("  · " + s)
            return 1 if args.strict else 0
        print("OK: registry report is current")
        return 0

    OUT_HTML.write_text(html_out)
    OUT_MD.write_text(md_out)
    print(f"wrote {OUT_HTML.relative_to(ROOT)}")
    print(f"wrote {OUT_MD.relative_to(ROOT)}")
    print(f"  {reg['coverage']['n_rows']} rows · "
          f"{reg['coverage']['n_scoreable']} scoreable · "
          f"{reg['coverage']['n_unscoreable']} rendered as a reason, not a number")

    if args.serve:
        import http.server, functools

        class _Utf8(http.server.SimpleHTTPRequestHandler):
            def guess_type(self, path):
                t = http.server.SimpleHTTPRequestHandler.guess_type(self, path)
                if t in ("text/html", "text/plain") or str(path).endswith(".html"):
                    return "text/html; charset=utf-8"
                return t
        h = functools.partial(_Utf8, directory=str(OUT_HTML.parent))
        print("serving http://localhost:8601/registry-report.html  (Ctrl-C)")
        http.server.HTTPServer(("127.0.0.1", 8601), h).serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
