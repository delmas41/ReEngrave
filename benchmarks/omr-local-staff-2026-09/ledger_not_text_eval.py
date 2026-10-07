"""lane-ledger-not-text (2026-10-05): in-sample control. Note-first reader with `ledger_not_text` False (before) vs True
(after), in the deskewed gather frame, on the 41 Litolff + 11 Brahms scored far heads. Names every head that changes.
  python3 ledger_not_text_eval.py"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import jut_from_ink_eval as J
from tools.omr.annotate import far_head_reader as FH


def arm(on):
    FH.CHORD_SPLIT = True
    FH.READER_KEYWORDS["through_head_on_rung"] = True
    FH.READER_KEYWORDS["note_first"] = True
    FH.READER_KEYWORDS["ledger_not_text"] = on


if __name__ == "__main__":
    for doc, page in (("beethoven5-litolff", 3), ("brahms1-breitkopf", 1)):
        L, fp, far = J.prepare(doc, page)
        arm(False); old = J.run(L, fp, far, "ink")
        arm(True); new = J.run(L, fp, far, "ink")
        print("==", doc, "n", len(far), "before", J.tal(old), "| after", J.tal(new))
        broken = []
        for s in old:
            if old[s][:2] != new[s][:2]:
                t = [h for h in far if h["subject"] == s][0]["truth"]
                print("  ", s, "truth", t, old[s][:2], "->", new[s][:2], "|", new[s][2][:90])
                if old[s][0] == "right" and new[s][0] != "right":
                    broken.append(s)
        print("  right heads broken:", broken)
