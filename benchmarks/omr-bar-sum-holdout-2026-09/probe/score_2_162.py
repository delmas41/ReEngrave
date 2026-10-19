"""ROADMAP 2.162 -- Sean's judged tiles against each replay arm's mini record (`python3 -m tools.omr.staged.judged`'s own
`score`). The index is main's committed `benchmarks/acceptance/judged-tiles.json` PLUS the 2.153b Set F gallery, which
is answered on lane-2.153-retile and not yet on main (its answers.json + manifest.json read with `git show`).
Reports totals per arm and every tile whose status changes between the arm pairs.
usage: score_2_162.py OUTDIR OUT.json"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, ".")
from tools.omr.staged import judged as J  # noqa: E402

OUTDIR, OUT = sys.argv[1:3]
idx = json.loads(J.INDEX_PATH.read_text())
have = {r["item"] for r in idx["tiles"]}
with tempfile.TemporaryDirectory() as td:
    g = pathlib.Path(td) / "2.153b-review"
    g.mkdir()
    for f in ("answers.json", "manifest.json"):
        g.joinpath(f).write_text(subprocess.check_output(
            ["git", "show", "origin/lane-2.153-retile:out/print/2.153b-review/" + f], text=True))
    extra = J.item_rows(g / "answers.json", pathlib.Path(td))
assert "2.153b-review" not in have
idx = dict(idx, tiles=idx["tiles"] + extra)
res = {"n_tiles": len(idx["tiles"]), "set_f_rows": len(extra)}
PAIRS = (("base", "mine"), ("b153", "both"), ("base", "b153"))
for doc in ("litolff", "brahms"):
    reps = {}
    for arm in ("base", "mine", "b153", "both"):
        p = os.path.join(OUTDIR, "%s.%s.record.json" % (doc, arm))
        if os.path.exists(p):
            reps[arm] = J.score(idx, pathlib.Path(p), doc)
    res[doc] = {"totals": {a: {k: r["totals"].get(k, 0) for k in ("right", "wrong", "narrowed", "abstained", "not_found")}
                           for a, r in reps.items()}}
    for A, B in PAIRS:
        if A in reps and B in reps:
            sa = {(t["item"], t["tile"]): t for t in reps[A]["tiles"]}
            sb = {(t["item"], t["tile"]): t for t in reps[B]["tiles"]}
            moved = [dict(item=key[0], tile=key[1], subject=sa[key]["subject"], answer=sa[key]["answer"],
                          A=sa[key]["status"], B=sb[key]["status"], noteA=sa[key]["note"], noteB=sb[key]["note"])
                     for key in sa if key in sb and (sa[key]["status"], sa[key]["note"]) != (sb[key]["status"], sb[key]["note"])]
            res[doc]["%s->%s" % (A, B)] = moved
json.dump(res, open(OUT, "w"), indent=1, default=str)
for doc in ("litolff", "brahms"):
    print("==", doc, res[doc]["totals"])
    for pk in ("%s->%s" % p for p in PAIRS):
        for m in res[doc].get(pk, []):
            print("  ", pk, m["item"], m["tile"], m["subject"], "Sean", m["answer"], ":", m["A"], "->", m["B"], "|", m["noteB"])
