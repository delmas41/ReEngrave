"""Does the SLOT partition (`export._stitch_slots_by_slot`) match the
hand-read truth on the rows where the ORDINAL join (`export._stitch_slots`)
REFUSES? — read-only, no pipeline run.

`docs/scope-part-correspondence-2026-09-07.md` recommends replacing the
exporter's ordinal staff-join with the contextual pass's `slot_index` join.
The previous falsifier found zero disagreement between the two joins where
the ordinal join SUCCEEDS — but on n=2 documents, and it could not test the
population that matters: the rows where the ordinal join REFUSES, because
there the ordinal join has no answer to compare against. This probe closes
that gap using `benchmarks/omr-scan-e2e-2026-09/works.json`'s hand-read
`systems_as_printed` / `staves` maps as ground truth.

Imports the REAL `_stitch_slots` and `_stitch_slots_by_slot` from
`tools.omr.export` — does not restate their logic.

Reads only committed JSON. Runs no transcription, no scan_eval, no
orchestral_eval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.omr.export import _stitch_slots, _stitch_slots_by_slot  # noqa: E402


def _bench_root() -> Path:
    """`benchmarks/omr-scan-e2e-2026-09` — in THIS checkout or the main one.

    Fixtures are gitignored build products that live in the main checkout; a
    worktree has the harness and none of the artefacts.
    """
    here = REPO / "benchmarks/omr-scan-e2e-2026-09"
    if (here / "fixtures").is_dir():
        return here
    main = Path(os.environ.get(
        "REENGRAVE_MAIN", "/Users/seanjohnson/Desktop/ReEngrave"))
    return main / "benchmarks/omr-scan-e2e-2026-09"


BENCH = _bench_root()
FIXTURES = BENCH / "fixtures"
WORKS = BENCH / "works.json"

Key = tuple  # (system_idx: int, position_in_system: int)


# --------------------------------------------------------------------------
# Ground truth derivation
# --------------------------------------------------------------------------

def _true_groups_from_systems_as_printed(
    row: dict[str, Any],
) -> tuple[list[frozenset[Key]], str] | None:
    """Align hand-read per-system staff lists BY NAME to derive the true
    cross-system partition. Verifies each system's list is either identical
    to, or a clean order-preserving SUBSEQUENCE of, the widest system's list
    (a suppressed staff is dropped from the margin, never reordered — this is
    checked, not assumed, and the probe abstains loudly if it does not hold).
    """
    sap = row.get("systems_as_printed")
    if not isinstance(sap, dict):
        return None
    sys_keys = sorted(
        (k for k in sap if k.startswith("system_")),
        key=lambda k: int(k.split("_")[1]),
    )
    if len(sys_keys) < 2:
        return None
    per_system_names: list[list[str]] = []
    for k in sys_keys:
        entries = sap[k]
        if not isinstance(entries, list) or not entries:
            return None
        per_system_names.append([e["name"] for e in entries])

    # The widest system is assumed to be the full lineup; every other system
    # must be an order-preserving subsequence of it BY NAME.
    widest = max(per_system_names, key=len)
    for names in per_system_names:
        it = iter(widest)
        for n in names:
            for w in it:
                if w == n:
                    break
            else:
                raise AssertionError(
                    "systems_as_printed alignment failed: "
                    f"{n!r} is not an order-preserving subsequence match "
                    f"against the widest system's names {widest!r}"
                )

    # Build groups: one group per full-lineup slot (by name identity, since
    # a name can repeat -- e.g. two systems might both print "Timpani" -- we
    # key on (name, its ordinal occurrence among same-named entries in the
    # widest list) to disambiguate).
    def _keyed(names: list[str]) -> list[tuple[str, int]]:
        seen: dict[str, int] = {}
        out = []
        for n in names:
            i = seen.get(n, 0)
            out.append((n, i))
            seen[n] = i + 1
        return out

    widest_keyed = _keyed(widest)
    group_of: dict[tuple[str, int], frozenset] = {gk: frozenset() for gk in widest_keyed}
    group_lists: dict[tuple[str, int], list[Key]] = {gk: [] for gk in widest_keyed}

    for sys_idx, names in enumerate(per_system_names):
        keyed = _keyed(names)
        # Walk widest_keyed in order, consuming from keyed as they match, to
        # get the correct POSITION (index within this system's own staff
        # list) for each matched name.
        wi = 0
        for pos, gk in enumerate(keyed):
            # advance wi until widest_keyed[wi] matches gk's name, honoring
            # order and occurrence count
            while widest_keyed[wi] != gk:
                wi += 1
            group_lists[widest_keyed[wi]].append((sys_idx, pos))
            wi += 1

    groups = [frozenset(v) for v in group_lists.values()]
    return groups, "systems_as_printed (name-aligned)"


def _true_groups_uniform_lineup(
    row: dict[str, Any], n_systems: int, system_sizes: list[int],
) -> tuple[list[frozenset[Key]], str] | None:
    """Rows with only a flat `staves` map (no `systems_as_printed`): the
    label/notes text asserts the SAME lineup prints on every system (no
    suppression). True only when every system's detected staff count equals
    every other's -- i.e. exactly the population where the ordinal join
    itself would not refuse. This is a WEAKER validation than the
    name-aligned case: it does not independently re-derive the alignment,
    it only confirms hand truth agrees a uniform lineup exists.
    """
    st = row.get("staves")
    if not isinstance(st, list) or not st or not isinstance(st[0], dict):
        return None
    if len(set(system_sizes)) != 1:
        return None
    n = system_sizes[0]
    if len(st) != n:
        # Hand truth's flat staff count doesn't match detected per-system
        # count (e.g. a condensed grand-staff entry covering 2 physical
        # staves) -- still fine for a POSITIONAL truth as long as it's a
        # uniform lineup; we only need position-count agreement, not the
        # flat list's length. Do not fail here, just don't use it to name
        # groups (position is still 1:1 by assumption of "no suppression").
        pass
    groups = [frozenset((s, i) for s in range(n_systems)) for i in range(n)]
    return groups, "uniform-lineup positional (hand truth asserts one unchanging lineup; not independently name-aligned per system)"


# --------------------------------------------------------------------------
# Candidate partitions from the REAL exporter functions
# --------------------------------------------------------------------------

def _systems_of(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [system for page in result.get("pages", [])
            for system in page.get("systems", []) if system.get("staves")]


def _id_to_key(systems: list[dict[str, Any]]) -> dict[int, Key]:
    out = {}
    for sys_idx, system in enumerate(systems):
        for pos, staff in enumerate(system["staves"]):
            out[id(staff)] = (sys_idx, pos)
    return out


def _ordinal_partition(result: dict[str, Any]) -> tuple[list[frozenset[Key]] | None, str]:
    systems = _systems_of(result)
    id2key = _id_to_key(systems)
    slots = _stitch_slots(result)
    if slots is None:
        return None, "REFUSED"
    groups = [frozenset(id2key[id(st)] for st in group) for group in slots]
    return groups, "succeeded"


def _slot_partition(result: dict[str, Any]) -> tuple[list[frozenset[Key]] | None, str]:
    systems = _systems_of(result)
    id2key = _id_to_key(systems)
    out = _stitch_slots_by_slot(result)
    if out is None:
        return None, "abstained"
    slots, slot_systems = out
    groups = []
    for group, sysidx_list in zip(slots, slot_systems):
        # slot_systems gives the system index per element; the position
        # within that system comes from identity lookup.
        keys = []
        for staff in group:
            sys_idx, pos = id2key[id(staff)]
            keys.append((sys_idx, pos))
        groups.append(frozenset(keys))
    return groups, "succeeded"


# --------------------------------------------------------------------------
# Comparison
# --------------------------------------------------------------------------

def _compare(true_groups: list[frozenset[Key]], cand_groups: list[frozenset[Key]]) -> dict[str, Any]:
    true_set = set(true_groups)
    cand_set = set(cand_groups)
    exact_equal = true_set == cand_set

    # per-staff: does the candidate group containing staff x equal the true
    # group containing x, as SETS (i.e. x's groupmates are exactly right)?
    true_group_of: dict[Key, frozenset] = {}
    for g in true_groups:
        for k in g:
            true_group_of[k] = g
    cand_group_of: dict[Key, frozenset] = {}
    for g in cand_groups:
        for k in g:
            cand_group_of[k] = g

    universe = sorted(true_group_of.keys())
    n_correct = 0
    mismatches = []
    for k in universe:
        tg = true_group_of.get(k)
        cg = cand_group_of.get(k)
        if tg == cg:
            n_correct += 1
        else:
            mismatches.append({
                "staff": list(k),
                "true_group": sorted(list(t) for t in tg) if tg else None,
                "cand_group": sorted(list(t) for t in cg) if cg else None,
            })
    n = len(universe)
    return {
        "exact_partition_equal": exact_equal,
        "n_staves": n,
        "n_staves_correctly_grouped": n_correct,
        "per_staff_agreement": (n_correct / n) if n else None,
        "mismatches": mismatches,
    }


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def _content_fingerprint(result: dict[str, Any]) -> str:
    """Fingerprint a transcription by its partition-relevant content (system
    sizes + per-staff slot_index/instrument), so two files that are the same
    underlying document (e.g. two scans of the same plate) collapse to one
    distinct document rather than being double-counted.
    """
    sig = []
    for si, system in enumerate(_systems_of(result)):
        for staff in system["staves"]:
            sig.append((si, staff.get("slot_index"), staff.get("instrument")))
    return hashlib.md5(json.dumps(sig, sort_keys=True).encode()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="restamp-composed")
    ap.add_argument("--works", type=Path, default=WORKS,
                     help="override works.json path (for the negative-path guard test)")
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()

    if not args.works.is_file():
        print(f"FATAL: no works.json at {args.works}", file=sys.stderr)
        return 2
    works = json.load(args.works.open())
    rows = works.get("rows", [])
    if not rows:
        print("FATAL: works.json carries zero rows", file=sys.stderr)
        return 2

    # Resolve `"staves": "same-as:<row_id>"` references so a twin scan of the
    # same plate is not silently dropped as "no derivable truth" -- it has
    # truth, borrowed. Whether it then collapses to the SAME distinct
    # document is decided later, by content fingerprint, not by this label.
    by_id = {r["row_id"]: r for r in rows}
    resolved_same_as = []
    for row in rows:
        st = row.get("staves")
        if isinstance(st, str) and st.startswith("same-as:"):
            target_id = st.split("same-as:", 1)[1]
            target = by_id.get(target_id)
            if target is not None and isinstance(target.get("staves"), list):
                row = dict(row)
                row["staves"] = target["staves"]
                by_id[row["row_id"]] = row
                resolved_same_as.append((row["row_id"], target_id))
    if resolved_same_as:
        rows = [by_id[r["row_id"]] for r in rows]

    if not FIXTURES.is_dir():
        print(f"FATAL: no fixtures dir at {FIXTURES}", file=sys.stderr)
        return 2

    excluded_single_system = []
    excluded_no_transcription = []
    excluded_no_truth = []
    tested = []

    for row in rows:
        rid = row["row_id"]
        n_sys_declared = row.get("page", {}).get("n_systems")
        if n_sys_declared == 1:
            excluded_single_system.append(rid)
            continue

        f = FIXTURES / f"{rid}.{args.arm}.omr.json"
        if not f.is_file():
            excluded_no_transcription.append(rid)
            continue

        result = json.load(f.open())
        systems = _systems_of(result)
        if len(systems) < 2:
            # declared multi-system but detector found <2 -- still exclude,
            # a single detected system cannot exercise the join either.
            excluded_single_system.append(f"{rid} (declared multi-system, detected {len(systems)})")
            continue
        system_sizes = [len(s["staves"]) for s in systems]

        true_out = _true_groups_from_systems_as_printed(row)
        method = None
        if true_out is not None:
            true_groups, method = true_out
        else:
            true_out2 = _true_groups_uniform_lineup(row, len(systems), system_sizes)
            if true_out2 is None:
                excluded_no_truth.append(rid)
                continue
            true_groups, method = true_out2

        ordinal_groups, ordinal_status = _ordinal_partition(result)
        slot_groups, slot_status = _slot_partition(result)

        entry: dict[str, Any] = {
            "row": rid,
            "n_systems": len(systems),
            "system_sizes": system_sizes,
            "truth_method": method,
            "ordinal_status": ordinal_status,
            "slot_status": slot_status,
            "fingerprint": _content_fingerprint(result),
        }
        if ordinal_groups is not None:
            entry["ordinal_vs_truth"] = _compare(true_groups, ordinal_groups)
        else:
            entry["ordinal_vs_truth"] = None
        if slot_groups is not None:
            entry["slot_vs_truth"] = _compare(true_groups, slot_groups)
        else:
            entry["slot_vs_truth"] = None
        tested.append(entry)

    if not tested:
        print("FATAL: probe tested zero rows (no row had both a stored "
              "transcription and derivable hand-read truth)", file=sys.stderr)
        return 2

    # Dedupe to DISTINCT DOCUMENTS by content fingerprint.
    by_fp: dict[str, list[dict]] = {}
    for e in tested:
        by_fp.setdefault(e["fingerprint"], []).append(e)

    if resolved_same_as:
        print(f"Resolved {len(resolved_same_as)} 'same-as' truth reference(s): {resolved_same_as}")
    print(f"Rows excluded as single-system (join is a no-op): {len(excluded_single_system)}")
    for r in excluded_single_system:
        print(f"    - {r}")
    print(f"Rows excluded, no stored transcription for arm {args.arm!r}: {len(excluded_no_transcription)}")
    print(f"Rows excluded, no derivable hand-read truth: {len(excluded_no_truth)}")
    print()
    print(f"Rows tested: {len(tested)}  ->  distinct documents (by content fingerprint): {len(by_fp)}")
    for fp, group in by_fp.items():
        names = [e["row"] for e in group]
        if len(group) > 1:
            print(f"  fingerprint {fp[:10]}: {names}  <-- SAME document, counted once")

    print()
    header = f"{'row':40s} {'sizes':12s} {'ordinal':9s} {'slot':10s} {'ord=truth':10s} {'slot=truth':10s} {'ord staff%':11s} {'slot staff%':11s}"
    print(header)
    for e in tested:
        ov = e["ordinal_vs_truth"]
        sv = e["slot_vs_truth"]
        ord_eq = "n/a" if ov is None else str(ov["exact_partition_equal"])
        slot_eq = "n/a" if sv is None else str(sv["exact_partition_equal"])
        ord_pct = "n/a" if ov is None else f"{ov['per_staff_agreement']:.3f}"
        slot_pct = "n/a" if sv is None else f"{sv['per_staff_agreement']:.3f}"
        print(f"{e['row']:40s} {str(e['system_sizes']):12s} {e['ordinal_status']:9s} "
              f"{e['slot_status']:10s} {ord_eq:10s} {slot_eq:10s} {ord_pct:11s} {slot_pct:11s}")

    print()
    refusing = [e for e in tested if e["ordinal_status"] == "REFUSED"]
    succeeding = [e for e in tested if e["ordinal_status"] == "succeeded"]
    print(f"Ordinal REFUSES on {len(refusing)} tested row(s); succeeds on {len(succeeding)}.")

    print()
    print("=== THE WHOLE QUESTION: rows where ordinal REFUSES ===")
    if not refusing:
        print("  none tested -- cannot speak to the refusing population at all.")
    for e in refusing:
        sv = e["slot_vs_truth"]
        print(f"  {e['row']}  slot_status={e['slot_status']}")
        if sv is None:
            print("    slot join ALSO abstained -- no partition offered.")
        else:
            print(f"    exact_partition_equal={sv['exact_partition_equal']}  "
                  f"per_staff_agreement={sv['per_staff_agreement']:.3f} "
                  f"({sv['n_staves_correctly_grouped']}/{sv['n_staves']})")
            for m in sv["mismatches"]:
                print(f"    MISMATCH staff {m['staff']}: true groupmates={m['true_group']}  "
                      f"slot groupmates={m['cand_group']}")

    if args.json:
        args.json.write_text(json.dumps({
            "excluded_single_system": excluded_single_system,
            "excluded_no_transcription": excluded_no_transcription,
            "excluded_no_truth": excluded_no_truth,
            "tested": tested,
            "distinct_documents": len(by_fp),
        }, indent=2) + "\n")
        print(f"\nwrote {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
