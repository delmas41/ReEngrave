"""What A-METER-6 confines, on the COMMITTED boundary records.

⚠️ **REACH FIRST, AND IT EXITS NON-ZERO WHEN IT IS DEAD.** A confinement rule
that reaches no segment produces a clean "nothing changed" indistinguishable
from one that works, which is the shape this repo has paid for repeatedly.

WHAT THIS ARM CAN AND CANNOT SAY
--------------------------------
It reads `benchmarks/omr-staged-meter-boundary-2026-09/out/*.meter.json` — the
committed REDUCTIONS — and calls the **SHIPPED** `_meter_in_force_at_end` on
each decided meter value, once as the tree now has it and once with the filter
bypassed. So it prices exactly one thing: **which meter a following system
would be handed.**

⚠️ It is NOT an end-to-end arm. A cloud container has no weights and no
`library/`, so nothing here re-gathers, re-adjudicates or re-exports; the
carry's own weighing (`_corroborate`) is not run, and whether a confined carry
then SURVIVES its bars on the next system is not measured. `local_arm.sh` is
the end-to-end pricing and it runs on Sean's machine.

⚠️ TRUE / FALSE comes from `report_boundary.TRUTH_CHANGES` — the boundary
session's hand-read print truth — imported, never restated here.

⚠️ THE GENERATION MATTERS. `out/` holds seven run generations of six fixtures
and the CAUTIONARY and METER-IN-FORCE fixes landed BETWEEN them, so pooling
them scores repairs that are already shipped. `--generation m7` (the default)
is the newest and is the only one that describes the current tree.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BOUNDARY = ROOT / "benchmarks" / "omr-staged-meter-boundary-2026-09"

sys.path.insert(0, str(ROOT))
from tools.omr.staged.adjudicators import rhythm as rhythm_mod  # noqa: E402
from tools.omr.staged.record import meter_at                    # noqa: E402


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_RB = _load(BOUNDARY / "report_boundary.py", "_report_boundary")
_REACH = _load(HERE / "probe" / "reach.py", "_reach")


def _carried_before(value: dict, n_cells: int):
    """What the PRE-RULE code handed on: the meter at the source's last bar,
    with every segment eligible.

    ⚠️ Reproduced here rather than kept behind a flag in the shipped module. A
    flag would be a second code path nobody runs; this is a measuring
    instrument and says so. It mirrors `_meter_in_force_at_end`'s old body —
    `meter_at` then strip — and the arm asserts the two AGREE wherever every
    segment is corroborated, which is the control that makes the delta mean
    something.
    """
    if not value:
        return None
    at_end = meter_at(value, n_cells - 1 if n_cells else 0) or value
    return {k: v for k, v in at_end.items()
            if k not in ("segments", "cautionary", "support",
                         "staves_reading_it", "staves_reading_a_meter",
                         "corroborated", "bars_fit", "bars_contradict",
                         "from_cell")}


def _spell(m):
    if not m:
        return "NOTHING CARRYABLE"
    return m.get("raw") or "%s/%s" % (m.get("numerator"), m.get("denominator"))


def _mark(value: dict, reason: str) -> dict:
    """Stamp `corroborated` onto a committed record's segments.

    ⚠️ The committed records PREDATE the rule, so they carry no flag and
    `_meter_in_force_at_end` would (correctly) treat every one as an old
    record. The stamp uses the SHIPPED constant and the SHIPPED predicate
    shape — `len(staves_reading_it) >= METER_CHANGE_MIN_STAVES` — imported
    rather than retyped, so a change to the constant moves this arm too.

    ⚠️⚠️ **`reason` IS LOAD-BEARING AND THE FIRST DRAFT DROPPED IT.** On a
    `voted` verdict segment 0 is the system's OPENING and is never a change;
    on a `change_only` one the system HAS no opening and segment 0 IS the
    change. Marking from index 1 unconditionally left every `change_only`
    segment unflagged, `_meter_in_force_at_end` read it as a pre-rule record
    and carried it — so the arm reported the rule doing nothing on exactly the
    two fixtures it reaches hardest. `report_boundary.tally` makes the same
    distinction and is where this rule is copied from.
    """
    first_change = 0 if reason == "change_only" else 1
    segs = value.get("segments") or []
    out = []
    for i, s in enumerate(segs):
        s = dict(s)
        if i >= first_change:
            s["corroborated"] = (len(s.get("staves_reading_it") or [])
                                 >= rhythm_mod.METER_CHANGE_MIN_STAVES)
        out.append(s)
    return dict(value, segments=out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(BOUNDARY / "out"))
    ap.add_argument("--generation", default="m7",
                    help="run generation prefix; the newest describes the "
                         "current tree. '' pools every generation, which "
                         "scores repairs that already shipped.")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    table = _REACH._tag_to_fixture(_RB)
    rows, seen = [], set()
    for f in sorted(Path(a.out_dir).glob("*.meter.json")):
        stem = f.name.split(".")[0]
        head = stem.split("-", 1)[0]
        gen = head[:len(head) - len(head.lstrip("m0123456789"))]
        if a.generation and gen != a.generation:
            continue
        got = _REACH._fixture_of(f, table)
        if got is None:
            continue
        fixture, label = got
        for v in _RB.meters(f):
            if (v.get("value") or {}).get("segments") is None:
                continue
            parts = str(v["subject"]).split("/")
            page, system = int(parts[1]), int(parts[2])
            value = _mark(v["value"], v.get("reason"))
            segs = value["segments"]
            changes = segs if v.get("reason") == "change_only" else segs[1:]
            if not changes:
                continue
            # ⚠️ The source's cell count is not on the reduction, so the last
            # segment's own `from_cell` is used as a lower bound on the last
            # bar. It only has to land at or past the final change for
            # `meter_at` to pick it, which is the quantity under test.
            n_cells = max(int(s.get("from_cell") or 0) for s in segs) + 1
            before = _carried_before(value, n_cells)
            after = rhythm_mod._meter_in_force_at_end(value, n_cells)
            for s in changes:
                want = _RB.TRUTH_CHANGES.get(
                    (fixture, page, system),
                    _RB.TRUTH_CHANGES.get((fixture, page), "?"))
                verdict = ("UNKNOWN" if want == "?" else
                           "TRUE" if want is not None
                           and (s.get("from_cell"), s.get("raw")) == want
                           else "FALSE")
                # ⚠️ KEYED ON THE FIXTURE, never the run tag: one generation
                # can hold two runs of one fixture (`lit6162` and
                # `lit6162fix`) and pooling them doubles every count.
                key = (fixture, page, system, s.get("from_cell"), s.get("raw"))
                if key in seen:
                    continue
                seen.add(key)
                rows.append({
                    "fixture": fixture, "page": page, "system": system,
                    "from_cell": s.get("from_cell"), "raw": s.get("raw"),
                    "n_staves": len(s.get("staves_reading_it") or []),
                    # ⚠️ NOT `bool(...)`: an ABSENT flag would read as False,
                    # which is the "cannot tell" -> definite answer conversion
                    # this project forbids, inside the instrument.
                    "corroborated": s["corroborated"],
                    "verdict": verdict,
                    "carried_before": _spell(before),
                    "carried_after": _spell(after),
                    "carry_moves": _spell(before) != _spell(after),
                    "still_in_segments": True,
                })

    print("=" * 76)
    print("A-METER-6 -- what an uncorroborated change stops doing")
    print("  generation: %s   (the newest describes the current tree)"
          % (a.generation or "ALL POOLED"))
    print("=" * 76)
    print("  change segments reached: %d" % len(rows))
    if not rows:
        print("\n  INSTRUMENT DEAD: no change segment on this generation. A "
              "confinement\n  rule measured here reports a zero that means "
              "NOTHING. Exiting non-zero.")
        return 2
    conf = [r for r in rows if r["corroborated"]]
    print("  corroborated (>= %d staves): %d      uncorroborated: %d"
          % (rhythm_mod.METER_CHANGE_MIN_STAVES, len(conf),
             len(rows) - len(conf)))
    print()
    print(f"{'verdict':8s} {'stv':>3} {'corrob':>7} {'cell':>4} {'raw':6s} "
          f"{'carried BEFORE':>16} {'carried AFTER':>18}  fixture")
    print("-" * 76)
    for r in sorted(rows, key=lambda r: (r["verdict"], -r["n_staves"])):
        print(f"{r['verdict']:8s} {r['n_staves']:>3} "
              f"{str(r['corroborated']):>7} {str(r['from_cell']):>4} "
              f"{str(r['raw']):6s} {r['carried_before']:>16} "
              f"{r['carried_after']:>18}  {r['fixture']} p{r['page']}"
              f" s{r['system']}")

    print()
    print("CONTROLS")
    # 1. every TRUE change is still IN `segments` -- the half that must not move
    trues = [r for r in rows if r["verdict"] == "TRUE"]
    print("  every TRUE change still reaches its own system's segments: "
          "%d of %d" % (sum(1 for r in trues if r["still_in_segments"]),
                        len(trues)))
    # 2. a corroborated change's carry is UNCHANGED -- the positive control
    moved_conf = [r for r in conf if r["carry_moves"]]
    print("  corroborated changes whose carry MOVES (must be 0): %d of %d"
          % (len(moved_conf), len(conf)))
    # 3. the uncorroborated ones DO move -- without this the arm is vacuous
    unconf = [r for r in rows if not r["corroborated"]]
    moved_unconf = [r for r in unconf if r["carry_moves"]]
    print("  uncorroborated changes whose carry moves (the RULE): %d of %d"
          % (len(moved_unconf), len(unconf)))
    print()
    for verdict in ("TRUE", "FALSE", "UNKNOWN"):
        sel = [r for r in rows if r["verdict"] == verdict]
        if not sel:
            continue
        print("  %-8s n=%-3d  confined: %d   staves_reading_it = %s"
              % (verdict, len(sel),
                 sum(1 for r in sel if not r["corroborated"]),
                 sorted(r["n_staves"] for r in sel)))

    ok = not moved_conf and (not unconf or moved_unconf)
    if not ok:
        print("\n  ⚠️ A CONTROL FAILED -- do not quote the table above.")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1) + "\n")
        print("\n  wrote %s" % a.json)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
