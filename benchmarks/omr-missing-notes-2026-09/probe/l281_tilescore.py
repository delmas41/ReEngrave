#!/usr/bin/env python3
"""l281_tilescore: score Sean's answers on the 2.81 blind tiles (`out/print/2.81-review/`).

The answers are Sean's words per tile, in a JSON file `{"tile_01": "quarter", "tile_02": "dotted
eighth", "control_1": "quarter", ...}` (a value, or "not a note" / "rest" / "unclear"). Nothing is
inferred from our own reading: the only thing compared against the answer is the rule's level-0
candidate, taken from the manifest's hidden `our_reading`.

CONTROLS FIRST. `control_*` tiles are heads Sean's own hand-truth boxes show BEAMED (the answer must
not be a quarter) or BARE (must be a quarter or dotted quarter). If his answers on them disagree
with his boxes, the tile pipeline or the derived truth is what is in doubt, and the sample numbers
below are printed under that warning, not trusted.

THE SAMPLE'S JUDGEMENT of the rule *filled head, bare stem -> level 0* (a quarter, a dotted quarter
with a dot):
  right      the answer is a quarter or a dotted quarter
  wrong      an eighth or shorter (a beam or flag the reader missed), or a half or longer
  not_a_note a rest, a dot, a stem fragment: a false head (counted separately, never right or wrong)
  unclear    set aside
and, apart, whether the DOT agrees (our dots read vs the dot in the answer).

The estimate is per stratum with a 95% Wilson interval and, for the population, the strata weighted
by their frame sizes (stratified estimator; the interval is the Wilson interval of the weighted
rate at the effective sample size -- an approximation, labelled).

    python3 l281_tilescore.py --dir out/print/2.81-review --answers answers.json
"""
import argparse
import collections
import json
import math
import re
import sys
from pathlib import Path

LEVEL0_RIGHT = {"quarter", "dotted quarter", "double dotted quarter"}
NOT_A_NOTE = {"not a note", "rest", "quarter rest", "eighth rest", "no note", "dot", "not a head"}
UNCLEAR = {"unclear", "can't tell", "cannot tell", "unreadable", ""}
ALIASES = {"crotchet": "quarter", "dotted crotchet": "dotted quarter", "quaver": "eighth",
           "dotted quaver": "dotted eighth", "semiquaver": "sixteenth", "minim": "half",
           "dotted minim": "dotted half", "8th": "eighth", "16th": "sixteenth", "32nd": "thirty-second",
           "dotted 8th": "dotted eighth", "dotted 16th": "dotted sixteenth", "1/4": "quarter",
           "1/8": "eighth"}


def norm(s):
    s = re.sub(r"\s+", " ", str(s or "").strip().lower().replace("-", " ")).strip()
    if s in NOT_A_NOTE or s in UNCLEAR:
        return s
    s = re.sub(r"\s*\bnotes?\b\s*$", "", s).strip()      # "quarter note" -> "quarter"
    return ALIASES.get(s, s)


def wilson(k, n, z=1.96):
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)


def fmt(k, n):
    if n == 0:
        return "n=0"
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {k / n:.3f} (95% Wilson {lo:.3f}-{hi:.3f})"


