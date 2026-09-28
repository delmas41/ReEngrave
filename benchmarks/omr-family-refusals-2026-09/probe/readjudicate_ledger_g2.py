"""GATHER ONCE, ADJUDICATE TWICE — the ledger arm of ROADMAP 3.4g-2.

    python3 .../readjudicate_ledger_g2.py <record.json> --out <dir>

BASE = the ledger decision exactly as 3.4g shipped it, loaded from
`origin/main`'s `family_precision.py` (`--base-ref`) and swapped into the ONE
registry entry it owns — the rest of the pipeline is today's tree in both
arms. ARM = the decision on this tree (Sean's two conventions, 2026-09-24).
Everything downstream (EVALUATE, INFER, EXPORT) runs in both, so a change in
`<note>`, the census or `glyph_owner` would show here.

⚠️ THE CONTROL COMES FIRST AND CAN FAIL. The BASE ledger tally must equal,
reason for reason, what 3.4g's own harness recorded for the same record
(`out/ledger-arm-<record>.json`, its `arm` block). If the swap loaded the
wrong function, or today's tree feeds the decision different rows, the two
disagree and this probe exits 3 before it reports an arm.

⚠️ BLIND TO GATHER, like every tool of its shape — fine here: this lane
files no new GATHER row, and `glyph_owner`'s ladder is GATHER's count
(ROADMAP 2.14), so `glyph_owner` is EXPECTED not to move and is reported.

⚠️ REACH BEFORE ACCURACY: population first, exit 2 DEAD AT ZERO.
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import json
import pathlib
import subprocess
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import adjudicate, evaluate, infer             # noqa: E402
from tools.omr.staged import adjudicators, consequences, inferences  # noqa: E402,F401
from tools.omr.staged import export as SX                            # noqa: E402
from tools.omr.staged.record import Q                                # noqa: E402
from tools.omr.staged.record_io import load_record                   # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "probe"))
from readjudicate_ledger import rebuild, verdicts_of                 # noqa: E402

LEDGER = "ledgerLine"
FP_PATH = "tools/omr/staged/adjudicators/family_precision.py"


def load_base_fn(ref: str):
    """3.4g's `adjudicate_ledger_is_not_a_ledger`, from `ref`, unregistered.

    ⚠️ `@decision` REGISTERS, and one quantity has one owner — so the old
    source is executed with `decision` replaced by an identity decorator for
    the duration of the exec, then restored. The function comes back bare;
    the caller swaps it into today's `DecisionSpec` (whose `reasons` are a
    superset of the old ones, so nothing the old body returns is undeclared).
    """
    src = subprocess.check_output(["git", "show", f"{ref}:{FP_PATH}"],
                                  cwd=ROOT, text=True)
    mod = types.ModuleType("tools.omr.staged.adjudicators._fp_base_34g")
    mod.__package__ = "tools.omr.staged.adjudicators"
    mod.__file__ = f"<{ref}:{FP_PATH}>"
    saved = adjudicate.decision
    adjudicate.decision = lambda **_kw: (lambda f: f)
    try:
        exec(compile(src, mod.__file__, "exec"), mod.__dict__)
    finally:
        adjudicate.decision = saved
    return mod.adjudicate_ledger_is_not_a_ledger


def run_once(rec: dict) -> dict:
    log = rebuild(rec)
    adjudicate.run(log)
    evaluated = evaluate.run(log)
    infer.run(log, evaluated)
    out = log.to_json()
    xml, report = SX.to_musicxml({"record": out})
    return {"record": out, "xml_notes": xml.count("<note"), "report": report}


def tally(vs: dict) -> dict:
    c = collections.Counter()
    for v in vs.values():
        if v["outcome"] != "decided":
            c[f"ABSTAINED:{v.get('reason')}"] += 1
        elif v["value"] is True:
            c[f"refused:{v.get('reason')}"] += 1
        else:
            c["kept"] += 1
    return dict(sorted(c.items()))


def transitions(base: dict, arm: dict) -> dict:
    """base reason -> arm reason, per box. Every box counted once."""
    def word(v):
        if v is None:
            return "<absent>"
        if v["outcome"] != "decided":
            return f"ABSTAINED:{v.get('reason')}"
        return f"refused:{v.get('reason')}" if v["value"] is True else "kept"
    c = collections.Counter()
    named = collections.defaultdict(list)
    for key in sorted(set(base) | set(arm)):
        b, a = word(base.get(key)), word(arm.get(key))
        c[f"{b} -> {a}"] += 1
        if b != a and len(named[f"{b} -> {a}"]) < 12:
            named[f"{b} -> {a}"].append(key)
    return {"counts": dict(sorted(c.items())), "named": dict(named)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out", required=True)
    ap.add_argument("--base-ref", default="origin/main")
    a = ap.parse_args()

    name = pathlib.Path(a.record).name
    stem = name.split(".")[0]
    rec = load_record(a.record)["record"]
    n_ledger = sum(1 for o in rec["observations"]
                   if o.get("quantity") == Q.GLYPH_BOX
                   and isinstance(o.get("value"), (list, tuple))
                   and len(o["value"]) == 5 and o["value"][0] == LEDGER)
    print(f"[{name}] POPULATION FIRST: {n_ledger} ledgerLine boxes",
          flush=True)
    if n_ledger == 0:
        print("DEAD AT ZERO — this record holds no ledger box to move.")
        return 2

    spec = adjudicate.REGISTRY[Q.LEDGER_IS_NOT_A_LEDGER]
    base_fn = load_base_fn(a.base_ref)

    print(f"[{name}] base (3.4g rule from {a.base_ref}) ...", flush=True)
    adjudicate.REGISTRY[Q.LEDGER_IS_NOT_A_LEDGER] = dataclasses.replace(
        spec, fn=base_fn)
    try:
        base = run_once(rec)
    finally:
        adjudicate.REGISTRY[Q.LEDGER_IS_NOT_A_LEDGER] = spec

    vb = verdicts_of(base["record"], Q.LEDGER_IS_NOT_A_LEDGER)
    t_base = tally(vb)
    prior_path = HERE / "out" / f"ledger-arm-{stem}.json"
    control = {"prior_file": str(prior_path.relative_to(ROOT))}
    if prior_path.exists():
        prior = json.loads(prior_path.read_text())["arm"]
        control["prior_3_4g_arm"] = prior
        control["base_here"] = t_base
        control["agrees"] = (prior == t_base)
        n_same = sum(min(prior.get(k, 0), t_base.get(k, 0))
                     for k in set(prior) | set(t_base))
        control["agreeing_boxes"] = f"{n_same} of {len(vb)}"
        print(f"[{name}] CONTROL base == 3.4g's recorded arm: "
              f"{control['agrees']} ({control['agreeing_boxes']})",
              flush=True)
        if not control["agrees"]:
            print(json.dumps(control, indent=1))
            print("CONTROL FAILED — the base is not 3.4g's rule on this "
                  "record; refusing to report an arm.")
            return 3
    else:
        control["agrees"] = None
        print(f"[{name}] no prior 3.4g arm on disk — control NOT RUN",
              flush=True)

    print(f"[{name}] arm  (3.4g-2 rule, this tree) ...", flush=True)
    arm = run_once(rec)
    va = verdicts_of(arm["record"], Q.LEDGER_IS_NOT_A_LEDGER)

    o_b = verdicts_of(base["record"], Q.GLYPH_OWNER)
    o_a = verdicts_of(arm["record"], Q.GLYPH_OWNER)
    moved = [k for k, b in o_b.items()
             if (o_a.get(k) or {}).get("value") != b.get("value")
             or (o_a.get(k) or {}).get("reason") != b.get("reason")]

    def ladder(out):
        found = collections.Counter()
        fired = 0
        for v in out["verdicts"]:
            if v["quantity"] != Q.NOTEHEAD_IS_NOT_A_NOTEHEAD:
                continue
            sig = (v.get("detail") or {}).get("unladdered_signal")
            if not sig:
                continue
            found[str(sig.get("ledger_found"))] += 1
            fired += bool(sig.get("would_fire"))
        return {"ledger_found_hist": dict(sorted(found.items())),
                "would_fire": fired}

    def census(rep):
        sc = rep.get("status_census") or {}
        return {"unaccounted": sc.get("unaccounted"),
                "balanced": sc.get("balanced")}

    out = {
        "record": name,
        "base_ref": a.base_ref,
        "ledger_boxes_on_the_record": n_ledger,
        "control": control,
        "base": t_base,
        "arm": tally(va),
        "transitions": transitions(vb, va),
        "glyph_owner_verdicts": {"base": len(o_b), "arm": len(o_a)},
        "glyph_owner_moved": len(moved),
        "glyph_owner_moved_named": moved[:40],
        "unladdered_signal_base": ladder(base["record"]),
        "unladdered_signal_arm": ladder(arm["record"]),
        "notes_base": base["xml_notes"],
        "notes_arm": arm["xml_notes"],
        "notes_not_written_identical": (
            base["report"].get("notes_not_written")
            == arm["report"].get("notes_not_written")),
        "census_base": census(base["report"]),
        "census_arm": census(arm["report"]),
        "family_refusals_ledger_arm":
            (arm["report"].get("family_refusals") or {}).get(
                Q.LEDGER_IS_NOT_A_LEDGER),
    }
    dest = pathlib.Path(a.out) / f"ledger-g2-arm-{stem}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: v for k, v in out.items()
                      if k not in ("glyph_owner_moved_named",)},
                     indent=1, default=str))
    print("wrote", dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
