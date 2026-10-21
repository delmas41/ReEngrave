"""2.186 live == replay: re-run the PRODUCTION detector (class-wise NMS, floor 0.25, imgsz_for_cell, same weights) + `one_ink.merge` on whole pages
and compare, per cell, with (a) the record's stored production boxes (reader `detector`) and (b) the replay's merge (`one_ink.plan` on those stored boxes).
usage: live_check_2_186.py lit|bra PAGE[,PAGE...] SLICEDIR OUT.json   (SLICEDIR as slices_2_186.py wrote it)"""
import collections, glob, json, os, sys
sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves
from tools.omr.measure_extractor import extract_measures
from tools.omr.staged.gather import _system_local
from tools.omr.staged import one_ink as OI
from tools.omr.yolo_detector import YoloDetector
PDF = {"lit": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "bra": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
W = "tools/omr/training/data/weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt"
plate, pages, SD, out = sys.argv[1], [int(p) for p in sys.argv[2].split(",")], sys.argv[3], sys.argv[4]
doc = {"lit": "litolff", "bra": "brahms"}[plate]
det = YoloDetector(W)
res = {}
for p in pages:
    stored = collections.defaultdict(list)
    for l in open(os.path.join(SD, doc, "p%02d.observations.jsonl" % p)):
        if '"glyph_box"' in l:
            o = json.loads(l)
            if o["quantity"] == "glyph_box" and o["reader"] == "detector" and isinstance(o["value"], list):
                stored["/".join(o["subject"].split("/")[:5])].append((o["value"][0], o["value"][1], o["value"][2], o["value"][3], o["value"][4], round(o["score"], 3)))
    pws = detect_staves(render_page(PDF[plate], p, dpi=600))
    cells = extract_measures(pws)
    local = _system_local(pws.staves)
    r = collections.Counter()
    for c in cells:
        k = local.get(c.staff_index)
        if k is None:
            continue
        key = "glyph/%d/%d/%d/%d" % (p, k[0], k[1], c.measure_index)
        live = det.detect(c, conf_threshold=0.25)
        lb = sorted((d.smufl_name, d.x_canonical, d.y_canonical, d.width_canonical, d.height_canonical, round(d.confidence, 3)) for d in live)
        sb = sorted(stored.get(key, []))
        r["cells"] += 1
        r["cells_live_boxes_equal_stored"] += int(lb == sb)
        r["live_boxes"] += len(lb); r["stored_boxes"] += len(sb)
        merged = OI.merge(live)
        plan = OI.plan([(d.smufl_name, d.x_canonical, d.y_canonical, d.width_canonical, d.height_canonical, d.confidence) for d in live])
        r["live_merged_winners"] += sum(1 for d in merged if d.one_ink_rivals)
        r["live_absorbed"] += len(live) - len(merged)
        splan = OI.plan([(a, b, c_, d_, e, f) for a, b, c_, d_, e, f in sorted(stored.get(key, []), key=lambda t: 0)])
        r["replay_absorbed"] += sum(len(i["absorbed"]) for i in splan.values())
        r["live_plan_equals_replay_plan(by winner class/box)"] += int(sorted((live[i].smufl_name, live[i].x_canonical) for i in plan) == sorted((stored[key][i][0], stored[key][i][1]) for i in splan) if key in stored else not plan)
    res[p] = dict(r)
    print(plate, p, dict(r), flush=True)
    json.dump(res, open(out, "w"), indent=1)
