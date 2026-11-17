"""Write brahms.{off,on}.{musicxml,mini-record.json} (the names truth_p0.py reads) from run_arms.py's output."""
import json
import pathlib
import shutil
import sys

w = pathlib.Path(sys.argv[1])
for arm in ("off", "on"):
    rec = json.load(open(w / ("%s.record.json" % arm)))
    mini = {"observations": [o for o in rec["observations"] if o.get("quantity") == "glyph_box"], "abstentions": [], "verdicts": []}
    (w / ("brahms.%s.mini-record.json" % arm)).write_text(json.dumps(mini))
    shutil.copy(w / ("%s.musicxml" % arm), w / ("brahms.%s.musicxml" % arm))
