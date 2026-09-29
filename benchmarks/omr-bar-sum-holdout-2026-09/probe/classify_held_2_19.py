"""ROADMAP 2.19 -- attribute every held bar to the MINIMAL set of fixes that
would release it. Reads the dump `held_funnel_2_19.py` writes; imports
nothing from the exporter.

A bar is RELEASED under a fix set when every voice, with those fixes applied,
either IS the bar (a lone measure rest) or sums exactly to the PRINTED meter.
Without `M` the bar is still judged against the meter 2.8 used, so where that
meter is not the printed one a voice landing on it would be a WRONG bar
written, not a release: only `W` (a voice that IS the bar whatever the meter)
can release such a bar on its own.

Fixes -- each a SIMULATION of a repair, never a claim that the repair is
right (the crops are for that):

  M  meter: judge against the printed meter (--truth, a diagnosis-only table
     read off the print by eye; NEVER a pipeline input)
  W  a voice that is exactly ONE dotless 4-beat rest not marked as a measure
     rest IS the bar (CLAUDE.md §10) -- `size_measure_rest`'s own rule
  H  drop hollow "heads" standing where a meter is PRINTED (--meter-ink, the
     x-window of each printed meter, read off the print by eye)
  E  drop a quarter rest within 60 canonical units of the cell's edge (a
     barline read as a rest)
  V  one voice: merge the streams (`adjudicate_voices` splits by stem
     direction alone -- `voicing.split_events_into_voices` V1)
  N  restore the cell's NARROWED heads with some choice of their own
     candidates (a head within 40 units of a written event joins it and
     adds no time)
  R  restore heads refused `not_a_notehead:*` at their decided duration
     (same x-join)
  A  restore an abstained rest at any value in {0.5, 1, 1.5, 2, 3}
  D  add or remove ONE dot on one event
  S  merge two events of one voice closer than 40 units in x (a chord, or a
     rest/note pair, split into two events)
  B  ONE written note read one beam/flag level off (value doubled or
     halved) -- `reconcile_duration`'s search, without its uniqueness bound

For a multi-voice bar restored heads may go to any ONE voice (an upper bound
on N/R/A). A bar no subset releases is `none_of_these`.
"""
from __future__ import annotations

import argparse
import collections
import itertools
import json

JOIN = 40.0
EDGE = 60.0
CELL_W = 2048.0
FIXES = "MWHEVNRADSB"


def _t(e, div):
    return e["units"] / float(div)


def _prep(streams, fixes, meter_ink):
    """Apply the structural fixes (H, E, V, S) to the streams."""
    out = []
    for s in streams:
        evs = [dict(e) for e in s]
        if "H" in fixes and meter_ink:
            evs = [e for e in evs if not (
                e["kind"] == "chord"
                and any(str(c).startswith(("noteheadWhole", "noteheadHalf"))
                        for c in e["classes"])
                and any(lo <= e["x"] <= hi for lo, hi in meter_ink))]
        if "E" in fixes:
            evs = [e for e in evs if not (
                e["kind"] == "rest" and e["classes"][0] == "restQuarter"
                and (e["x"] < EDGE or e["x"] > CELL_W - EDGE - 20))]
        out.append(evs)
    if "V" in fixes and len(out) > 1:
        seen, merged = set(), []
        for s in out:
            for e in s:
                k = tuple(e["glyphs"])
                if k in seen:
                    continue
                seen.add(k)
                merged.append(e)
        out = [sorted(merged, key=lambda e: e["x"])]
    if "S" in fixes:
        new = []
        for s in out:
            merged = []
            for e in sorted(s, key=lambda e: e["x"]):
                if merged and e["x"] - merged[-1]["x"] < JOIN:
                    if e["units"] > merged[-1]["units"]:
                        merged[-1] = e
                    continue
                merged.append(e)
            new.append(merged)
        out = new
    return out


