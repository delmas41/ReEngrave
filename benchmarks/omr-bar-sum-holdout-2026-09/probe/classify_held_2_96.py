"""ROADMAP 2.96 -- the minimal cause of every held bar, EVIDENCE-GATED.

`classify_held_mvt_2_22.py`'s method (simulate a fix, ask whether the bar then
sums to the printed meter, search the smallest set) with the lesson of
FINDINGS §18 built in: a fix whose arithmetic lands is NOT a cause. §18 found
7 of 13 `D` attributions had no dot anywhere in the cell; the sum simply
coincided. So every simulated fix is one of two TIERS:

  EVIDENCED  the record holds a row that says where the repair is and what it
             is (a refused box with a value, an unexplained ink piece, a dot
             row, a beam-doubt counter, a doubtful owner, a cell twice as wide
             as its neighbours, ...).
  ARITHMETIC the sum would land but nothing in the record points at it.

Per bar: search EVIDENCED tokens alone (size 1..3). Found -> the bar's cause is
that set (the most specific tied set). Else search EVIDENCED + ARITHMETIC; found
-> `arith_only:<tokens>` (a sum, not a diagnosis). Else `unexplained`. The
partition is exhaustive and `main` asserts it sums to the held total (plus the
bars on a doubled staff the exporter counts but cannot locate).

Tokens (a letter for a cause class; refusal reasons are named):
  V  merge two streams (2.21's gate: no shared onset)        evidenced if 2 streams
  S  merge two events <40 cell-units apart (a box twice)     evidenced if such a pair
  E  drop a quarter rest at the cell edge (a barline)        evidenced if such a rest
  W  a lone 4-beat dotless rest IS the bar                   evidenced if such a rest
  K  the cell holds k bars (a missed barline): sum == k*T    evidenced if width ~ k x median
  N  restore a head refused duration_narrowed at a candidate evidenced (the candidates)
  Y  restore a chord_value_undecided head at its candidate   evidenced
  O  restore an owner_not_read head                          evidenced
  Q  restore an owned_by_another_staff head (ownership wrong) evidenced (decided value)
  P  restore a no_pitch head                                 evidenced
  R:<why>  restore a head/rest refused for <why> (too_narrow, clipped_fragment,
        rest_has_a_stem, rest_clipped_by_crop, ...). Value from its own duration
        verdict. DUPLICATE-box refusals and non-notes (clef, digit, dynamic
        letter, ...) are NEVER offered: restoring those is inventing.
  U:<why>  as R but the refused box has NO duration verdict -- position evidence
        only, any standard value
  A  an abstained rest, any standard value                   evidenced (the abstention)
  I  UNBOXED INK: the cell holds ink pieces no standing glyph explains (2.80's
        witness); fill = any standard rest value (or two)    evidenced (the ink)
  D  one dot added/removed                                   evidenced iff a Q.AUG_DOT row is in the cell or an event is dotted
  B  one beam/flag level (both values <= quarter)            evidenced iff a chord's duration verdict carries a beam-doubt counter
  G  every beamed note of one voice one level off            same evidence as B
  F  one head fill/stem (quarter<->half, half<->whole)       evidenced iff a chord's members disagree about class/fill
  X  drop ONE event                                          evidenced iff an event's owner verdict is not DECIDED

    python3 .../classify_held_2_96.py <dump.2.96.held.json> --truth '{"default": 2.0}' --out <partition.json> [--doubled N]
"""
from __future__ import annotations

import argparse
import collections
import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import classify_held_mvt_2_22 as C   # noqa: E402  voices_overlap, _prep, geometry

JOIN = C.JOIN
STD = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
SUSPECT_NOTEHEAD = {"too_narrow", "clipped_fragment", "head_cut_piece",
                    "belongs_to_a_nearer_staff"}
SUSPECT_REST = {"rest_has_a_stem", "rest_clipped_by_crop", "rest_off_center",
                "rest_outside_its_staff", "rest_overlaps_a_notehead",
                "rest_touches_two_staff_lines"}
