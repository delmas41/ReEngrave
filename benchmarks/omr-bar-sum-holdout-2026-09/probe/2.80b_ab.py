"""2.80b base vs arm on ONE tree, from ONE saved gather record.

    python3 .../2.80b_ab.py REC.json OUTDIR

REC.json is a `--through gather` record from a tree with `Q.NARROW_BOX_SHAPE`.
Both arms re-run ADJUDICATE..INFER from the SAME gather rows. The ONLY
difference: the OFF arm makes `adjudicate_narrow_box_is_an_eighth_rest`
abstain on everything (the tree as it was before 2.80b), the ON arm lets it
decide. Prints REACH first (how many `too_narrow` refusals, how many become
rests), then the bars that changed, and writes OUTDIR/ab2.json.
"""
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, ".")
from tools.omr.staged import adjudicate, export as EXPORT  # noqa: E402
from tools.omr.staged import record as R  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged.review import rerun  # noqa: E402
from tools.omr.staged.adjudicators import narrow_rest  # noqa: E402

rec_path, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
doc = load_record(rec_path)
rec = doc["record"] if "record" in doc else doc
adjudicate._ensure_decisions()
spec = adjudicate.REGISTRY["adjudicate_narrow_box_is_an_eighth_rest"] \
    if "adjudicate_narrow_box_is_an_eighth_rest" in adjudicate.REGISTRY \
    else [s for s in adjudicate.REGISTRY.values()
          if s.quantity == Q.NOTEHEAD_IS_AN_EIGHTH_REST][0]
real_fn = spec.fn


def run(arm):
    log, _ = rerun.rebuild_gather(rec)
    if arm == "off":
        # the tree as it was before 2.80b: the decision abstains on everything
        object.__setattr__(spec, "fn", lambda ev: adjudicate.Ruling.abstain(
            "not_refused_as_too_narrow"))
    try:
        rerun.run_stages(log)
    finally:
        object.__setattr__(spec, "fn", real_fn)
    result = {"record": log.to_json(), "summary": log.summary()}
    xml, report = EXPORT.to_musicxml(result)
    (out / f"{arm}.musicxml").write_text(xml)
    vs = result["record"]["verdicts"]
    reasons = collections.Counter()
    reinstated = []
    for v in vs:
        if v["quantity"] == Q.NOTEHEAD_IS_AN_EIGHTH_REST:
            reasons[(v["outcome"], v["value"], v["reason"])] += 1
            if v["outcome"] == "decided" and v["value"] is True:
                reinstated.append(v["subject"])
    narrow_refusals = [v["subject"] for v in vs
                       if v["quantity"] == Q.NOTEHEAD_IS_NOT_A_NOTEHEAD
                       and v["outcome"] == "decided" and v["value"] is True
                       and v["reason"] == "too_narrow"]
    landings = collections.Counter(
        v["value"].get("beats") is not None and "landing"
        for v in vs if v.get("decider") == "reconcile_duration")
    return {"reasons": {str(k): n for k, n in reasons.items()},
            "reinstated": reinstated, "too_narrow_refusals": len(narrow_refusals),
            "reconcile_landings": sum(landings.values()),
            "held": (report.get("bars_held_out_sum") or {}).get("bars"),
            "of": (report.get("bars_held_out_sum") or {}).get("of_bars_with_events"),
            "notes_not_written_total": report.get("notes_not_written_total"),
            "rests_in_file": report.get("rests"),
            "balanced": report.get("balanced")}


res = {a: run(a) for a in ("off", "on")}
print("REACH too_narrow refusals:", res["on"]["too_narrow_refusals"])
print("REACH narrow-box decisions (on):", res["on"]["reasons"])
print("reinstated as eighth rests:", len(res["on"]["reinstated"]),
      res["on"]["reinstated"])
for a in ("off", "on"):
    r = res[a]
    print(a, {k: r[k] for k in ("held", "of", "reconcile_landings",
                                 "notes_not_written_total", "balanced")})


def bars(xml):
    d = {}
    for pm in re.finditer(r'<part id="([^"]+)">(.*?)</part>', xml, re.S):
        for mm in re.finditer(r'<measure number="([^"]+)"[^>]*>(.*?)</measure>',
                              pm.group(2), re.S):
            d[(pm.group(1), mm.group(1))] = mm.group(2)
    return d


b0 = bars((out / "off.musicxml").read_text())
b1 = bars((out / "on.musicxml").read_text())
changed = sorted(k for k in set(b0) | set(b1) if b0.get(k) != b1.get(k))
print("MusicXML bars changed:", len(changed), changed)
for k in changed:
    for tag, b in (("off", b0), ("on ", b1)):
        evs = re.findall(r"<note>(.*?)</note>", b.get(k, ""), re.S)
        kinds = ["R%s" % re.search(r"<duration>(\d+)", e).group(1) if "<rest" in e
                 else "n%s" % re.search(r"<duration>(\d+)", e).group(1)
                 for e in evs if "<chord/>" not in e]
        print("   ", k, tag, kinds)
res["changed_bars"] = [list(k) for k in changed]
(out / "ab2.json").write_text(json.dumps(res, indent=1, default=str))
