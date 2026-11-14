"""2306 r6: replay ONE record (gathered OMR_PAGE_STEMS=1) through ADJUDICATE..EXPORT, flag 0 and 1, on THIS tree (cwd); dump per arm every verdict
(short detail), the red bars, traced written hosts, and EXPORT's per-glyph fate (`_place_notes` fates). Usage: replay_fates.py REC.json OUTPREFIX"""
import sys, os, json, gc
sys.path.insert(0, os.getcwd())
from tools.omr.staged.record_io import load_record
from tools.omr.staged.review import rerun as RR
from tools.omr.staged import export as E
from tools.omr.staged import lane_report as LR

path, outp = sys.argv[1], sys.argv[2]
rec = load_record(path)["record"]
obs, abst = rec["observations"], rec["abstentions"]
boxes = LR.glyph_boxes(obs)
cap = {}
_orig = E._place_notes


def _wrap(*a, **k):
    out = _orig(*a, **k)
    cap["fates"] = dict(k.get("fates") or {})
    return out


E._place_notes = _wrap


def short(d):
    if not isinstance(d, dict):
        return None
    return {k: v for k, v in d.items() if isinstance(v, (str, int, float, bool)) or k in ("refused_strokes", "used")
            or (isinstance(v, (list, dict)) and len(json.dumps(v, default=str)) < 1500)}


ARMS = sys.argv[sys.argv.index("--arms") + 1].split(",") if "--arms" in sys.argv else ["off", "on"]
for arm, on in (("off", "0"), ("on", "1")):
    if arm not in ARMS:
        continue
    os.environ["OMR_PAGE_STEMS"] = on
    log, _ = RR.rebuild_gather({"observations": obs, "abstentions": abst, "verdicts": [], "format": rec.get("format")})
    RR.run_stages(log)
    j = {"record": log.to_json(), "summary": log.summary()}
    cap.clear()
    with LR.traced_export():
        xml, report = E.to_musicxml(j)
    sym = LR.parse_symbols(xml, boxes)
    red = (report.get("bars_written_red") or {}).get("bars_list") or []
    vs = [dict(q=v["quantity"], s=v["subject"], o=v["outcome"], r=v.get("reason"), v=v.get("value"), d=short(v.get("detail")), u=v.get("used") if v["quantity"] in ("duration", "head_stem", "stem_value", "event") else None) for v in j["record"]["verdicts"]]
    json.dump(dict(verdicts=vs, red=red, hosts=sym["hosts"], fates=cap.get("fates") or {}), open("%s.%s.json" % (outp, arm), "w"), default=str)
    print(arm, "verdicts", len(vs), "red", len(red), "fates", len(cap.get("fates") or {}), flush=True)
    del log, j, xml
    gc.collect()
