"""2306 r2: replay ONE record (gathered with OMR_PAGE_STEMS=1) through ADJUDICATE..EXPORT with the flag 0 and 1 on THIS tree (cwd), and dump per arm:
every verdict (quantity, subject, outcome, reason, value, short detail) and the export report's red bars list + the traced written hosts.
Usage: diag_replay.py REC.json OUTPREFIX"""
import sys, os, json, gc
sys.path.insert(0, os.getcwd())
from tools.omr.staged.record_io import load_record
from tools.omr.staged.review import rerun as RR
from tools.omr.staged import export as E
from tools.omr.staged import lane_report as LR

path, outp = sys.argv[1], sys.argv[2]
res = load_record(path)
rec = res["record"]
obs, abst = rec["observations"], rec["abstentions"]
boxes = LR.glyph_boxes(obs)


def short(d):
    if not isinstance(d, dict):
        return None
    keep = {}
    for k in ("stem", "stem_rows", "page_how", "page_stroke", "direction", "members", "voice", "voices", "events", "chord", "partner", "used_stem"):
        if k in d:
            keep[k] = d[k]
    return keep


for arm, on in (("off", "0"), ("on", "1")):
    os.environ["OMR_PAGE_STEMS"] = on
    log, _ = RR.rebuild_gather({"observations": obs, "abstentions": abst, "verdicts": [], "format": rec.get("format")})
    RR.run_stages(log)
    j = {"record": log.to_json(), "summary": log.summary()}
    with LR.traced_export():
        xml, report = E.to_musicxml(j)
    sym = LR.parse_symbols(xml, boxes)
    red = (report.get("bars_written_red") or {}).get("bars_list") or []
    vs = [dict(q=v["quantity"], s=v["subject"], o=v["outcome"], r=v.get("reason"), v=v.get("value"), d=short(v.get("detail"))) for v in j["record"]["verdicts"]]
    json.dump(dict(verdicts=vs, red=red, hosts=sym["hosts"], loose=sym.get("loose")), open("%s.%s.json" % (outp, arm), "w"), default=str)
    print(arm, "verdicts", len(vs), "red", len(red), "hosts", len(sym["hosts"]), flush=True)
    del log, j, xml
    gc.collect()
