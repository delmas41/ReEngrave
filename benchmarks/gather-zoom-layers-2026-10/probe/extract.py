"""2.152 -- one streamed pass over a record -> a slim pickle of what the three layers need (boxes, staves, verdicts).

    python3 extract.py DOC OUT.pkl        DOC in rec.RECORDS (litolff | brahms | brahms_p0p3)

GATHER rows only (glyph_box, notehead_class, rest, staff_lines/spacing/extent, cell_box) plus the standing ADJUDICATE verdicts
of the gates (notehead_is_not_a_notehead, rest_is_not_a_rest, dynamic_is_not_a_dynamic, duration). Nothing is decided here.
"""
import pickle
import sys
from collections import defaultdict

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import rec  # noqa: E402

KEEP_OBS = {"glyph_box", "notehead_class", "rest", "staff_lines", "staff_spacing", "staff_extent", "staff_ordinal",
            "system_staff_count", "cell_box", "cell_staff_space", "glyph_band_distance", "aug_dot",
            "dynamic_letter", "notehead_staff_position"}
KEEP_VRD = {"notehead_is_not_a_notehead", "rest_is_not_a_rest", "dynamic_is_not_a_dynamic", "duration",
            "unboxed_ink_is_a_rest", "accidental_is_not_an_accidental"}


def run(doc, out):
    P = rec.RECORDS[doc]
    D = {"box": {}, "ncls": {}, "rest": {}, "staff": defaultdict(dict), "sys": {}, "cell": {}, "cellsp": {},
         "band": {}, "vrd": {}, "npos": {}, "dyn": {}, "adot": {}}
    with rec.lock():
        for o in rec.items(P, "observations"):
            q = o["quantity"]
            if q not in KEEP_OBS:
                continue
            s = o["subject"]
            if q == "glyph_box":
                d = o["detail"]
                D["box"][s] = (o["value"][0], d.get("category"), o.get("score"), tuple(d["bbox_page_px"]))
            elif q == "notehead_class":
                D["ncls"][s] = (o["value"], o.get("score"))
            elif q == "rest":
                D["rest"][s] = (o["value"], o.get("score"), tuple(o["detail"]["bbox_page_px"]))
            elif q in ("staff_lines", "staff_spacing", "staff_extent", "staff_ordinal"):
                D["staff"][s][q] = o["value"]
            elif q == "system_staff_count":
                D["sys"][s] = o["value"]
            elif q == "cell_box":
                D["cell"][s] = tuple(o["value"])
            elif q == "cell_staff_space":
                D["cellsp"][s] = o["value"]
            elif q == "glyph_band_distance":
                d = o["detail"]
                if d.get("own"):
                    D["band"][s] = (o["value"], d.get("local_position_in_candidate"))
            elif q == "notehead_staff_position":
                D["npos"][s] = o["value"]
            elif q == "dynamic_letter":
                D["dyn"][s] = (o["value"], o.get("score"), tuple(o["detail"]["bbox_page_px"]))
            elif q == "aug_dot":
                D["adot"][s] = o["score"]
        for v in rec.items(P, "verdicts"):
            q = v["quantity"]
            if q not in KEEP_VRD:
                continue
            val = v["value"]
            if q == "duration" and isinstance(val, dict):
                val = {k: val.get(k) for k in ("beats", "written", "dots", "is_rest")}
            cands = v.get("candidates")
            D["vrd"][(v["subject"], q)] = (v["outcome"], val, v.get("reason"), v.get("decider"),
                                           (v.get("detail") or {}).get("class"), cands and len(cands))
    D["staff"] = dict(D["staff"])
    pickle.dump(D, open(out, "wb"))
    print(doc, {k: len(v) for k, v in D.items()})


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
