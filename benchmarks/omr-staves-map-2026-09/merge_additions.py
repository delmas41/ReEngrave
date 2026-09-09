"""Review, PROVE, and then merge the confirmed maps into works.json.

    python3 benchmarks/omr-staves-map-2026-09/merge_additions.py           # dry
    python3 benchmarks/omr-staves-map-2026-09/merge_additions.py --write

`works.json` is hand-verified truth that seven other benchmarks read, so the UI
never touches it.  This is the only thing that does, and it refuses on anything
it cannot prove:

  * the row exists and does NOT already carry a `staves` map (never overwrite
    someone else's hand reading);
  * the additions row is `done`;
  * the map's shape is works.json's shape exactly — a list of
    `{"name": str, "parts": [int, ...]}`, nothing else. ⚠️ `parts` must be
    UNIQUE but is deliberately NOT required to be sorted: `page_normalise`
    keeps `parts[0]`, so the order chooses the merged staff's identity and
    sorting it renames three printed staves `Piccolo` — measured, see
    `shape_problems`;
  * every reference part is named exactly ONCE.  `page_normalise` raises
    `IncompleteMap` on a map that leaves a part out, because a normalised truth
    missing a part scores BETTER for the wrong reason; a part named TWICE is the
    mirror fault and nothing downstream checks it;
  * ⚠️ and the map actually NORMALISES.  `page_normalise.normalise` is run on
    the row's own trimmed truth before anything is written.  A map that passes
    every shape check and then raises in the consumer is exactly the "mismatched
    shape is worse than no map" failure — so the consumer is asked first.

With `--write` it copies `works.json` to `works.json.bak-<utc>` first, inserts
`staves` immediately before `notes` (where every mapped row already has it), and
re-checks that the file re-parses and that no OTHER row changed.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BENCH = Path(__file__).resolve().parent
sys.path.insert(0, str(BENCH))
from build_cache import MAIN, SCAN, find_fixture  # noqa: E402
# ⚠️ FROM `build_cache`, NOT A SECOND LOAD. `SCAN` points at the MAIN checkout
# (`works.json` is hand-verified DATA, one copy) while the SHAPE of a `staves`
# entry is CODE and must be this checkout's — `build_cache` loads it by path
# for exactly that reason, and re-loading it here would give two instances.
from build_cache import staves_schema  # noqa: E402

WORKS = SCAN / "works.json"
ADDITIONS = SCAN / "works.staves-additions.json"

sys.path.insert(0, str(SCAN))


#: The two ARITY fields, both facts about the ENGRAVING rather than about the
#: reference encoding, and both optional.
#:
#: ⚠️ THIS WRITER USED TO REFUSE THEM, AND THAT COST A WHOLE PAGE. `lines`
#: landed in `166759fc`; `shape_problems` predates it and kept demanding
#: entries be "exactly name+parts", so a CORRECT map carrying `lines: 1` would
#: have been rejected at merge time — while `build_cache.research_proposal` was
#: computing `"lines": spec.get("lines", 5)` for every entry and four
#: projections down the path threw it away. mahler p2's hand-confirmed map
#: arrived unflagged and its whole page stayed unassessable; the only thing
#: that noticed was `test_works_json_staff_lineup.py`, AFTER the human pass was
#: spent. See `benchmarks/omr-part-join-2026-09/FINDINGS.md` §7.
#:
#: ⚠️⚠️ AND THE FIRST REPAIR ANSWERED A HAND LIST WITH A HAND LIST. `e9c82c82`
#: wrote these two names out here — and on the day it landed the list was
#: ALREADY incomplete: `beethoven-sym5-mvt1-984073-p1` carries `clef` and `key`
#: on all twelve staves (`scan_eval`'s rule 2, THE PAGE IS THE TRUTH NOT THE
#: FILE) and was still refused, so this writer still could not re-merge a sixth
#: of the file it had written. They are now DERIVED BY AST from
#: `run_ledger.expand_lineup` — the same function `arity_problems` below
#: already refuses to second-guess — and the facts no consumer reads yet are
#: DECLARED, with reasons, in `staves_schema.RECORDED_ONLY`.
ARITY_FIELDS = staves_schema.arity_fields()


def shape_problems(staves) -> list[str]:
    """`works.json`'s own shape, asked of `staves_schema` — never of a copy.

    ⚠️ ALLOWED IS NOT UNCHECKED, and that rule survives the move: every
    optional key has a validator, and `staves_schema.unvalidated()` fails the
    suite on an allowed key without one — which a DERIVED list needs and a
    hand-written one did not, because a hand list and its validators are edited
    together while a derived list can grow a field on its own.
    """
    return staves_schema.problems(staves)


#: ⚠️ `parts` IS ORDERED, AND THE ORDER IS NOT A STORAGE CONVENTION.
#: `page_normalise.normalise` does `keep = parts[idx[0]]` and merges the rest
#: INTO it, so the FIRST index decides which reference part the merged staff
#: IS — its name, and whose bar survives a `silent_all` measure.
#:
#: This check used to demand `sorted-unique`, which conflated two different
#: things: uniqueness (a real invariant, still enforced above) and sortedness
#: (a canonicalisation that MOVES the answer). It refused three rows of a
#: finished human pass on 2026-09-07, and the repair was nearly to sort them.
#: Measured instead, on those rows' own maps
#: (`benchmarks/omr-page-normalise-fixes-2026-09/probe_parts_order.py` and
#: `…_diff.py`):
#:
#:   * the NOTES are untouched — 15/15, 21/21 and 21/21 output parts compare
#:     bar-for-bar identical under both orderings;
#:   * the merged part's IDENTITY is not. Sorting puts the silent, tacet-folded
#:     Piccolo ahead of the printed staff, so `Zwei Fagotte.`, `Drei Hoboen.`
#:     and `Drei Klarinetten in A` all come back named **Piccolo**;
#:   * and musicdiff then pairs those parts by the wrong name: −3, +19, −8
#:     edits across the three rows, +8 net.
#:
#: So a sorted map is not a tidier spelling of the same truth — it is a truth
#: in which three printed staves claim to be a piccolo. The convention the
#: proposals carry (printed part first, tacet folds after) is the meaningful
#: one and is preserved verbatim.
#:
#: ⚠️ THE PRINCIPLED FOLLOW-UP, NOT DONE HERE: `keep` is chosen by list
#: POSITION, which is why an ordering can carry meaning at all. An explicit
#: rule — prefer the first part that SOUNDS on this page — would agree with
#: the human's order on all three rows and make ordering irrelevant. That
#: changes the transform, so it needs the Dvořák +0 and engraved no-op
#: controls before it ships, and it is not what unblocks a finished pass.


# ------------------------------------------------- the one normalisation proof

def prove_normalises(row_id: str, staves, *, source_reference=None) -> dict:
    """Would `page_normalise` accept this map for this row? THE shared answer.

    ⚠️ THIS FUNCTION EXISTS SO TWO CONSUMERS CANNOT DRIFT APART. `check_row`
    asks it before writing `works.json`; the confirmation UI
    (`server.py`) asks it before letting a row be marked `done`. Until
    2026-09-07 the UI re-implemented only the CHEAP structural checks and never
    called `page_normalise` at all — so a row could go green staff by staff,
    be marked done, and refuse at merge time, AFTER the human's whole pass was
    spent. Two `page_normalise` faults did exactly that to Mahler p3 and p4.
    A second implementation would reopen the same gap one level down.

    Returns `ok` / `problem` / `normalised`, plus `unavailable`, which the two
    callers are ENTITLED TO TREAT DIFFERENTLY and do:

      * `unavailable` means the proof could not RUN — no `<row>.truth.musicxml`
        on this machine. `check_row` counts that a refusal, because it is about
        to WRITE hand-verified truth and must not write what it could not
        prove. The UI counts it a warning, because it writes only the additions
        file and blocking Sean's keystroke over a missing fixture would cost
        more than it protects — the merge step still refuses later.
      * `ok is False` with `unavailable is False` means `page_normalise`
        actually REFUSED the map. Both callers block on that, identically.
    """
    truth, _ = find_fixture(row_id, ".truth.musicxml")
    if truth is None:
        return {"ok": False, "unavailable": True, "normalised": None,
                "problem": "no <row>.truth.musicxml on disk — cannot prove the "
                           "map against the consumer"}
    try:
        import page_normalise  # from benchmarks/omr-scan-e2e-2026-09
        _score, report = page_normalise.normalise(
            truth, staves, source_reference=source_reference)
    except Exception as exc:                           # noqa: BLE001
        return {"ok": False, "unavailable": False, "normalised": None,
                "problem": f"page_normalise REFUSED this map: "
                           f"{type(exc).__name__}: {exc}"}
    return {"ok": True, "unavailable": False, "problem": None,
            "normalised": {
                "n_source_parts": report["n_source_parts"],
                "n_output_parts": report["n_output_parts"],
                "exact_duplication_share": report["exact_duplication_share"],
                "divisi_share": report["divisi_share"],
            }}


def _entry_for_works_json(s: dict) -> dict:
    """One additions-file staff as works.json spells it.

    ⚠️ THE ONE PLACE THE PROJECTION IS WRITTEN — `staves_schema.project`, whose
    second return value is what it DROPPED. It used to be spelled inline in
    two places and both rebuilt the entry as `{name, parts}` literally, so a
    field the proposal carried could not survive to the file however many
    writers allowed it. A projection repeated is a projection that drops
    something; a projection that drops SILENTLY is how a typo becomes
    indistinguishable from an absent flag.

    Defaults are omitted (`lines: 5`, `printed_staves: 1`): every merged row
    omits them and writing them would make this writer's output differ from the
    file it is appending to.
    """
    return staves_schema.project(s)[0]


def arity_problems(row: dict, staves) -> list[str]:
    """Does this map claim as many FIVE-LINE staves as the page prints?

    ⚠️ THIS IS THE GUARD THE WRITER DID NOT HAVE, AND ITS ABSENCE IS THE WHOLE
    DEFECT. `test_works_json_staff_lineup.py` asserts this of the FILE, so it
    fires after a map is merged — which on mahler p2 meant after a 21-staff
    human confirmation pass had been spent. The same question asked HERE
    refuses the merge instead, with the fields named in the message.

    ⚠️ It calls `run_ledger.expand_lineup` rather than recomputing the count.
    That function IS the definition of "how many parts this lineup expects",
    and this file already refuses to hold a second copy of a shared answer —
    see `prove_normalises`, which exists for exactly that reason.

    Asserted only where the systems are UNIFORM (`n_staves % n_systems == 0`),
    the same abstention the test makes: a tacet-suppressed page prints a
    different lineup per system (beethoven p3 is 11 then 8), so one lineup
    names no single count and there is nothing to check against.
    """
    if not isinstance(staves, list) or not staves:
        return []
    page = row.get("page") or {}
    n_staves, n_sys = page.get("n_staves"), page.get("n_systems") or 1
    if not n_staves or not n_sys or n_staves % n_sys:
        return []
    expand = _expand_lineup()
    if expand is None:                      # the ledger is not importable here
        return []
    per_system = n_staves // n_sys
    got = len(expand(staves))
    if got == per_system:
        return []
    one_line = sum(1 for s in staves
                   if isinstance(s, dict) and int(s.get("lines") or 5) != 5)
    return [f"the lineup expands to {got} five-line staves but the page prints "
            f"{per_system} per system ({len(staves)} entries, {one_line} "
            f"flagged `lines: 1`). Either a one-line percussion rule is "
            f"missing `lines: 1`, or an entry the page prints as several "
            f"staves is missing `printed_staves: N`."]


def _expand_lineup():
    """`run_ledger.expand_lineup`, or None if the ledger is not on this tree."""
    ledger = BENCH.parent / "omr-symbol-ledger-2026-09"
    if not (ledger / "run_ledger.py").is_file():
        return None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "_run_ledger_for_merge", ledger / "run_ledger.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.expand_lineup
    except Exception:                                          # noqa: BLE001
        return None


def check_row(row_id: str, row: dict, add: dict) -> dict:
    problems: list[str] = []
    if add.get("status") != "done":
        problems.append(f"additions status is {add.get('status')!r}, not 'done'")
    if isinstance(row.get("staves"), (list, str)):
        problems.append("works.json already carries a `staves` map for this row "
                        "— refusing to overwrite a hand reading")

    # ⚠️ WHAT THE PROJECTION DROPPED IS REPORTED, NOT ASSUMED TO BE JUNK. The
    # fallback branch is the UI's working state, which carries bookkeeping
    # (`proposed`, `verdict`, `adopted_from`) that must not reach truth — so a
    # projection is right. But a misspelled `linnes: 1` is dropped by exactly
    # the same rule, and the only thing separating it from bookkeeping is that
    # the drop is printed.
    dropped: dict[int, list[str]] = {}
    staves = add.get("staves_for_works_json")
    if staves is None:
        staves = []
        for k, s in enumerate(add.get("staves", [])):
            if not isinstance(s, dict):
                staves.append(s)
                continue
            entry, gone = staves_schema.project(s)
            staves.append(entry)
            if gone:
                dropped[k] = gone
    shape = shape_problems(staves)
    problems += shape
    # ⚠️ Gated on the SHAPE problems specifically, not on `problems` — which by
    # here can already hold "works.json already carries a map". Gating on all
    # of them silences the arity report on exactly the rows most worth seeing
    # it (every already-merged row), and that is how the retrospective control
    # in FINDINGS §8 was briefly lost. The narrow gate is only about not
    # RAISING: `expand_lineup` reads `int(s["lines"])`.
    if not shape:
        problems += arity_problems(row, staves)

    counts: dict[int, int] = {}
    for s in staves or []:
        for i in (s.get("parts") or []):
            counts[i] = counts.get(i, 0) + 1

    # ⚠️ THE SAME PROOF THE UI RUNS — `prove_normalises`, not a second copy.
    n_parts = None
    normalised = None
    if not problems:
        proof = prove_normalises(
            row_id, staves,
            source_reference=row["reference"]["catalog_path"])
        if proof["ok"]:
            normalised = proof["normalised"]
            n_parts = normalised["n_source_parts"]
        else:
            # About to WRITE: `unavailable` is a refusal here. See the
            # docstring of `prove_normalises` for why the UI differs.
            problems.append(proof["problem"])
    elif find_fixture(row_id, ".truth.musicxml")[0] is None:
        # Shape problems already stand, but a missing fixture is reported too:
        # it is why the proof did not run, and it was reported before this
        # function was factored out.
        problems.append("no <row>.truth.musicxml on disk — cannot prove the "
                        "map against the consumer")

    doubled = sorted(i for i, c in counts.items() if c > 1)
    if doubled:
        problems.append(f"part(s) named by more than one staff: {doubled}")
    if n_parts is not None:
        missing = [i for i in range(n_parts) if i not in counts]
        if missing:
            problems.append(f"parts unaccounted for: {missing}")

    return {"row_id": row_id, "staves": staves, "problems": problems,
            "normalised": normalised, "dropped": dropped,
            "n_staves": len(staves or []),
            "n_parts_named": len(counts)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--additions", default=str(ADDITIONS))
    ap.add_argument("--works", default=str(WORKS))
    ap.add_argument("--rows", nargs="+", default=None)
    ap.add_argument("--write", action="store_true",
                    help="actually edit works.json (default is a dry run)")
    args = ap.parse_args(argv)

    apath, wpath = Path(args.additions), Path(args.works)
    if not apath.is_file():
        print(f"no additions file at {apath} — nothing to merge", file=sys.stderr)
        return 1

    add_doc = json.loads(apath.read_text())
    works = json.loads(wpath.read_text())
    by_id = {r["row_id"]: r for r in works["rows"]}

    wanted = args.rows or list(add_doc.get("rows", {}))
    checks, ready = [], []
    for rid in wanted:
        add = add_doc["rows"].get(rid)
        if add is None:
            print(f"  -- {rid}: not in the additions file"); continue
        if rid not in by_id:
            print(f"  !! {rid}: not a row of works.json"); continue
        c = check_row(rid, by_id[rid], add)
        checks.append(c)
        head = "OK  " if not c["problems"] else "REFUSE"
        print(f"  {head} {rid}: {c['n_staves']} staves, "
              f"{c['n_parts_named']} parts named"
              + (f", normalises to {c['normalised']['n_output_parts']} parts "
                 f"(exact-duplication {c['normalised']['exact_duplication_share']})"
                 if c["normalised"] else ""))
        for p in c["problems"]:
            print(f"          - {p}")
        # ⚠️ Reported as `key xN/M`, not entry by entry: bookkeeping is on
        # EVERY entry, so a `linnes` on one entry of twenty-one stands out
        # against `proposed x21/21` instead of scrolling past inside it.
        if c.get("dropped"):
            tally = Counter(k for gone in c["dropped"].values() for k in gone)
            n = c["n_staves"] or 1
            print("          . not carried into works.json: "
                  + ", ".join(f"{k} x{v}/{n}"
                              for k, v in sorted(tally.items())))
        if not c["problems"]:
            ready.append(c)
            for s in c["staves"]:
                print(f"            {s['name']!r} -> {s['parts']}")

    if not ready:
        print("\nnothing mergeable.")
        return 1 if any(c["problems"] for c in checks) else 0

    if not args.write:
        print(f"\nDRY RUN — {len(ready)} row(s) would be merged. "
              f"Re-run with --write.")
        return 0

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bak = wpath.with_name(wpath.name + f".bak-{stamp}")
    shutil.copy2(wpath, bak)
    print(f"\nbacked up {wpath.name} -> {bak.name}")

    before = json.loads(wpath.read_text())
    for c in ready:
        row = by_id[c["row_id"]]
        # Rebuild the dict so `staves` lands where every mapped row has it:
        # immediately before `notes`.
        new = {}
        for k, v in row.items():
            if k == "notes":
                new["staves"] = c["staves"]
            new[k] = v
        if "staves" not in new:
            new["staves"] = c["staves"]
        row.clear(); row.update(new)
        row.setdefault("notes", "")

    tmp = wpath.with_suffix(".merge-tmp")
    tmp.write_text(json.dumps(works, indent=1) + "\n")
    reparsed = json.loads(tmp.read_text())

    merged_ids = {c["row_id"] for c in ready}
    for a, b in zip(before["rows"], reparsed["rows"]):
        if a["row_id"] in merged_ids:
            continue
        if a != b:
            tmp.unlink()
            print(f"REFUSING: row {a['row_id']} changed and should not have.",
                  file=sys.stderr)
            return 1
    tmp.replace(wpath)
    print(f"merged {len(ready)} row(s) into {wpath}")
    print("Re-run the consumers to price it:\n"
          "  python3 benchmarks/omr-headline-validity-2026-09/"
          "probe_map_coverage_cost.py\n"
          "  python3 benchmarks/omr-headline-validity-2026-09/normalised_arm.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
