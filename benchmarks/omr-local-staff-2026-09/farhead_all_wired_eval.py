"""lane-farhead-all-wired (2026-10-04): the STAGED far-head reader with the chord split and the through-head
rule wired in (`far_head_reader.CHORD_SPLIT`, `READER_KEYWORDS['through_head_on_rung']`), before vs after, in the
CORRECT (deskewed gather) frame; names every head that changes. Read-only; no gather."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import jut_from_ink_eval as J
from tools.omr.annotate import far_head_reader as FH

def arm(on):
    FH.CHORD_SPLIT = on
    FH.READER_KEYWORDS["through_head_on_rung"] = on

if __name__ == "__main__":
    for doc, page in (("beethoven5-litolff", 3), ("brahms1-breitkopf", 1)):
        L, fp, far = J.prepare(doc, page)
        arm(False); old = J.run(L, fp, far, "ink")
        arm(True); new = J.run(L, fp, far, "ink")
        print("==", doc, "n", len(far), "before", J.tal(old), "after", J.tal(new))
        broken = []
        for s in old:
            if old[s][:2] != new[s][:2]:
                t = [h for h in far if h["subject"] == s][0]["truth"]
                print("  ", s, "truth", t, old[s][:2], "->", new[s][:2], new[s][2][:70])
                if old[s][0] == "right" and new[s][0] != "right": broken.append(s)
        for s in ("glyph/3/0/0/2/4", "glyph/3/0/0/2/9"):
            if s in new: print("  watch", s, new[s])
        print("  right heads broken:", broken)
