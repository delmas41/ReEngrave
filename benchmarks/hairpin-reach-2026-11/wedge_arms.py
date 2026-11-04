"""ROADMAP 2.261 fix 1: CV wedge reads in the OFF and ON gathered records of a lane_report work dir, and the beam-between-stems refusals.

    python3 benchmarks/hairpin-reach-2026-11/wedge_arms.py out/2.261-fix1/work litolff brahms
"""
import sys

sys.path.insert(0, ".")
from tools.omr.staged.record_io import load_record  # noqa: E402


def rows(path):
    w = load_record(path)
    rec = w.get("record", w)
    wb = {o["subject"]: [round(v) for v in o["detail"]["bbox_page_px"]] for o in rec["observations"]
          if o["quantity"] == "wedge_box" and o.get("reader") == "cv_hairpins" and o["detail"].get("bbox_page_px")}
    ref = [(a["subject"], a["detail"]) for a in rec["abstentions"]
           if a.get("quantity") == "wedge_box" and (a.get("detail") or {}).get("why") == "beam_between_two_stems"]
    return wb, ref


for plate in sys.argv[2:]:
    off, _ = rows("%s/%s.off.gathered.record.json" % (sys.argv[1], plate))
    on, ref = rows("%s/%s.on.gathered.record.json" % (sys.argv[1], plate))
    print(plate, "OFF wedges", len(off), "ON wedges", len(on))
    print("  lost in ON:", sorted(set(off) - set(on)))
    print("  gained in ON:", sorted(set(on) - set(off)))
    for s, d in ref:
        print("  refused", s, d["bbox_page_px"], d["width_spaces"], "stems", d["stem_left_spaces"], d["stem_right_spaces"])
