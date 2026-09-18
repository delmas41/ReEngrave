"""THE BEAM-MATE TIER'S FIRE SET, re-derived from the record — subject by subject.

The marginal question needs to know WHICH heads the shipped tier serves, not
how many. Re-adjudicating the whole record answers that and takes tens of
minutes (the 2026-09-17 handoff records one such rebuild running past forty
minutes and not finishing), so this replays the tier's own logic over the
record's rows instead.

⚠️ EVERY PIECE OF THE TIER IS IMPORTED FROM THE SHIPPED MODULE -- `_on_beam`,
`_stems_on`, `_project`, `_xywh`, `_xywh_head`. Nothing is re-implemented, so
the only thing this file can get wrong is which ROWS it hands them.

⚠️ AND IT HAS A PUBLISHED NUMBER TO CHECK AGAINST, which is what makes it
admissible: the shipped tier's reach on Litolff Beethoven 5 pp.1-4 is **152**
(commit `1b01f8ec`; `no_stem` 793 -> 641). `--expect 152` fails the run if this
re-derivation does not land on it exactly. That is the same standard the
whole-rest verification pass used -- *the fire set re-derived from the shipped
constants must be identical to the artefact's, subject for subject.*

⚠️ TWO FAITHFULNESS DETAILS, both of which would give a believable wrong
number:
  * `_heads_in` selects on `detail["category"] == "notehead"`, NOT on the
    glyph's SMuFL name. A name test is a different set.
  * the tier does **not** exclude whole notes. The nine whole notes among
    Litolff's 793 abstentions are described in the commit message as not being
    the target; they are not filtered in code, so excluding them here would
    under-count the fire set.

    python3 beam_mate_set.py --record R --label L --out out/L-beammate.json \
        [--expect 152]
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[0] / "omr-ledger-extrapolation-2026-09"))

from recordstream import stream_array                            # noqa: E402
from tools.omr.staged.adjudicators.rhythm import (               # noqa: E402
    _on_beam, _project, _stems_on, _xywh, _xywh_head)


class Row:
    __slots__ = ("value", "id", "detail")

    def __init__(self, value, rid, detail=None):
        self.value, self.id, self.detail = value, rid, (detail or {})


def cell_of(subject: str) -> str:
    """⚠️ The KIND is the FIRST segment, so `rsplit` is wrong: a glyph key
    `glyph/1/0/2/4/1` must become `cell/1/0/2/4`."""
    p = subject.split("/")
    return "cell/" + "/".join(p[1:5]) if len(p) >= 5 else subject


def borrow(head_box, heads, stems, beams):
    """`_direction_from_a_beam_mate`, replayed. Returns a direction or None."""
    on = [b for b in beams if _on_beam(head_box, _xywh(b))]
    if not on:
        return None
    votes, mates = set(), 0
    for b in on:
        bbox = _xywh(b)
        for h in heads:
            other = _xywh_head(h.value)
            if other == head_box or not _on_beam(other, bbox):
                continue
            its = _stems_on(other, stems)
            if not its:
                continue
            answers = {_project(s, heads, other) for s in its}
            if len(answers) != 1:
                continue        # a mate that cannot answer for itself
            votes |= answers
            mates += 1
    if mates == 0 or len(votes) != 1:
        return None
    return votes.pop()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out")
    ap.add_argument("--expect", type=int,
                    help="the shipped tier's published reach; fail if unmet")
    a = ap.parse_args()

    heads_by_cell: dict[str, list] = collections.defaultdict(list)
    stems_by_cell: dict[str, list] = collections.defaultdict(list)
    beams_by_cell: dict[str, list] = collections.defaultdict(list)
    own_box: dict[str, list] = collections.defaultdict(list)
    klass: dict[str, str] = {}
    for o in stream_array(a.record, "observations"):
        q = o.get("quantity")
        if q == "glyph_box":
            r = Row(o.get("value"), o["id"], o.get("detail"))
            own_box[o["subject"]].append(r)
            if (r.detail.get("category") == "notehead"
                    and _xywh_head(r.value) is not None):
                heads_by_cell[cell_of(o["subject"])].append(r)
        elif q == "notehead_class":
            klass[o["subject"]] = str(o.get("value"))
        elif q == "stem":
            r = Row(o.get("value"), o["id"])
            if _xywh(r) is not None:
                stems_by_cell[o["subject"]].append(r)
        elif q == "beam_stroke":
            r = Row(o.get("value"), o["id"])
            if _xywh(r) is not None:
                beams_by_cell[o["subject"]].append(r)
    if not heads_by_cell or not beams_by_cell:
        print("DEAD: no notehead boxes or no beam strokes", file=sys.stderr)
        return 2

    verdict = {}
    for v in stream_array(a.record, "verdicts"):
        if v.get("quantity") == "stem_direction":
            verdict[v["subject"]] = ("DECIDED" if v.get("outcome") == "decided"
                                     else str(v.get("reason")))

    fired, tally = {}, collections.Counter()
    for s, reason in verdict.items():
        if reason != "no_stem":
            continue                  # the tier sits under exactly this branch
        boxes = own_box.get(s) or []
        hb = _xywh_head(boxes[-1].value) if boxes else None
        if hb is None:
            tally["no readable box"] += 1
            continue
        cell = cell_of(s)
        stems = stems_by_cell.get(cell, [])
        if _stems_on(hb, stems):
            # ⚠️ must not happen: the record says `no_stem`, so no stem of
            # this cell may overlap this head. If it does, the replay is not
            # reading the rows the tier read.
            tally["INCONSISTENT: a stem overlaps a `no_stem` head"] += 1
            continue
        d = borrow(hb, heads_by_cell.get(cell, []), stems,
                   beams_by_cell.get(cell, []))
        if d is None:
            tally["stays no_stem"] += 1
        else:
            fired[s] = d
            tally["beam_mate"] += 1
            if "Whole" in klass.get(s, ""):
                tally["  of which WHOLE notes"] += 1

    print(f"{a.label}: {len(verdict)} stem_direction verdicts, "
          f"{sum(1 for r in verdict.values() if r == 'no_stem')} `no_stem`\n")
    for k, n in tally.most_common():
        print(f"   {k:<44} {n:>6}")
    bad = tally["INCONSISTENT: a stem overlaps a `no_stem` head"]
    if bad:
        print(f"\nDEAD: {bad} heads contradict the record -- the replay is not "
              f"reading the rows the tier read.", file=sys.stderr)
        return 2

    if a.out:
        Path(a.out).write_text(json.dumps(
            {"label": a.label, "reach": len(fired), "fired": fired}, indent=1))
        print(f"\nwrote {a.out}")

    if a.expect is not None:
        if len(fired) != a.expect:
            print(f"\nFAILED: re-derived reach {len(fired)} != the shipped "
                  f"tier's published {a.expect}.", file=sys.stderr)
            return 1
        print(f"CONTROL: reproduces the shipped tier's published reach "
              f"({a.expect}) exactly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
