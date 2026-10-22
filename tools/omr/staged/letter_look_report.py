"""ROADMAP 2.107 -- what the second look at head/rest ink did, read off a record.

    python3 -m tools.omr.staged.letter_look_report REC.json [--json OUT] [--near N]

Counts, from the record alone (no re-gather): the groups the look read
(`read` = spelled, `narrowed` = a library string with an unread letter), the
ones it could not read and WHY (`no_letter_read`, `not_in_library`, skipped
because the detector had already boxed a dynamic), the letters it added, the
head and rest boxes whose ink they explain, and what ADJUDICATE then did with
them (heads refused `on_a_dynamic_letter` by the look, rests refused
`rest_on_a_dynamic_letter`). `--near N` lists the N rejected groups that came
closest (best letter confidence), the near-miss gallery the principles plan
asks every refusal to make possible.

A record made before the look existed has NO such rows, and this says so in one
line instead of reporting zeros as a result.

Reads a record the one way the repo reads one (`record_io.load_record`).
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from typing import Any, Dict, List

from .record import Q, READERS


def report(result: Dict[str, Any], near: int = 10) -> Dict[str, Any]:
    rec = result["record"]
    obs, absts, verdicts = (rec.get("observations", []),
                            rec.get("abstentions", []), rec.get("verdicts", []))
    letters = [o for o in obs if o["quantity"] == Q.GLYPH_BOX
               and o.get("reader") == READERS.LETTER_LOOK]
    covers = [o for o in obs if o["quantity"] == Q.LETTER_LOOK_COVER]
    unread = [a for a in absts if a["quantity"] == Q.GLYPH_BOX
              and a.get("reader") == READERS.LETTER_LOOK]
    by_reason = collections.Counter(a["reason"] for a in unread)
    groups_read = {(o["detail"] or {}).get("group_box_page") and
                   tuple((o["detail"] or {})["group_box_page"]): o["detail"]
                   for o in letters}
    status = collections.Counter(
        ("read" if (d or {}).get("read_as") else "narrowed")
        for d in groups_read.values())
    covered = {o["subject"] for o in covers}
    # a covered head is refused by whichever same-ink rule reaches it first:
    # 2.76's (a letter the detector boxed -- the read letters ARE boxes now) or
    # 2.107's own; either way the ink is a letter's and the head is not a note
    refused_heads = [v for v in verdicts
                     if v["quantity"] == Q.NOTEHEAD_IS_NOT_A_NOTEHEAD
                     and v.get("value") is True and v["subject"] in covered
                     and v.get("reason") == "on_a_dynamic_letter"]
    refused_rests = [v for v in verdicts
                     if v["quantity"] == Q.REST_IS_NOT_A_REST
                     and v.get("reason") == "rest_on_a_dynamic_letter"]
    out: Dict[str, Any] = {
        "ran": bool(letters or covers or unread),
        "groups_read": status.get("read", 0),
        "groups_narrowed": status.get("narrowed", 0),
        "groups_unread_by_reason": dict(by_reason),
        # cost: how many of the unread groups the two-scale probe alone settled
        "unread_at_the_probe": sum(1 for a in unread
                                   if (a.get("detail") or {}).get("probe_only")),
        "letter_boxes_added": len(letters),
        "boxes_covered": len(covers),
        "heads_refused": len(refused_heads),
        "rests_refused": len(refused_rests),
        "read": sorted(
            ({"group_box_page": list(k) if k else None,
              "read_as": d.get("read_as"), "candidates": d.get("candidates"),
              "library_term": d.get("library_term")}
             for k, d in groups_read.items()),
            key=lambda r: (r["group_box_page"] or [0])),
    }
    rejected = [a for a in unread if a["reason"] in ("no_letter_read",
                                                     "not_in_library")]

    def best(a):
        letters_ = (a.get("detail") or {}).get("best_letters") or []
        return letters_[0][1] if letters_ else 0.0
    rejected.sort(key=lambda a: -best(a))
    out["nearest_misses"] = [
        {"cell": a["subject"], **{k: (a.get("detail") or {}).get(k) for k in
         ("group_box_page", "best_letters", "best_note_or_rest",
          "library_tried", "unstable_across_erasures", "seeds")}}
        for a in rejected[:near]]
    return out


def main(argv: List[str] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("record")
    ap.add_argument("--json", default=None)
    ap.add_argument("--near", type=int, default=10)
    args = ap.parse_args(argv)
    from .record_io import load_record
    out = report(load_record(args.record), near=args.near)
    if not out["ran"]:
        print("this record holds no letter-look rows (made before ROADMAP "
              "2.107, or a gather with no detector): nothing to report")
        return 0
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(out, fh, indent=1, default=str)
    print(f"letter look: {out['groups_read']} read, {out['groups_narrowed']} "
          f"narrowed, unread {out['groups_unread_by_reason']} "
          f"({out['unread_at_the_probe']} settled at the probe); "
          f"{out['letter_boxes_added']} letter boxes added; "
          f"{out['boxes_covered']} head/rest boxes covered; refused: "
          f"{out['heads_refused']} heads, {out['rests_refused']} rests")
    for r in out["read"]:
        print(f"  read {r['read_as'] or r['candidates']} at {r['group_box_page']}")
    for m in out["nearest_misses"]:
        print(f"  near miss {m['cell']} {m['group_box_page']} best "
              f"{m['best_letters']} vs {m['best_note_or_rest']} "
              f"tried {m['library_tried']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
