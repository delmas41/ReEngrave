"""GATHER ONCE, ADJUDICATE TWICE — the ledger arm of ROADMAP 3.4g.

    python3 .../readjudicate_ledger.py <record.json> --out <dir>

⚠️ BASE AND ARM ON ONE TREE, IN ONE PROCESS. The committed verdicts of the
shared records no longer reproduce on today's tree (CLAUDE.md §6b), so the
record's own `glyph_owner` rows are an INPUT and not a baseline. The BASE is
this same rebuild with the ledger GEOMETRY disabled — `_line_gap_spaces` made
unreachable and the height floor put out of range, which returns the decision
to what it did before it existed (the human rules stay, and are inert on a
record with no human rows). The ARM is the shipped decision.

⚠️ BLIND TO GATHER, like every tool of its shape. It re-adjudicates ONE saved
record, so a change to what GATHER files is invisible to it — which is fine
here, because this lane files no new GATHER row.

⚠️ THE ARM PRINTS ITS POPULATION FIRST AND EXITS NON-ZERO DECLARING ITSELF
DEAD AT ZERO (CLAUDE.md §6b, reach before accuracy): a change that moves
nothing because it is inert and one that moves nothing because the page holds
nothing to move are the same number otherwise.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from tools.omr.staged import adjudicate, evaluate, infer             # noqa: E402
from tools.omr.staged import adjudicators, consequences, inferences  # noqa: E402,F401
from tools.omr.staged import export as SX                            # noqa: E402
from tools.omr.staged.adjudicators import family_precision as FP     # noqa: E402
from tools.omr.staged.record import Log, Q, Subject                  # noqa: E402
from tools.omr.staged.record_io import load_record                   # noqa: E402

LEDGER = "ledgerLine"


def rebuild(rec: dict) -> Log:
    log = Log()
    rows = [(r, "obs") for r in rec["observations"]]
    rows += [(r, "abs") for r in rec.get("abstentions", [])]
    rows.sort(key=lambda t: t[0]["id"])
    for r, kind in rows:
        sub = Subject.from_key(r["subject"])
        detail = dict(r.get("detail") or {})
        if kind == "obs":
            log.observe(sub, r["quantity"], r["value"], reader=r["reader"],
                        frame=r["frame"], score=r.get("score"), **detail)
        else:
            log.abstain(sub, r["quantity"], reader=r["reader"],
                        frame=r["frame"], reason=r["reason"], **detail)
    return log


def run_once(rec: dict, *, geometry: bool) -> dict:
    """One full ADJUDICATE -> EVALUATE -> INFER -> EXPORT pass."""
    if geometry:
        FP.ON_A_STAFF_LINE_TOL_SPACES = _TOL
        FP.TALL_MIN_HEIGHT_SPACES = _TALL
    else:
        # ⚠️ RETURNED TO NOTHING, not deleted: a negative tolerance can never
        # be met and an out-of-range floor can never be exceeded, so the
        # decision falls through to `ledger_line` exactly as it would have
        # before either rule existed. The human rules are untouched and are
        # inert on a record holding no human row.
        FP.ON_A_STAFF_LINE_TOL_SPACES = -1.0
        FP.TALL_MIN_HEIGHT_SPACES = float("inf")
    log = rebuild(rec)
    adjudicate.run(log)
    evaluated = evaluate.run(log)
    infer.run(log, evaluated)
    out = log.to_json()
    xml, report = SX.to_musicxml({"record": out})
    return {"record": out, "xml_notes": xml.count("<note"), "report": report}


_TOL = FP.ON_A_STAFF_LINE_TOL_SPACES
_TALL = FP.TALL_MIN_HEIGHT_SPACES


def verdicts_of(out: dict, quantity: str) -> dict:
    return {v["subject"]: v for v in out["verdicts"]
            if v["quantity"] == quantity}


def summarise(name: str, base: dict, arm: dict, rec: dict) -> dict:
    ledger_boxes = [o["subject"] for o in rec["observations"]
                    if o.get("quantity") == Q.GLYPH_BOX
                    and isinstance(o.get("value"), (list, tuple))
                    and len(o["value"]) == 5 and o["value"][0] == LEDGER]

    v_arm = verdicts_of(arm["record"], Q.LEDGER_IS_NOT_A_LEDGER)
    v_base = verdicts_of(base["record"], Q.LEDGER_IS_NOT_A_LEDGER)

    def tally(vs):
        c = collections.Counter()
        for v in vs.values():
            if v["outcome"] != "decided":
                c[f"ABSTAINED:{v.get('reason')}"] += 1
            elif v["value"] is True:
                c[f"refused:{v.get('reason')}"] += 1
            else:
                c["kept"] += 1
        return dict(c)

    # ── glyph_owner: which verdicts MOVED, named ────────────────────────────
    o_arm = verdicts_of(arm["record"], Q.GLYPH_OWNER)
    o_base = verdicts_of(base["record"], Q.GLYPH_OWNER)
    moved = []
    for key, b in o_base.items():
        a = o_arm.get(key)
        if a is None:
            moved.append({"subject": key, "base": b.get("value"),
                          "arm": "<absent>", "base_reason": b.get("reason")})
        elif (a.get("value") != b.get("value")
              or a.get("reason") != b.get("reason")):
            moved.append({"subject": key,
                          "base": b.get("value"), "arm": a.get("value"),
                          "base_reason": b.get("reason"),
                          "arm_reason": a.get("reason")})

    # ── the ADJUDICATE ladder term, which the refusal DOES reach ────────────
    def ladder(out):
        found = collections.Counter()
        fired = 0
        for v in out["verdicts"]:
            if v["quantity"] != Q.NOTEHEAD_IS_NOT_A_NOTEHEAD:
                continue
            sig = (v.get("detail") or {}).get("unladdered_signal")
            if not sig:
                continue
            found[sig.get("ledger_found")] += 1
            fired += bool(sig.get("would_fire"))
        return {"ledger_found_hist": {str(k): v for k, v in
                                      sorted(found.items(),
                                             key=lambda t: (t[0] is None,
                                                            t[0]))},
                "would_fire": fired, "signals": sum(found.values())}

    return {
        "record": name,
        "ledger_boxes_on_the_record": len(ledger_boxes),
        "ledger_verdicts_arm": len(v_arm),
        "ledger_verdicts_base": len(v_base),
        "arm": tally(v_arm),
        "base": tally(v_base),
        "glyph_owner_verdicts": {"base": len(o_base), "arm": len(o_arm)},
        "glyph_owner_moved": len(moved),
        "glyph_owner_moved_named": moved[:40],
        "unladdered_signal_base": ladder(base["record"]),
        "unladdered_signal_arm": ladder(arm["record"]),
        "notes_base": base["xml_notes"],
        "notes_arm": arm["xml_notes"],
        "notes_not_written_base": base["report"].get("notes_not_written"),
        "notes_not_written_arm": arm["report"].get("notes_not_written"),
        "family_refusals_arm": arm["report"].get("family_refusals"),
        "status_census_arm_unaccounted":
            (arm["report"].get("status_census") or {}).get("unaccounted"),
        "status_census_arm_balanced":
            (arm["report"].get("status_census") or {}).get("balanced"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    name = pathlib.Path(a.record).name
    rec = load_record(a.record)["record"]

    n_ledger = sum(1 for o in rec["observations"]
                   if o.get("quantity") == Q.GLYPH_BOX
                   and isinstance(o.get("value"), (list, tuple))
                   and len(o["value"]) == 5 and o["value"][0] == LEDGER)
    print(f"[{name}] POPULATION FIRST: {n_ledger} ledgerLine boxes")
    if n_ledger == 0:
        print("DEAD AT ZERO — this record holds no ledger box to move.")
        return 2

    print(f"[{name}] base (geometry off) ...", flush=True)
    base = run_once(rec, geometry=False)
    print(f"[{name}] arm  (geometry on)  ...", flush=True)
    arm = run_once(rec, geometry=True)

    out = summarise(name, base, arm, rec)
    dest = pathlib.Path(a.out) / f"ledger-arm-{name.split('.')[0]}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: v for k, v in out.items()
                      if k != "glyph_owner_moved_named"}, indent=1,
                     default=str))
    print("wrote", dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