# specificity order for ties (a refused box with a value first, then
# structure, then ink, then the weakest evidence)
ORDER = ["W", "V", "S", "E", "K", "N", "Y", "O", "P", "Q"]
ORDER_TAIL = ["A", "I:eighth", "I:quarter", "I:half_whole", "D", "B", "G", "F", "X",
              "B~", "G~", "F~", "X~"]


def rank(tok):
    if tok in ORDER:
        return ORDER.index(tok)
    if tok.startswith("R:"):
        return len(ORDER)
    if tok.startswith("U:"):
        return len(ORDER) + 1
    if tok == "K~":
        return len(ORDER) + 21
    if tok == "I:any":
        return len(ORDER) + 20
    return len(ORDER) + 2 + ORDER_TAIL.index(tok)


def _t(e, div):
    return e["units"] / float(div)


def _vals(dv):
    return C._durs(dv)


def refusal_groups(bar):
    """[(token, options)] for every refused box the record points at, plus the
    I (unboxed ink) group. Boxes next to a written event add no time."""
    xs = [e["x"] for s in bar["streams"] for e in s]
    out = []
    why = {}
    for r in bar["refused_in_cell"]:
        box = r.get("box")
        if not box:
            continue
        x = float(box[1]) + float(box[3]) / 2.0
        if any(abs(x - xw) < JOIN for xw in xs):
            continue
        ref = r["refusal"]
        dv = r.get("duration") or {}
        vals = _vals(dv)
        if ref == "duration_narrowed":
            tok, opts = "N", vals
        elif ref == "chord_value_undecided":
            tok, opts = "Y", vals
        elif ref == "owner_not_read":
            tok, opts = "O", vals
        elif ref == "no_pitch":
            tok, opts = "P", vals
        elif ref == "owned_by_another_staff":
            tok, opts = "Q", vals
        elif ref in ("rest_duration_abstained", "rest_duration_narrowed"):
            tok, opts = "A", set(STD)
        elif ref.startswith("not_a_notehead:") or ref.startswith("not_a_rest:"):
            reason = ref.split(":", 1)[1]
            if reason not in SUSPECT_NOTEHEAD | SUSPECT_REST:
                continue
            if vals:
                tok, opts = f"R:{reason}", vals
            else:
                tok, opts = f"U:{reason}", set(STD)
        else:
            continue
        why[tok] = ref
        for o in out:
            if o[0] == tok and abs(o[1] - x) < JOIN:
                o[2] |= set(opts)
                break
        else:
            out.append([tok, x, set(opts)])
    ink = bar.get("ink") or {}
    un = ink.get("unexplained") or []
    by_cls = collections.defaultdict(int)
    for u in un:
        by_cls[u["cls"]] += 1
    shape_opts = {"eighth": {0.25, 0.5, 0.75}, "quarter": {1.0},
                  "half_whole": {2.0, 3.0, 4.0}}
    for cl, n in by_cls.items():
        if cl in shape_opts:
            o = set(shape_opts[cl])
            if n >= 2:
                o |= {a + b for a in o for b in o}
            out.append([f"I:{cl}", 0.0, o])
    if un:                      # ink of ANY shape: the arithmetic-tier version
        rv = set(STD)
        out.append(["I:any", 0.0, rv | {a + b for a in rv for b in rv}
                    if len(un) >= 2 else rv])
    return [(k, sorted(o)) for k, _x, o in out if o]


def mark_events(bar):
    """Per-event flags the evidenced B/G/F/X restrict themselves to."""
    for s in bar["streams"]:
        for e in s:
            e["_beam"] = bool(e["kind"] == "chord" and any(
                d and d.get("beam_doubt") for d in e.get("dur") or []))
            e["_owner"] = bool(e["kind"] == "chord" and any(
                o in ("abstained", "narrowed") for o in e.get("owner") or []))
            cl = e["classes"] if e["kind"] == "chord" else []
            e["_mixed"] = bool(len(set(cl)) > 1 and any(
                ("Half" in c) != ("Half" in cl[0]) or ("Whole" in c) != ("Whole" in cl[0])
                for c in cl))


