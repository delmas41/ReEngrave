"""Pre-registered falsifier for docs/scope-part-correspondence-2026-09-07.md.

THE CLAIM UNDER TEST: `apply_contextual_analysis` already decides part
boundaries (`slot_index`, on every staff) at least as well as the exporter's
own ordinal join (`export._stitch_slots`), so the exporter should read that
decision instead of re-deriving a weaker one. Supporting measurement quoted in
the doc: "3 rows of 3, identical partitions" (n=3, load-bearing).

THE KILL CONDITION (pre-registered, not chosen after seeing data): on any row
where the ordinal join `_stitch_slots` SUCCEEDS, if the slot join
`_stitch_slots_by_slot` would partition the same staves DIFFERENTLY, the
inversion is unsafe as stated. One such row kills it.

This probe calls the REAL functions from `tools.omr.export` — never a
restatement — on every committed/already-built transcription-shaped JSON it
can find, over BOTH the shipped arm and, separately, the poisoned-reference
arm (`OMR_SPAN_REFERENCE_FIT=off`, the flag that once named 149 Brahms staves
an instrument the work has not got).

No pipeline run. Every input here is a file already on disk, in this worktree
(git-tracked) or in the main checkout (gitignored build products this
worktree does not carry — the same escape hatch `probe_correspondence.py`
already uses, documented in CLAUDE.md's OMR-NED section: "a worktree has the
harness and none of the artefacts").

⚠️ Exits non-zero if it reads zero candidate files, finds zero testable rows,
or discovers zero staves carrying a slot_index anywhere — see `main()`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MAIN_DEFAULT = "/Users/seanjohnson/Desktop/ReEngrave"

sys.path.insert(0, str(REPO))

# The real, shipped functions — imported, never restated. A divergence
# between this probe and the exporter is then structurally impossible: we are
# calling the exporter's own code.
from tools.omr.export import (  # noqa: E402
    _stitch_slots,
    _stitch_slots_by_slot,
    _is_fragmented_row,
)


# ─────────────────────────────────────────────────────────────────────────
# Discovery — every JSON file, tracked or gitignored-but-present, that could
# hold a transcribe.py-shaped result with staff-level `slot_index`.
# ─────────────────────────────────────────────────────────────────────────

def _tracked_json_files(root: Path) -> list[Path]:
    out = subprocess.run(["git", "ls-files", "*.json"], cwd=root,
                         capture_output=True, text=True)
    if out.returncode != 0:
        return []
    return [root / line for line in out.stdout.split("\n") if line]


def _all_json_under(root: Path) -> list[Path]:
    return list(root.rglob("*.json"))


def discover(worktree: Path, main: Path) -> list[tuple[str, Path]]:
    """`(relpath, abspath)` for every candidate, deduped by relpath.

    Tracked files are identical in both checkouts at a shared commit, so a
    relpath seen from the worktree wins; a gitignored build product only
    exists under `main` and is added from there. This is the ONLY dedup key —
    two different relpaths are always kept as two rows, even if their content
    turns out identical (that gets reported separately, as a fingerprint
    collision, not silently dropped).
    """
    seen: dict[str, Path] = {}
    order: list[str] = []

    def add(root: Path, files: list[Path]):
        for f in files:
            try:
                rel = str(f.relative_to(root))
            except ValueError:
                continue
            if rel in seen:
                continue
            # Fast pre-filter: only files that mention slot_index (native
            # schema) OR staff_slots (the flattened omr-span-composition
            # harness schema, field name "slot" not "slot_index" — see
            # `reconstruct_native_from_flat`) are worth the json.load.
            try:
                data = f.read_bytes()
                if b'"slot_index"' not in data and b'"staff_slots"' not in data:
                    continue
            except OSError:
                continue
            seen[rel] = f
            order.append(rel)

    add(worktree, _tracked_json_files(worktree))
    if main.is_dir() and main.resolve() != worktree.resolve():
        add(main, [p for p in _all_json_under(main / "benchmarks")])
    return [(rel, seen[rel]) for rel in order]


# ─────────────────────────────────────────────────────────────────────────
# Schema
# ─────────────────────────────────────────────────────────────────────────

def is_native_schema(d: dict) -> bool:
    """True for a real transcribe.py-shaped result: `pages` is a list of
    dicts, each with a `systems` list. (Rejects the flattened `compose.py`
    summary shape, where `pages` is a bare list of page-index ints.)
    """
    pages = d.get("pages")
    if not isinstance(pages, list) or not pages:
        return False
    for p in pages:
        if not isinstance(p, dict):
            return False
        if "systems" not in p:
            return False
    return True


def get_systems(result: dict) -> list[dict]:
    return [s for p in result.get("pages", []) for s in p.get("systems", [])
            if s.get("staves")]


# ─────────────────────────────────────────────────────────────────────────
# The `omr-spans-veto-composition-2026-09/probe/compose.py` harness (used to
# build the OMR_SPAN_REFERENCE_FIT poisoned-arm artefacts) stores a
# FLATTENED summary, not a native transcribe.py result: `pages` is a bare
# list of page-index ints, and per-staff slot assignment lives in
# `contextual.absent_instrument_veto.staff_slots` as flat records
# `{page_index, system_index, staff_index, slot}` (field name "slot", not
# "slot_index" — confirmed by reading `score_brahms.py` in that benchmark).
#
# `_stitch_slots` never reads `staff_index` — it uses LIST ORDER
# (`enumerate(system["staves"])`). So reconstruction must recover list
# order, not just carry the slot values across. Verified against a genuine
# native document from the SAME publisher/work
# (omr-labeling-hollow2-2026-09-breitkopf-brahms1/transcription.json):
# `staff_index` there is PAGE-CUMULATIVE (system 0 = 0..13, system 1 =
# 14..26, not reset per system) but monotonically ascending within each
# system — i.e. sorting a system's records by `staff_index` recovers the
# true list order. This is a load-bearing assumption for this arm only; it
# is stated here rather than silently trusted.
#
# ⚠️ Cannot reconstruct `measures`, so `_is_fragmented_row` is a structural
# no-op on this reconstruction (same caveat noted in FINDINGS.md) — it always
# reads `len([]) == 1 -> False`, i.e. it can only under-refuse, never
# over-refuse.
# ─────────────────────────────────────────────────────────────────────────

def is_flattened_span_schema(d: dict) -> bool:
    pages = d.get("pages")
    if not isinstance(pages, list) or not pages or isinstance(pages[0], dict):
        return False
    return bool(
        d.get("contextual", {}).get("absent_instrument_veto", {}).get("staff_slots"))


def reconstruct_native_from_flat(d: dict) -> dict | None:
    recs = d["contextual"]["absent_instrument_veto"]["staff_slots"]
    if not recs:
        return None
    by_page: dict[int, dict[int, list[dict]]] = {}
    for r in recs:
        p, s, st_idx, slot = (r["page_index"], r["system_index"],
                              r["staff_index"], r.get("slot"))
        by_page.setdefault(p, {}).setdefault(s, []).append(
            {"staff_index": st_idx,
             "slot_index": slot if isinstance(slot, int) and slot >= 0 else -1})
    pages_out = []
    for p in sorted(by_page):
        systems_out = []
        for s in sorted(by_page[p]):
            staves = sorted(by_page[p][s], key=lambda r: r["staff_index"])
            systems_out.append({"system_index": s, "staves": staves})
        pages_out.append({"page_index": p, "systems": systems_out})
    return {"pages": pages_out}


# ─────────────────────────────────────────────────────────────────────────
# Partition comparison, by Python object identity — `_stitch_slots` and
# `_stitch_slots_by_slot` are called on the SAME loaded `result` object, so
# every staff dict is the same object in memory across both calls, and id()
# is a safe, index-free way to ask "is this the same staff".
# ─────────────────────────────────────────────────────────────────────────

def _blocks_by_id(blocks: list[list[dict]]) -> dict[int, int]:
    m: dict[int, int] = {}
    for bi, block in enumerate(blocks):
        for st in block:
            m[id(st)] = bi
    return m


def partitions_agree(ordinal_blocks, slot_blocks):
    """Are these the SAME partition of the same staves (block labels may
    differ, membership may not)? Returns (agree: bool, detail: dict).
    """
    ord_of = _blocks_by_id(ordinal_blocks)
    slt_of = _blocks_by_id(slot_blocks)
    if set(ord_of) != set(slt_of):
        only_ord = len(set(ord_of) - set(slt_of))
        only_slt = len(set(slt_of) - set(ord_of))
        return False, {"reason": "different staff universes",
                       "only_in_ordinal": only_ord, "only_in_slot": only_slt}
    fwd: dict[int, set] = {}
    for k, ob in ord_of.items():
        fwd.setdefault(ob, set()).add(slt_of[k])
    bwd: dict[int, set] = {}
    for k, sb in slt_of.items():
        bwd.setdefault(sb, set()).add(ord_of[k])
    split_ordinal_blocks = {ob: sorted(v) for ob, v in fwd.items() if len(v) > 1}
    merged_slot_blocks = {sb: sorted(v) for sb, v in bwd.items() if len(v) > 1}
    agree = not split_ordinal_blocks and not merged_slot_blocks
    return agree, {"reason": "partitions differ" if not agree else "identical",
                   "ordinal_blocks_that_split_under_slot": split_ordinal_blocks,
                   "slot_blocks_that_merge_ordinal_blocks": merged_slot_blocks}


def diagnose_slot_abstain(systems: list[dict]) -> dict:
    missing = 0
    dup_systems = 0
    frag_systems = 0
    for s in systems:
        staves = s["staves"]
        vals = [st.get("slot_index", -1) for st in staves]
        missing += sum(1 for v in vals if v is None or v < 0)
        if len(set(vals)) != len(vals):
            dup_systems += 1
        if _is_fragmented_row(staves):
            frag_systems += 1
    return {"staves_missing_slot": missing,
           "systems_with_duplicate_slot": dup_systems,
           "fragmented_systems": frag_systems}


# ─────────────────────────────────────────────────────────────────────────
# Per-row classification
# ─────────────────────────────────────────────────────────────────────────

def classify(rel: str, path: Path) -> dict:
    row: dict = {"row": rel}
    try:
        result = json.loads(path.read_text())
    except Exception as e:  # noqa: BLE001
        row["status"] = "unreadable"
        row["error"] = str(e)
        return row

    row["reconstructed"] = False
    if not isinstance(result, dict) or not is_native_schema(result):
        if isinstance(result, dict) and is_flattened_span_schema(result):
            rebuilt = reconstruct_native_from_flat(result)
            if rebuilt is None:
                row["status"] = "flattened_schema_empty"
                return row
            result = rebuilt
            row["reconstructed"] = True
        else:
            row["status"] = "not_native_schema"
            return row

    systems = get_systems(result)
    total_staves = sum(len(s["staves"]) for s in systems)
    n_systems = len(systems)
    row["n_systems"] = n_systems
    row["total_staves"] = total_staves
    has_measures_field = any(
        "measures" in st for s in systems for st in s["staves"][:1])
    row["has_measures_field"] = has_measures_field

    if n_systems == 0:
        row["status"] = "empty_no_systems"
        return row
    if n_systems == 1:
        row["status"] = "single_system_excluded"
        return row

    ordinal = _stitch_slots(result)
    if ordinal is None:
        sizes = sorted({len(s["staves"]) for s in systems})
        row["system_sizes"] = sizes
        if len(sizes) != 1:
            row["status"] = "refused_size_mismatch"
        else:
            row["status"] = "refused_fragmented_row"
        return row

    # Ordinal join SUCCEEDED — this row is a candidate for the falsifier.
    row["ordinal_parts"] = len(ordinal)
    row["cross_check_n_via_first_system_size"] = len(systems[0]["staves"])

    slot = _stitch_slots_by_slot(result)
    if slot is None:
        row["status"] = "ordinal_succeeded_slot_abstained"
        row["abstain_detail"] = diagnose_slot_abstain(systems)
        return row

    slot_blocks, slot_systems = slot
    row["slot_parts"] = len(slot_blocks)
    distinct_slots = {st.get("slot_index") for s in systems for st in s["staves"]}
    row["cross_check_n_via_distinct_slot_values"] = len(distinct_slots)

    agree, detail = partitions_agree(ordinal, slot_blocks)
    row["status"] = "TESTABLE_AGREE" if agree else "TESTABLE_DISAGREE_KILL"
    row["comparison"] = detail

    fp_source = sorted(
        (p_i, s_i, st.get("staff_index"), st.get("slot_index"))
        for p_i, p in enumerate(result.get("pages", []))
        for s_i, s in enumerate(p.get("systems", []))
        for st in s.get("staves", []))
    row["content_fingerprint"] = hashlib.sha1(
        repr(fp_source).encode()).hexdigest()[:12]
    return row


ARM_TAGS = [
    ("fitoff-spans-on", "POISONED: OMR_SPAN_REFERENCE_FIT=off, spans(movement-ref)=on"),
    ("fitrefuse-spans-on", "refuse arm, spans=on"),
    ("fitsearch-spans-on", "shipped default (search), spans=on — in-harness control"),
    ("fitoff-spans-off", "SPAN_REFERENCE_FIT=off, spans=off (pre-2026-09-06 behaviour)"),
    ("fitrefuse-spans-off", "refuse arm, spans=off"),
    ("fitsearch-spans-off", "search arm, spans=off"),
    ("noshape-spans-on", "noshape variant, spans=on"),
    ("noshape-spans-off", "noshape variant, spans=off"),
]


def arm_of(rel: str) -> str | None:
    name = Path(rel).name
    if "omr-span-composition-2026-09" not in rel:
        return None
    for token, _label in ARM_TAGS:
        if token in name:
            return token
    return "unrecognised-span-arm"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--main-root", default=os.environ.get(
        "REENGRAVE_MAIN", MAIN_DEFAULT))
    ap.add_argument("--json-out", type=Path, default=None)
    args = ap.parse_args()

    worktree = REPO
    main_root = Path(args.main_root)

    candidates = discover(worktree, main_root)
    print(f"discovered {len(candidates)} candidate file(s) mentioning "
          f"\"slot_index\" (worktree={worktree}, main={main_root})",
          file=sys.stderr)
    if not candidates:
        print("FATAL: zero candidate files found. Either the substring "
              "pre-filter or the discovery walk is broken — this must not "
              "be read as \"no disagreements\".", file=sys.stderr)
        return 2

    rows = [classify(rel, path) for rel, path in candidates]

    # ── partition the census ────────────────────────────────────────────
    default_rows = [r for r in rows if arm_of(r["row"]) is None]
    span_rows = {tag: [r for r in rows if arm_of(r["row"]) == tag]
                 for tag, _ in ARM_TAGS}

    def summarise(label: str, group: list[dict]) -> dict:
        by_status: dict[str, int] = {}
        for r in group:
            by_status[r.get("status", "?")] = by_status.get(r.get("status", "?"), 0) + 1
        testable = [r for r in group if r["status"].startswith("TESTABLE")]
        kills = [r for r in testable if r["status"] == "TESTABLE_DISAGREE_KILL"]
        staves_tested = sum(r["total_staves"] for r in testable)
        n_cross_ok = sum(
            1 for r in testable
            if r.get("cross_check_n_via_first_system_size") == r.get("ordinal_parts"))
        n_slot_cross_ok = sum(
            1 for r in testable
            if r.get("cross_check_n_via_distinct_slot_values") == r.get("slot_parts"))
        return {
            "label": label,
            "n_files": len(group),
            "by_status": by_status,
            "n_testable": len(testable),
            "n_kills": len(kills),
            "kill_rows": [r["row"] for r in kills],
            "staves_in_testable_rows": staves_tested,
            "cross_check_ordinal_n_matches": f"{n_cross_ok}/{len(testable)}",
            "cross_check_slot_n_matches": f"{n_slot_cross_ok}/{len(testable)}",
        }

    print("\n" + "=" * 78)
    print("PRIMARY CORPUS — every non-span-composition candidate (the default,")
    print("shipped-flags population)")
    print("=" * 78)
    s_default = summarise("primary", default_rows)
    for k, v in s_default.items():
        print(f"  {k}: {v}")

    print("\nPer-row detail (primary corpus):")
    w = max((len(r["row"]) for r in default_rows), default=10)
    for r in sorted(default_rows, key=lambda r: r["row"]):
        extra = ""
        if r["status"].startswith("TESTABLE"):
            extra = (f" ordinal={r['ordinal_parts']} slot={r['slot_parts']} "
                     f"staves={r['total_staves']}")
        elif r["status"] == "refused_size_mismatch":
            extra = f" sizes={r.get('system_sizes')}"
        print(f"  {r['row']:{w}s}  {r['status']:32s}{extra}")

    print("\n" + "=" * 78)
    print("POISONED-REFERENCE ARM(S) — OMR_SPAN_REFERENCE_FIT re-tested")
    print("=" * 78)
    span_summaries = {}
    for tag, label in ARM_TAGS:
        group = span_rows[tag]
        if not group:
            continue
        s = summarise(label, group)
        span_summaries[tag] = s
        print(f"\n--- {label}  ({tag}) ---")
        for k, v in s.items():
            print(f"  {k}: {v}")

    all_kills = [r for r in rows if r["status"] == "TESTABLE_DISAGREE_KILL"]

    print("\n" + "=" * 78)
    print("OVERALL")
    print("=" * 78)
    n_total_testable = sum(1 for r in rows if r["status"].startswith("TESTABLE"))
    print(f"  files discovered: {len(rows)}")
    print(f"  testable rows (ordinal succeeded, slot resolved): {n_total_testable}")
    print(f"  KILLS (disagreement where ordinal succeeded): {len(all_kills)}")
    if all_kills:
        print("  KILL ROWS:")
        for r in all_kills:
            print(f"    {r['row']}: {r['comparison']}")

    staves_with_slot_anywhere = sum(
        1 for r in rows
        for _ in range(1)
        if r.get("total_staves", 0) > 0
    )
    if staves_with_slot_anywhere == 0 or n_total_testable == 0:
        print("\nFATAL: zero testable rows across the whole census. This is "
              "the exact zero-looks-healthy trap — treat as a probe failure, "
              "not as a clean bill of health.", file=sys.stderr)
        return 2

    if args.json_out:
        args.json_out.write_text(json.dumps(
            {"rows": rows, "primary_summary": s_default,
             "span_summaries": span_summaries}, indent=2, default=str))
        print(f"\nwrote {args.json_out}")

    return 1 if all_kills else 0


if __name__ == "__main__":
    raise SystemExit(main())
