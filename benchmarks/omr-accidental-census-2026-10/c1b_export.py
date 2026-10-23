"""2.197 C1b: a full gathered record (tools.omr.staged --out, current tree) -> traced MusicXML + the slim view the census reads.
usage: c1b_export.py RECORD.json OUT_PREFIX [TREE_SHA]"""
import json, os, sys, collections
sys.path.insert(0, os.getcwd())
from tools.omr.staged import export as E
from tools.omr.staged import lane_report as LR
from tools.omr.staged.record_io import load_record
rp, pre = sys.argv[1], sys.argv[2]
result = load_record(rp)
if "record" not in result: result = {"record": result, "summary": {}}
with LR.traced_export():
    xml, report = E.to_musicxml(result)
rec = result["record"]
obs = [o for o in rec["observations"] if o["quantity"] in ("glyph_box", "accidental_staff_position", "keysig_marker", "cell_box", "cell_staff_space",
                                                           "keysig_template_fit", "keysig_run_position", "notehead_staff_position")]
keepv = [v for v in rec["verdicts"] if v["quantity"] in ("accidental_owner", "accidental", "key_signature", "accidental_is_not_an_accidental",
                                                         "keysig_marker_is_not_a_marker", "glyph_owner", "notehead_is_not_a_notehead", "pitch", "part_key", "system_key")]
json.dump(dict(tree_sha=(sys.argv[3] if len(sys.argv) > 3 else None), record=dict(observations=obs, verdicts=keepv), source=rp,
               report_keys={k: report[k] for k in report if "accid" in k or "key" in k}), open(pre + ".view.json", "w"), default=str)
open(pre + ".musicxml", "w").write(xml)
print("ok", len(obs), len(keepv))
