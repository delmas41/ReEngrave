"""ONE gather, exported TWICE: with the words placed and with them withheld.

⚠️⚠️ THE OBVIOUS BYTE-IDENTITY CONTROL IS VACUOUS AND THE WEDGE JOB NEARLY
SHIPPED ONE. Exporting three committed transcriptions before and after a
change and comparing md5 PASSES, and cannot fail, when `grep -c` for the
element under test is ZERO in all three -- the code under test never ran. So
this prints the element COUNT first and EXITS NON-ZERO on zero, before it
compares anything.

What it asserts, on a real record:

  1. `<words>` is written at all (the positive control, printed first);
  2. with every `<direction>` block that carries a `<words>` child removed,
     the two exports are BYTE-IDENTICAL -- so the emission adds words and
     changes nothing else, not one note, rest, slur, tie or dynamic;
  3. the `<dynamics>` count is UNMOVED, which is the counter-split control:
     `counters["dynamics"] += len(directions)` used to count every entry of
     the list, so a word would have been billed to the dynamic family.

⚠️ THIS IS AN EXPORT ARM AND IS STRUCTURALLY BLIND TO A GATHER CHANGE. It
re-exports ONE saved record, so a quantity that is not in that record cannot
enter -- the mirror of `readjudicate.py`'s blind spot. Only two full
re-gathers answer "did GATHER change what ADJUDICATE sees". The guard below
refuses a record with no `Q.DIRECTION_WORD` row rather than reporting the
clean zero that follows.

    python3 .../probe/reexport_identity.py staged.json
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from tools.omr.staged import export as SX                     # noqa: E402
from tools.omr.staged.record import Q                         # noqa: E402

#: The exact block `_legacy._mxl_direction` writes for a word. Matched rather
#: than parsed so the comparison is over BYTES, which is the claim.
_WORDS_BLOCK = re.compile(
    r'^[ ]*<direction placement="below">\n'
    r"[ ]*<direction-type>\n"
    r"[ ]*<words>.*?</words>\n"
    r"[ ]*</direction-type>\n"
    r"[ ]*</direction>\n",
    re.MULTILINE | re.DOTALL)


def _strip_words(xml: str) -> str:
    return _WORDS_BLOCK.sub("", xml)


def main(path: str) -> int:
    result = json.loads(pathlib.Path(path).read_text())

    rows = [o for o in result["record"].get("observations", [])
            if o.get("quantity") == Q.DIRECTION_WORD]
    if not rows:
        print(f"REFUSED: {path} holds no `Q.DIRECTION_WORD` observation. "
              "This arm re-exports a SAVED record, so a gather that predates "
              "the quantity cannot be measured by it -- re-gather instead of "
              "reading the zero that would follow.")
        return 2

    after, rep_after = SX.to_musicxml(result)
    n_words = after.count("<words>")
    n_dyn_after = after.count("<dynamics>")
    print("=" * 72)
    print(f"POSITIVE CONTROL: {n_words} `<words>` written "
          f"({len(rows)} Q.DIRECTION_WORD rows in the record)")
    print("=" * 72)
    if n_words == 0:
        print("DEAD ARM: no `<words>` reached the file, so a byte-identical "
              "result below would say nothing about the emission.")
        return 2

    # the BEFORE arm: the same record, with the placement inert
    real = SX._place_direction_words
    try:
        SX._place_direction_words = lambda rec, runs: None
        before, rep_before = SX.to_musicxml(result)
    finally:
        SX._place_direction_words = real

    n_dyn_before = before.count("<dynamics>")
    stripped = _strip_words(after)
    identical = stripped == before

    print(f"  words stripped from AFTER == BEFORE : {identical}")
    print(f"  <dynamics>  before {n_dyn_before}  after {n_dyn_after}  "
          f"(must not move)")
    print(f"  notes       before {rep_before['written'].get('notes')}  "
          f"after {rep_after['written'].get('notes')}")
    print(f"  rests       before {rep_before['written'].get('rests')}  "
          f"after {rep_after['written'].get('rests')}")
    print(f"  counter direction_words : "
          f"{rep_after['written'].get('direction_words')}")
    print(f"  balance     : {rep_after['direction_balance']}")

    ok = identical and n_dyn_before == n_dyn_after
    if not ok and not identical:
        # show the first divergence, because "not identical" is not a finding
        b, a = before.splitlines(), stripped.splitlines()
        for i, (lb, la) in enumerate(zip(b, a)):
            if lb != la:
                print(f"\n  FIRST DIVERGENCE at line {i}:\n"
                      f"    before: {lb!r}\n    after : {la!r}")
                break
        else:
            print(f"\n  lengths differ: before {len(b)}, after {len(a)}")
    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(64)
    raise SystemExit(main(sys.argv[1]))
