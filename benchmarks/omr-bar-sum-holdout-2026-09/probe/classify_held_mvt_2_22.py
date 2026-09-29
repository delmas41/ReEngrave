"""ROADMAP 2.22 -- attribute every held bar of a WHOLE MOVEMENT to the minimal
set of simulated fixes that would release it. Reads the dump
`held_funnel_mvt_2_22.py` writes; imports nothing from the exporter.

`classify_held_2_19.py`'s method at movement scale, with its letters kept
where they mean the same thing and new ones where the movement needs them.
A bar is RELEASED under a fix set when every voice, with the fixes applied,
IS the bar (a lone measure rest) or sums exactly to the PRINTED meter.
Without `M`, a bar judged against a meter that is not the printed one can
only be released by `W` (a voice that is the bar whatever the meter).

Every letter is a SIMULATION of a repair, never a claim the repair is right:

  M  meter: judge against the PRINTED meter. Diagnosis-only table
     (`--truth`), taken from the work's dossier (`data/dossiers/*.json`,
     `meter_changes`) and keyed by OUR file's measure number. NEVER a
     pipeline input.
  W  a voice that is ONE dotless 4-beat rest not marked as a measure rest IS
     the bar (CLAUDE.md §10; `size_measure_rest`'s own rule).
  V  ROADMAP 2.21's gate (branch `claude/voice-split-2.21`, BUILT, held for
     Sean): two streams are merged into one unless some chord only in stream
     1 and some chord only in stream 2 share an onset within
     `ONSET_COLUMN_TOLERANCE_SPACES` (0.10) staff spaces of PAGE x. 2.21
     prefers `Q.ONSET_COLUMN` where it is decided; this uses its fallback
     (the staff's own page x) everywhere -- an approximation, named. Where
     page x is missing 2.21 abstains and EXPORT writes one stream, so V
     merges there too.
  H  a meter printed at the bar's head boxed as heads: drop a chord event
     standing within 3.0 staff spaces of the cell's left edge whose heads
     include a stacked pair (dx <= 0.25, dy 0.30-1.20 spaces) -- 2.12l's
     pair test WITHOUT its cross-staff quorum, so an UPPER bound (a real
     third at a bar's head passes it).
  E  drop a quarter rest within 60 canonical units of a cell edge (a
     barline read as a rest).
  S  merge two events of one voice closer than 40 units in x (one chord or
     one rest boxed as two events).
  X  drop ONE event of one voice (a spurious head/rest or a duplicate box
     that nothing refused). The most generic letter; ranked last in ties.
  N  restore a head refused `duration_narrowed` at one of its candidates.
  O  restore a head refused `owner_not_read` at its decided duration (or a
     candidate).
  R  restore a head refused `not_a_notehead:*` at its decided duration; the
     sub-reason is tallied.
  P  restore a head refused `no_pitch` at its decided duration.
  A  restore an abstained rest at any value in {0.5, 1, 1.5, 2, 3}.
  D  add or remove ONE dot on one event.
  B  ONE written note read one beam/flag level off, both values a quarter
     or shorter (eighth<->quarter, 16th<->eighth).
  G  EVERY flagged/beamed note of one voice (shorter than a quarter, at
     least two of them) one level off
     TOGETHER -- one beam group's stroke count misread (added after the
     first unmodelled crops, §17c).
  F  ONE written note whose head FILL or STEM is misread (quarter<->half,
     half<->whole) -- split from 2.19's B at movement scale, because
     `reconcile_duration` cannot reach it by construction (`_admitted`
     never offers a level below 0).

Restored heads join a written event when within 40 units of it (adding no
time) and may go to any ONE voice. D, B, X each contribute a set of deltas
and compose. The search stops at `--max-k` letters; a bar no subset of that
size releases is `none_of_these`.

    python3 .../classify_held_mvt_2_22.py <dump.held.json> --truth '{"default": 2.0}' --out <partition.json>
"""
from __future__ import annotations

import argparse
import collections
import itertools
import json

JOIN = 40.0
EDGE = 60.0
CELL_W = 2048.0
ONSET_TOL_SPACES = 0.10          # rhythm.ONSET_COLUMN_TOLERANCE_SPACES
DIGIT_X_MAX = 3.0
DIGIT_DX = 0.25
DIGIT_DY = (0.30, 1.20)
# tie order: the more SPECIFIC explanation is preferred over the generic one
FIXES = "MWVHENORPASDBGFX"
RANK = {f: i for i, f in enumerate(FIXES)}


def _t(e, div):
    return e["units"] / float(div)


def _centre(pp):
    return (float(pp[0]) + float(pp[2])) / 2.0


