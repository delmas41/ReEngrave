"""ROADMAP 2.157 -- the replay harness on a SLICE: the OLD `rebuild_gather` (renumbers rows, remaps only `basis`; copied
below verbatim from origin/main d9353217) against the FIXED one (`review.rerun.rebuild_gather`, every row id in `detail` /
`value` / `basis` re-pointed, an unresolvable one RAISES), and, when importable, against 2.153's probe harness
(`replay_util_2_153.rebuild`). STAGED ADJUDICATE..INFER through `pipeline.decide`; no page gather, records on disk only.

Prints, per harness: glyphs whose FIRST `adjudicate_duration` verdict differs from the record's own stored one (the control:
at the record's own commit a faithful replay differs on 0), and Sean's judged tiles of DOC scored live (right / wrong /
narrowed holding / not / missing), and the tiles where OLD and FIXED disagree (the false regressions). Also asserts FIXED
and the 2.153 probe build identical verdict lists (no real difference lost or added).
usage: harness_2_157.py SLICE.json DOC NOTES.json OUT.json
"""
import json
import sys

sys.path.insert(0, ".")
from tools.omr.staged.record import Log, Subject  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

SL, DOC, NOTES, OUT = sys.argv[1:5]
EPS = 1e-6


def old_rebuild_gather(rec):
    """origin/main d9353217 `rebuild_gather`, verbatim apart from the name."""
    log = Log()
    rows = [(r, "obs") for r in rec.get("observations") or ()]
    rows += [(r, "abs") for r in rec.get("abstentions") or ()]
    rows.sort(key=lambda t: RR._row_no(t[0]["id"]))
    id_map = {}
    for r, kind in rows:
        sub = Subject.from_key(r["subject"])
        detail = dict(r.get("detail") or {})
        if kind == "obs":
            basis = tuple(id_map[b] for b in (r.get("basis") or ()) if b in id_map)
            new = log.observe(sub, r["quantity"], r["value"], reader=r["reader"], frame=r["frame"],
                              score=r.get("score"), derived_from=basis, **detail)
        else:
            new = log.abstain(sub, r["quantity"], reader=r["reader"], frame=r["frame"], reason=r["reason"], **detail)
        id_map[r["id"]] = new.id
    return log, id_map


def live(chain):
    sup = {v.get("supersedes") for v in chain if v.get("supersedes")}
    lv = [v for v in chain if v["id"] not in sup]
    return (lv or chain)[-1]


def durations(verdicts):
    by = {}
    for v in verdicts:
        if v["quantity"] == "duration":
            by.setdefault(v["subject"], []).append(v)
    return by


def first_key(chain):
    a = next((v for v in chain if v.get("decider") == "adjudicate_duration"), None)
    if a is None:
        return None
    return (a["outcome"], a.get("reason"), json.dumps(a["value"], sort_keys=True, default=str))


def score(chain, beats):
    if not chain:
        return "missing"
    L = live(chain)
    val = L["value"] if isinstance(L["value"], dict) else {}
    if L["outcome"] == "decided":
        w = val.get("written")
        return "right" if (w is not None and not val.get("is_rest") and abs(w - beats) < EPS) else "wrong"
    if L["outcome"] == "narrowed":
        c = [x.get("value", {}).get("written") for x in (L.get("candidates") or [])]
        return "narrowed_holding" if any(x is not None and abs(x - beats) < EPS for x in c) else "narrowed_not"
    return L["outcome"]


rec = json.load(open(SL))
tiles = json.load(open(NOTES))[DOC]
stored = durations(rec["verdicts"])
harnesses = [("old", old_rebuild_gather), ("fixed", RR.rebuild_gather)]
try:
    sys.path.insert(0, "benchmarks/omr-bar-sum-holdout-2026-09/probe")
    import replay_util_2_153 as RU  # noqa: E402
    harnesses.append(("probe_2_153", RU.rebuild))
except ImportError:
    pass
res = {"doc": DOC, "slice": SL, "glyphs_stored": len(stored), "harness": {}}
full = {}
for name, fn in harnesses:
    log, _ = fn(rec)
    RR.run_stages(log)
    vs = log.to_json()["verdicts"]
    del log
    if name != "old":
        full[name] = json.dumps(vs, sort_keys=True, default=str)
    new = durations(vs)
    differ = [g for g, ch in stored.items() if first_key(ch) is not None and g in new
              and first_key(new[g]) is not None and first_key(ch) != first_key(new[g])]
    t = {x["glyph"]: score(new.get(x["glyph"]), x["beats"]) for x in tiles}
    s = {x["glyph"]: score(stored.get(x["glyph"]), x["beats"]) for x in tiles}
    res["harness"][name] = {"first_duration_differs_from_stored": len(differ), "differ_examples": differ[:10],
                            "tiles": t}
    res["stored_tiles"] = s
    print(name, "first adjudicate_duration differs from stored on", len(differ), "of", len(stored), flush=True)
if len(full) == 2:
    res["fixed_equals_probe_2_153"] = full["fixed"] == full["probe_2_153"]
    print("fixed verdicts == 2.153 probe verdicts:", res["fixed_equals_probe_2_153"])
o, f = res["harness"]["old"]["tiles"], res["harness"]["fixed"]["tiles"]
st = res["stored_tiles"]
GOOD = ("right", "narrowed_holding")
res["old_vs_fixed"] = [(g, st[g], o[g], f[g]) for g in o if o[g] != f[g]]
res["false_regressions"] = [r for r in res["old_vs_fixed"] if r[3] in GOOD and r[2] not in GOOD]
print("tiles", len(tiles), "| old != fixed on", len(res["old_vs_fixed"]), "| fixed good, old not:",
      len(res["false_regressions"]))
for r in res["old_vs_fixed"]:
    print("   ", r)
json.dump(res, open(OUT, "w"), indent=1, default=str)
