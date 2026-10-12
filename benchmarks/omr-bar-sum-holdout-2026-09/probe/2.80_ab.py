"""2.80 base vs arm on ONE tree, from ONE saved gather record.

    python3 benchmarks/omr-bar-sum-holdout-2026-09/probe/2.80_ab.py REC.json OUTDIR

`REC.json` is a `python3 -m tools.omr.staged ... --through adjudicate --out`
record gathered on a tree that has `Q.CELL_INK_PIECES` (this lane's GATHER
reader). Both arms re-run ADJUDICATE..INFER from the SAME gather rows
(`review.rerun.rebuild_gather`) and export. The ONLY difference is
`consequences._missed_rest_witness`: the BASE arm answers "clear" for every
bar (the rule as it was), the ARM answers from the ink.

Prints (and writes OUTDIR/ab.json): per arm, the `reconcile_duration`
landings split into LENGTHENED / SHORTENED / NARROWED-chosen; the arm's
refusals by witness answer; bars written / held out; and the MusicXML bars
that differ.
"""
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, ".")
from tools.omr.staged import consequences, export as EXPORT  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged.review import rerun  # noqa: E402

rec_path, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
doc = load_record(rec_path)
rec = doc["record"] if "record" in doc else doc

real = consequences._missed_rest_witness


def run(arm):
    calls = []

    def witness(log, subject):
        ans, left = real(log, subject)
        calls.append({"cell": subject.at(consequences.Kind.CELL).to_key(),
                      "answer": ans, "unexplained_pieces": left})
        return ((consequences.WITNESS_CLEAR, 0) if arm == "base"
                else (ans, left))

    consequences._missed_rest_witness = witness
    try:
        log, _ = rerun.rebuild_gather(rec)
        rerun.run_stages(log)
        result = {"record": log.to_json(), "summary": log.summary()}
        xml, report = EXPORT.to_musicxml(result)
    finally:
        consequences._missed_rest_witness = real
    vs = result["record"]["verdicts"]
    byid = {v["id"]: v for v in vs}
    land = collections.Counter()
    rows = []
    for v in vs:
        if v.get("decider") != "reconcile_duration":
            continue
        old = byid.get(v.get("supersedes"))
        ob = "narrowed" if old and old["outcome"] != "decided" else (
            old["value"].get("beats") if old else None)
        nb = v["value"].get("beats")
        kind = ("narrowed" if ob == "narrowed" else
                "lengthen" if nb > ob else "shorten")
        land[kind] += 1
        rows.append({"subject": v["subject"], "old": ob, "new": nb,
                     "kind": kind})
    (out / f"{arm}.musicxml").write_text(xml)
    return {"landings": dict(land), "rows": rows, "calls": calls,
            "report": {k: report.get(k) for k in (
                "bars_held_out_sum", "bars_add_up_control",
                "measure_rests_read", "notes_not_written_total")}}


res = {a: run(a) for a in ("base", "arm")}
b, a = res["base"], res["arm"]
print("landings   base", b["landings"], " arm", a["landings"])
ans = collections.Counter(c["answer"] for c in a["calls"])
print("witness asked", len(a["calls"]), dict(ans))
print("report base", b["report"])
print("report arm ", a["report"])
base_keys = {r["subject"] for r in b["rows"]}
arm_keys = {r["subject"] for r in a["rows"]}
lost = sorted(base_keys - arm_keys)
print("landings the arm no longer makes:", len(lost))
for r in b["rows"]:
    if r["subject"] in lost:
        print("   ", r)


def bars(xml):
    d = {}
    for pm in re.finditer(r'<part id="([^"]+)">(.*?)</part>', xml, re.S):
        for mm in re.finditer(r'<measure number="([^"]+)"[^>]*>(.*?)</measure>',
                              pm.group(2), re.S):
            d[(pm.group(1), mm.group(1))] = mm.group(2)
    return d


bb = bars((out / "base.musicxml").read_text())
ba = bars((out / "arm.musicxml").read_text())
changed = sorted(k for k in set(bb) | set(ba) if bb.get(k) != ba.get(k))
print("MusicXML bars changed:", len(changed), changed[:40])
res["changed_bars"] = [list(k) for k in changed]
res["landings_lost"] = lost
(out / "ab.json").write_text(json.dumps(res, indent=1, default=str))
