"""The wedge arm: reach FIRST, then the numbers, on ONE gather.

⚠️⚠️ REACH IS PRINTED BEFORE ANYTHING ELSE, AND IT IS NOT A FORMALITY. The
wedge family has **ZERO** `Q.WEDGE_BOX` rows on Litolff `984073` and 47 on
Breitkopf Brahms 1. Measured on Litolff this arm would print a clean zero
that means NOTHING about the rule, and a change that moves nothing because it
is inert and one that moves nothing because the page holds nothing to move
are the same number. So the reach line comes first and the arm says plainly
when it is dead.

    python3 benchmarks/omr-staged-wedge-2026-09/wedge_arm.py /tmp/wedge/brahms.json
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from tools.omr.staged import export as SX          # noqa: E402
from tools.omr.staged.record import Q             # noqa: E402
from tools.omr.staged.export import Record        # noqa: E402


def main(path: str) -> int:
    result = json.loads(pathlib.Path(path).read_text())
    rec = Record(result)

    rows = rec.obs_of(Q.WEDGE_BOX)
    readers = collections.Counter(str(o.get("reader")) for o in rows)
    with_page = sum(1 for o in rows
                    if (o.get("detail") or {}).get("bbox_page_px"))

    print("=" * 72)
    print(f"REACH: {len(rows)} Q.WEDGE_BOX rows")
    print(f"  by reader     : {dict(readers)}")
    print(f"  with page box : {with_page}  (the rest can only abstain)")
    prov = result.get("provenance") or {}
    print(f"  provenance    : {prov.get('commit', '?')[:8]} "
          f"dirty={prov.get('dirty')}")
    if not rows:
        print("\n⚠️ INSTRUMENT DEAD ON THIS DOCUMENT — the page holds no "
              "hairpin ink at all. Every number below is a property of the "
              "FIXTURE and says nothing whatever about the rule.")
        return 1
    print("=" * 72)

    verdicts = rec.verdicts_of(Q.WEDGE_ANCHOR)
    decided = [v for v in verdicts if v["outcome"] == "decided"]
    by_reason = collections.Counter(
        v["reason"] for v in verdicts if v["outcome"] != "decided")
    print(f"\nDECIDED  : {len(decided)} of {len(verdicts)} verdicts")
    for reason, n in by_reason.most_common():
        print(f"  abstain {reason:24} {n}")

    kinds = collections.Counter(
        (v.get("detail") or {}).get("kind") for v in decided)
    degen = sum(1 for v in decided if (v.get("detail") or {}).get("degenerate"))
    print(f"\n  kinds        : {dict(kinds)}")
    print(f"  under ONE note (start == stop): {degen}")

    xml, report = SX.to_musicxml(result)
    print(f"\nWRITTEN  : {report['written'].get('wedges', 0)} <wedge> pairs")
    print(f"  balance      : {report['wedge_balance']}")
    print(f"  not written  : {report['wedges_not_written']}")
    print(f"  notes        : {report['written'].get('notes', 0)}   "
          f"rests: {report['written'].get('rests', 0)}")

    cov = SX.coverage(result, report["written"])
    row = next(r for r in cov["families"] if r["family"] == "wedge")
    print(f"\nCOVERAGE : {row['status']}  detector_glyphs="
          f"{row['detector_glyphs']} cv_glyphs={row['cv_glyphs']} "
          f"ink_rows={row['ink_rows']}")
    census = cov["status_census"]
    print(f"  census unaccounted: {census['unaccounted']}  "
          f"balanced={census['balanced']}")

    out = pathlib.Path(path).with_suffix(".wedge.musicxml")
    out.write_text(xml)
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
