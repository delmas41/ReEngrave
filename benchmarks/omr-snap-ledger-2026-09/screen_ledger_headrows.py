"""⚠️ REFUTED AS A GENERAL FIX — kept as the record of why, not as a screen to run.

This implements the "measure only notehead-width rows" idea I proposed after
finding that audit_ledger_zone_labels.py false-flags six of seven ledger-zone
labels in the Simrock batch. The mechanism it targets is real and confirmed
independently on the pixels by the mxl-prefill session:

  LEDGER LINES SURVIVE STAFF-LINE REMOVAL, so on an out-of-staff notehead the
  rung falls inside the label box and print-merges into the same connected
  component as head+stem. A blob measured over that component is dragged toward
  the rung: dvorak9-p12-sys1-s26-m7's four heads measure +10.8..+11.0 (true,
  matching the labels) and the tool reported +10.11..+10.25, which rounds even
  and reads OnLine.

⚠️ BUT THE FIX DOES NOT GENERALISE, measured across BOTH corpora by that session:

  | measure                          | Brahms (6 correct) | Simrock (4 known FPs) |
  |----------------------------------|-------------------:|----------------------:|
  | shipped blob_centre              |                6/6 |      0/4  (the bug)   |
  | peak-row (max-width row)         |                2/6 |                   4/4 |
  | median-outlier row trim          |                6/6 |                   0/4 |
  | erosion 3-8px                    |              3-5/6 |                   0/4 |
  | THIS (row run <= 1.6x box width) |                0/6 |                   4/4 |

  THE CONFOUND IS BOX PADDING, and it is recorded nowhere per batch or labeler.
  This measure can only see the rung's excess width where the human's box has
  slack around the head. Simrock's boxes do; Brahms's are drawn tight to the
  ink, so "run within the box" saturates at the box width almost everywhere and
  the filter silently degenerates to plain box-centroid — the least reliable
  measure of the three, because a click-placed box inherits the snap grid.

  Width alone fails too: the 4 Simrock false positives measure 1.91-2.14 staff
  spaces wide, and so do 40 of Brahms's 76 uncontested ledger-zone labels.

⚠️ AND THIS SCRIPT PRODUCES ITS OWN FALSE POSITIVES. Run over Simrock it raises
9 flags that barely overlap the 7 the shipped tool raises. Two geometric
measures disagreeing on the same labels is the evidence that geometry does not
settle this: each candidate needs a by-hand check of pixels against known staff
and ledger positions, which is how all 7 Simrock and all 6 Brahms cases were
actually resolved.

WHAT TO USE INSTEAD: audit_ledger_zone_labels.py as a RECALL-ORIENTED SCREEN,
reading its rate as an upper bound. Adjudicated, Simrock's 6.9% raw flag rate
was 0.9% true — an order of magnitude. It earns its place: it found one real
error nobody would have looked for. It does not earn being read as a count.
"""

from __future__ import annotations
import argparse, glob, json, os
import cv2, numpy as np

RUN_TOL = 1.6          # a row wider than this x box width is a ledger rung
HEAD_MIN, HEAD_MAX = 0.55, 1.45     # plausible notehead height, staff spaces
OFF_GRID_MAX = 0.35    # only flag when the head sits confidently on a slot

def screen(batch: str):
    mp = os.path.join(batch, "cells.json")
    if not os.path.exists(mp): return []
    man = {e["cell_id"]: e for e in json.load(open(mp))}
    out = []
    for vf in sorted(glob.glob(os.path.join(batch, "verdicts", "*.json"))):
        v = json.load(open(vf)); cid = v["cell_id"]; e = man.get(cid)
        if not e: continue
        ys = sorted(float(y) for y in (e.get("staff_line_ys_canonical") or []))
        if len(ys) != 5: continue
        sp = (ys[4] - ys[0]) / 4
        ns = os.path.join(batch, "cells", f"{cid}_nostaff.png")
        g = cv2.imread(ns, cv2.IMREAD_GRAYSCALE)
        if g is None: continue
        bw = g < 128
        for i, b in enumerate(v.get("added_detections") or []):
            cls = b.get("human_class") or ""
            if not cls.endswith(("OnLine", "InSpace")): continue
            bb = b["bbox"]
            box_step = (bb["y"] + bb["h"] / 2 - ys[0]) / (sp / 2)
            if 0 <= box_step <= 8: continue          # inside the staff, not our business
            cx = int(bb["x"] + bb["w"] / 2)
            if not (0 <= cx < bw.shape[1]): continue
            rows = []
            for y in range(max(0, bb["y"] - 4), min(bw.shape[0], bb["y"] + bb["h"] + 4)):
                if not bw[y, cx]: continue
                l = cx
                while l > 0 and bw[y, l - 1]: l -= 1
                r = cx
                while r < bw.shape[1] - 1 and bw[y, r + 1]: r += 1
                if (r - l + 1) <= bb["w"] * RUN_TOL: rows.append(y)
            if not rows: continue
            head_h = (max(rows) - min(rows) + 1) / sp
            if not (HEAD_MIN <= head_h <= HEAD_MAX):
                continue                              # isolation failed -> abstain, do not flag
            st = ((min(rows) + max(rows)) / 2 - ys[0]) / (sp / 2)
            if abs(st - round(st)) > OFF_GRID_MAX: continue
            says = "OnLine" if round(st) % 2 == 0 else "InSpace"
            if not cls.endswith(says):
                out.append((cid, i, cls, says, st, head_h, box_step))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", action="append")
    a = ap.parse_args()
    batches = a.batch or sorted(b for b in glob.glob("benchmarks/omr-labeling-*")
                                if os.path.isdir(os.path.join(b, "verdicts")))
    total = 0
    for b in batches:
        hits = screen(b)
        total += len(hits)
        print(f"{os.path.basename(b):52s} flags={len(hits)}")
        for cid, i, cls, says, st, hh, bs in hits:
            print(f"    {cid}[{i}] {cls} -> {cls[:-len(cls.split('On')[-1]) if 'OnLine' in cls else 0]}"
                  f"{says}   head step {st:+.2f} (box {bs:+.2f})  head {hh:.2f}sp")
    print(f"\nTOTAL {total} flags — read-only; each is a question for a human, not a finding.")

if __name__ == "__main__":
    main()
