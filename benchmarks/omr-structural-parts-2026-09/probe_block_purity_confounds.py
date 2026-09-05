"""Is the 22/39 block impurity real, or my own metric's artifact?

`probe_bracket_blocks.py` reports 22 of 39 bracket blocks holding more than one
instrument FAMILY, against the staff-identity audit's "22/22 precise — it never
split a family in two". Before reporting a contradiction, check the metric.

Three candidate confounds, each checked by naming the actual instruments in
every mixed block:

  CONVENTION  A bracket block is an ENGRAVING unit, not a taxonomy. Timpani is
              `percussion` in the lexicon and is bracketed with the brass on
              every classical page. A block holding Horn+Trumpet+Timpani is the
              block doing exactly its job; the family label is too fine.

  LEXICON     `Basso` at the foot of a string block resolves to the Bass VOICE
              — the documented ambiguity in `instruments.py` (candidates are
              Bass voice and Contrabass). A `string+voice` block is a lexicon
              artifact, not a grouping error.

  RECALL      A block holding woodwind+brass+percussion is one boundary NOT
              FOUND, not a boundary drawn wrongly. Under-segmentation shows up
              as impurity under a purity metric, and the audit counted it as
              recall — which is why it reported 22/39 RECALLED and 22/22
              precise from the same data.

    python3 benchmarks/omr-structural-parts-2026-09/probe_block_purity_confounds.py
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent

#: Timpani sits inside the brass bracket on a classical page. This is a
#: statement about ENGRAVING, applied only to decide whether a block is doing
#: its job — never to relabel an instrument.
CONVENTIONAL = {"percussion": "brass"}
#: `Basso` -> Bass voice is the documented lexicon ambiguity; on an orchestral
#: page in a string block it is the contrabass.
VOICE_IN_STRINGS = {"voice": "string"}


def collapse(fam: str | None) -> str | None:
    if fam is None:
        return None
    fam = CONVENTIONAL.get(fam, fam)
    return VOICE_IN_STRINGS.get(fam, fam)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocks", default=str(HERE / "bracket-blocks.json"))
    args = ap.parse_args()
    report = json.loads(Path(args.blocks).read_text())

    misjoined = {"beethoven-sym5-mvt1-984073-p4",
                 "beethoven-sym5-mvt1-575951-p4"}

    print("EVERY MIXED BLOCK, WITH ITS ACTUAL PRINTED STAVES\n")
    raw = Counter()
    coll = Counter()
    for rid in sorted(report):
        rec = report[rid]
        if not rec.get("blocks") or not rec.get("families"):
            continue
        fams, names = rec["families"], rec["printed"]
        for gid, slots in sorted(rec["blocks"].items()):
            seen = {fams[s] for s in slots if s < len(fams) and fams[s]}
            seen_c = {collapse(f) for f in seen}
            if rid not in misjoined:
                raw["pure" if len(seen) <= 1 else "mixed"] += 1
                coll["pure" if len(seen_c) <= 1 else "mixed"] += 1
            if len(seen) > 1:
                members = [f"{names[s]}[{fams[s]}]" for s in slots
                           if s < len(names)]
                verdict = ("CONVENTION/LEXICON — one family once collapsed"
                           if len(seen_c) <= 1 else
                           "GENUINELY MIXED — a boundary was not found")
                tag = "  (MIS-JOINED)" if rid in misjoined else ""
                print(f"{rid}  g{gid}{tag}\n    {', '.join(members)}"
                      f"\n    -> {verdict}\n")

    rt = raw["pure"] + raw["mixed"]
    ct = coll["pure"] + coll["mixed"]
    print(f"purity as first measured     : {raw['pure']}/{rt} "
          f"({raw['pure']/max(1,rt):.3f})")
    print(f"purity, families collapsed   : {coll['pure']}/{ct} "
          f"({coll['pure']/max(1,ct):.3f})")
    print("\nThe residue after collapsing is UNDER-SEGMENTATION — a boundary "
          "the detector\ndid not find — which the audit counted as RECALL, not "
          "as a precision failure.\nThat is why 22/22 precise and 22/39 "
          "recalled came from the same data, and why a\npurity metric is not "
          "the audit's metric.")


if __name__ == "__main__":
    main()