def evidence(bar, T, groups):
    """Which of the delta/structure tokens are EVIDENCED on this bar."""
    ev = set()
    ev_all = [e for s in bar["streams"] for e in s]
    if bar["n_streams"] > 1 and bar["_overlap"] is not True:
        ev.add("V")
    for s in bar["streams"]:
        xs = sorted(e["x"] for e in s)
        if any(b - a < JOIN for a, b in zip(xs, xs[1:])):
            ev.add("S")
    if any(e["kind"] == "rest" and e["classes"][0] == "restQuarter"
           and (e["x"] < C.EDGE or e["x"] > C.CELL_W - C.EDGE - 20)
           for e in ev_all):
        ev.add("E")
    if any(len(s) == 1 and s[0]["kind"] == "rest" and not s[0]["measure_rest"]
           and s[0]["beats"] == 4.0 and not s[0]["dots"] for s in bar["streams"]):
        ev.add("W")
    w, m = bar.get("cell_w_px"), bar.get("sys_cell_w_median_px")
    bar["_k_ratio"] = (w / m) if (w and m) else None
    if bar["_k_ratio"] and bar["_k_ratio"] >= 1.6:
        ev.add("K")
    # D: a dot the record SAW and did not settle (role abstained / no verdict)
    if any((d.get("role") or {}).get("outcome") != "decided"
           for d in bar.get("dots") or []):
        ev.add("D")
    chords = [e for e in ev_all if e["kind"] == "chord"]
    if any(e["_beam"] for e in chords):
        ev.update(("B", "G"))
    if any(e["_mixed"] for e in chords):
        ev.add("F")
    if any(e["_owner"] for e in chords):
        ev.add("X")
    for k, _o in groups:
        if k != "I:any":
            ev.add(k)
    return ev


def _voice_ok(evs, T, div, fx, extras, kratio):
    if C._is_lone_bar_rest(evs, fx):
        return True
    if ("X" in fx or "X~" in fx) and len(evs) == 2 and any(
            C._is_lone_bar_rest([evs[1 - i]], fx) for i in (0, 1)):
        return True
    sums = {round(sum(_t(e, div) for e in evs), 6)}
    for tok in ("D", "B", "B~", "F", "F~", "X", "X~"):
        if tok not in fx:
            continue
        f = tok[0]
        deltas = {0.0}
        for e in evs:
            b = _t(e, div)
            if f == "B" and tok == "B" and not e.get("_beam"):
                continue
            if f == "F" and tok == "F" and not e.get("_mixed"):
                continue
            if f == "X" and tok == "X" and not e.get("_owner"):
                continue
            if f == "D":
                d = int(e["dots"] or 0)
                undot = b / (2 - 0.5 ** d) if d else b
                deltas.add(undot * 0.5 ** (d + 1))
                if d:
                    deltas.add(-undot * 0.5 ** d)
            elif f in "BF" and e["kind"] == "chord":
                for new in (2.0 * b, b / 2.0):
                    if (max(b, new) <= 1.0 + 1e-9) == (f == "B"):
                        deltas.add(new - b)
            elif f == "X":
                deltas.add(-b)
        sums = {round(s + d, 6) for s in sums for d in deltas}
    for tok in ("G", "G~"):
        if tok not in fx:
            continue
        pool = [e for e in evs if e["kind"] == "chord"
                and _t(e, div) < 1.0 - 1e-9 and (tok == "G~" or e.get("_beam"))]
        grp = sum(_t(e, div) for e in pool)
        if len([e for e in evs if e["kind"] == "chord" and _t(e, div) < 1.0 - 1e-9]) >= 2 and pool:
            sums = {round(s + d, 6) for s in sums for d in (0.0, grp, -grp / 2)}
    for kind, opts in extras:
        if kind not in fx:
            continue
        sums = {round(s + o, 6) for s in sums for o in list(opts) + [0.0]}
    if "K" in fx or "K~" in fx:
        for k in (2, 3, 4):
            if "K" in fx and not (kratio and abs(kratio - k) < 0.45):
                continue
            if round(T * k, 6) in sums:
                return True
    return round(T, 6) in sums


