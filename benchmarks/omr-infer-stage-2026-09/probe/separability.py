"""SEPARABILITY — can a consumer ask "was this inferred?" and get an answer?

⚠️ THE PROPERTY THE WHOLE STAGE EXISTS TO KEEP SAYABLE, checked on the real
artefacts rather than on a fixture:

    Everything in the record before EXPORT was READ or ENTAILED.
    Everything after INFER was read, entailed, or INFERRED -- and LABELLED.

It asks three things of each record, and the third is the STAGE BOUNDARY:

  1. how many verdicts carry the `infer:` label;
  2. whether the pipeline's `inference` key is present at all (off means
     ABSENT, not quiet);
  3. **every verdict that supersedes a NARROWED one must be an inference.**
     If any other decider ever collapses a narrowing, the boundary between
     EVALUATE and INFER has moved and nothing else would notice.

    python3 .../probe/separability.py <record.json> [<record.json> ...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.staged import infer                                # noqa: E402


def main() -> int:
    bad_total = 0
    for path in sys.argv[1:]:
        d = json.load(open(path))
        rec = d["record"] if "record" in d else d
        vs = rec["verdicts"]
        by_id = {v["id"]: v for v in vs}
        labelled = [v for v in vs if infer.is_inferred(v)]
        collapses = [v for v in vs
                     if v.get("supersedes")
                     and by_id.get(v["supersedes"], {}).get("outcome")
                     == "narrowed"]
        bad = [v for v in collapses if not infer.is_inferred(v)]
        bad_total += len(bad)
        print(f"{path}")
        print(f"   verdicts .................... {len(vs)}")
        print(f"   labelled `infer:` ........... {len(labelled)}")
        print(f"   supersede a NARROWING ....... {len(collapses)}")
        print(f"   ...of those NOT inferred .... {len(bad)}"
              + ("  ⚠️ THE STAGE BOUNDARY HAS MOVED" if bad else "  ✓"))
        print(f"   top-level `inference` key ... "
              f"{'present' if 'inference' in d else 'ABSENT'}")
    return 1 if bad_total else 0


if __name__ == "__main__":
    raise SystemExit(main())
