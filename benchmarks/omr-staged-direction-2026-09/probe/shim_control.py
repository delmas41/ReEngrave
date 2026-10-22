"""⚠️⚠️ THE CONTROL FOR THE ONE THING THIS WIRING COULD SILENTLY DEGRADE.

`gather_direction_words` does not re-implement the reader -- it hands it a
`page_dict` built out of GATHER's cells and detections. So the whole risk is
that the SHIM is not equivalent to the dict `transcribe` builds: a wrong
`bbox_page` convention blanks the wrong rectangle, a missing measure span
attributes a word to the wrong bar, and NEITHER raises. Both failures look
exactly like "this document has few directions", which is also the true
answer, so no count on the staged side alone can tell them apart.

This runs the LEGACY path over the same pages and compares the accepted words.
⚠️ It is an EQUIVALENCE control, not a truth control: agreement means the shim
feeds the reader what `transcribe` feeds it, and says nothing about whether
either is right about the print.

⚠️ Detector jitter is real here and is NOT cancelled -- the two runs each did
their own detection, and a from-scratch rebuild of the hairpin fix reproduced
the categorical result and not the edit count. So a small difference is
expected and a LARGE one is the finding. The text SET is compared as well as
the count, because a matching count with different words would be a coincidence
reported as agreement.

    python3 .../probe/shim_control.py staged.json legacy.json
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from tools.omr.staged.record import Q                         # noqa: E402


def _staged(path: str):
    r = json.loads(pathlib.Path(path).read_text())
    out = collections.Counter()
    for o in r["record"]["observations"]:
        if o["quantity"] == Q.DIRECTION_WORD:
            page = str(o["subject"]).split("/")[1]
            out[(page, str(o["value"]))] += 1
    return out


def _legacy(path: str):
    r = json.loads(pathlib.Path(path).read_text())
    out = collections.Counter()
    for p in r.get("pages", []):
        page = str(p.get("page_index"))
        for s in p.get("systems", []):
            for st in s.get("staves", []):
                for m in st.get("measures", []):
                    for e in m.get("direction_texts", []) or []:
                        out[(page, str(e.get("text")))] += 1
    return out


def main(staged_path: str, legacy_path: str) -> int:
    a, b = _staged(staged_path), _legacy(legacy_path)
    print("=" * 72)
    print(f"STAGED accepted : {sum(a.values())}")
    print(f"LEGACY accepted : {sum(b.values())}")
    print("=" * 72)
    if not a and not b:
        print("DEAD CONTROL: neither path accepted a word, so agreement here "
              "says nothing about the shim.")
        return 2
    keys = sorted(set(a) | set(b))
    print(f"{'page':>5} {'text':<24} {'staged':>7} {'legacy':>7}")
    same = 0
    for k in keys:
        mark = "" if a[k] == b[k] else "   <-- differs"
        same += a[k] == b[k]
        print(f"{k[0]:>5} {k[1]:<24} {a[k]:>7} {b[k]:>7}{mark}")
    print(f"\n{same} of {len(keys)} (page, text) pairs agree exactly")
    only_staged = sorted(set(a) - set(b))
    only_legacy = sorted(set(b) - set(a))
    if only_staged:
        print(f"  only STAGED: {only_staged}")
    if only_legacy:
        print(f"  only LEGACY: {only_legacy}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        raise SystemExit(64)
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
