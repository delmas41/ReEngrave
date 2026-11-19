"""ROADMAP 2.326 small test (read-only): Sean's judged duration tiles on one plate, found in the 20261117-night record by
place (`judged.score`, streamed -- the record is never loaded whole), with every fill reading the record holds for the head
and its standing duration verdict. Writes work/judged-<doc>.json.

    python3 benchmarks/notehead-fill-by-page-2026-11/extract_judged.py litolff
"""
import json
import pathlib
import sys

from tools.omr.staged import judged as J

ROOT = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records")
REC = {"litolff": ROOT / "beethoven5-litolff-mvt1-whole-20261117-night.record.json",
       "brahms": ROOT / "brahms1-breitkopf-mvt1-whole-20261117-night.record.json"}
OUT = pathlib.Path(__file__).parent / "work"
OBS_Q = ("glyph_box", "notehead_ink", "head_ink", "notehead_class", "notehead_recentre", "head_oval")


def cell_of(sub):
    p = sub.split("/")
    return "cell/" + "/".join(p[1:5])


def main(doc):
    rec = REC[doc]
    index = json.load(open("benchmarks/acceptance/judged-tiles.json"))
    rows = {(r["item"], r["tile"]): r for r in index["tiles"]}
    rep = J.score(index, rec, doc)
    heads = []
    for t in rep["tiles"]:
        r = rows.get((t["item"], t["tile"]))
        if r is None or r["answer_kind"] != "duration" or r["value"] is None:
            continue
        sub = t["subject"]
        if not isinstance(sub, str):
            continue
        heads.append({"item": t["item"], "tile": t["tile"], "subject": sub, "answer": r["answer"], "value": r["value"],
                      "status_today": t["status"], "note_today": t["note"], "matched_by": t["matched_by"],
                      "tile_page_box": r["page_box"]})
    subs = {h["subject"] for h in heads}
    cells = {cell_of(s) for s in subs}
    obs = {}
    for o in J.iter_array(rec, "observations"):
        s, q = o.get("subject"), o.get("quantity")
        if (s in subs and q in OBS_Q) or (s in cells and q in ("cell_staff_space", "cell_box")):
            obs.setdefault(s, {})[q] = {"value": o.get("value"), "detail": o.get("detail"), "score": o.get("score"),
                                        "reader": o.get("reader"), "frame": o.get("frame")}
    S = J.standing_for(rec, subs, quantities=("duration", "notehead_is_not_a_notehead", "head_ink"))
    for h in heads:
        s = h["subject"]
        h["obs"] = obs.get(s, {})
        h["cell"] = obs.get(cell_of(s), {})
        h["duration"] = S.get((s, "duration"))
        h["not_a_notehead"] = S.get((s, "notehead_is_not_a_notehead"))
    OUT.mkdir(exist_ok=True)
    json.dump({"doc": doc, "record": str(rec), "totals": rep["totals"], "matched": rep["matched"], "heads": heads},
              open(OUT / ("judged-%s.json" % doc), "w"), default=str)
    print(doc, "duration heads", len(heads), "totals", rep["totals"])


if __name__ == "__main__":
    main(sys.argv[1])