def _voice_ok(evs, T, div, fixes, extras):
    if len(evs) == 1 and evs[0]["measure_rest"]:
        return True
    if "W" in fixes and len(evs) == 1 and evs[0]["kind"] == "rest" \
            and not evs[0]["measure_rest"] and evs[0]["beats"] == 4.0 \
            and not evs[0]["dots"]:
        return True
    if T != T:        # NaN: judged against a meter that is not the printed one
        return False
    base = sum(_t(e, div) for e in evs)
    sums = {round(base, 6)}
    if "D" in fixes:
        for e in evs:
            b = _t(e, div)
            d = int(e["dots"] or 0)
            undot = b / (2 - 0.5 ** d) if d else b
            sums.add(round(base + undot * 0.5 ** (d + 1), 6))
            if d:
                sums.add(round(base - undot * 0.5 ** d, 6))
    if "B" in fixes:
        for e in evs:
            if e["kind"] == "chord":
                b = _t(e, div)
                sums.add(round(base + b, 6))        # one level longer
                sums.add(round(base - b / 2.0, 6))  # one level shorter
    for kind, opts in extras:
        if kind not in fixes:
            continue
        sums = {round(s + o, 6) for s in sums for o in opts}
    return round(T, 6) in sums


def _extras(bar):
    """(fix letter, options) per refused event, grouped by x."""
    xs_written = [e["x"] for s in bar["streams"] for e in s]
    groups = []
    for r in bar["refused_in_cell"]:
        box = r.get("box")
        if not box:
            continue
        x = float(box[1]) + float(box[3]) / 2.0
        dv = r.get("duration") or {}
        ref = r["refusal"]
        if ref == "duration_narrowed":
            opts = {float(c["value"]["beats"])
                    for c in (dv.get("candidates") or [])
                    if isinstance(c.get("value"), dict)
                    and c["value"].get("beats") is not None}
            kind = "N"
        elif ref.startswith("not_a_notehead"):
            v = dv.get("value") if dv.get("outcome") == "decided" else None
            if not isinstance(v, dict) or v.get("beats") is None:
                continue
            opts, kind = {float(v["beats"])}, "R"
        elif ref == "rest_duration_abstained":
            opts, kind = {0.5, 1.0, 1.5, 2.0, 3.0}, "A"
        else:
            continue
        if not opts or any(abs(x - xw) < JOIN for xw in xs_written):
            continue
        g = next((g for g in groups if g[0] == kind and abs(g[1] - x) < JOIN),
                 None)
        if g is None:
            groups.append([kind, x, set(opts)])
        else:
            g[2] |= opts
    return [(k, sorted(o)) for k, _x, o in groups]


def released(bar, T_true, fixes, meter_ink):
    judged = bar["detail"]["want_quarters"]
    div = bar["detail"]["divisions"]
    T = T_true if ("M" in fixes or abs(judged - T_true) < 1e-6) \
        else float("nan")
    streams = _prep(bar["streams"], fixes, meter_ink)
    extras = _extras(bar)
    for i in range(len(streams)):
        if all(_voice_ok(s, T, div, fixes, extras if i == j else [])
               for j, s in enumerate(streams)):
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dump")
    ap.add_argument("--truth", required=True,
                    help='JSON {"page/system/cell": quarters, "default": q}')
    ap.add_argument("--meter-ink", default="{}",
                    help='JSON {"page/system/cell": [[x0, x1], ...]}')
    ap.add_argument("--out")
    a = ap.parse_args()
    d = json.load(open(a.dump))
    truth = json.loads(a.truth)
    ink = json.loads(a.meter_ink)

    single = collections.Counter()
    minimal = collections.Counter()
    necessary = collections.Counter()
    rows = []
    for b in d["bars"]:
        p, s, _st, c = b["cell"]
        T = float(truth.get(f"{p}/{s}/{c}", truth["default"]))
        mi = ink.get(f"{p}/{s}/{c}") or []
        for f in FIXES:
            if released(b, T, f, mi):
                single[f] += 1
        found = None
        for k in range(1, len(FIXES) + 1):
            hits = ["".join(x) for x in itertools.combinations(FIXES, k)
                    if released(b, T, "".join(x), mi)]
            if hits:
                found = hits
                break
        if found:
            for f in FIXES:
                if all(f in h for h in found):
                    necessary[f] += 1
        key = " | ".join(found) if found else "none_of_these"
        minimal[key] += 1
        rows.append({"cell": b["cell"], "measure": (b.get("report") or {})
                     .get("measure"), "T": T,
                     "judged": b["detail"]["want_quarters"],
                     "quarters": b["detail"]["quarters"], "minimal": found})
    print(f"held bars: {len(d['bars'])}")
    print("single fix releases outright:", dict(single))
    print("fix in EVERY minimal set of the bar (necessary):", dict(necessary))
    print("minimal sets:")
    for k, v in minimal.most_common():
        print(f"  {v:4d}  {k}")
    if a.out:
        json.dump({"single": single, "necessary": necessary,
                   "minimal": minimal, "rows": rows},
                  open(a.out, "w"), indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
