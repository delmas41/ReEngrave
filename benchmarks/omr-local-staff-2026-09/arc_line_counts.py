"""lane-arc-not-a-line: counts + seeded samples, replaying the CURRENT `adjudicate_arc_is_not_an_arc` through the real harness over the
re-measured `Q.ARC_INK_SHAPE` rows.   python3 arc_line_counts.py <tag> [n_per_class] -> out/arc_line_counts_<tag>.json
Thresholds are the ones fixed in family_precision.py BEFORE any count (ARC_LINE_*, ARC_BARLINE_*)."""
import collections, json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import pickle
from tools.omr.staged import adjudicate as A
import tools.omr.staged.adjudicators  # noqa
from tools.omr.staged.record import Log, Subject, Q, READERS

tag = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
pkl = {"brahms": "/private/tmp/claude-501/arc/brh.pkl", "litolff": "/private/tmp/claude-501/arc/lit.pkl"}[tag]
rows = json.load(open(HERE / f"out/arc_ink_{tag}.json"))["rows"]
d = pickle.load(open(pkl, "rb"))
spec = A.REGISTRY["arc_is_not_an_arc"]
res = {}
for o in d["obs"]:
    if o["quantity"] != "arc_box":
        continue
    s = o["subject"]
    log = Log()
    sub = Subject.from_key(s)
    log.observe(sub, Q.ARC_BOX, o["value"], reader=o["reader"], frame=o["frame"], score=o["score"], **o["detail"])
    r = rows.get(s)
    if r:
        log.observe(sub, Q.ARC_INK_SHAPE, r["coverage"], reader=READERS.CV_ARC_INK, frame=o["frame"], tall_cols=r["tall_cols"],
                    lines_in_box=r["lines_in_box"], width_spaces=r["width_spaces"], height_spaces=r["height_spaces"])
    v = A.adjudicate_one(log, spec, sub)
    res[s] = (v.reason, v.value)
c = collections.Counter(r for r, _ in res.values())
print(tag, len(res), dict(c))
rnd = random.Random(20261007)
refused = sorted(s for s, (r, _) in res.items() if r.startswith("ink_is"))
kept = sorted(s for s, (r, _) in res.items() if r == "arc")
out = dict(counts=dict(c), arcs=len(res), refused40=rnd.sample(refused, min(n, len(refused))), kept40=rnd.sample(kept, min(n, len(kept))),
           refused=refused)
json.dump(out, open(HERE / f"out/arc_line_counts_{tag}.json", "w"))
