#!/usr/bin/env python3
"""Split the OMR_CV_HAIRPINS ON-vs-OFF edit-count movement into two buckets:

  (B) structural non-correspondence  -- 'entire staff insert/delete' and
      'entire measure insert/delete' deltas, which fire regardless of where
      a hairpin is anchored (the row's parts don't line up with the truth's
      parts at all).
  (A) anchor placement -- 'wrong crescendo' / 'wrong diminuendo' deltas on a
      row whose parts DO correspond (so a wedge could in principle be scored
      right or wrong on its own terms).

Reads the two already-scored, already-committed scan-gate result files. Runs
no pipeline code. Fails loudly (non-zero exit) if either file is missing, if
the row sets do not match 1:1 after stripping the on/off suffix, or if a
sanity total does not reconcile.
"""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent
OFF_PATH = BENCH_DIR / "results-scan-arm-hpoff.json"
ON_PATH = BENCH_DIR / "results-scan-arm-hpon.json"

STRUCTURAL_BUCKETS = ["entire staff insert/delete", "entire measure insert/delete"]
ANCHOR_BUCKETS = ["wrong crescendo", "wrong diminuendo"]

# Rows this file independently derives as REFUSED joins (export._stitch_slots
# emitted per-system fragment parts instead of one continuous part per staff).
# Derivation: count <score-part id= in the row's own pred MusicXML and compare
# it to the row's `printed.staves` (staves summed across ALL systems on the
# page) and to that figure divided by `printed.systems` (staves per system).
#   - n_parts_in_xml == staves-per-system  -> ordinal join succeeded (merged)
#   - n_parts_in_xml == staves-summed-across-systems (and >1 system)
#     -> join refused, one fragment part per staff per system, pairs with
#        nothing in a truth built from continuous parts.
# A single-system page can never refuse (there is only one system to disagree
# with itself), so it is never counted as a refusal by this rule even if its
# part count differs from the truth's own roster size for other reasons
# (condensed staves, suppressed tacet parts, etc.) -- that is ordinary
# under/over-count, not the fragmentation failure mode this script isolates.


def _strip_suffix(row_id: str) -> str:
    for suffix in ("-hpon", "-hpoff"):
        if row_id.endswith(suffix):
            return row_id[: -len(suffix)]
    raise ValueError(f"row_id {row_id!r} has neither -hpon nor -hpoff suffix")


def _load(path: Path) -> dict:
    if not path.is_file():
        print(f"FATAL: missing {path}", file=sys.stderr)
        sys.exit(1)
    with path.open() as fh:
        data = json.load(fh)
    rows = data.get("rows")
    if not rows:
        print(f"FATAL: {path} parsed but has no rows", file=sys.stderr)
        sys.exit(1)
    return data


def _parse_xml(xml_path: str) -> ET.Element:
    p = Path(xml_path)
    if not p.is_file():
        print(f"FATAL: xml missing on disk: {xml_path}", file=sys.stderr)
        sys.exit(1)
    try:
        return ET.parse(str(p)).getroot()
    except ET.ParseError as exc:
        print(f"FATAL: {xml_path} did not parse as XML: {exc}", file=sys.stderr)
        sys.exit(1)


def _part_count_in_xml(xml_path: str) -> int:
    root = _parse_xml(xml_path)
    n = len(root.findall(".//score-part"))
    if n == 0:
        print(f"FATAL: 0 <score-part> in {xml_path} -- parser found nothing", file=sys.stderr)
        sys.exit(1)
    return n


def _wedge_count(xml_path: str) -> int:
    root = _parse_xml(xml_path)
    return len(root.findall(".//wedge"))


def _derive_refused(row: dict) -> bool:
    """True iff export._stitch_slots refused the ordinal join on this row."""
    printed = row.get("printed") or {}
    systems = printed.get("systems")
    staves_total = printed.get("staves")
    if systems is None or staves_total is None:
        raise ValueError(f"row {row['row_id']} has no printed.systems/staves")
    if systems < 2:
        return False  # nothing to disagree with itself
    n_parts = _part_count_in_xml(row["pred_xml"])
    # Refusal signature: no merge happened, i.e. the exported part count
    # equals the RAW staff total across all systems rather than staves/system.
    return n_parts == staves_total and staves_total != staves_total // systems


