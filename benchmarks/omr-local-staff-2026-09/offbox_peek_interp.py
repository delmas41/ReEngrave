"""lane-offbox-check: why does a reader answer whose named line is INTERPOLATED almost never pass? Prints examples:
the staff edge, the measured rungs (in spaces from the edge), the answer, the box (spaces from the edge)."""
import json, sys, random
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import offbox_check as C

res = json.loads(Path("/private/tmp/claude-501/ex/offbox.json").read_text())
doc = sys.argv[1]
M = json.loads(Path(f"/private/tmp/claude-501/ex/m_RUN2_{doc}.json").read_text())["heads"]
H = res[doc]["heads"]["RUN2"]
rng = random.Random(1)
ex = []
for s, g in sorted(H.items()):
    m = M.get(s)
    if g["dec"] is None or not m or not m.get("repro"):
        continue
    r = C.Rows(g["lines"], m["rungs"])
    if "interpolated" in C.named_kinds(g["dec"], r):
        ex.append((s, g, m, r))
print(len(ex))
for s, g, m, r in rng.sample(ex, 12):
    side = -1 if g["dec"] < 0 else 1
    edge = r.top if side < 0 else r.bot
    sp = r.sp
    rungs = sorted(side * (y - edge) / sp for y in m["rungs"])
    b = g["box"]
    bn = sorted(side * (y - edge) / sp for y in (b[1], b[3]))
    print(s, "ans", g["dec"], "geo", g["geo"], "rungs(sp from edge)", [round(x, 2) for x in rungs],
          "box(sp from edge)", [round(x, 2) for x in bn], "box_src", g["box_source"])
