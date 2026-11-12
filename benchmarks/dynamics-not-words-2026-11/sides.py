"""ROADMAP 2.303: for each dynamic claim of a page, the neighbour ink the CV reader (`Q.DYNAMIC_LETTER_NEIGHBOURS`) measured beside each of its letters.

    python3 benchmarks/dynamics-not-words-2026-11/sides.py REC PAGE

Per claim: id, text, box, `compound` (split from a marking), and per detector letter `(letter, (left_spaces, right_spaces))` -- the gap in staff spaces to the nearest other ink on that side
(None = nothing within the reader's window). Reads a saved gather; writes nothing.
"""
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")


def main():
    from tools.omr.staged import claim_readout as CR
    rec, page = sys.argv[1], int(sys.argv[2])
    obs = CR.read_rows(CR.resolve_source(rec), [page])["observations"]
    sides = {o["subject"]: o["value"] for o in obs if o["quantity"] == "dynamic_letter_neighbours"}
    lrow = {o["id"]: o for o in obs if o["quantity"] == "dynamic_letter"}

    def f(s):
        if not s:
            return None
        ls, rs = s.get("left_spaces"), s.get("right_spaces")
        return (None if ls is None else round(ls, 2), None if rs is None else round(rs, 2))
    for o in obs:
        d = o.get("detail") or {}
        if o["quantity"] != "claimed_area" or d.get("owner") != "word" or d.get("source") != "dynamic_letters":
            continue
        ls = sorted([lrow[i] for i in (d.get("letter_rows") or []) if i in lrow], key=lambda r: r["detail"]["bbox_page_px"][0])
        if not ls:
            continue
        print(o["id"], d.get("text") or d.get("detector_letter"), [round(t) for t in o["value"]], "compound" if d.get("compound_of") else "",
              [(r["detail"]["letter"], f(sides.get(r["subject"]))) for r in ls])


main()
