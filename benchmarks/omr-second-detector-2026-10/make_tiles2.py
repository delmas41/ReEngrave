"""ROADMAP 2.114 round 2 blind tiles: `out/print/2.114-round2/`. Same format and question as round 1 (`make_tiles.py`): one question per tile,
*Hollow or black? (or: not a note)*, 32 px per staff space, the print as printed, ONE red corner bracket on the subject box, NOTHING of ours drawn.
Sources (cap 20 incl. 2 controls; none of the 17 already answered is re-asked):
  * THRESHOLD tiles (from `interior_variants.json`, Litolff 95 clean cells): the 8 lowest-reading production "black" boxes under variant (c) (the
    staff/barline junction skipped) and the 3 highest-reading truth hollow heads. The manifest records their interior readings under (a), (b), (c).
  * ROUND-2 tiles: heads the second detector touched in the NEW ON record that round 1 did not ask about, spread over how the rule settled them.
  * 2 controls of known answer (a Brahms truth-black head and a Brahms hollow head both detectors call hollow), not the two used in round 1.
usage: make_tiles2.py interior_variants.json rec-lit-on.json rec-bra-on.json score.json OUTDIR"""
import collections, json, random, sys
from pathlib import Path
import cv2, numpy as np
sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page
from tools.omr.staged import readout as RO
LIT = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
BRA = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"
PAGES = {"litolff": (LIT, 1), "brahms": (BRA, 0)}
QUESTION = "Hollow or black? (or: not a note)"
CAP, HDR = 20, 56
ASKED = {t["hidden"]["key"] for t in json.load(open("out/print/2.114-second-detector/manifest.json"))["tiles"]}

def main():
    iv, lit_p, bra_p, score_p, out = sys.argv[1:6]
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    items = []
    d = json.load(open(iv))["items"]
    L = [i for i in d if i["page"] == "litolff" and i["c"] is not None]
    blacks = sorted([i for i in L if i["label"] == "black"], key=lambda i: i["c"])[1:9]
    holl = sorted([i for i in L if i["label"] == "hollow"], key=lambda i: -i["c"])[:3]
    for i in blacks + holl:
        items.append(dict(doc="litolff", key=i["key"], rect=i["box"], sp=15.75, group="THRESHOLD " + ("black-labelled (production black box, no truth hollow)" if i["label"] == "black" else "truth hollow head"),
                          truth=("production black, not a truth hollow head" if i["label"] == "black" else "truth hollow head"),
                          interior={"a_current": i["a"], "b_recentred": i["b"], "c_recentred_line_rows_out": i["c"]}, threshold_tile=True))
    runs = {"litolff": RO.load_run(lit_p), "brahms": RO.load_run(bra_p)}
    sys.path.insert(0, "benchmarks/omr-second-detector-2026-10")
    from make_tiles import staff_space_page  # noqa  (module runs main on import: guarded below)
