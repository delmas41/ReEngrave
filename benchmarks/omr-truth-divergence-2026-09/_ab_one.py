"""One contextual pass over a stored reading; prints {staff_index: instrument}.

A separate process because `OMR_ROSTER` is read at call time inside the pass and
the two arms must not share an interpreter — the roster module caches, and an
A/B whose arms share state measures the cache.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))


def main() -> int:
    reading, pdf = Path(sys.argv[1]), Path(sys.argv[2])
    from tools.omr.assist import Assist
    from tools.omr.contextual import apply_contextual_analysis

    result = json.loads(reading.read_text())
    apply_contextual_analysis(result=result, pdf_path=pdf, dpi=600,
                              dossier=None, assist=Assist("none"))
    out = {}
    for pg in result["pages"]:
        for sy in pg["systems"]:
            for st in sy["staves"]:
                out[st.get("staff_index")] = st.get("instrument")
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