def judge(ans):
    a = norm(ans)
    if a in UNCLEAR:
        return "unclear"
    if a in NOT_A_NOTE:
        return "not_a_note"
    if a in LEVEL0_RIGHT:
        return "right"
    return "wrong"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--answers", required=True)
    a = ap.parse_args()
    man = json.loads((Path(a.dir) / "manifest.json").read_text())
    ans = json.loads(Path(a.answers).read_text())
    tiles = {t["id"]: t for t in man["tiles"]}
    missing = [i for i in tiles if i not in ans]
    if missing:
        print("NO ANSWER YET for:", missing)
    # controls
    cok = cn = 0
    for tid, t in sorted(tiles.items()):
        if t["kind"] != "control" or tid not in ans:
            continue
        j = judge(ans[tid])
        want = "wrong" if t["hidden"]["control"] == "beamed" else "right"
        cn += 1
        cok += (j == want)
        print(f"  control {tid}: {t['hidden']['control']:6s} (his boxes) answer {ans[tid]!r} -> {j} "
              f"{'ok' if j == want else 'DISAGREES WITH HIS BOXES'}")
    if cn:
        print(f"controls agree with his boxes: {cok}/{cn}"
              + ("" if cok == cn else "   <-- the numbers below are NOT to be trusted until this is understood"))
    rows = [(tid, t) for tid, t in sorted(tiles.items()) if t["kind"] == "sample" and tid in ans]
    by_s = collections.defaultdict(list)
    for tid, t in rows:
        by_s[t["hidden"]["stratum"]].append((tid, t, judge(ans[tid])))
    print(f"\nanswered sample tiles: {len(rows)} of {sum(1 for t in tiles.values() if t['kind'] == 'sample')}")
    tot_r = tot_n = 0
    for s in ("A", "B"):
        rs = by_s.get(s, [])
        right = sum(1 for _t, _x, j in rs if j == "right")
        wrong = sum(1 for _t, _x, j in rs if j == "wrong")
        nan = sum(1 for _t, _x, j in rs if j == "not_a_note")
        unc = sum(1 for _t, _x, j in rs if j == "unclear")
        print(f"stratum {s}: right {right}, wrong {wrong}, not-a-note {nan}, unclear {unc}; "
              f"precision over right+wrong {fmt(right, right + wrong)}")
        tot_r += right
        tot_n += right + wrong
        for mv in ("brahms", "litolff"):
            sub = [(t, x, j) for t, x, j in rs if x["hidden"]["movement"] == mv]
            r2 = sum(1 for _t, _x, j in sub if j == "right")
            w2 = sum(1 for _t, _x, j in sub if j == "wrong")
            print(f"    {mv:8s} {fmt(r2, r2 + w2)}")
        for tid, t, j in rs:
            if j == "wrong":
                print(f"    WRONG {tid}: answer {ans[tid]!r}  ours {t['hidden']['our_reading']}  "
                      f"tip={t['hidden']['tip_status']} stroke_at_tip={t['hidden']['stroke_at_tip']} "
                      f"ink_refusals={t['hidden']['ink_refusals']}")
    print(f"\nall answered sample tiles (strata pooled, UNWEIGHTED): {fmt(tot_r, tot_n)}")
    # stratified estimate
    sizes = man["frame_sizes"]
    wA = sizes["brahms/A"] + sizes["litolff/A"]
    wB = sizes["brahms/B"] + sizes["litolff/B"]
    pr = {}
    for s in ("A", "B"):
        rs = by_s.get(s, [])
        r_ = sum(1 for _t, _x, j in rs if j == "right")
        w_ = sum(1 for _t, _x, j in rs if j == "wrong")
        pr[s] = (r_ / (r_ + w_)) if (r_ + w_) else None
    if pr["A"] is not None and pr["B"] is not None:
        est = (wA * pr["A"] + wB * pr["B"]) / float(wA + wB)
        print(f"population estimate (frame sizes {wA} A + {wB} B, Brahms p0 excluded): {est:.3f} "
              f"(point estimate only; the strata's intervals above are the honest uncertainty)")
    # dots: does the dot agree
    dr = dn = 0
    for tid, t in rows:
        j = judge(ans[tid])
        if j != "right":
            continue
        dn += 1
        said_dotted = "dotted" in norm(ans[tid])
        dr += (said_dotted == bool(t["hidden"]["dots_read"]))
    if dn:
        print(f"of the quarter-valued answers, our dot reading agrees on {dr}/{dn}")
    # the n needed
    print("\n(for scale: an error-free sample needs n >= 73 for a 95% Wilson LOWER bound of 0.95; "
          "30 error-free tiles bound it only at 0.886)")


if __name__ == "__main__":
    main()
