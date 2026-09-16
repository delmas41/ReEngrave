#!/usr/bin/env python3
"""REACH FIRST: does the SUBSTITUTED arbiter exist on the corpus at all?

The brief keeps Sean's decision table and swaps its arbiter — the measure math
out, the template reader's own correlation `score` in — on the ground that the
bars are SILENT exactly where the table needs them.

⚠️⚠️ BEFORE ASKING WHETHER THE SCORE SEPARATES, ASK WHETHER IT IS THERE. A
score-based arbiter needs a score on BOTH sides of every pair:

    the CAUTIONARY side  a `Q.METER_TEMPLATE_AT_BAR` row at that system's LAST
                         cell — which exists only on the base branch, only
                         with `OMR_METER_TEMPLATE_AT_BAR=1`, and only after a
                         re-gather;
    the OPENING side     a `Q.METER_TEMPLATE` row on the NEXT system's staves.

This probe counts both over every committed artefact, and exits non-zero under
`--check` when the arbiter is DEAD — which is this repo's own rule (*measure
REACH before accuracy; print it first; exit non-zero if dead*) applied to a
proposal rather than to a reader.

⚠️ IT IS NOT A NEGATIVE RESULT ABOUT THE SCORE. It is a statement about what a
container with no `omr-weights/` and no `library/` can see. The distinction
matters because the two are reported in the same table and would otherwise be
read as one.

    python3 benchmarks/omr-meter-cautionary-arbiter-2026-09/arbiter_reach.py
    python3 .../arbiter_reach.py --check      # non-zero while the arbiter is DEAD
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SIBLING = ROOT / "benchmarks" / "omr-meter-cautionary-2026-09"
sys.path.insert(0, str(SIBLING))

# ⚠️ IMPORTED, NOT RESTATED — `common.py` and `probe_contest.py` are the
# cautionary session's own deliverable, brought onto this branch VERBATIM so
# this job can call them. Restating the pair-builder would give this repository
# two readings of one artefact set, which is the failure this file's own
# neighbours record for the accuracy figure held in four places.
import common                                                  # noqa: E402
import probe_contest                                           # noqa: E402


def _template_rows_anywhere():
    """Every committed `.meter.json` verdict that carries a template SCORE.

    ⚠️ `.meter.json` is an EXTRACT of the meter verdicts, not a full record, so
    a zero here means *no committed artefact carries one* and never *the
    gatherer does not write one*. The positive control is `raw`, which
    `adjudicate_meter` does read and which therefore reaches these extracts —
    if `raw` is absent too, the search itself is broken.
    """
    out = {"files": 0, "with_score": 0, "with_raw": 0,
           "with_template_at_bar": 0}
    for p in sorted((ROOT / "benchmarks" / "omr-staged-meter-boundary-2026-09"
                     / "out").glob("*.meter.json")):
        text = p.read_text()
        out["files"] += 1
        if '"score"' in text:
            out["with_score"] += 1
        if '"raw"' in text:
            out["with_raw"] += 1
        if "meter_template_at_bar" in text:
            out["with_template_at_bar"] += 1
    return out


def _shared_quantity_is_two_readers():
    """⚠️ THE ONE QUANTITY BOTH SIDES OF THE CONTEST STATE IS NOT ONE QUANTITY.

    The cautionary session's decisive negative is that the only currency both
    sides share — *how many staves read it* — prefers the WRONG reading (9 for
    the true cautionary against 10 for the false opening). That is true, and it
    is weaker than it looks: the two counts are produced by DIFFERENT READERS
    over DIFFERENT WINDOWS.

        the cautionary's `staves_reading_it`   `_meter_changes`   -> Q.METER_GLYPH
                                               the DETECTOR's stacked digits,
                                               read inside a measure cell
        the opening's `n_staves_spoke`         `adjudicate_meter` -> Q.METER_TEMPLATE
                                               the TEMPLATE reader, over a
                                               16-staff-space header window

    So "9 against 10" compares a count of detector staves with a count of
    template staves. Derived from the SOURCE rather than asserted, with a
    positive control: each function must be found and must name at least one
    quantity, or the scan itself is broken.
    """
    import inspect
    import re

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tools.omr.staged.adjudicators import rhythm as R

    def _trace(fn, field, shape):
        """Which `Q.` the variable behind `field` is read from, in `fn`.

        ⚠️ NARROW ON PURPOSE. `adjudicate_meter` reads ten quantities; listing
        them all would prove nothing about this one count. This finds the
        VARIABLE the field is built from and then the `ev.rows(Q.X)` that
        assigned it, so a rename or a re-source shows up as `null` rather than
        as a quietly wrong answer.
        """
        try:
            src = inspect.getsource(fn)
        except OSError:                                        # noqa: BLE001
            return {"found": False, "variable": None, "quantity": None}
        m = re.search(shape, src)
        if not m:
            return {"found": True, "variable": None, "quantity": None}
        var = m.group(1)
        a = re.search(rf"\b{re.escape(var)}\s*=\s*ev\.rows\(\s*Q\.([A-Z_]+)",
                      src)
        if a:
            return {"found": True, "variable": var, "quantity": a.group(1)}
        # The change side builds its staff set from the glyph rows it walked,
        # so name the quantity the enclosing reader gathers from instead.
        qs = sorted(set(re.findall(r"ev\.rows\(\s*Q\.([A-Z_]+)", src)))
        return {"found": True, "variable": var,
                "quantity": qs[0] if len(qs) == 1 else None,
                "candidates": qs}

    return {
        "cautionary staves (_meter_changes.staves_reading_it)":
            _trace(R._meter_changes, "staves_reading_it",
                   r'"staves_reading_it":\s*sorted\((\w+)\)'),
        "opening staves (adjudicate_meter.n_staves_spoke)":
            _trace(R.adjudicate_meter, "n_staves_spoke",
                   r"n_staves_spoke[=:]\s*len\((\w+)\)"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out", default=str(HERE / "out" / "arbiter-reach.json"))
    args = ap.parse_args()

    pairs = probe_contest._pairs()
    scored = [p for p in pairs if p["truth"] is not None]

    caut_score = sum(1 for p in pairs if p.get("caut_score") is not None)
    open_score = sum(1 for p in pairs if p.get("open_score") is not None)
    both = sum(1 for p in pairs
               if p.get("caut_score") is not None
               and p.get("open_score") is not None)

    print("REACH — the SUBSTITUTED arbiter")
    print(f"  cautionary/opening pairs in the whole corpus ......... {len(pairs)}")
    print(f"  ...with a hand-read print truth ...................... {len(scored)}")
    print(f"  ...carrying a CAUTIONARY-side template score ......... {caut_score}")
    print(f"  ...carrying an OPENING-side template score ........... {open_score}")
    print(f"  ...carrying BOTH — the arbiter's own reach ........... {both}")

    art = _template_rows_anywhere()
    print("\nWHY — the committed artefacts, greppd rather than assumed")
    print(f"  committed *.meter.json files ......................... {art['files']}")
    print(f"  ...carrying a template `score` ....................... {art['with_score']}")
    print(f"  ...carrying `raw` (THE POSITIVE CONTROL for this grep) {art['with_raw']}")
    print(f"  ...carrying any `meter_template_at_bar` row .......... "
          f"{art['with_template_at_bar']}")
    if art["with_raw"] == 0:
        print("  ⚠️ the positive control is ZERO — this search is broken, "
              "not the artefacts")

    print("\nTHE STATES THE TABLE HAS TO FACE, and what each pair carries")
    for p in pairs:
        print(f"  {p['fixture']:<18} {p['system']:<12} {p['state']:<16}"
              f" caut={p['caut_raw']!s:<5} open={p['open_raw']!s:<5}"
              f" truth={p['truth']!s:<5}"
              f" caut_staves={p['caut_staves']} open_staves={p['open_staves']}"
              f" caut_bars={p['caut_bars_fit']}/{p['caut_bars_contradict']}")

    readers = _shared_quantity_is_two_readers()
    print("\nTHE 'SHARED' QUANTITY, DERIVED FROM THE SOURCE")
    for name, info in readers.items():
        if not info["found"] or info["variable"] is None:
            print(f"  {name:<52} ⚠️ NOT FOUND — this scan is broken, "
                  f"not the code")
            continue
        print(f"  {name:<52} `{info['variable']}` <- Q.{info['quantity']}"
              + (f"   candidates {info['candidates']}"
                 if info.get("candidates") else ""))
    qs = {i.get("quantity") for i in readers.values()}
    if len(qs) == 1 and None not in qs:
        print("  ⚠️ both counts come from ONE quantity — the 'two readers' "
              "claim is FALSE on this tree")
    elif None not in qs:
        print("  ⚠️⚠️ TWO DIFFERENT QUANTITIES: the one currency the contest "
              "shares is not one currency.")

    payload = {"pairs": pairs, "artefacts": art, "readers": readers,
               "reach": {"pairs": len(pairs), "truthed": len(scored),
                         "caut_score": caut_score, "open_score": open_score,
                         "both": both}}
    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.out).write_text(json.dumps(payload, indent=1))
    print(f"\nwrote {args.out}")

    if args.check:
        if not pairs:
            print("DEAD: no cautionary/opening pair in the corpus at all")
            return 2
        if both == 0:
            print("DEAD: the substituted arbiter has reach ZERO — not one "
                  "pair carries a template score on both sides.")
            return 3
        print("CHECK OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
