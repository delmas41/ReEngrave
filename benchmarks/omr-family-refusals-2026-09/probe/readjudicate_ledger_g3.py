"""GATHER ONCE, ADJUDICATE TWICE — Part A of ROADMAP 3.4g-3.

    python3 .../readjudicate_ledger_g3.py <record.json> --out <dir>

BASE = the ledger decision exactly as 3.4g-2 shipped it, loaded from
`--base-ref` (default `8226aa93`, the tree this lane branched from) and
swapped into today's registry entry; ARM = this tree. Everything downstream
runs in both.

⚠️ THE CONTROL COMES FIRST AND CAN FAIL: the BASE ledger tally must equal,
reason for reason, 3.4g-2's own recorded ARM on the same record
(`out/ledger-g2-arm-<record>.json`), or this exits 3 before reporting.

⚠️ BLIND TO GATHER. The shared records carry no `Q.LEDGER_INK_UNDER` row, so
on them the ARM is exactly Part A: every `no_head_on_the_rung` refusal
should become an ABSTENTION (`rung_without_boxed_head`) and NOTHING ELSE
should move. "Nothing else" is measured, not asserted: every verdict of
every quantity is compared (outcome, value, reason) and each mover named.

⚠️ REACH BEFORE ACCURACY: population first, exit 2 DEAD AT ZERO.
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "probe"))

from tools.omr.staged import adjudicate                                # noqa: E402
from tools.omr.staged.record import Q                                  # noqa: E402
from tools.omr.staged.record_io import load_record                     # noqa: E402
from readjudicate_ledger import verdicts_of                            # noqa: E402
from readjudicate_ledger_g2 import (LEDGER, load_base_fn, run_once,    # noqa: E402
                                    tally, transitions)


def every_verdict(out: dict) -> dict:
    return {(v["quantity"], v["subject"]): v for v in out["verdicts"]}


def word(v):
    if v is None:
        return None
    return (v["outcome"], json.dumps(v.get("value"), sort_keys=True,
                                     default=str), v.get("reason"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out", required=True)
    ap.add_argument("--base-ref", default="8226aa93")
    a = ap.parse_args()

    name = pathlib.Path(a.record).name
    stem = name.split(".")[0]
    rec = load_record(a.record)["record"]
    n_ledger = sum(1 for o in rec["observations"]
                   if o.get("quantity") == Q.GLYPH_BOX
                   and isinstance(o.get("value"), (list, tuple))
                   and len(o["value"]) == 5 and o["value"][0] == LEDGER)
    n_ink = sum(1 for o in rec["observations"]
                if o.get("quantity") == Q.LEDGER_INK_UNDER)
    print(f"[{name}] POPULATION FIRST: {n_ledger} ledgerLine boxes, "
          f"{n_ink} Q.LEDGER_INK_UNDER rows", flush=True)
    if n_ledger == 0:
        print("DEAD AT ZERO — this record holds no ledger box to move.")
        return 2

    spec = adjudicate.REGISTRY[Q.LEDGER_IS_NOT_A_LEDGER]
    base_fn = load_base_fn(a.base_ref)
    print(f"[{name}] base (3.4g-2 rule from {a.base_ref}) ...", flush=True)
    adjudicate.REGISTRY[Q.LEDGER_IS_NOT_A_LEDGER] = dataclasses.replace(
        spec, fn=base_fn)
    try:
        base = run_once(rec)
    finally:
        adjudicate.REGISTRY[Q.LEDGER_IS_NOT_A_LEDGER] = spec
    vb = verdicts_of(base["record"], Q.LEDGER_IS_NOT_A_LEDGER)
    t_base = tally(vb)

    prior_path = HERE / "out" / f"ledger-g2-arm-{stem}.json"
    control = {"prior_file": str(prior_path.relative_to(ROOT))}
    if prior_path.exists():
        prior = json.loads(prior_path.read_text())["arm"]
        control.update(prior_3_4g2_arm=prior, base_here=t_base,
                       agrees=(prior == t_base))
        n_same = sum(min(prior.get(k, 0), t_base.get(k, 0))
                     for k in set(prior) | set(t_base))
        control["agreeing_boxes"] = f"{n_same} of {len(vb)}"
        print(f"[{name}] CONTROL base == 3.4g-2's recorded arm: "
              f"{control['agrees']} ({control['agreeing_boxes']})",
              flush=True)
        if not control["agrees"]:
            print(json.dumps(control, indent=1))
            print("CONTROL FAILED — refusing to report an arm.")
            return 3
    else:
        control["agrees"] = None
        print(f"[{name}] no 3.4g-2 arm on disk — control NOT RUN", flush=True)

    print(f"[{name}] arm  (3.4g-3, this tree) ...", flush=True)
    arm = run_once(rec)
    va = verdicts_of(arm["record"], Q.LEDGER_IS_NOT_A_LEDGER)

    eb, ea = every_verdict(base["record"]), every_verdict(arm["record"])
    moved = collections.Counter()
    moved_named = collections.defaultdict(list)
    for key in sorted(set(eb) | set(ea)):
        if word(eb.get(key)) != word(ea.get(key)):
            moved[key[0]] += 1
            if len(moved_named[key[0]]) < 8:
                moved_named[key[0]].append(
                    {"subject": key[1], "base": word(eb.get(key)),
                     "arm": word(ea.get(key))})

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

    fam = (arm["report"].get("family_refusals") or {}).get(
        Q.LEDGER_IS_NOT_A_LEDGER)
    sc = arm["report"].get("status_census") or {}
    out = {
        "record": name, "base_ref": a.base_ref,
        "ledger_boxes_on_the_record": n_ledger,
        "ledger_ink_rows_on_the_record": n_ink,
        "control": control,
        "base": t_base, "arm": tally(va),
        "transitions": transitions(vb, va),
        "verdicts_moved_by_quantity": dict(sorted(moved.items())),
        "verdicts_moved_named": dict(moved_named),
        "unladdered_signal_base": ladder(base["record"]),
        "unladdered_signal_arm": ladder(arm["record"]),
        "notes_base": base["xml_notes"], "notes_arm": arm["xml_notes"],
        "notes_not_written_identical": (
            base["report"].get("notes_not_written")
            == arm["report"].get("notes_not_written")),
        "census_arm": {"unaccounted": sc.get("unaccounted"),
                       "balanced": sc.get("balanced")},
        "family_refusals_ledger_arm": fam,
    }
    dest = pathlib.Path(a.out) / f"ledger-g3-arm-{stem}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: v for k, v in out.items()
                      if k not in ("verdicts_moved_named",)},
                     indent=1, default=str))
    print("wrote", dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
