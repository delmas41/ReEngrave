"""lane-edge-vs-through (2026-10-06): the in-sample CONTROL for the `edge_vs_through` keyword.

The scored far heads (41 Litolff p3 + 11 Brahms p1, deskewed gather frame, the page the reader's rules were
written on) read with the keyword OFF and ON, everything else at the tree's defaults. Reports the right / wrong /
abstain tally of both arms, every head whose answer changes, how many heads reach the rule (the middle-rung
branch with a second rung at the staff-side edge -- the REACH, so a rule that is simply inert is not read as "0
right heads broken"), and the quantities the rule thresholds for the heads that reach it. Read-only; no gather.

  python3 edge_vs_through_eval.py
"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import jut_from_ink_eval as J
from tools.omr.annotate import far_head_reader as FH, ledger_grid as lg


def arm(on):
    FH.CHORD_SPLIT = True
    FH.READER_KEYWORDS["through_head_on_rung"] = True
    FH.READER_KEYWORDS["note_first"] = True
    FH.READER_KEYWORDS["edge_vs_through"] = on


if __name__ == "__main__":
    calls = []
    orig = lg.edge_vs_through_evidence

    def spy(*a, **k):
        r = orig(*a, **k)
        calls.append(r)
        return r
    lg.edge_vs_through_evidence = spy
    for doc, page in (("beethoven5-litolff", 3), ("brahms1-breitkopf", 1)):
        L, fp, far = J.prepare(doc, page)
        arm(False); calls.clear(); old = J.run(L, fp, far, "ink")
        n_off = len(calls)
        arm(True); calls.clear(); new = J.run(L, fp, far, "ink")
        reach = list(calls)
        print("==", doc, "n", len(far), "| keyword OFF", J.tal(old), "| keyword ON", J.tal(new))
        print("   rule evaluated (the head has a middle rung): off-arm calls", n_off, "| on-arm calls", len(reach),
              "| fired (ok)", sum(1 for r in reach if r["ok"]),
              "| why:", sorted({r["why"] for r in reach}))
        broken = []
        for s in old:
            if old[s][:2] != new[s][:2]:
                t = [h for h in far if h["subject"] == s][0]["truth"]
                print("  ", s, "truth", t, old[s][:2], "->", new[s][:2], "|", new[s][2][:90])
                if old[s][0] == "right" and new[s][0] != "right":
                    broken.append(s)
        print("   right heads broken:", broken)
