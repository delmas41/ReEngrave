"""The two INDEPENDENT witnesses: Verovio and music21.

Verovio raised `Mismatching measure number 87` on the first cleanup artefact
UNPROMPTED -- nobody was looking for a numbering defect, the renderer simply
said so. It is therefore the one instrument here that was not built by the
person making the change, and a correct fix should silence it.

    python3 benchmarks/omr-measure-numbering-2026-09/probe/witnesses.py FILE

⚠️ Verovio writes its complaints to the C++ log, not to Python's logger, so
they are captured by redirecting the process's own fd 2 -- `contextlib
.redirect_stderr` operates on `sys.stderr` and would return a clean zero here,
which is a dead instrument wearing a pass.
"""
from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path


def verovio_log(path: Path) -> str:
    import verovio
    fd, tmp = tempfile.mkstemp(suffix=".log")
    os.close(fd)
    saved = os.dup(2)
    sink = os.open(tmp, os.O_WRONLY | os.O_TRUNC)
    try:
        os.dup2(sink, 2)
        tk = verovio.toolkit()
        tk.loadFile(str(path))
        tk.renderToSVG(1)
    finally:
        os.dup2(saved, 2)
        os.close(saved)
        os.close(sink)
    text = Path(tmp).read_text(errors="replace")
    os.unlink(tmp)
    return text


def main(argv=None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if not argv:
        print("usage: witnesses.py FILE.musicxml", file=sys.stderr)
        return 2
    path = Path(argv[0])

    log = verovio_log(path)
    mismatches = [ln for ln in log.splitlines()
                  if "ismatching measure" in ln]
    warnings = [ln for ln in log.splitlines()
                if re.search(r"\[Warning\]|\[Error\]", ln)]
    print("=" * 70)
    print("VEROVIO  %s" % path.name)
    print("=" * 70)
    print("  'Mismatching measure number' lines : %d" % len(mismatches))
    for ln in mismatches[:10]:
        print("     " + ln.strip())
    if len(mismatches) > 10:
        print("     ... %d more" % (len(mismatches) - 10))
    print("  total warning/error lines          : %d" % len(warnings))
    for ln in warnings[:6]:
        print("     " + ln.strip())

    print()
    print("=" * 70)
    print("MUSIC21  %s" % path.name)
    print("=" * 70)
    import music21
    score = music21.converter.parse(str(path), format="musicxml")
    parts = list(score.parts)
    print("  parses                 : yes (music21 %s)" % music21.__version__)
    print("  parts                  : %d" % len(parts))
    total = 0
    firsts, lasts = [], []
    for p in parts:
        ms = list(p.getElementsByClass("Measure"))
        total += len(ms)
        if ms:
            firsts.append(ms[0].number)
            lasts.append(ms[-1].number)
    print("  measures               : %d" % total)
    print("  first measure numbers  : %s" % sorted(set(firsts)))
    print("  last  measure numbers  : %s" % sorted(set(lasts)))
    print("  notes                  : %d" % len(score.flatten().notes))
    return 0 if not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())
