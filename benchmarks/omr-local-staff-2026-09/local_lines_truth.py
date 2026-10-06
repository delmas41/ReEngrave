"""lane-local-staff-lines: the truth set (Litolff p3, Brahms p1; farhead_all_wired_eval's frame) with the local five lines
read the OLD way (`local_lines_in_window` off) and the NEW way (on). Names every head whose verdict changes."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import jut_from_ink_eval as J
import farhead_all_wired_eval as W
from tools.omr.annotate import far_head_reader as FH

if __name__ == "__main__":
    W.arm(True)
    for doc, page in (("beethoven5-litolff", 3), ("brahms1-breitkopf", 1)):
        L, fp, far = J.prepare(doc, page)
        FH.READER_KEYWORDS["local_lines_in_window"] = False; old = J.run(L, fp, far, "ink")
        FH.READER_KEYWORDS["local_lines_in_window"] = True; new = J.run(L, fp, far, "ink")
        print("==", doc, "n", len(far), "old", J.tal(old), "new", J.tal(new))
        broken = []
        for s in old:
            if old[s][:2] != new[s][:2]:
                t = [h for h in far if h["subject"] == s][0]["truth"]
                print("  ", s, "truth", t, old[s][:2], "->", new[s][:2], new[s][2][:70])
                if old[s][0] == "right" and new[s][0] != "right": broken.append(s)
        print("  right heads broken:", broken)