def main() -> int:
    off = _load(OFF_PATH)
    on = _load(ON_PATH)

    off_by_key = {_strip_suffix(r["row_id"]): r for r in off["rows"]}
    on_by_key = {_strip_suffix(r["row_id"]): r for r in on["rows"]}

    if not off_by_key or not on_by_key:
        print("FATAL: empty row map after stripping suffixes", file=sys.stderr)
        return 1

    off_keys = set(off_by_key)
    on_keys = set(on_by_key)
    if off_keys != on_keys:
        print("FATAL: row sets differ between arms", file=sys.stderr)
        print("  only in OFF:", sorted(off_keys - on_keys), file=sys.stderr)
        print("  only in ON: ", sorted(on_keys - off_keys), file=sys.stderr)
        return 1

    keys = sorted(off_keys)
    print(f"{len(keys)} rows matched between arms\n")

    total_delta_ed = 0
    total_structural_delta = 0
    total_anchor_delta = 0
    total_structural_delta_no_brahms_p2 = 0
    total_anchor_delta_no_brahms_p2 = 0

    per_row = []
    refused_derived = []

    for key in keys:
        row_off = off_by_key[key]
        row_on = on_by_key[key]

        cats_off = row_off["omr_ned"]["categories"]
        cats_on = row_on["omr_ned"]["categories"]
        if not cats_off and not cats_on:
            print(f"FATAL: row {key} has empty categories in both arms", file=sys.stderr)
            return 1

        all_buckets = set(cats_off) | set(cats_on)
        row_delta_ed_from_cats = sum(
            cats_on.get(b, 0) - cats_off.get(b, 0) for b in all_buckets
        )
        row_ed_off = row_off["omr_ned"]["omr_ed"]
        row_ed_on = row_on["omr_ned"]["omr_ed"]
        row_ed_delta = row_ed_on - row_ed_off
        if row_delta_ed_from_cats != row_ed_delta:
            print(
                f"FATAL: row {key} category deltas sum to {row_delta_ed_from_cats} "
                f"but omr_ed delta is {row_ed_delta} -- parse is wrong",
                file=sys.stderr,
            )
            return 1

        structural_delta = sum(cats_on.get(b, 0) - cats_off.get(b, 0) for b in STRUCTURAL_BUCKETS)
        anchor_delta = sum(cats_on.get(b, 0) - cats_off.get(b, 0) for b in ANCHOR_BUCKETS)

        refused = _derive_refused(row_off)
        refused_derived.append((key, refused))

        total_delta_ed += row_ed_delta
        total_structural_delta += structural_delta
        total_anchor_delta += anchor_delta
        if "brahms-sym1-mvt1-317803-p2" not in key:
            total_structural_delta_no_brahms_p2 += structural_delta
            total_anchor_delta_no_brahms_p2 += anchor_delta

        truth_wedges = _wedge_count(row_off["truth_xml"])
        off_wedges = _wedge_count(row_off["pred_xml"])
        on_wedges = _wedge_count(row_on["pred_xml"])

        per_row.append(
            {
                "row": key,
                "refused_join": refused,
                "ed_delta": row_ed_delta,
                "structural_delta": structural_delta,
                "anchor_delta": anchor_delta,
                "truth_wedges": truth_wedges,
                "off_pred_wedges": off_wedges,
                "on_pred_wedges": on_wedges,
            }
        )

    pooled_off_ed = off["pooled"]["omr_ed"]
    pooled_on_ed = on["pooled"]["omr_ed"]
    pooled_delta = pooled_on_ed - pooled_off_ed
    if total_delta_ed != pooled_delta:
        print(
            f"FATAL: sum of per-row ed deltas ({total_delta_ed}) != pooled delta "
            f"({pooled_delta}) -- something is double counted or missing",
            file=sys.stderr,
        )
        return 1

    print("Sanity check passed: per-row category deltas reconcile to the pooled")
    print(f"edit-count delta ({pooled_delta:+d} edits, {pooled_off_ed} -> {pooled_on_ed}).\n")

    print("Independently derived join-refusal (fragment-part) rows, from the")
    print("exported MusicXML's own <score-part> count vs printed staff counts:")
    for key, refused in refused_derived:
        if refused:
            print(f"  REFUSED: {key}")
    print()

    hdr = (
        f"{'row':45s} {'refused':>8s} {'ed_delta':>9s} {'structural(B)':>14s} "
        f"{'anchor(A)':>10s} {'wedges truth/off/on':>20s}"
    )
    print(hdr)
    print("-" * len(hdr))
    for r in per_row:
        wedges = f"{r['truth_wedges']}/{r['off_pred_wedges']}/{r['on_pred_wedges']}"
        print(
            f"{r['row']:45s} {str(r['refused_join']):>8s} {r['ed_delta']:>9d} "
            f"{r['structural_delta']:>14d} {r['anchor_delta']:>10d} {wedges:>20s}"
        )

    print()
    print(f"TOTAL structural(B) delta (all 20 rows):      {total_structural_delta:+d}")
    print(f"TOTAL anchor(A) delta (all 20 rows):           {total_anchor_delta:+d}")
    print(f"TOTAL structural(B) delta (Brahms p2 excluded): {total_structural_delta_no_brahms_p2:+d}")
    print(f"TOTAL anchor(A) delta (Brahms p2 excluded):     {total_anchor_delta_no_brahms_p2:+d}")

    # Also break down anchor-bucket movement restricted to rows whose parts
    # actually correspond (not refused), since a refused row's A-bucket delta
    # (if any) cannot mean "wrong anchor" in any recoverable sense.
    anchor_on_corresponding = sum(
        r["anchor_delta"] for r in per_row if not r["refused_join"]
    )
    anchor_on_refused = sum(r["anchor_delta"] for r in per_row if r["refused_join"])
    print()
    print(f"anchor(A) delta on CORRESPONDING rows only:    {anchor_on_corresponding:+d}")
    print(f"anchor(A) delta on REFUSED rows only:          {anchor_on_refused:+d}")

    out_path = BENCH_DIR / "bucket_split_result.json"
    with out_path.open("w") as fh:
        json.dump(
            {
                "pooled_ed_delta": pooled_delta,
                "total_structural_delta": total_structural_delta,
                "total_anchor_delta": total_anchor_delta,
                "total_structural_delta_no_brahms_p2": total_structural_delta_no_brahms_p2,
                "total_anchor_delta_no_brahms_p2": total_anchor_delta_no_brahms_p2,
                "anchor_delta_on_corresponding_rows": anchor_on_corresponding,
                "anchor_delta_on_refused_rows": anchor_on_refused,
                "rows": per_row,
            },
            fh,
            indent=2,
        )
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
