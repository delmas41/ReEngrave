"""HYPOTHESIS A, SHARPENED: does a SHARED stem fail to reach its inner members?

`probe_shared_stems.py` reported 23.2% of x-columns MIXED. A share is not
evidence without a null -- under independence a column of two heads drawn from
a population 35.4% stemless is MIXED 46% of the time, so 23.2% could be
BELOW chance, which would be the opposite of what hypothesis A predicts.

⚠️ `Q.EVENT` IS THE RECORD'S OWN CHORD GROUPING AND IT MAY NOT BE USED HERE.
`adjudicate_event` declares `wants=(..., Q.STEM_DIRECTION)` and its divisi
guard RUNS on it, so grouping by `Q.EVENT` and then asking about
`stem_direction` is the arbiter-correlated-with-a-party fault this thread
already paid for once. Columns are built from GLYPH BOXES alone.

Three questions:
  1. the permutation NULL for the mixed share;
  2. how many heads each detected stem actually CARRIES -- if shared stems were
     broken, almost every stem would carry exactly one;
  3. the decisive one: a stem that ALREADY serves a head, and a stemless head
     standing in its x-span that it fails to reach in y. That is hypothesis A
     stated as a geometry, and it is countable.
"""
from __future__ import annotations

import argparse
import collections
import json
import random
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr.staged.adjudicators.rhythm import _xywh_head, _boxes_overlap  # noqa: E402
from tools.omr.staged.record import Kind, Subject                            # noqa: E402


def cell_of(k):
    return Subject.from_key(k).at(Kind.CELL).to_key()


