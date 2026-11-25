"""2.306 r23 item 3: does retiring the old cell join for COPIES (a head box filed with another staff, `Q.PAGE_STEM` abstention
`copy_on_another_staff`) change the exported file? One gathered record, re-adjudicated twice in this tree: as gathered (copies say so, the
old join no longer answers) and with the copy rows dropped (the old join answers for them, as r22). Same GATHER, same tree, the one change.
Usage (from the worktree, flags as the ON arm): r23_copy_proof.py GATHERED.record.json PLATE COUNT_PAGES OUT_PREFIX [keep|drop]
  keep|drop runs ONE variant and writes OUT_PREFIX.<variant>.symbols.json + .musicxml (one process per variant: memory);
  with neither, it diffs the two saved symbol files."""
import json
import os
import sys

sys.path.insert(0, os.getcwd())
from tools.omr.staged import lane_report as LR  # noqa: E402

rec_p, plate, pages, pre = sys.argv[1:5]
count = {int(x) for x in pages.split(",")}
if len(sys.argv) > 5:
    from tools.omr.staged import export as E
    from tools.omr.staged.record_io import load_record
    from tools.omr.staged.review import rerun as RR
    variant = sys.argv[5]
    rec = load_record(rec_p)
    rec = rec.get("record", rec)
    ab = rec.get("abstentions") or []
    copies = [a for a in ab if (a.get("detail") or {}).get("how") == "copy_on_another_staff"]
    if variant == "drop":
        ab = [a for a in ab if (a.get("detail") or {}).get("how") != "copy_on_another_staff"]
    print(variant, "copy rows", len(copies), "kept" if variant == "keep" else "dropped", flush=True)
    obs = rec["observations"]
    boxes = LR.glyph_boxes(obs)
    log, _ = RR.rebuild_gather(dict(observations=obs, abstentions=ab, verdicts=[]))
    del rec, ab
    RR.run_stages(log)
    result = {"record": log.to_json(), "summary": log.summary()}
    del log
    with LR.traced_export():
        xml, report = E.to_musicxml(result)
    hs = [v for v in result["record"]["verdicts"] if v["quantity"] == "head_stem"]
    sym = LR.parse_symbols(xml, boxes)
    sym["hosts"] = [h for h in sym["hosts"] if h["page"] is None or h["page"] in count]
    sym["loose"] = [d for d in sym["loose"] if d.get("page") is None or d["page"] in count]
    sym["head_stem_reasons"] = {}
    for v in hs:
        sym["head_stem_reasons"][v.get("reason") or v.get("outcome")] = sym["head_stem_reasons"].get(v.get("reason") or v.get("outcome"), 0) + 1
    open(pre + "." + variant + ".musicxml", "w").write(xml)
    json.dump(sym, open(pre + "." + variant + ".symbols.json", "w"), default=str)
    print(variant, "done", sym["head_stem_reasons"])
else:
    a = json.load(open(pre + ".drop.symbols.json"))
    b = json.load(open(pre + ".keep.symbols.json"))
    d = LR.diff_arms(a, b, tol=0.5 * LR.PLATES[plate]["unit"])
    print(plate, "copies retired (drop -> keep):", LR.format_counts(d["counts"]))
    print("  head_stem reasons drop:", a["head_stem_reasons"])
    print("  head_stem reasons keep:", b["head_stem_reasons"])
    same_xml = open(pre + ".drop.musicxml").read() == open(pre + ".keep.musicxml").read()
    print("  musicxml byte-identical:", same_xml)
