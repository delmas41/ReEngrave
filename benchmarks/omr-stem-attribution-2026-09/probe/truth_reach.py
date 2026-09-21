"""Which PRINT-ADJUDICATED head is reachable by an end rule on `_stems_on`?

⚠️⚠️ THIS IS THE QUESTION THE LANE TURNED ON, AND IT IS A REACH QUESTION, NOT
AN ACCURACY ONE. Two print passes exist on this thread and they adjudicated
two DIFFERENT populations:

  * the CROP PASS's 26-head standoff -- heads where the raster attachment
    reader and the shipped BEAM-MATE tier disagree. The beam-mate tier fires
    only where `_stems_on` came back EMPTY, so every one of these heads has no
    overlapping stem at all.
  * the STROKE lane's 6-of-6 DISAGREE stratum -- *"the record's notehead box
    stands part-way along a neighbouring note's stem"*. That is a head WITH an
    overlapping stroke, and it is the population an end rule acts on -- but
    those strokes were found by `OMR_STEM_STROKE`'s column profile, which is
    default OFF and therefore NOT in the shared records.

An end rule on `_stems_on` can only ever REMOVE an attribution; it can never
create one. So it cannot move a head that has no stem. This probe asks, of
each print-adjudicated head, whether the SHIPPED record gives it a stem at
all -- i.e. whether the rule can reach the only truth this thread owns.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reach import collect, overlap  # noqa: E402


def index_heads(stems, heads):
    head_box, head_stems = {}, {}
    for c, hs in heads.items():
        ss = stems.get(c, [])
        for subj, _hid, hb in hs:
            head_box[subj] = hb
            mine = []
            for sid, sb in ss:
                if overlap(sb, hb):
                    hcy = hb[1] + hb[3] / 2.0
                    f = (hcy - sb[1]) / sb[3] if sb[3] > 0 else 0.5
                    mine.append({"stem": sid, "frac": round(f, 4),
                                 "stem_box": [round(x, 1) for x in sb]})
            head_stems[subj] = mine
    return head_box, head_stems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--label", default="")
    ap.add_argument("--standoff", default="")
    ap.add_argument("--stroke-crops", default="")
    ap.add_argument("--stroke-disagree-only", action="store_true")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    stems, heads, _ = collect(args.record)
    head_box, head_stems = index_heads(stems, heads)

    out = {"label": args.label or Path(args.record).name, "populations": {}}

    def describe(name, rows, subject_key="subject"):
        det = []
        for r in rows:
            subj = r[subject_key]
            mine = head_stems.get(subj)
            det.append({**r,
                        "in_record": subj in head_box,
                        "n_overlapping_stems": len(mine) if mine else 0,
                        "fracs": [m["frac"] for m in (mine or [])]})
        out["populations"][name] = {
            "n": len(det),
            "in_record": sum(1 for d in det if d["in_record"]),
            "with_a_stem": sum(1 for d in det if d["n_overlapping_stems"] > 0),
            "with_a_MID_stroke_stem_0.25":
                sum(1 for d in det
                    if any(0.25 < f < 0.75 for f in d["fracs"])),
            "rows": det,
        }

    if args.standoff:
        so = json.load(open(args.standoff))
        describe("crop_pass_standoff_26", [
            {"id": r["id"], "subject": r["subject"],
             "print_says": r.get("print_says"),
             "attachment_says": r.get("attachment_says"),
             "beam_mate_says": r.get("beam_mate_says")}
            for r in so["rows"]])

    if args.stroke_crops:
        sc = json.load(open(args.stroke_crops))
        rows = [r for r in sc["index"]
                if not args.stroke_disagree_only or r["stratum"] == "disagree"]
        describe("stroke_lane_crops", [
            {"i": r["i"], "stratum": r["stratum"], "subject": r["subject"],
             "we_say": r.get("we_say"), "convention": r.get("convention")}
            for r in rows])

    print(json.dumps(
        {k: {kk: vv for kk, vv in v.items() if kk != "rows"}
         for k, v in out["populations"].items()}, indent=2))
    for name, v in out["populations"].items():
        print(f"\n--- {name} ---")
        for d in v["rows"]:
            print(f"  {d.get('id') or d.get('i')} {d['subject']:22s} "
                  f"in_record={str(d['in_record']):5s} "
                  f"stems={d['n_overlapping_stems']} fracs={d['fracs']}")
    if args.out:
        Path(args.out).write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
