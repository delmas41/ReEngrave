"""Does the file PARSE, semantically — not merely as well-formed XML?

⚠️ `byte_control.py` proves the arms are well-formed XML, because
ElementTree parsed them. That is a weaker claim than it looks: a `<note>` with
a `<duration>` that does not fit its `<voice>`'s timeline is perfectly
well-formed and is still a broken file. This is the control every other staged
export in this repo uses — read it back with music21 and count.

⚠️ It must run under the `.venv-omrned` interpreter: the host is Python 3.9
and music21 needs 3.10+.

    .venv-omrned/bin/python .../probe/m21_parse.py out/export-off.musicxml \
        out/export-on.musicxml
"""
from __future__ import annotations

import sys


def main() -> int:
    from music21 import converter, note as m21note

    for path in sys.argv[1:]:
        s = converter.parse(path)
        notes = len(list(s.recurse().getElementsByClass(m21note.Note)))
        rests = len(list(s.recurse().getElementsByClass(m21note.Rest)))
        chords = len(list(s.recurse().getElementsByClass("Chord")))
        slurs = len(list(s.recurse().getElementsByClass("Slur")))
        print(f"{path}")
        print(f"   parts {len(s.parts)}  Note {notes}  Rest {rests}  "
              f"Chord {chords}  Slur {slurs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
