"""The new field must not reach the file.

`staff["label_contradiction"]` is diagnostic metadata on the JSON. Exports the
same transcription twice — once as written, once with every such field deleted —
and compares the MusicXML and the LilyPond byte for byte. A control, not a
result: if it ever fails, the check has started changing the output it exists to
comment on.

    python3 export_is_untouched.py <transcription.json>
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr import export  # noqa: E402


def strip(doc: dict) -> dict:
    out = copy.deepcopy(doc)
    n = 0
    for page in out.get("pages", []):
        for system in page.get("systems", []):
            for staff in system.get("staves", []):
                n += staff.pop("label_contradiction", None) is not None
    out.get("contextual", {}).pop("label_contradiction", None)
    print(f"stripped {n} per-staff field(s) and the summary block")
    return out


def main() -> int:
    doc = json.loads(Path(sys.argv[1]).read_text())
    bare = strip(doc)
    ok = True
    for fmt, fn in (("musicxml", export.to_musicxml),
                    ("lilypond", export.to_lilypond)):
        a = hashlib.sha256(fn(doc).encode()).hexdigest()
        b = hashlib.sha256(fn(bare).encode()).hexdigest()
        print(f"{fmt:10} with={a[:16]} without={b[:16]} "
              f"{'IDENTICAL' if a == b else 'DIFFERENT'}")
        ok &= a == b
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