def released(bar, T, fx):
    fxs = set(fx)
    struct = "".join(c for c in fxs if c in "VSE")
    streams = C._prep(bar, struct)
    div = bar["detail"]["divisions"]
    ex = bar["_groups"]
    for i in range(len(streams)):
        if all(_voice_ok(s, T, div, fxs, ex if i == j else [], bar.get("_k_ratio"))
               for j, s in enumerate(streams)):
            return True
    return False


def search(bar, T, toks, max_k):
    for k in range(1, max_k + 1):
        hits = [h for h in itertools.combinations(toks, k) if released(bar, T, h)]
        if hits:
            return hits
    return []


def n_landings(bar, T, kinds=("N", "Y")):
    """For a single-stream bar: how many ways to give every narrowed/undecided
    chord ONE of its own candidates so the bar lands exactly (1 = the record's
    candidates plus the meter decide it uniquely)."""
    if bar["n_streams"] != 1:
        return None
    div = bar["detail"]["divisions"]
    base = sum(_t(e, div) for e in bar["streams"][0])
    gs = [o for k, o in bar["_groups"] if k in kinds]
    if not gs:
        return None
    return sum(1 for ch in itertools.product(*gs)
               if abs(base + sum(ch) - T) < 1e-6)


def residual(bar):
    """want - best voice sum, in quarters (+ = the bar is SHORT)."""
    div = bar["detail"]["divisions"]
    T = bar["detail"]["want_quarters"]
    best = min((T - sum(_t(e, div) for e in s) for s in bar["streams"]),
               key=abs)
    return round(best, 3)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dump")
    ap.add_argument("--truth", required=True)
    ap.add_argument("--max-k", type=int, default=3)
    ap.add_argument("--doubled", type=int, default=0)
    ap.add_argument("--expect-total", type=int, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    d = json.load(open(a.dump))
    truth = json.loads(a.truth)

    primary = collections.Counter()
    single_ev = collections.Counter()
    single_arith = collections.Counter()
    necessary = collections.Counter()
    sub = collections.defaultdict(collections.Counter)
    rows = []
    ev_freq = collections.Counter()
    meter_mismatch = 0
    for b in d["bars"]:
        T = C._truth(truth, b)
        judged = b["detail"]["want_quarters"]
        if abs(judged - T) > 1e-6:
            meter_mismatch += 1
        b["_overlap"] = C.voices_overlap(b)
        mark_events(b)
        b["_groups"] = refusal_groups(b)
        ev = evidence(b, T, b["_groups"])
        arith = ({t + "~" for t in ("B", "G", "F", "X")} | ({"D"} - ev)
                 | ({"K~"} if "K" not in ev else set())
                 | ({"I:any"} if any(k == "I:any" for k, _ in b["_groups"]) else set()))
        for t in ev:
            ev_freq[t] += 1
        ev_toks = sorted(ev, key=rank)
        arith_toks = sorted(arith, key=rank)
        for t in ev_toks:
            if released(b, T, (t,)):
                single_ev[t] += 1
        for t in arith_toks:
            if released(b, T, (t,)):
                single_arith[t] += 1
        res = residual(b)
        tier, key = None, None
        hits = search(b, T, ev_toks, a.max_k)
        if hits:
            tier = "evidenced"
            for t in ev_toks:
                if all(t in h for h in hits):
                    necessary[t] += 1
            best = min(hits, key=lambda h: sorted((rank(t) for t in h),
                                                  reverse=True))
            best = tuple(sorted(best, key=rank))
            key = "+".join(best)
        else:
            hits = search(b, T, ev_toks + arith_toks, a.max_k) if arith_toks else []
            if hits:
                tier = "arith_only"
                best = min(hits, key=lambda h: (sum(t in arith for t in h),
                                                sorted((rank(t) for t in h),
                                                       reverse=True)))
                best = tuple(sorted(best, key=rank))
                key = "+".join(best)
            else:
                tier, key = "unexplained", "unexplained"
        primary[(tier, key)] += 1
        sm = b.get("system_meter") or {}
        lead = key.split("+")[0]
        if tier != "unexplained":
            sub[f"[{tier}] {lead}: system meter verdict"][
                f"{sm.get('outcome')}/{sm.get('reason')}"] += 1
            sub[f"[{tier}] {lead}: residual (+ = short)"][res] += 1
            nref = collections.Counter(r["refusal"] for r in b["refused_in_cell"])
            if lead in ("N", "Y"):
                sub[f"[{tier}] {lead}: ways the record's own candidates land the bar"][
                    n_landings(b, T)] += 1
                sub[f"[{tier}] {lead}: (landings, meter verdict)"][
                    (n_landings(b, T), sm.get("outcome"))] += 1
                sub[f"[{tier}] {lead}: narrowed/undecided heads in the cell"][
                    nref.get("duration_narrowed", 0) + nref.get("chord_value_undecided", 0)] += 1
        if tier == "unexplained":
            sub["unexplained: residual sign"]["short" if res > 0 else "over" if res < 0 else "zero"] += 1
            sub["unexplained: has a refusal"][bool(b["refused_in_cell"])] += 1
            sub["unexplained: ink"][(b.get("ink") or {}).get("answer")] += 1
            sub["unexplained: n_streams"][b["n_streams"]] += 1
            sub["unexplained: residual"][res] += 1
        rows.append({"cell": b["cell"], "measure": (b.get("report") or {}).get("measure"),
                     "part": (b.get("report") or {}).get("part"),
                     "T": T, "judged": judged, "residual": res,
                     "tier": tier, "cause": key, "evidenced_tokens": ev_toks,
                     "n_streams": b["n_streams"],
                     "ink": (b.get("ink") or {}).get("answer"),
                     "n_unexplained_ink": len((b.get("ink") or {}).get("unexplained") or [])})
    n = len(d["bars"])
    total = n + a.doubled
    part_sum = sum(primary.values()) + a.doubled
    ok = (part_sum == a.expect_total == total)
    print(f"{d['label']}: captured {n} + doubled {a.doubled} = {total}; expected "
          f"{a.expect_total}; partition sums to {part_sum}  CONTROL "
          f"{'PASS' if ok else 'FAIL'}")
    print(f"judged != printed meter on {meter_mismatch} bars")
    for tier in ("evidenced", "arith_only", "unexplained"):
        t = sum(v for (tt, _k), v in primary.items() if tt == tier)
        print(f"\n== {tier}: {t} ({100*t/total:.1f}% of {total})")
        for (tt, k), v in primary.most_common():
            if tt == tier:
                print(f"  {v:5d}  {k}")
    print("\nbars on which each token is EVIDENCED (how common the evidence is):",
          dict(ev_freq.most_common()))
    print("\nsingle EVIDENCED fix releases alone:", dict(single_ev.most_common()))
    print("single ARITHMETIC-only fix releases alone:", dict(single_arith.most_common()))
    print("necessary in every minimal evidenced set:", dict(necessary.most_common()))
    for k, c in sub.items():
        if any(w in k for w in ("unexplained", "landings", "W:", "I:eighth: res",
                                "N: system", "D: system", "D: res")):
            print(f"{k}:", dict(c.most_common(8)))
    json.dump({"label": d["label"], "captured": n, "doubled": a.doubled,
               "total": total, "expect_total": a.expect_total,
               "partition_sums": ok, "meter_mismatch": meter_mismatch,
               "primary": {f"{t}|{k}": v for (t, k), v in primary.most_common()},
               "evidence_frequency": ev_freq, "single_evidenced": single_ev, "single_arith": single_arith,
               "necessary": necessary,
               "sub": {k: {str(x): y for x, y in c.items()} for k, c in sub.items()},
               "rows": rows}, open(a.out, "w"), indent=1, default=str)
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