def x_overlap(a, b):
    return a[0] <= b[0] + b[2] and a[0] + a[2] >= b[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--json", default=str(HERE / "out" / "chord-columns.json"))
    ap.add_argument("--tol", type=float, default=0.35)
    ap.add_argument("--draws", type=int, default=400)
    a = ap.parse_args()

    doc = json.load(open(a.record))
    rec = doc["record"] if "record" in doc else doc

    box_of, space_of, step_of = {}, {}, {}
    stems = collections.defaultdict(list)
    heads = collections.defaultdict(list)
    for o in rec["observations"]:
        q = o["quantity"]
        if q == "glyph_box":
            b = _xywh_head(o.get("value"))
            if b is not None:
                box_of[o["subject"]] = b
        elif q == "stem":
            v = o.get("value")
            if isinstance(v, (list, tuple)) and len(v) == 4:
                stems[cell_of(o["subject"])].append(tuple(float(t) for t in v))
        elif q == "cell_staff_space":
            try:
                space_of[cell_of(o["subject"])] = float(o["value"])
            except (TypeError, ValueError):
                pass
        elif q == "notehead_staff_position":
            try:
                step_of[o["subject"]] = float(o["value"])
            except (TypeError, ValueError):
                pass
    for o in rec["observations"]:
        if o["quantity"] == "notehead_class":
            b = box_of.get(o["subject"])
            if b is not None:
                heads[cell_of(o["subject"])].append((o["subject"], b))

    verdicts = [v for v in rec["verdicts"] if v["quantity"] == "stem_direction"]
    no_stem = {v["subject"] for v in verdicts if v["reason"] == "no_stem"}
    decided = {v["subject"] for v in verdicts if v["outcome"] == "decided"}
    every = no_stem | decided

    print("== REACH")
    print(f"   cells with heads   {len(heads):6d}")
    print(f"   heads with a box   {sum(1 for s in every if s in box_of):6d}")
    print(f"   stem rows          {sum(len(v) for v in stems.values()):6d}")
    if not heads or not stems:
        print("DEAD.")
        return 2

    # ── 2: how many heads does each DETECTED stem carry? ──────────────────
    carry = collections.Counter()
    for c, ss in stems.items():
        hs = heads.get(c, [])
        for s in ss:
            carry[sum(1 for _sub, b in hs if _boxes_overlap(b, s))] += 1
    tot = sum(carry.values())
    print("\n== A-q2: heads carried by each detected stem "
          "(shared stems, if they work, show up here)")
    for k in sorted(carry):
        print(f"   {k} head(s): {carry[k]:5d}  "
              f"({100.0 * carry[k] / tot:5.1f}%)")

    # ── 1: columns and the permutation null ───────────────────────────────
    def columns(cell_heads, tol):
        items = sorted(cell_heads, key=lambda t: t[1][0] + t[1][2] / 2.0)
        out, cur = [], []
        for sub, b in items:
            cx = b[0] + b[2] / 2.0
            if cur and abs(cx - cur[-1][1]) > tol * max(cur[-1][2], b[2], 1.0):
                out.append(cur)
                cur = []
            cur.append((sub, cx, b[2]))
        if cur:
            out.append(cur)
        return out

    cols = []
    cols_cell = []
    cell_pool = {}
    for c, hs in heads.items():
        scored = [(s, b) for s, b in hs if s in every]
        cell_pool[c] = [1 if s in decided else 0 for s, _ in scored]
        for col in columns(scored, a.tol):
            if len(col) >= 2:
                cols.append([s for s, _, _ in col])
                cols_cell.append(c)
    obs_mixed = sum(1 for col in cols
                    if 0 < sum(1 for s in col if s in decided) < len(col))
    print(f"\n== A-q1: {len(cols)} columns of >=2 heads at tol {a.tol}; "
          f"MIXED = {obs_mixed} ({100.0 * obs_mixed / max(1, len(cols)):.1f}%)")

    pool = [1 if s in decided else 0 for col in cols for s in col]
    rng = random.Random(20260917)
    null = []
    for _ in range(a.draws):
        shuffled = pool[:]
        rng.shuffle(shuffled)
        i, m = 0, 0
        for col in cols:
            k = len(col)
            seg = shuffled[i:i + k]
            i += k
            if 0 < sum(seg) < k:
                m += 1
        null.append(m)
    null.sort()
    mean = sum(null) / len(null)
    below = sum(1 for n in null if n <= obs_mixed)
    print(f"   NULL (labels shuffled within the column population, "
            f"{a.draws} draws): mean {mean:.1f}, "
            f"p5 {null[int(0.05 * len(null))]}, p95 {null[int(0.95 * len(null))]}")
    print(f"   observed {obs_mixed} -> {below}/{a.draws} null draws are <= it")
    # ⚠️ A SECOND, STRICTER NULL, AND IT IS THE ONE THAT ANSWERS A.
    # The null above shuffles across the WHOLE column population, so a bar
    # where the CV rung read nothing at all -- 211 of the 793 heads sit in
    # one -- makes its columns all-stemless for a reason that has nothing to
    # do with sharing a stem, and drives the observed count below chance on
    # its own. Shuffling WITHIN EACH CELL holds that constant and asks the
    # question hypothesis A actually poses: given this bar's own mix of
    # stemmed and stemless heads, do heads standing at ONE x share an outcome
    # more than two heads of that bar drawn at random?
    null2 = []
    for _ in range(a.draws):
        perm = {}
        for c, lab in cell_pool.items():
            v = lab[:]
            rng.shuffle(v)
            perm[c] = v
        idx = collections.Counter()
        m2 = 0
        for col, c in zip(cols, cols_cell):
            # positions within the cell are consumed in the order the columns
            # were built, which is the same order `columns()` produced them
            seg = []
            for _s in col:
                seg.append(perm[c][idx[c]])
                idx[c] += 1
            if 0 < sum(seg) < len(seg):
                m2 += 1
        null2.append(m2)
    null2.sort()
    mean2 = sum(null2) / len(null2)
    below2 = sum(1 for n in null2 if n <= obs_mixed)
    print(f"   NULL-2 (labels shuffled WITHIN EACH CELL, {a.draws} draws): "
          f"mean {mean2:.1f}, p5 {null2[int(0.05 * len(null2))]}, "
          f"p95 {null2[int(0.95 * len(null2))]}")
    print(f"   observed {obs_mixed} -> {below2}/{a.draws} null-2 draws are <= it")
    verdict_q2 = ("MORE mixed than a bar-matched null -- hypothesis A"
                  if obs_mixed > null2[int(0.95 * len(null2))] else
                  "FEWER mixed than a bar-matched null -- an x-column SHARES "
                  "its outcome beyond what the bar explains"
                  if obs_mixed < null2[int(0.05 * len(null2))] else
                  "indistinguishable from a bar-matched null")
    print(f"   => {verdict_q2}")

    verdict_q1 = ("MORE mixed than chance (hypothesis A's prediction)"
                  if obs_mixed > null[int(0.95 * len(null))] else
                  "FEWER mixed than chance -- a column's heads SHARE an outcome"
                  if obs_mixed < null[int(0.05 * len(null))] else
                  "indistinguishable from chance")
    print(f"   => {verdict_q1}")

    # ── 3: THE DECISIVE TEST ──────────────────────────────────────────────
    # A stem that already serves a head, and a stemless head standing in its
    # x-span that it fails to reach in y.
    print("\n== A-q3: a SERVED stem whose x-span covers a STEMLESS head it "
          "does not reach in y")
    hit, gaps = set(), []
    for c, ss in stems.items():
        hs = heads.get(c, [])
        sp = space_of.get(c) or 0.0
        for s in ss:
            served = [sub for sub, b in hs if _boxes_overlap(b, s)]
            if not served:
                continue
            for sub, b in hs:
                if sub not in no_stem or _boxes_overlap(b, s):
                    continue
                if not x_overlap(b, s):
                    continue
                dy = max(s[1] - (b[1] + b[3]), b[1] - (s[1] + s[3]), 0.0)
                hit.add(sub)
                if sp:
                    gaps.append(dy / sp)
    print(f"   stemless heads in this shape   {len(hit):5d}"
          f"  ({100.0 * len(hit) / max(1, len(no_stem)):5.1f}% of "
          f"{len(no_stem)})")
    if gaps:
        gaps.sort()
        print(f"   y-gap to that stem: median {statistics.median(gaps):.2f} "
              f"spaces, p10 {gaps[int(0.1 * len(gaps))]:.2f}, "
              f"p90 {gaps[int(0.9 * len(gaps))]:.2f}")
        for cut in (0.25, 0.5, 1.0, 2.0):
            n = sum(1 for g in gaps if g <= cut)
            print(f"   ... within {cut:>4.2f} spaces of it: {n:5d}")

    # ── A-q4: THE SHARPEST CASE -- the displaced head of a SECOND ────────
    # Sean, 2026-09-17: any notes sounding on the same beat in one voice share
    # ONE stem, whatever the interval; a SECOND is special only because the two
    # heads cannot both sit on the same side of that stem, so one is displaced
    # to the far side. That displaced head is the one whose box is most likely
    # to miss the stem, so if hypothesis A holds anywhere it holds hardest
    # here. `Q.NOTEHEAD_STAFF_POSITION` is in half steps, so a second is 1.0.
    print(f"\n== A-q4: a STEMLESS head one staff step from a STEMMED head at "
          f"the same x (the displaced head of a second)")
    print(f"   heads carrying a staff position: {len(step_of)}")
    second, by_interval = set(), collections.Counter()
    for c, hs in heads.items():
        scored = [(s, b) for s, b in hs if s in every]
        for col in columns(scored, a.tol):
            subs = [s for s, _, _ in col]
            if len(subs) < 2:
                continue
            for s in subs:
                if s not in no_stem or s not in step_of:
                    continue
                for o in subs:
                    if o is s or o not in decided or o not in step_of:
                        continue
                    d = abs(step_of[s] - step_of[o])
                    by_interval[round(d)] += 1
                    if abs(d - 1.0) < 0.26:
                        second.add(s)
    print(f"   stemless heads a SECOND from a stemmed same-x head: "
          f"{len(second):5d}  ({100.0 * len(second) / max(1, len(no_stem)):.1f}% "
          f"of {len(no_stem)})")
    print(f"   the same pairing at every interval (half steps -> pairs):")
    for k in sorted(by_interval)[:12]:
        print(f"      {k:>3} : {by_interval[k]:5d}")

    out = {"heads_per_stem": {str(k): v for k, v in sorted(carry.items())},
           "columns_ge2": len(cols), "observed_mixed": obs_mixed,
           "null_mean": round(mean, 1),
           "null_p5": null[int(0.05 * len(null))],
           "null_p95": null[int(0.95 * len(null))],
           "null_draws_le_observed": below,
           "q1_verdict": verdict_q1,
           "null2_within_cell_mean": round(mean2, 1),
           "null2_p5": null2[int(0.05 * len(null2))],
           "null2_p95": null2[int(0.95 * len(null2))],
           "null2_draws_le_observed": below2,
           "q1_verdict_bar_matched": verdict_q2,
           "served_stem_misses_stemless_head_in_y": len(hit),
           "y_gap_median_spaces": round(statistics.median(gaps), 3) if gaps else None,
           "y_gap_within": {str(c): sum(1 for g in gaps if g <= c)
                            for c in (0.25, 0.5, 1.0, 2.0)},
           "stemless_a_second_from_a_stemmed_same_x_head": len(second),
           "same_x_interval_histogram_half_steps":
               {str(k): v for k, v in sorted(by_interval.items())},
           "heads_with_a_staff_position": len(step_of),
           "no_stem_population": len(no_stem)}
    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
