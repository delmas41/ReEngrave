"""2.197 C1: replay the saved GATHER rows of the 20261020-night record (a slice dir from c0_slice.py or lane_report's) through the
CURRENT tree's ADJUDICATE..EXPORT (lane_report.run_arm's adjudicate path, no flags set -> tree defaults) and keep what the census needs:
  <out>/<plate>.replay.json  = {tree_sha, verdicts (selected quantities, all fields), xml, obs_keep: glyph_box/accidental rows}
usage: c1_replay.py SLICE_DIR PLATE OUT_DIR"""
import json, os, sys, pathlib, subprocess, collections, time
sys.path.insert(0, os.getcwd())
from tools.omr.staged import export as E
from tools.omr.staged.review import rerun as RR
from tools.omr.staged import lane_report as LR
sl, plate, out = pathlib.Path(sys.argv[1]), sys.argv[2], pathlib.Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
t0 = time.time()
rec = LR.load_slices(sl / plate)
rec["verdicts"] = []
log, idmap = RR.rebuild_gather(rec)
RR.run_stages(log)
result = {"record": log.to_json(), "summary": log.summary()}
print("stages done %.0fs" % (time.time() - t0), flush=True)
with LR.traced_export():
    xml, report = E.to_musicxml(result)
print("export done %.0fs" % (time.time() - t0), flush=True)
vs = result["record"]["verdicts"]
c = collections.Counter(v["quantity"] for v in vs)
print(sorted(c.items(), key=lambda x: -x[1])[:60])
KEEP = ("accidental_owner", "accidental", "key_signature", "accidental_is_not_an_accidental", "keysig_marker_is_not_a_marker",
        "glyph_owner", "notehead_is_not_a_notehead", "pitch", "notehead_staff_position", "clef", "key_change")
keepv = [v for v in vs if v["quantity"] in KEEP or "key" in v["quantity"] or "accid" in v["quantity"]]
obs = result["record"]["observations"]
keepo = [o for o in obs if o["quantity"] in ("glyph_box", "glyph_conf", "accidental_staff_position", "keysig_marker", "cell_box", "staff_lines",
                                             "cell_staff_space", "keysig_template_fit", "keysig_run_position", "keysig_clef_fit")]
sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
(out / (plate + ".replay.json")).write_text(json.dumps(dict(tree_sha=sha, slice=str(sl), verdict_counts=dict(c), verdicts=keepv, observations=keepo,
                                                          report_keys={k: report[k] for k in report if "accid" in k or "key" in k}), default=str))
(out / (plate + ".replay.musicxml")).write_text(xml)
print("wrote", out, len(keepv), len(keepo), sha, flush=True)
