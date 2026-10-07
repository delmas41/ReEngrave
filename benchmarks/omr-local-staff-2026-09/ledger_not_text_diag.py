"""lane-ledger-not-text: text statistics per REJECTED rung (read only): row continuity and the MEDIAN vertical ink run
(in spaces) over the columns within +-1.2 sp of the head column that hold ink at the row. A ledger stays thin along its
length; the letters of a word are tall."""
import sys, json
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2
import truth_set_2_44c as ts
from frame import render_page_matching_gather
from tools.omr.annotate import ledger_grid as lg


def stat(gray, y, cx, sp, half=1.2):
    a, b = int(cx - half * sp), int(cx + half * sp)
    runs = []
    for x in range(a, b):
        t = lg._column_ink_run(gray, y, x, sp)
        if t is not None:
            runs.append(t / sp)
    return (lg.rung_row_continuity(gray, y, cx, sp), float(np.median(runs)) if runs else -1.0, len(runs))


def fmt(v):
    return "cont %.2f  median run %.2f sp  (n=%d columns)" % v


def rows(name):
    return {r["subject"]: r for r in json.loads((HERE / name).read_text())}


if __name__ == "__main__":
    cache = {}

    def g(doc, page):
        if (doc, page) not in cache:
            cache[(doc, page)] = cv2.cvtColor(render_page_matching_gather(ts.DOCS[doc]["pdf"], page, 600).rgb,
                                              cv2.COLOR_RGB2GRAY)
        return cache[(doc, page)]
    for which, doc in (("brahms", "brahms1-breitkopf"), ("litolff", "beethoven5-litolff")):
        B, A = rows(f"farhead_note_first_oos_{which}.json"), rows(f"ledger_not_text_oos_{which}.json")
        for s, a in A.items():
            r = B[s]
            if r["new"]["pos"] == a["new"]["pos"] or not r["new"]["between"]:
                continue
            box = r["new"]["box_used"]
            cx = (box[0] + box[2]) / 2
            sp = (max(r["new"]["lines"]) - min(r["new"]["lines"])) / 4
            keep = a["new"]["between"] or []
            for y in r["new"]["between"]:
                if all(abs(y - k) > 1.5 for k in keep):
                    print(which, s, "geom", r["geometry"], "before", r["new"]["pos"], fmt(stat(g(doc, r["page"]), y, cx, sp)))
