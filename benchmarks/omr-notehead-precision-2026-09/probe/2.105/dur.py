"""duration verdict (ADJUDICATE) of named glyphs. usage: dur.py RECORD KEY..."""
import sys

from tools.omr.staged.readout import load_run
from tools.omr.staged.record import Q

run = load_run(sys.argv[1])
for k in sys.argv[2:]:
    v = run.standing(k, Q.DURATION, "ADJUDICATE")
    d = (v or {}).get("detail") or {}
    print(k, run.glyphs[k].cls, (v or {}).get("outcome"), (v or {}).get("value"), (v or {}).get("reason"),
          {x: d.get(x) for x in ("tip_unread", "candidates") if x in d})