def voices_overlap(bar):
    """2.21's gate: True / False / None (cannot tell)."""
    if bar["n_streams"] < 2:
        return None
    s0, s1 = bar["streams"][0], bar["streams"][1]
    k0 = {tuple(e["glyphs"]) for e in s0 if e["kind"] == "chord"}
    k1 = {tuple(e["glyphs"]) for e in s1 if e["kind"] == "chord"}
    up = [e for e in s0 if e["kind"] == "chord" and tuple(e["glyphs"]) not in k1]
    dn = [e for e in s1 if e["kind"] == "chord" and tuple(e["glyphs"]) not in k0]

    def xs(evs):
        out = []
        for e in evs:
            c = [_centre(p) for p in (e.get("page_px") or []) if p]
            if c:
                out.append(sum(c) / len(c))
        return out
    ux, dx = xs(up), xs(dn)
    sp = bar.get("staff_spacing_px")
    if not ux or not dx or not sp:
        return None
    tol = float(sp) * ONSET_TOL_SPACES
    return any(abs(u - d) <= tol for u in ux for d in dx)


def _is_digit_pair(e, css):
    if e["kind"] != "chord" or not css or e["x"] > DIGIT_X_MAX * css:
        return False
    bb = [b for b in e["bboxes"] if b]
    for a, b in itertools.combinations(bb, 2):
        ax, ay = a[0] + a[2] / 2.0, a[1] + a[3] / 2.0
        bx, by = b[0] + b[2] / 2.0, b[1] + b[3] / 2.0
        if abs(ax - bx) <= DIGIT_DX * css \
                and DIGIT_DY[0] * css <= abs(ay - by) <= DIGIT_DY[1] * css:
            return True
    return False


def _prep(bar, fixes):
    css = bar.get("cell_staff_space")
    out = []
    for s in bar["streams"]:
        evs = [dict(e) for e in s]
        if "H" in fixes:
            evs = [e for e in evs if not _is_digit_pair(e, css)]
        if "E" in fixes:
            evs = [e for e in evs if not (
                e["kind"] == "rest" and e["classes"][0] == "restQuarter"
                and (e["x"] < EDGE or e["x"] > CELL_W - EDGE - 20))]
        out.append(evs)
    if "V" in fixes and len(out) > 1 and bar["_overlap"] is not True:
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


def _is_lone_bar_rest(evs, fixes):
    if len(evs) == 1 and evs[0]["measure_rest"]:
        return True
    return ("W" in fixes and len(evs) == 1 and evs[0]["kind"] == "rest"
            and not evs[0]["measure_rest"] and evs[0]["beats"] == 4.0
            and not evs[0]["dots"])


def _voice_ok(evs, T, div, fixes, extras):
    if _is_lone_bar_rest(evs, fixes):
        return True
    # X is also STRUCTURAL: dropping the one spurious event may leave a lone
    # whole rest, which is the bar whatever the meter
    if "X" in fixes and len(evs) == 2 and any(
            _is_lone_bar_rest([evs[1 - i]], fixes) for i in (0, 1)):
        return True
    if T != T:
        return False
    sums = {round(sum(_t(e, div) for e in evs), 6)}
    for f in "DBFX":
        if f not in fixes:
            continue
        deltas = {0.0}
        for e in evs:
            b = _t(e, div)
            if f == "D":
                d = int(e["dots"] or 0)
                undot = b / (2 - 0.5 ** d) if d else b
                deltas.add(undot * 0.5 ** (d + 1))
                if d:
                    deltas.add(-undot * 0.5 ** d)
            elif f in "BF" and e["kind"] == "chord":
                # B: a beam/flag level (both values a quarter or shorter);
                # F: a head fill or stem (quarter<->half, half<->whole)
                for new in (2.0 * b, b / 2.0):
                    if (max(b, new) <= 1.0 + 1e-9) == (f == "B"):
                        deltas.add(new - b)
            elif f == "X":
                deltas.add(-b)
        sums = {round(s + d, 6) for s in sums for d in deltas}
    if "G" in fixes:
        # every beamable note of the voice (a quarter or shorter) one level
        # off TOGETHER -- a beam GROUP's stroke count misread once
        beamed = [_t(e, div) for e in evs
                  if e["kind"] == "chord" and _t(e, div) < 1.0 - 1e-9]
        grp = sum(beamed)
        if len(beamed) >= 2:
            sums = {round(s + d, 6) for s in sums for d in (0.0, grp, -grp / 2)}
    for kind, opts in extras:
        if kind not in fixes:
            continue
        sums = {round(s + o, 6) for s in sums for o in list(opts) + [0.0]}
    return round(T, 6) in sums


def _durs(dv):
    if not dv:
        return set()
    if dv.get("outcome") == "decided" and isinstance(dv.get("value"), dict) \
            and dv["value"].get("beats") is not None:
        return {float(dv["value"]["beats"])}
    return {float(c["value"]["beats"]) for c in (dv.get("candidates") or [])
            if isinstance(c.get("value"), dict)
            and c["value"].get("beats") is not None}


