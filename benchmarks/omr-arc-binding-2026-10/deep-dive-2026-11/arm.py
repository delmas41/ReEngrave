"""ARC DEEP DIVE 2026-11 (measure only). One (plate, arm): re-adjudicate the saved 20261104-night GATHER rows of the frozen
sample pages (the lane report's own replay, `--from adjudicate`), export, and write a COMPACT arc dump:

    python3 benchmarks/omr-arc-binding-2026-10/deep-dive-2026-11/arm.py PLATE ARMNAME OUTDIR [ENV=VAL ...] [--tag 20261104-night]

OUTDIR/PLATE.ARMNAME.arcs.json  holds, per arc: its detector box, the page-curve row (Q.SYSTEM_ARC), every verdict/abstention that touches
it (ARC_IS_NOT_AN_ARC, ARC_OWNER, ARC_KIND, TIE_PAIR), the exporter's arc counters, and the written ties / slurs (by glyph key).
No tools/ code is changed; flags are plain environment variables set before the import of the staged modules.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))   # (a --code dir given later is put in front of this)


def main() -> None:
    argv = sys.argv[1:]
    tag = "20261104-night"
    if "--tag" in argv:
        i = argv.index("--tag")
        tag = argv[i + 1]
        del argv[i:i + 2]
    pages_arg = None
    if "--code" in argv:        # a lane branch's tree, exported read-only to a scratch dir (git archive); never edited
        i = argv.index("--code")
        sys.path.insert(0, argv[i + 1])
        del argv[i:i + 2]
    if "--pages" in argv:
        i = argv.index("--pages")
        pages_arg = [int(x) for x in argv[i + 1].split(",")]
        del argv[i:i + 2]
    only_pages = None
    if "--only-pages" in argv:
        i = argv.index("--only-pages")
        only_pages = [int(x) for x in argv[i + 1].split(",")]
        del argv[i:i + 2]
    plate, arm, out = argv[0], argv[1], pathlib.Path(argv[2])
    for kv in argv[3:]:
        k, v = kv.split("=", 1)
        os.environ[k] = v
    os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
    out.mkdir(parents=True, exist_ok=True)
    from tools.omr.staged import lane_report as L
    from tools.omr.staged import export as E
    from tools.omr.staged.review import rerun as RR
    sample = L.load_sample()
    count_pages = pages_arg or sample["plates"][plate]["pages"]
    t0 = time.time()
    rec = L.load_slices(L.slice_dir(plate, tag))
    if only_pages is not None:      # the replay is cut to these pages (+ every document-level row); the opening page is a context page
        keep_pg = set(only_pages)
        for kind in ("observations", "abstentions"):
            rec[kind] = [it for it in rec[kind] if L.page_of(it.get("subject")) is None or L.page_of(it.get("subject")) in keep_pg]
    boxes = L.glyph_boxes(rec["observations"])
    rec["verdicts"] = []
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    result = {"record": log.to_json(), "summary": log.summary()}
    del log
    r = result["record"]
    with L.traced_export():
        try:    # the exporter's own refusals per subject (review.rerun, with its sum-back control); a failed control falls back to the plain export
            xml, report, refusals, _placed = RR.export_with_subjects(result)
        except RuntimeError:
            xml, report = E.to_musicxml(result)
            refusals = []
    sym = L.parse_symbols(xml, boxes)
    cp = set(count_pages)
    page_of = L.page_of
    keep = lambda subj: (page_of(subj) in cp)                                    # noqa: E731
    obs = r["observations"]
    verd = r["verdicts"]
    abst = r.get("abstentions") or []
    Q_OBS = {"arc_box", "system_arc", "arc_ink_shape", "arc_position"}
    Q_VER = {"arc_is_not_an_arc", "arc_owner", "arc_kind", "tie_pair", "notehead_is_not_a_notehead", "glyph_owner"}
    dump = {"plate": plate, "arm": arm, "tag": tag, "env": {k: os.environ[k] for k in os.environ if k.startswith("OMR_") and k != "OMR_SURYA_KEEP_ALIVE"},
            "pages": sorted(cp)}
    dump["arc_box"] = [o for o in obs if o["quantity"] == "arc_box" and keep(o["subject"])]
    sa = []
    for o in obs:
        if o["quantity"] == "system_arc" and keep(o["subject"]):
            d = dict(o)
            d["detail"] = {k: v for k, v in o["detail"].items() if k not in ("trace",)}
            d["detail"]["trace_n"] = len(o["detail"].get("trace") or [])
            sa.append(d)
    dump["system_arc"] = sa
    dump["heads"] = [{"subject": o["subject"], "box": o["detail"].get("bbox_page_px"), "cat": o["detail"].get("category"), "value": o["value"]}
                     for o in obs if o["quantity"] == "glyph_box" and (o["detail"] or {}).get("category") == "notehead" and keep(o["subject"])]
    from slim import slim_verdict
    dump["verdicts"] = [slim_verdict(v) for v in verd if v["quantity"] in Q_VER and keep(v["subject"])]
    dump["abstentions"] = [a for a in abst if a.get("quantity") in Q_VER and keep(a["subject"])]
    dump["report_arc"] = {k: v for k, v in report.items() if any(s in k.lower() for s in ("arc", "slur", "tie"))}
    dump["refusals"] = [[s, r] for s, r in refusals if s and keep(s)]
    dump["report_other"] ={k: report.get(k) for k in ("notes_not_written", "notes_not_written_total", "bars_written_red", "bars_held_out_sum")}
    dump["hosts"] =[h for h in sym["hosts"] if h["page"] is None or h["page"] in cp]
    dump["loose"] = [d for d in sym["loose"] if d.get("page") is None or d["page"] in cp]
    dump["seconds"] = round(time.time() - t0, 1)
    (out / ("%s.%s.arcs.json" % (plate, arm))).write_text(json.dumps(dump, default=str))
    from tools.omr.staged.judged import _QUANTITIES as JQ     # the mini record the lane report scores Sean's judged answers against
    mini = {"observations": [o for o in obs if o["quantity"] == "glyph_box"], "abstentions": [], "verdicts": [v for v in verd if v["quantity"] in JQ]}
    (out / ("%s.%s.mini-record.json" % (plate, arm))).write_text(json.dumps(mini, default=str))
    (out / ("%s.%s.musicxml" % (plate, arm))).write_text(xml)
    print("done %s %s in %.0fs: arcs %d, curves %d, hosts %d" % (plate, arm, dump["seconds"], len(dump["arc_box"]), len(sa), len(dump["hosts"])))


if __name__ == "__main__":
    main()
