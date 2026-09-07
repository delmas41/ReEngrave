"""STEP 3 — does the same logic generalise to the METER, and what offsets exist?

Two questions, one walk of the same corpus.

**1. The meter.** A time signature change involves no transposition, so the
"delta" degenerates to the identity: every staff should print the SAME meter
at the same bar. That is already what `rhythm.drop_uncorroborated_meter_changes`
tests. This measures whether the premise holds on ground truth — and the
comparison worth having is that the meter's agreement rate should be HIGHER
than the key's, because the key has transposition to survive and the meter
does not.

**2. The offsets.** `key_signature_vote.TRANSPOSITION_FIFTHS_OFFSETS` is
`(-3, 0, 1, 2, 3)` — the written-signature offsets a "standard" transposing
instrument prints. That is a hand-written constant. The reference corpus
declares its transpositions in `<transpose>`, so the true distribution is
measurable rather than assumed, and any offset outside that tuple is a staff
the vote's tolerance cannot model.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _refs import encodings                       # noqa: E402  fail-loud
from keys import read_xml_bytes, _strip_ns, _find, _text   # noqa: E402
from probe_delta_mechanism import interval_fifths          # noqa: E402

OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")


def meters_and_offsets(path: str):
    root = ET.fromstring(read_xml_bytes(Path(path)))
    if _strip_ns(root.tag) != "score-partwise":
        return None
    per_part_meter: list[dict[int, str]] = []
    offsets: Counter[int] = Counter()
    for part in root:
        if _strip_ns(part.tag) != "part":
            continue
        stated: dict[int, str] = {}
        measures = [m for m in part if _strip_ns(m.tag) == "measure"]
        for ordinal, measure in enumerate(measures):
            for node in measure:
                if _strip_ns(node.tag) != "attributes":
                    continue
                for child in node:
                    ctag = _strip_ns(child.tag)
                    if ctag == "time":
                        beats = _text(_find(child, "beats"))
                        btype = _text(_find(child, "beat-type"))
                        sym = child.get("symbol") or ""
                        if beats and btype:
                            stated[ordinal] = f"{beats}/{btype}{sym}"
                        elif child.get("senza-misura") is not None:
                            stated[ordinal] = "senza"
                    elif ctag == "transpose":
                        try:
                            dia = int(_text(_find(child, "diatonic")) or 0)
                            chrom = int(_text(_find(child, "chromatic")) or 0)
                        except ValueError:
                            continue
                        offsets[-interval_fifths(dia, chrom)] += 1
        per_part_meter.append(stated)
    return per_part_meter, offsets


def main() -> int:
    files = encodings()
    sys.stderr.write(f"reading {len(files)} encodings\n")
    offsets: Counter[int] = Counter()
    bars = agree = 0
    change_bars = 0
    disagree_examples = []
    parsed = 0
    for i, f in enumerate(files):
        if i % 300 == 0:
            sys.stderr.write(f"  {i}/{len(files)}\n")
        try:
            got = meters_and_offsets(f)
        except Exception as exc:            # noqa: BLE001
            sys.stderr.write(f"  parse failed {f}: {exc}\n")
            continue
        if got is None:
            continue
        parsed += 1
        per_part, offs = got
        offsets.update(offs)
        if len(per_part) < 2:
            continue
        # A meter CHANGE bar: some part states a meter differing from the one
        # it carried. Compare the stated values across parts at that bar.
        carried: list[str | None] = [None] * len(per_part)
        ordinals = sorted({o for p in per_part for o in p})
        for o in ordinals:
            stated_here = {}
            changed = False
            for pi, p in enumerate(per_part):
                if o in p:
                    stated_here[pi] = p[o]
                    if carried[pi] is not None and p[o] != carried[pi]:
                        changed = True
            if changed and len(stated_here) >= 2:
                change_bars += 1
                bars += 1
                vals = set(stated_here.values())
                if len(vals) == 1:
                    agree += 1
                elif len(disagree_examples) < 40:
                    disagree_examples.append(
                        {"file": os.path.basename(f), "ordinal": o,
                         "values": sorted(vals),
                         "counts": dict(Counter(stated_here.values()))})
            for pi, v in stated_here.items():
                carried[pi] = v

    if not parsed:
        sys.stderr.write("FATAL: parsed nothing.\n")
        return 2
    if not bars:
        sys.stderr.write("FATAL: no multi-part meter-change bars found — "
                         "refusing to report a clean zero.\n")
        return 2

    print("=" * 72)
    print(f"parsed {parsed} encodings")
    print()
    print("--- METER: do the parts stating a meter at a CHANGE bar agree?")
    print(f"  meter-change bars with >=2 parts stating: {bars}")
    print(f"  all parts state the SAME meter          : {agree} / {bars} = "
          f"{agree/bars:.4f}")
    print(f"  disagreeing                             : {bars - agree}")
    for d in disagree_examples[:20]:
        print(f"     {d['file'][:52]:52s} ord {d['ordinal']:>5} "
              f"{d['counts']}")
    print()
    print("--- <transpose>-implied written-key OFFSETS, over every declaration")
    known = (-3, 0, 1, 2, 3)
    tot = sum(offsets.values())
    inside = sum(v for k, v in offsets.items() if k in known)
    for k, v in sorted(offsets.items()):
        flag = "" if k in known else "   <- OUTSIDE TRANSPOSITION_FIFTHS_OFFSETS"
        print(f"  offset {k:+3d} : {v:6d}  ({v/tot:.4f}){flag}")
    print(f"  inside the constant: {inside}/{tot} = {inside/tot:.4f}")

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "meter-and-offsets.json"), "w") as fh:
        json.dump({"parsed": parsed, "meter_change_bars": bars,
                   "meter_agree": agree,
                   "meter_disagree_examples": disagree_examples,
                   "offsets": {str(k): v for k, v in sorted(offsets.items())},
                   "offsets_inside_constant": inside,
                   "offsets_total": tot}, fh, indent=1)
    print(f"\nwrote {OUT}/meter-and-offsets.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
