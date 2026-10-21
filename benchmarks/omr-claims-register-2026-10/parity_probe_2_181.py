"""2.181 parity probe (GATHER only, no ADJUDICATE): run the real `gather_claimed_register` on the record's pages that hold the
old rules' refusals, and say for each refused glyph which claims hold it and what they say (owner, standing, share, line test).
usage: parity_probe_2_181.py DOC SLICEDIR OLD_REFUSALS.json OUT.json"""
import collections
import json
import os
import sys

sys.path.insert(0, ".")
sys.argv, ARGS = sys.argv[:1] + [sys.argv[1], sys.argv[2], "scratch/probe_out", "none"], sys.argv
DOC, SD, OLD, OUT = ARGS[1], ARGS[2], ARGS[3], ARGS[4]
os.environ["OMR_CLAIMED_REGISTER"] = "1"
from tools.omr.staged import claims as CL  # noqa: E402
from tools.omr.staged.record import Log, Q  # noqa: E402

old = json.load(open(OLD))
pages = sorted({int(g.split("/")[1]) for g in old})
import importlib.util  # noqa: E402
spec = importlib.util.spec_from_file_location("rp", os.path.join(os.path.dirname(__file__), "replay_2_181.py"))
src = open(spec.origin).read().split("t0 = time.time()")[0]
ns = {"__name__": "rp", "__file__": spec.origin}
exec(compile(src, spec.origin, "exec"), ns)
rows_obs = []
for pg in pages:
    rows_obs += [json.loads(line) for line in open(os.path.join(SD, DOC, "p%02d.observations.jsonl" % pg))]
by_page = collections.defaultdict(list)
for o in rows_obs:
    if o["quantity"] in ("staff_lines", "cell_box", "glyph_box"):
        by_page[int(o["subject"].split("/")[1])].append(o)
log = Log()
# the located clefs the register reads, re-filed as they stand on the record
for o in rows_obs:
    if o["quantity"] == "clef_located":
        p = o["subject"].split("/")
        from tools.omr.staged import record as R
        log.observe(R.staff(int(p[1]), int(p[2]), int(p[3])), Q.CLEF_LOCATED, o["value"], reader=o["reader"], frame=o["frame"],
                    score=o.get("score"), **(o.get("detail") or {}))
_rast = {}


def binary_of(pg):
    if pg not in _rast:
        _rast.clear()
        _rast[pg] = ns["render_page"](ns["PDFS"][DOC], pg, dpi=600).binary
    return _rast[pg]


import tools.omr.staged.gather as G  # noqa: E402
_orig = G.gather_meter_object
G.gather_meter_object = lambda *a, **k: None                       # register only
ns["inject"](log, by_page, binary_of, True)
G.gather_meter_object = _orig
claim_rows = [r for r in log.all_rows() if getattr(r, "quantity", None) == Q.CLAIMED_AREA and getattr(r, "value", None) is not None]
out, tally = {}, collections.Counter()
for g, v in old.items():
    held = CL.covering(claim_rows, g)
    desc = [dict(owner=r.detail["owner"], standing=r.detail["standing"], source=r.detail.get("source"), right_edge=r.detail.get("right_edge"),
                 share=e.get("ink_share_inside"), named=e.get("named"), through=(e.get("through") or {}).get("through")) for r, e in held]
    out[g] = dict(old=v[1], held=desc)
    if not desc:
        tally[(v[1], "NOT HELD")] += 1
    else:
        best = "refuse?" if any(d["named"] or (d["owner"] == "clef" and d["standing"] == "READ") or
                                (d["owner"] == "leading_column" and d["through"]) for d in desc) else "narrow"
        tally[(v[1], best)] += 1
json.dump(out, open(OUT, "w"), indent=0, default=str)
for k, n in sorted(tally.items()):
    print(k, n)
print("claims filed", collections.Counter((r.detail["owner"], r.detail["standing"], r.detail.get("right_edge")) for r in claim_rows))
