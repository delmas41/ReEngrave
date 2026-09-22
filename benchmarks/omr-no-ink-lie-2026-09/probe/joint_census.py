#!/usr/bin/env python3
"""For each family that says `no_ink`, what is the reader's OWN situation?

`trace --empty-claims` already establishes that the word is false about the
page (2,377 contradicted on one record). It does NOT say what the honest word
would have been, and the three big populations do not share a cause:

  dynamic_letter   a FAMILY FILTER over a non-empty detection list
  stem             every CANDIDATE refused by a dimension filter
  beam_stroke      a reader whose INPUT IS THE STEM SET

⚠️ The third is the one no report has ever put beside the other two. If a cell
has no stem, `detect_beams` cannot produce a beam whatever the ink does -- so
the claim is not merely about the wrong subject, it is not the beam reader's
claim to make at all.

REACH FIRST: every number here is a population before it is a rate.

⚠️ ONE-SIDED, inherited from `trace.contradicted`: ink being present does not
mean ink of the refusing reader's own KIND is present. What this establishes
is whether the reason word names the reader's own situation.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

# A cell key is `cell/<page>/<system>/<staff>/<cell>`; a glyph key carries the
# same four coordinates after its own kind. Derived here once so two readers
# of this file cannot spell it differently.
def cell_of(key: str):
    parts = key.split("/")
    if len(parts) < 5:
        return None
    if parts[0] == "cell":
        return "cell/" + "/".join(parts[1:5])
    if parts[0] == "glyph":
        return "cell/" + "/".join(parts[1:5])
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", required=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    data = json.loads(Path(args.run).read_text())
    if "record" not in data:
        # ⚠️ RAISES rather than reading an unrecognised envelope as empty --
        # a filter that silently empties a file looks exactly like a file
        # with nothing in it.
        raise KeyError(f"{args.run} has no 'record' key; refusing to guess.")
    rec = data["record"]

    obs_n = collections.defaultdict(collections.Counter)   # cell -> q -> n
    abst = collections.defaultdict(dict)                   # cell -> q -> reason
    cells = set()

    for o in rec["observations"]:
        ck = cell_of(o.get("subject", ""))
        if ck is None:
            continue
        cells.add(ck)
        obs_n[ck][o["quantity"]] += 1
    for a in rec["abstentions"]:
        ck = cell_of(a.get("subject", ""))
        if ck is None:
            continue
        cells.add(ck)
        abst[ck][a["quantity"]] = a.get("reason")

    # POSITIVE CONTROL: the census must see the populations `trace` reports.
    # A join that quietly matches nothing produces a clean, believable zero.
    control = collections.Counter()
    for ck, byq in abst.items():
        for q, reason in byq.items():
            if reason == "no_ink":
                control[q] += 1
    if not control:
        print("DEAD: no `no_ink` abstention reached the join at all.",
              file=sys.stderr)
        return 2

    rows = []
    for q in ("dynamic_letter", "stem", "beam_stroke", "wedge_box"):
        pop = [ck for ck in cells if abst[ck].get(q) == "no_ink"]
        if not pop:
            rows.append({"quantity": q, "no_ink": 0, "dead": True})
            continue
        r = {
            "quantity": q,
            "no_ink": len(pop),
            # the reader's own input, per family
            "with_any_detection": sum(1 for ck in pop if obs_n[ck].get("glyph_box", 0)),
            "with_ink_row": sum(1 for ck in pop if obs_n[ck].get("ink", 0)),
            "with_a_stem": sum(1 for ck in pop if obs_n[ck].get("stem", 0)),
            "with_a_beam": sum(1 for ck in pop if obs_n[ck].get("beam_stroke", 0)),
            "also_stem_no_ink": sum(1 for ck in pop if abst[ck].get("stem") == "no_ink"),
        }
        rows.append(r)

    # The beam question, stated as its own table: a beam reader whose input is
    # the stem set cannot speak where the stem set is empty.
    beams = [ck for ck in cells if abst[ck].get("beam_stroke") == "no_ink"]
    beam_split = collections.Counter()
    for ck in beams:
        n_stems = obs_n[ck].get("stem", 0)
        if n_stems == 0:
            beam_split["no stem at all -- the reader had NO INPUT"] += 1
        elif n_stems == 1:
            beam_split["exactly ONE stem -- a beam needs two"] += 1
        else:
            beam_split[f"{'2+'} stems -- the reader COULD have spoken"] += 1

    out = {
        "cells_seen": len(cells),
        "control_no_ink_by_quantity": dict(control.most_common()),
        "families": rows,
        "beam_stroke_no_ink_by_stem_count": dict(beam_split.most_common()),
    }
    if args.json:
        print(json.dumps(out, indent=2))
        return 0

    print(f"cells joined: {out['cells_seen']}")
    print(f"control (no_ink per quantity): {out['control_no_ink_by_quantity']}\n")
    for r in rows:
        if r.get("dead"):
            print(f"  {r['quantity']:<16} DEAD -- no `no_ink` on this record")
            continue
        print(f"  {r['quantity']:<16} no_ink={r['no_ink']:<5} "
              f"had a detection={r['with_any_detection']:<5} "
              f"had an ink row={r['with_ink_row']:<5} "
              f"had a stem={r['with_a_stem']:<5}")
    print("\nbeam_stroke/no_ink, split by the reader's OWN INPUT (the stem set):")
    for k, n in out["beam_stroke_no_ink_by_stem_count"].items():
        print(f"  {n:6d}  {k}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
