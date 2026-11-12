"""ROADMAP 2.303 PART 1: cut the REAL rows the test of `OMR_UNREAD_WORD_SIBLING` runs on, from the saved gather of the 20261029-night record (sliced for the frozen sample by `lane_report`).

    python3 benchmarks/dynamics-not-words-2026-11/make_fixture_2_303p1.py

Two regions of Litolff p8 (the print Sean judged): (A) system 0, x >= 1480 -- `sempre piu p` printed on staves 0-3 and 5-8 (staves 0-3 cut by a barline, the lexicon refused those; staff 8 READ)
and the real lone `pp` of staff 8 bar 17; (B) system 1, staff 4 bar 12 -- the lone `ff` Sean judged a dynamic (2.301 r1 tile 3), which has an unread candidate window over it.
Keeps the rows of three quantities (dynamic letter, its neighbour ink, direction word) whose page box meets a region, as the log held them. Writes
tools/omr/tests/data_unread_word_sibling_2_303p1.json.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SL = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261029-night/litolff")
REGIONS = {"A": (0, [1480, 440, 2120, 1800]), "B": (1, [1540, 2560, 1760, 2720])}
KEEP = ("dynamic_letter", "dynamic_letter_neighbours", "direction_word")


def meets(bb, box):
    return bb[0] < box[2] and bb[2] > box[0] and bb[1] < box[3] and bb[3] > box[1]


def main():
    rows, boxes_of = [], {}
    for fn, kind in (("observations.jsonl", "obs"), ("abstentions.jsonl", "abs")):
        for line in open(SL / fn):
            r = json.loads(line)
            if r.get("quantity") not in KEEP:
                continue
            p = r["subject"].split("/")
            if p[0] != "glyph" or p[1] != "8":
                continue
            r["_kind"] = kind
            rows.append(r)
            bb = (r.get("detail") or {}).get("bbox_page_px")
            if bb and r["quantity"] != "dynamic_letter_neighbours":
                boxes_of[r["subject"]] = bb
    out = []
    for r in rows:
        if r["quantity"] == "dynamic_letter_neighbours":
            continue
        p = r["subject"].split("/")
        bb = boxes_of.get(r["subject"])
        if not bb:
            continue
        for _name, (system, box) in REGIONS.items():
            if int(p[2]) == system and meets(bb, box):
                out.append(r)
                break
    # neighbour rows carry no box of their own: take those of kept letters
    kept_letters = {r["subject"] for r in out if r["quantity"] == "dynamic_letter"}
    for r in rows:
        if r["quantity"] == "dynamic_letter_neighbours" and r["subject"] in kept_letters:
            out.append(r)
    path = ROOT / "tools" / "omr" / "tests" / "data_unread_word_sibling_2_303p1.json"
    json.dump(out, open(path, "w"), sort_keys=True)
    print(len(out), "rows ->", path)


main()
