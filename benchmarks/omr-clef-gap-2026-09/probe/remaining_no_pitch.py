"""What is LEFT in `no_pitch` after the clef gap is filled, and whose fault it is.

⚠️ ASKED BECAUSE A HEADLINE THAT HALVES IS THE MOMENT TO ASK WHAT THE OTHER
HALF IS. On Litolff the arm takes `no_pitch` 807 -> 552, and reading that as
*"the clef was most of it"* would be exactly the inference CLAUDE.md warns
against: a convincing number is not evidence about its cause. This partitions
the SURVIVING refusals by the state of their staff's clef, so the next lane
gets a population rather than a hunch.

The buckets are exhaustive by construction and the residue is reported:

  clef_abstained        the rule did not reach this staff (expected: 0)
  clef_narrowed         `adjudicate_clef` read it and could not separate two
  clef_decided,
    no_position_row     the detector boxed a head the CV never measured
  clef_decided,
    clef_not_in_anchors `_pitch_from_position` has no anchor for that clef name
  clef_decided,
    pitch_exists        a pitch STANDS and the exporter still refused -- which
                        would be an EXPORT fault, not a reading one
  clef_missing          no clef verdict on the staff at all

    python3 benchmarks/omr-clef-gap-2026-09/probe/remaining_no_pitch.py \\
        --record <replay.py --write-arm dir>/<id>-arm.record.json
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.omr.pitch_resolver import _CLEF_ANCHORS          # noqa: E402
from tools.omr.staged import export                         # noqa: E402
from tools.omr.staged.record_io import load_record          # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--out-json")
    a = ap.parse_args()

    d = load_record(a.record)
    rec = d["record"] if "record" in d else d

    # ⚠️⚠️ THIS COUNTS THE PREMISE OF THE REFUSAL, NOT THE REFUSAL, AND THE
    # TWO ARE COMPARED BEFORE ANYTHING IS READ OFF IT. `_place_notes` files
    # `no_pitch` for a notehead with no standing `Q.PITCH` that reached that
    # test -- and the tests BEFORE it (not-a-notehead, `ink_is_a_whole_rest`)
    # take some heads out first, so this population is a SUPERSET. The
    # exporter's own total is printed beside it; where they differ the
    # difference is the earlier tests and is reported rather than absorbed.
    # A benchmark that kept its own copy of "the three refusals" reported 542
    # where the exporter refused 738 (`omr-notehead-funnel-2026-09`), which is
    # why this says what it is counting instead of claiming to be the same
    # number.
    superseded = {v["supersedes"] for v in rec["verdicts"] if v.get("supersedes")}
    standing = [v for v in rec["verdicts"] if v["id"] not in superseded]
    pitch_of = {v["subject"] for v in standing if v["quantity"] == "pitch"}
    clef_of = {v["subject"]: v for v in standing if v["quantity"] == "clef"}
    owner_of = {v["subject"]: v.get("value") for v in standing
                if v["quantity"] == "glyph_owner"}
    dur_narrowed = {v["subject"] for v in standing
                    if v["quantity"] == "duration" and v["outcome"] == "narrowed"}
    positions = {o["subject"] for o in rec["observations"]
                 if o["quantity"] == "notehead_staff_position"}
    rests = {v["subject"] for v in standing
             if v["quantity"] == "notehead_is_a_whole_rest" and v.get("value")}

    heads = [o["subject"] for o in rec["observations"]
             if o["quantity"] == "notehead_class"]

    buckets: collections.Counter = collections.Counter()
    examples: dict = {}
    for g in heads:
        if g in pitch_of or g in rests:
            continue
        staff = "staff/" + "/".join(g.split("/")[1:4])
        own = owner_of.get(g)
        if own and own != staff:
            buckets["owned_by_another_staff (a different refusal)"] += 1
            continue
        c = clef_of.get(staff)
        if c is None:
            key = "clef_missing"
        elif c["outcome"] == "abstained":
            key = "clef_abstained"
        elif c["outcome"] == "narrowed":
            key = "clef_narrowed"
        elif str(c.get("value")) not in _CLEF_ANCHORS:
            key = f"clef_decided, not in _CLEF_ANCHORS ({c.get('value')})"
        elif g not in positions:
            key = "clef_decided, NO notehead_staff_position row"
        else:
            key = "clef_decided, position row present — UNEXPLAINED"
        buckets[key] += 1
        examples.setdefault(key, []).append(g)

    xml, report = export.to_musicxml({"record": rec})
    out = {
        "record": a.record,
        "exporter_no_pitch_refusals": report["notes_not_written"].get(
            "no_pitch", 0),
        "noteheads_without_a_standing_pitch": sum(buckets.values()),
        "by_cause": dict(buckets.most_common()),
        "examples": {k: v[:5] for k, v in examples.items()},
        "n_duration_narrowed_among_them": len(
            {g for gs in examples.values() for g in gs} & dur_narrowed),
    }
    print(json.dumps(out, indent=2))
    if a.out_json:
        Path(a.out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out_json).write_text(json.dumps(out, indent=1))
        print(f"wrote {a.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
