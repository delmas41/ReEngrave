"""2.99 CONTROLS: run the decision on ink the detector ALREADY NAMED.

    python3 .../controls_2_99.py REC.json [REC2.json ...]

`Q.UNBOXED_REST_SHAPE` is filed for every rest-sized cluster, covered or not.
Here the decision is run over the COVERED ones with the coverage zeroed (so the
standing box no longer speaks for them), and its answer is set against what the
detector's own box called the ink:

  * a standing `rest8th`        -> should be "eighth"  (recall of the eighth rule)
  * a standing `restQuarter`    -> should be "quarter" (recall of the quarter rule)
  * a standing flat/sharp/natural/double-sharp, a notehead, a clef/key
                                -> must NEVER be decided a rest (the control that
                                   can fail: a decision that decides everything
                                   passes the first two rows and fails this one)

A mismatch is not automatically the decision's fault -- the detector is wrong
too (3 `accidentalDoubleSharp` boxes in Litolff p1-3 sit on eighth-rest ink) --
so every non-agreement is listed with its numbers.
"""
import collections
import json
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/omr-bar-sum-holdout-2026-09/probe")
import unboxed_rest_2_99 as U  # noqa: E402
from tools.omr.staged import adjudicate  # noqa: E402
from tools.omr.staged import record as R  # noqa: E402
from tools.omr.staged.record import Log, Q, READERS  # noqa: E402

adjudicate._ensure_decisions()
tot = collections.Counter()
for path in sys.argv[1:]:
    rows = U.rows(U.load(path))
    for r in rows:
        k = U.klass(r)
        if k == "unboxed":
            continue
        log = Log()
        g = R.glyph(0, 0, 0, 1, 350000)
        det = {x: r.get(x) for x in (
            "width_spaces", "height_spaces", "staff_step", "n_pieces",
            "fill", "max_column_share", "mass_y", "column_profile",
            "covered_by", "right_head", "first_cell", "left_of_header",
            "header_known", "touches_cell_edge")}
        det.update(coverage=0.0, bbox_canonical=[0, 0, 1, 1],
                   bbox_page_px=[0.0, 0.0, 1.0, 1.0])
        log.observe(g, Q.UNBOXED_REST_SHAPE, r["height_spaces"],
                    reader=READERS.CV_UNBOXED_REST_SHAPE, frame="cell:1", **det)
        log.freeze()
        adjudicate.run(log, order=(Q.UNBOXED_INK_IS_A_REST,))
        v = log.verdict(Q.UNBOXED_INK_IS_A_REST, g)
        said = str(v.value) if v.outcome.value == "decided" else "abstain:" + v.reason
        by = [b for b in (r.get("covered_by") or []) if b != "ledgerLine"]
        if k == "rest":
            truth = ("rest8th" if any(b == "rest8th" for b in by)
                     else "restQuarter" if any(b == "restQuarter" for b in by)
                     else "rest-other:" + ",".join(by))
        else:
            truth = "NOT-A-REST:" + k
        tot[(truth, said)] += 1
        if (truth == "rest8th" and said != "eighth") or \
           (truth == "restQuarter" and said != "quarter") or \
           (truth.startswith("NOT") and said in ("eighth", "quarter")):
            print("DISAGREE", truth, said, r["subject"],
                  {x: r.get(x) for x in ("width_spaces", "height_spaces",
                                         "staff_step", "mass_y",
                                         "column_profile", "covered_by")})
print()
for (truth, said), n in sorted(tot.items()):
    print(f"{n:4d}  detector says {truth:28s} decision says {said}")
bad = sum(n for (t, s), n in tot.items()
          if t.startswith("NOT") and s in ("eighth", "quarter"))
print("covered-by-a-non-rest decided a rest:", bad)