def _extras(bar):
    """(letter, options) per refused event, grouped by x; and sub-reasons."""
    xs_written = [e["x"] for s in bar["streams"] for e in s]
    groups, why = [], collections.defaultdict(set)
    for r in bar["refused_in_cell"]:
        box = r.get("box")
        if not box:
            continue
        x = float(box[1]) + float(box[3]) / 2.0
        dv = r.get("duration") or {}
        ref = r["refusal"]
        if ref == "duration_narrowed":
            kind, opts = "N", _durs(dv)
        elif ref == "owner_not_read":
            kind, opts = "O", _durs(dv)
        elif ref.startswith("not_a_notehead"):
            kind = "R"
            opts = _durs(dv) if dv.get("outcome") == "decided" else set()
        elif ref == "no_pitch":
            kind, opts = "P", _durs(dv)
        elif ref == "rest_duration_abstained":
            kind, opts = "A", {0.5, 1.0, 1.5, 2.0, 3.0}
        else:
            continue
        if not opts or any(abs(x - xw) < JOIN for xw in xs_written):
            continue
        why[kind].add(ref)
        g = next((g for g in groups if g[0] == kind and abs(g[1] - x) < JOIN),
                 None)
        if g is None:
            groups.append([kind, x, set(opts)])
        else:
            g[2] |= opts
    return [(k, sorted(o)) for k, _x, o in groups], why


def released(bar, T_true, fixes):
    judged = bar["detail"]["want_quarters"]
    div = bar["detail"]["divisions"]
    T = T_true if ("M" in fixes or abs(judged - T_true) < 1e-6) \
        else float("nan")
    streams = _prep(bar, fixes)
    extras = bar["_extras"]
    for i in range(len(streams)):
        if all(_voice_ok(s, T, div, fixes, extras if i == j else [])
               for j, s in enumerate(streams)):
            return True
    return False


def _truth(truth, bar):
    """A `page/system/cell` key first (the print located by eye, as 2.19
    keyed it), then OUR file's measure number, then the default."""
    p, s, _st, c = bar["cell"]
    if f"{p}/{s}/{c}" in truth:
        return float(truth[f"{p}/{s}/{c}"])
    m = (bar.get("report") or {}).get("measure")
    return float(truth.get(str(m), truth["default"]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dump")
    ap.add_argument("--truth", required=True,
                    help='JSON {"<our measure no.>": quarters, "default": q}')
    ap.add_argument("--max-k", type=int, default=4)
    ap.add_argument("--out")
    a = ap.parse_args()
    d = json.load(open(a.dump))
    truth = json.loads(a.truth)

    single = collections.Counter()
    minimal = collections.Counter()
    chosen = collections.Counter()
    necessary = collections.Counter()
    r_reasons = collections.Counter()
    meter_ctx = collections.Counter()
    overlap = collections.Counter()
    rows = []
    for b in d["bars"]:
        T = _truth(truth, b)
        b["_overlap"] = voices_overlap(b)
        b["_extras"], why = _extras(b)
        if b["n_streams"] > 1:
            overlap[str(b["_overlap"])] += 1
        live = [f for f in FIXES
                if f not in "NORPA" or any(k == f for k, _ in b["_extras"])]
        for f in FIXES:
            if f in live and released(b, T, f):
                single[f] += 1
        found = None
        for k in range(1, a.max_k + 1):
            hits = ["".join(x) for x in itertools.combinations(live, k)
                    if released(b, T, "".join(x))]
            if hits:
                found = hits
                break
        if found:
            for f in FIXES:
                if all(f in h for h in found):
                    necessary[f] += 1
            best = min(found, key=lambda h: sorted(RANK[c] for c in h)[::-1])
            chosen[best] += 1
            if "R" in best:
                for r in why.get("R", ()):
                    r_reasons[r] += 1
            if "M" in best:
                sm = b.get("system_meter") or {}
                meter_ctx[(sm.get("outcome"), sm.get("reason"),
                           b["detail"]["want_quarters"])] += 1
        else:
            best = None
            chosen["none_of_these"] += 1
        key = " | ".join(found) if found else "none_of_these"
        minimal[key] += 1
        tot = [round(sum(_t(e, b["detail"]["divisions"]) for e in s), 4)
               for s in b["streams"]]
        rows.append({"cell": b["cell"],
                     "measure": (b.get("report") or {}).get("measure"),
                     "part": (b.get("report") or {}).get("part"),
                     "T": T, "judged": b["detail"]["want_quarters"],
                     "voice_sums": tot, "n_streams": b["n_streams"],
                     "minimal": found, "chosen": best})
    n = len(d["bars"])
    print(f"{d['label']} {d['phase']}: held bars {n}")
    print("single fix releases outright:", dict(single.most_common()))
    print("necessary (in every minimal set):", dict(necessary.most_common()))
    print("chosen minimal set (ties -> most specific):")
    for k, v in chosen.most_common(25):
        print(f"  {v:5d}  {k}")
    print("R sub-reasons in chosen R sets:", dict(r_reasons.most_common()))
    print("meter context where M chosen:",
          [(list(k), v) for k, v in meter_ctx.most_common(8)])
    print("2.21 overlap on multi-stream bars:", dict(overlap))
    if a.out:
        json.dump({"label": d["label"], "phase": d["phase"], "held": n,
                   "truth": truth, "max_k": a.max_k,
                   "single": single, "necessary": necessary,
                   "chosen": chosen, "minimal": dict(minimal.most_common()),
                   "r_reasons": r_reasons,
                   "meter_context": [[list(k), v]
                                     for k, v in meter_ctx.most_common()],
                   "overlap_2_21": overlap, "rows": rows},
                  open(a.out, "w"), indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
