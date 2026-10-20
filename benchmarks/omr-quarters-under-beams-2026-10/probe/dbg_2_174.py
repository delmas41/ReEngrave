"""2.174 step 2c: for a few glyph subjects of ONE page, print what `_beam_levels` was handed (head centre x, stem x-span, each beam's x0/x1/reader,
the joined ids, the join witness) -- the numbers the quarter's verdict was made from. Replays only that page's slice through ADJUDICATE.
usage: dbg_2_174.py DOC PAGE SUBJECT[,SUBJECT...]"""
import glob
import json
import os
import sys

sys.path.insert(0, ".")
from tools.omr.staged import pipeline  # noqa: E402,F401
from tools.omr.staged.adjudicators import rhythm as R  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

DOC, PG, SUBS = sys.argv[1], int(sys.argv[2]), set(sys.argv[3].split(","))
D = "scratch/slices/" + DOC


def rows(kind, names):
    out = []
    for n in names:
        p = os.path.join(D, "%s.%s.jsonl" % (n, kind))
        if os.path.exists(p):
            out += [json.loads(l) for l in open(p)]
    return out


names = ["common", "p%02d" % PG]
rec = {"observations": rows("observations", names), "abstentions": rows("abstentions", names), "verdicts": []}
orig = R._beam_levels
state = {"cur": None}
CENTERS = {}
for o in rec["observations"]:
    if o["subject"] in SUBS and o["quantity"] == "glyph_box":
        CENTERS[round(o["value"][1] + o["value"][3] / 2.0, 3)] = o["subject"]


def spy(beams, x_center, width, joined=(), join_witness=None, stem_x=None, unjoined_possible=False):
    out = orig(beams, x_center, width, joined, join_witness, stem_x, unjoined_possible)
    state["cur"] = CENTERS.get(round(x_center, 3)) if x_center is not None else None
    if state["cur"]:
        print(state["cur"], "x_center", x_center, "width", width, "stem_x", stem_x, "joined", [b.id for b in joined], "witness", join_witness,
              "->", out[:2])
        for b in beams:
            print("    beam", b.id, b.reader, "x0", b.detail.get("x0"), "x1", b.detail.get("x1"), "val", b.value)
    return out


R._beam_levels = spy
log, _ = RR.rebuild_gather(rec)
RR.run_stages(log)
