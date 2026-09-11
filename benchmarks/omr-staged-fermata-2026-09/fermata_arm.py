#!/usr/bin/env python3
"""The fermata arm: REACH first, then what moved, then the additive control.

    python3 benchmarks/omr-staged-fermata-2026-09/fermata_arm.py <staged.json>

⚠️ IT PRINTS REACH BEFORE IT PRINTS ANYTHING ELSE. A change that moves nothing
because it is inert and one that moves nothing because the page holds nothing
to move are the same number, and this project has now reported the second as
the first more than once. Litolff `984073` p1-3 carries 63 fermata glyphs;
Breitkopf Brahms 1 p0-3 carries ZERO, so the same script run there would print
a clean, meaningless line.

⚠️ THE CONTROL IS STRUCTURAL, NOT LINE-BASED, and that is the previous
session's finding rather than a preference. `_mxl_note` emits `<notations>`
only when non-empty, so a note whose ONLY mark is a fermata gains a WRAPPER as
well as the element -- a line strip removes the element, leaves an empty
wrapper, and reports the two files as DIFFERENT outside the family. A control
that reports a defect it was not built to see is how a real regression hides
behind an expected one.

⚠️ AND A `difflib` OVER TWO EXPORTED FILES GOES QUADRATIC -- one ran 50
minutes on ~50k lines and produced nothing. Everything here is a count or a
hash.
"""
from __future__ import annotations

import collections
import hashlib
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from tools.omr.staged import export as SX          # noqa: E402
from tools.omr.staged.record import Q              # noqa: E402

_FERMATA = re.compile(r"^\s*<fermata[^>]*/>\s*$")
_OPEN = re.compile(r"^\s*<notations>\s*$")
_CLOSE = re.compile(r"^\s*</notations>\s*$")


def strip_fermatas(xml: str) -> str:
    """The file with every `<fermata/>` gone -- and every wrapper it alone
    justified gone with it."""
    out, block = [], None
    for line in xml.splitlines():
        if _OPEN.match(line):
            block = [line]
            continue
        if block is not None:
            if _CLOSE.match(line):
                if len(block) > 1:            # something survived inside it
                    out.extend(block + [line])
                block = None
                continue
            if not _FERMATA.match(line):
                block.append(line)
            continue
        if not _FERMATA.match(line):
            out.append(line)
    return "\n".join(out)


def main(path: str) -> int:
    result = json.load(open(path))
    prov = result.get("provenance") or {}
    print(f"record   : {path}")
    print(f"provenance: commit={prov.get('commit')} dirty={prov.get('dirty')}")
    if prov.get("dirty") is not False:
        print("  ⚠️ NOT A CLEAN TREE. Fine for a reach-and-result report;"
              " NOT usable as one arm of an A/B.")

    # ── 1. REACH, by detector CLASS ────────────────────────────────────────
    marks = [o for o in result["record"]["observations"]
             if o["quantity"] == Q.FERMATA_MARK]
    by_class = collections.Counter(str(o["value"]) for o in marks)
    cells = {"/".join(o["subject"].split("/")[:5]) for o in marks}
    print("\n── REACH ──")
    print(f"  fermata glyphs, by CLASS: {dict(by_class)}")
    print(f"  cells holding one       : {len(cells)}")
    if not marks:
        print("  ⚠️ ZERO. Nothing below is a result about this change.")
        return 0
    scores = sorted(o["score"] for o in marks if o.get("score") is not None)
    if scores:
        print(f"  confidence  min {scores[0]:.3f}  med "
              f"{scores[len(scores)//2]:.3f}  max {scores[-1]:.3f}")

    # ── 2. THE VERDICTS ───────────────────────────────────────────────────
    reasons = collections.Counter()
    carriers = collections.Counter()
    for v in result["record"]["verdicts"]:
        if v["quantity"] != Q.FERMATA_OWNER:
            continue
        reasons[(v["outcome"], v["reason"])] += 1
        if v["outcome"] == "decided":
            carriers[(v.get("detail") or {}).get("carrier")] += 1
    print("\n── ADJUDICATE ──")
    for (outcome, reason), n in sorted(reasons.items()):
        print(f"  {outcome:10s} {reason:22s} {n}")
    print(f"  carriers: {dict(carriers)}")
    print("  ⚠️ A carrier that is a REST is the case an articulation rule"
          " structurally cannot reach.")

    # ── 3. THE FILE, AND THE CONTROL ──────────────────────────────────────
    xml, rep = SX.to_musicxml(result)
    print("\n── EXPORT ──")
    print(f"  <fermata> elements  : {xml.count('<fermata')}")
    print(f"  balance             : {json.dumps(rep['fermata_balance'])}")
    print(f"  not written         : {json.dumps(rep['fermatas_not_written'])}")

    # ⚠️ THE ARM: one record exported twice, so no detector jitter enters.
    off = {**result, "record": {
        **result["record"],
        "verdicts": [v for v in result["record"]["verdicts"]
                     if v["quantity"] != Q.FERMATA_OWNER]}}
    xml_off, rep_off = SX.to_musicxml(off)
    a = hashlib.md5(strip_fermatas(xml).encode()).hexdigest()
    b = hashlib.md5(strip_fermatas(xml_off).encode()).hexdigest()
    print("\n── THE ADDITIVE CONTROL ──")
    print(f"  with the fermatas removed, the two files are "
          f"{'IDENTICAL' if a == b else 'DIFFERENT'}  ({a[:12]} / {b[:12]})")
    if a != b:
        # ⚠️ NAME the difference rather than only flagging it.
        la, lb = strip_fermatas(xml).splitlines(), strip_fermatas(xml_off).splitlines()
        print(f"  lines {len(la)} vs {len(lb)}")
        for i, (x, y) in enumerate(zip(la, lb)):
            if x != y:
                print(f"  first at {i}: {x!r} vs {y!r}")
                break
    same = {k: (rep["written"].get(k), rep_off["written"].get(k))
            for k in set(rep["written"]) | set(rep_off["written"])
            if k != "fermatas" and rep["written"].get(k) != rep_off["written"].get(k)}
    print(f"  every OTHER counter moved: {same or 'nothing'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
