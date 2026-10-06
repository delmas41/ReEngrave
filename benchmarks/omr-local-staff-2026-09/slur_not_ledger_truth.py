"""lane-slur-not-ledger (2026-10-06): the in-sample truth-set control. The STAGED far-head reader (note-first, everything
else at its default) with `READER_KEYWORDS['slur_not_ledger']` OFF then ON, on the truth set (Litolff p3, Brahms p1; the
deskewed gather frame, `jut_from_ink_eval.prepare`). Names every head whose position changes and counts RIGHT heads
broken. Also the ownership-by-ledgers witness on the same heads, off then on (their own staff is the reference).
Read only; no gather.   python3 slur_not_ledger_truth.py
"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import jut_from_ink_eval as J
import truth_set_2_44c as ts
import farhead_owner_by_ledgers as OW
from tools.omr.annotate import far_head_reader as FH, far_head_owner as FO

if __name__ == "__main__":
    for doc, page in (("beethoven5-litolff", 3), ("brahms1-breitkopf", 1)):
        ts.DOCS[doc]["record"] = OW.TRUTHSET / ("beethoven5-litolff-p3.record.json" if "litolff" in doc else "brahms1-breitkopf-p1.record.json")
        L, fp, far = J.prepare(doc, page)
        res = {}
        for on in (False, True):
            FH.READER_KEYWORDS["slur_not_ledger"] = on
            res[on] = J.run(L, fp, far, "ink")
        print("==", doc, "n", len(far), "OFF", J.tal(res[False]), "ON", J.tal(res[True]))
        broken = []
        for s in res[False]:
            if res[False][s][:2] != res[True][s][:2]:
                t = [h for h in far if h["subject"] == s][0]["truth"]
                print("  CHANGED", s, "truth", t, res[False][s][:2], "->", res[True][s][:2], res[True][s][2][:70])
                if res[False][s][0] == "right" and res[True][s][0] != "right":
                    broken.append(s)
        print("  right heads broken:", len(broken), broken)
        st = OW.staves_on_page(L["rec"], page)
        own_moved = {}
        for on in (False, True):
            FH.READER_KEYWORDS["slur_not_ledger"] = on
            for h in far:
                own = OW.staff_key(h["subject"])
                r = FO.owner_by_ledgers(fp, h["subject"], h["box"], h["cls"], own, st)
                own_moved.setdefault(h["subject"], {})[on] = (r["owner"], r["word"])
        ch = [(s, v[False], v[True]) for s, v in own_moved.items() if v[False] != v[True]]
        kept = sum(1 for s, v in own_moved.items() if v[True][0] == OW.staff_key(s))
        print(f"  owner witness: far heads {len(far)}; owner = own staff ON {kept}; changed OFF->ON {len(ch)} {ch}")
        FH.READER_KEYWORDS["slur_not_ledger"] = True
