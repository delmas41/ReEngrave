"""ROADMAP 2.150b -- the ink test on the 21 blind tiles of 2.150, scored against Sean's answers.
usage: score_2_150b.py   (reads out/2.150/tiles-key.json, out/print/2.150-review/answers.json)
Applies the adjudicator's own cuts (family_precision constants) to rest_ink.measure over the page raster; prints
one line per tile and the right/wrong count. The width floor's result is read from the answers file for comparison."""
import json
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/omr-bar-sum-holdout-2026-09/probe")
import ink_2_150b as I  # noqa: E402
from tools.omr.staged.adjudicators import family_precision as FP  # noqa: E402


def refuses(m):
    ms = m["thin_run_sp"] / FP.REST_STROKE_MIN_SP - 1
    mh = max(m["blob_sp"] / FP.REST_HEAD_BLOB_MIN_SP - 1, m["head_ink_sp2"] / FP.REST_HEAD_INK_MIN_SP2 - 1)
    return min(ms, mh)


key = json.load(open("out/2.150/tiles-key.json"))
ans = {t["n"]: t for t in json.load(open("out/print/2.150-review/answers.json"))["tiles"]}
right = wrong = 0
for k in key:
    m = I.measure_glyph(k["document"], k["glyph"])
    a = ans[k["n"]]
    margin = refuses(m)
    refused = margin >= 0
    is_rest = "rest" in a["sean"]
    ok = (refused != is_rest)
    right += ok
    wrong += (not ok)
    print(f"{k['n']:2d} {a['sean'][:12]:12s} width={k['width_spaces']:.2f} thin={m['thin_run_sp']:.2f} blob={m['blob_sp']:.2f} "
          f"headink={m['head_ink_sp2']:.2f} margin={margin:+.2f} {'REFUSED' if refused else 'kept   '} "
          f"{'right' if ok else 'WRONG'}  (width floor: {a['verdict']})")
print("right", right, "wrong", wrong)
