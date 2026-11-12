"""ROADMAP 2.303 PART 1: cut the REAL rows the test of `OMR_UNREAD_WORD_SIBLING` runs on, from the saved gather of the 20261029-night record (sliced for the frozen sample by `lane_report`).

    python3 benchmarks/dynamics-not-words-2026-11/make_fixture_2_303p1.py

Regions (the print Sean judged / the places the flag first changed wrongly):
 (A) Litolff p8 system 0, x >= 1480 -- `sempre piu p` printed on staves 0-3 and 5-8 (staves 0-3 cut by a barline, the lexicon refused those; staff 8 READ), and the real lone `pp` of staff 8 bar 17;
 (B) Litolff p8 system 1, staff 4 bar 12 -- the lone `ff` Sean judged a dynamic (2.301 r1 tile 3), which has an unread candidate window over it;
 (C) Brahms p0 system 0 staff 10 (`f espr. e legato`, unread there, read on neighbouring staves): the round-1 build lost an `ff` / `f` here (2.303 part 1 round 2, fault 1).
Keeps the rows of three quantities (dynamic letter, its neighbour ink, direction word) whose page box meets a region, as the log held them. Writes
tools/omr/tests/data_unread_word_sibling_2_303p1.json.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SLICES = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261029-night")
REGIONS = [("litolff", 8, 0, [1480, 440, 2120, 1800]), ("litolff", 8, 1, [1540, 2560, 1760, 2720]), ("brahms", 0, 0, [1480, 0, 2300, 9000])]
KEEP = ("dynamic_letter", "dynamic_letter_neighbours", "direction_word")


def meets(bb, box):
    return bb[0] < box[2] and bb[2] > box[0] and bb[1] < box[3] and bb[3] > box[1]


def main():
    out = []
    for plate, page, system, box in REGIONS:
        rows, boxes_of = [], {}
        for fn, kind in (("observations.jsonl", "obs"), ("abstentions.jsonl", "abs")):
            for line in open(SLICES / plate / fn):
                r = json.loads(line)
                if r.get("quantity") not in KEEP:
                    continue
                p = r["subject"].split("/")
                if p[0] != "glyph" or int(p[1]) != page or int(p[2]) != system:
                    continue
                r["_kind"] = kind
                rows.append(r)
                bb = (r.get("detail") or {}).get("bbox_page_px")
                if bb and r["quantity"] != "dynamic_letter_neighbours":
                    boxes_of[r["subject"]] = bb
        kept = [r for r in rows if r["quantity"] != "dynamic_letter_neighbours" and r["subject"] in boxes_of and meets(boxes_of[r["subject"]], box)]
        letters = {r["subject"] for r in kept if r["quantity"] == "dynamic_letter"}
        kept += [r for r in rows if r["quantity"] == "dynamic_letter_neighbours" and r["subject"] in letters]
        seen = {(r["_kind"], r["id"]) for r in out}
        out += [r for r in kept if (r["_kind"], r["id"]) not in seen]
    path = ROOT / "tools" / "omr" / "tests" / "data_unread_word_sibling_2_303p1.json"
    json.dump(out, open(path, "w"), sort_keys=True)
    print(len(out), "rows ->", path)


main()
