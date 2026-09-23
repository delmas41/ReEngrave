"""Did the Viola's heads land on VIOLIN II or on CELLO instead?

The padded measure cell reaches the next staff's ink (CLAUDE.md §10), so the
same head is detected once per staff and `glyph_owner` arbitrates. This asks
the question BOTH ways, restricted to NOTEHEAD classes, and prices it:

  (a) noteheads filed under the Viola's cells whose owner is another staff;
  (b) noteheads filed under a NEIGHBOUR's cells whose owner is the Viola;
  (c) what each of those was refused under -- because a contest DROPS the
      loser, so (b) only reaches the file if the Viola's own copy does.

⚠️ `glyph_owner` is adjudicated on the CONTESTED population only, so a
notehead with NO `glyph_owner` verdict is uncontested and belongs to the
staff whose cell it sits in. Counted here as `uncontested`, never as
`owner_self`, so the two cannot be confused.
"""
from __future__ import annotations
import argparse, collections, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged.record_io import load_record            # noqa: E402
from tools.omr.yolo_detector import _class_name_to_category   # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--funnel", required=True)
    ap.add_argument("--page", type=int, default=3)
    ap.add_argument("--system", type=int, default=0)
    ap.add_argument("--staff", type=int, default=9)
    ap.add_argument("--out-json", required=True)
    a = ap.parse_args()

    d = load_record(a.record)
    pre = f"/{a.page}/{a.system}/"
    boxes, owners = {}, {}
    for o in d["record"]["observations"]:
        s = o["subject"]
        if o["quantity"] == "glyph_box" and s.startswith("glyph" + pre):
            if _class_name_to_category(o["value"][0]) == "notehead":
                boxes[s] = {"class": o["value"][0],
                            "page_box": o["detail"].get("bbox_page_px")}
    for v in d["record"]["verdicts"]:
        s = v["subject"]
        if v["quantity"] == "glyph_owner" and s in boxes:
            owners[s] = v.get("value") if v["outcome"] == "decided" else None

    F = json.loads(Path(a.funnel).read_text())
    refusal_of = dict(F["page_glyph_refusals"])

    home = f"staff/{a.page}/{a.system}/{a.staff}"
    out = {"from_subject_staff_to_others": collections.Counter(),
           "from_others_to_subject_staff": collections.Counter(),
           "uncontested_on_subject_staff": 0,
           "detail_others_to_subject": []}
    for s, b in boxes.items():
        st = int(s.split("/")[3])
        own = owners.get(s)
        if st == a.staff:
            if s not in owners:
                out["uncontested_on_subject_staff"] += 1
            elif own and own != home:
                out["from_subject_staff_to_others"][own] += 1
        elif own == home:
            out["from_others_to_subject_staff"][f"staff/{a.page}/{a.system}/{st}"] += 1
            out["detail_others_to_subject"].append(
                {"glyph": s, "class": b["class"], "page_box": b["page_box"],
                 "cell": int(s.split("/")[4])})

    # heads each staff WROTE in this system, from the funnel's page table
    wrote = {}
    for key, cells in F["page_funnel"].items():
        p, sy, st = key.split("/")
        if int(p) == a.page and int(sy) == a.system:
            wrote[key] = sum(c.get("written", 0) for c in cells.values())

    # ── (d) THE GEOMETRIC TEST, which needs no verdict at all: is any head
    # a NEIGHBOUR wrote actually standing on the Viola's own five lines?
    # `glyph_owner` only speaks where it was asked; this asks the page.
    lines = spacing = None
    for o in d["record"]["observations"]:
        if o["subject"] == home and o["quantity"] == "staff_lines":
            lines = o["value"]
        if o["subject"] == home and o["quantity"] == "staff_spacing":
            spacing = float(o["value"])
    band = (lines[0] - 2 * spacing, lines[-1] + 2 * spacing)
    on_our_staff = collections.Counter()
    for s, b in boxes.items():
        st = int(s.split("/")[3])
        if st == a.staff or not b["page_box"]:
            continue
        yc = (b["page_box"][1] + b["page_box"][3]) / 2.0
        if band[0] <= yc <= band[1] and not refusal_of.get(s):
            on_our_staff[f"staff/{a.page}/{a.system}/{st}"] += 1

    res = {
        "subject_staff": home,
        "subject_staff_band_page_px": [round(band[0], 1), round(band[1], 1)],
        "heads_WRITTEN_by_a_neighbour_standing_in_that_band":
            dict(on_our_staff),
        "noteheads_in_subject_cells_owned_elsewhere":
            dict(out["from_subject_staff_to_others"]),
        "noteheads_in_other_cells_owned_by_subject":
            dict(out["from_others_to_subject_staff"]),
        "detail_others_to_subject": out["detail_others_to_subject"],
        "uncontested_noteheads_in_subject_cells":
            out["uncontested_on_subject_staff"],
        "heads_written_per_staff_this_system": wrote,
        "refusals_of_the_cross_staff_rows": {
            e["glyph"]: refusal_of.get(e["glyph"]) for e in
            out["detail_others_to_subject"]},
    }
    Path(a.out_json).write_text(json.dumps(res, indent=2))
    print(json.dumps({k: v for k, v in res.items()
                      if k != "detail_others_to_subject"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
