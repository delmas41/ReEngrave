"""ROADMAP 2.311 small test -- TRY TO FALSIFY: "notes high above the staff on ledger lines are read at the wrong height".

    PYTHONPATH=. python3 benchmarks/note-loss-funnel-2026-11/ledger_heights.py OUT.json

STAGED, SAVED records only (no gather): the claim-readout slices of the 2306 frozen-sample gather (library/_shared-records/
claim-readout-slices-2306-smp4-{lit,bra}; pages Litolff 1 2 4 6 8 9 10 11 16, Brahms 0 4 5 8 12 14 19 25). Reads, decides nothing.

Per head (a glyph with a `notehead_class` row):
  geometry  = `notehead_staff_position` value (gather.gather_notehead_positions: the box centre against its own cell's staff grid,
              half-steps below the top line; 2.248 may move it by the ink centre -- `detail`),
  ledger    = `far_head_ledger_position` (gather.gather_far_head_ledger_positions via far_head_reader) or its refusal (abstentions),
  FINAL     = what `consequences.restate_pitch` reads: the ledger count where `adjudicators.position.adjudicate_notehead_position`
              decides it, else round(geometry) -- the extrapolation of the staff spacing.
Ledger lines owed by a position p: p <= -1 -> floor(-p / 2); p >= 9 -> floor((p - 8) / 2); inside the staff 0.
Our own ink count (rule 7: ours, not truth): short horizontal strokes in the strips just left and right of the head box, between
the staff's outer line and the head's far edge, from the un-erased page at 600 dpi.
Truth: Brahms p0 labels (data/hand-truth/pages/imslp317803/0.json) carry the CLASS (OnLine / InSpace) = the parity of the position.
"""
from __future__ import annotations

import collections
import json
import math
import random
import sys

import numpy as np

from tools.omr.staged.lane_report import PLATES, RECORDS

SLICE = {"litolff": RECORDS / "claim-readout-slices-2306-smp4-lit", "brahms": RECORDS / "claim-readout-slices-2306-smp4-bra"}
WANT = ("notehead_class", "notehead_staff_position", "far_head_ledger_position", "far_head_owner_ledger", "glyph_box", "staff_lines")


def load(plate):
    d = SLICE[plate]
    rows = collections.defaultdict(dict)
    for line in open(d / "observations.jsonl"):
        for q in WANT:
            if ('"quantity": "%s"' % q) in line[:200 + len(q)] or ('"quantity": "%s"' % q) in line[:400]:
                o = json.loads(line)
                rows[o["quantity"]][o["subject"]] = o
                break
    ref = {}
    for line in open(d / "abstentions.jsonl"):
        if '"far_head_ledger_position"' in line[:300]:
            o = json.loads(line)
            ref[o["subject"]] = o
    return rows, ref


def owed(p):
    if p <= -1:
        return (-p) // 2
    if p >= 9:
        return (p - 8) // 2
    return 0


def bin_of(n, side):
    if n == 0:
        return "inside staff (0 ledger lines)"
    return "%s %s" % (side, "1 line" if n == 1 else "2 lines" if n == 2 else "3+ lines")


def heads(plate):
    rows, ref = load(plate)
    out = []
    for sub, o in rows["notehead_class"].items():
        gp = rows["notehead_staff_position"].get(sub)
        gb = rows["glyph_box"].get(sub)
        if gp is None or gb is None:
            continue
        p, s, st = (int(x) for x in sub.split("/")[1:4])
        sl = rows["staff_lines"].get("staff/%d/%d/%d" % (p, s, st))
        owner = rows["far_head_owner_ledger"].get(sub)
        cand = ((owner or {}).get("detail") or {}).get("candidate")
        gv = float(gp["value"])
        led = rows["far_head_ledger_position"].get(sub)
        r = ref.get(sub)
        final_how = "geometry (no far read: within the staff)"
        final = int(round(gv))
        if led is not None:
            final, final_how = int(round(float(led["value"]))), "ledger count"
        elif r is not None:
            final_how = "geometry (ledger read refused: %s)" % ((r["detail"] or {}).get("ledger_reason") or "?").split(" (")[0].split(":")[0]
        d = gp.get("detail") or {}
        moved = "from_head_ink" in d or "from_head_hole" in d or "from_head_cut" in d
        out.append(dict(key=sub, page=p, system=s, staff=st, cls=o["value"], geom=gv, resid=abs(gv - round(gv)), geom_round=int(round(gv)),
                        final=final, final_how=final_how, ledger=None if led is None else int(round(float(led["value"]))),
                        ledger_reason=((led or r or {}).get("detail") or {}).get("ledger_reason"),
                        geometry_moved_by_ink=moved, ink_centre_why=d.get("ink_centre_why"),
                        ink_centre_pos=d.get("ink_centre_position_float"),
                        owner_candidate=cand, other_staff=bool(cand and cand != "staff/%d/%d/%d" % (p, s, st)),
                        box=gb["detail"]["bbox_page_px"], lines=None if sl is None else sl["value"]))
    return out


def side(p):
    return "above" if p <= -1 else "below" if p >= 9 else "in"


def main(out):
    res = {}
    for plate in ("litolff", "brahms"):
        hs = heads(plate)
        res[plate] = {"heads": hs}
        tab = collections.defaultdict(lambda: collections.Counter())
        rs = collections.defaultdict(list)
        for h in hs:
            if h["other_staff"]:
                tab["owned by another staff (moved)"]["n"] += 1
                continue
            n = owed(h["final"])
            b = bin_of(n, side(h["final"]))
            if n == 0:
                b = "inside staff (0 ledger lines)"
            t = tab[b]
            t["n"] += 1
            rs[b].append(h["resid"])
            t[h["final_how"].split(" (")[0]] += 1
            if h["ledger"] is not None:
                t["ledger != round(geometry)"] += int(h["ledger"] != h["geom_round"])
                t["ledger parity != geometry parity"] += int((h["ledger"] - h["geom_round"]) % 2 == 1)
            t["resid>=0.3"] += int(h["resid"] >= 0.3)
        res[plate]["table"] = {k: dict(v, mean_resid=round(float(np.mean(rs[k])), 3) if rs[k] else None,
                                       median_resid=round(float(np.median(rs[k])), 3) if rs[k] else None) for k, v in tab.items()}
    json.dump(res, open(out, "w"), default=str)
    for plate in res:
        print("==", plate, len(res[plate]["heads"]))
        for k in sorted(res[plate]["table"]):
            print("  ", k, res[plate]["table"][k])


if __name__ == "__main__":
    main(sys.argv[1])
