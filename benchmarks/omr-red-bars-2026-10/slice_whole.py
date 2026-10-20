"""ROADMAP 2.173 whole-class rules, FAST measurement: re-decide ADJUDICATE..INFER over only the SYSTEMS that hold a whole-class box
(`noteheadWhole*`), flag OFF vs ON, and list every whole-class glyph's outcome. Not an export (the full-export measure is rerun_whole.py);
this tunes the rule cheaply.
usage: slice_whole.py RECORD.json OUTDIR TAG
Writes OUTDIR/TAG.slice.json: {arm: {glyph: {cls, notehead(outcome, reason), duration(outcome, beats, reason)}}} and the mini records
for `judged score` (OUTDIR/TAG.slice.<arm>.record.json)."""
import collections
import json
import os
import sys
import time

sys.path.insert(0, ".")
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

path, outdir, tag = sys.argv[1], sys.argv[2], sys.argv[3]
t0 = time.time()
res = load_record(path)
rec = res["record"]
whole_sys = set()
for o in rec["observations"]:
    if o["quantity"] == "glyph_box" and o["subject"].startswith("glyph/") and str(o["value"][0]).startswith("noteheadWhole"):
        p = o["subject"].split("/")
        whole_sys.add((p[1], p[2]))
print(tag, "whole-class systems", len(whole_sys), "loaded %.0fs" % (time.time() - t0), flush=True)


def keep(subject):
    p = subject.split("/")
    if len(p) >= 3 and p[0] in ("glyph", "cell", "staff", "system", "mark", "page", "mg"):
        return (p[1], p[2]) in whole_sys if p[0] != "page" else True
    return True


obs = [o for o in rec["observations"] if keep(o["subject"])]
abst = [o for o in rec["abstentions"] if keep(o["subject"])]
print("rows kept", len(obs), len(abst), flush=True)
JUDGED_Q = {"duration", "notehead_is_not_a_notehead", "unboxed_ink_is_a_rest", "notehead_is_an_eighth_rest", "arc_kind"}
sl = {"observations": obs, "abstentions": abst}
out = {}
for arm in ("off", "on"):
    os.environ["OMR_WHOLE_NEEDS_HOLLOW_NO_STEM"] = "1" if arm == "on" else "0"
    log, _ = RR.rebuild_gather(sl)
    RR.run_stages(log)
    vs = log.to_json()["verdicts"]
    cls = {}
    for o in log.to_json()["observations"]:
        if o["quantity"] == "notehead_class" and str(o["value"]).startswith("noteheadWhole"):
            cls[o["subject"]] = o["value"]

    def live(q):
        ch = collections.defaultdict(list)
        for v in vs:
            if v["quantity"] == q and v["subject"] in cls:
                ch[v["subject"]].append(v)
        r = {}
        for g, c in ch.items():
            sup = {x.get("supersedes") for x in c if x.get("supersedes")}
            r[g] = ([x for x in c if x["id"] not in sup] or c)[-1]
        return r
    nh, du = live("notehead_is_not_a_notehead"), live("duration")
    arm_out = {}
    for g, c in cls.items():
        n, d = nh.get(g), du.get(g)
        arm_out[g] = dict(cls=c, notehead=[n["value"], n.get("reason")] if n else None,
                          duration=[d["outcome"], (d.get("value") or {}).get("beats") if isinstance(d.get("value"), dict) else None,
                                    d.get("reason")] if d else None)
    out[arm] = arm_out
    boxes = [{k: o.get(k) for k in ("id", "subject", "quantity", "detail")} for o in obs
             if o["quantity"] == "glyph_box" and o["subject"].startswith("glyph/")]
    json.dump({"observations": boxes, "abstentions": [], "verdicts": [v for v in vs if v["quantity"] in JUDGED_Q]},
              open(os.path.join(outdir, "%s.slice.%s.record.json" % (tag, arm)), "w"), default=str)
    print(arm, "whole-class glyphs", len(arm_out), "%.0fs" % (time.time() - t0), flush=True)
    del log, vs
json.dump(out, open(os.path.join(outdir, tag + ".slice.json"), "w"))
