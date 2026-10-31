"""2.240 step 3: replay a lane-report slice (the same rebuild + stages `lane_report.run_arm` uses) with OMR_PAGE_OWNER_READ OFF or ON and keep
what the mini-record drops: every `glyph_owner` / `arc_owner` verdict, the page-owner rows, the glyph boxes.

    PYTHONPATH=. python3 benchmarks/page-ledger-2026-10/s4/owner_verdicts.py PLATE TAG ARM OUT.json
"""
import json
import os
import sys


def main():
    plate, tag, arm, out = sys.argv[1:5]
    os.environ["OMR_PAGE_OWNER_READ"] = "1" if arm == "on" else "0"
    from tools.omr.staged import lane_report as L
    from tools.omr.staged.review import rerun as RR
    rec = L.load_slices(L.slice_dir(plate, tag))
    rec["verdicts"] = []
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    j = log.to_json()
    keep = {"verdicts": [v for v in j["verdicts"] if v["quantity"] in ("glyph_owner", "arc_owner", "notehead_is_not_a_notehead")],
            "observations": [o for o in j["observations"] if o["quantity"] in ("glyph_box", "page_mark_owner", "page_span")],
            "abstentions": [a for a in j["abstentions"] if a["quantity"] in ("page_mark_owner",)]}
    with open(out, "w") as fh:
        json.dump(keep, fh, default=str)
    print("wrote", out, {k: len(v) for k, v in keep.items()})


if __name__ == "__main__":
    main()
