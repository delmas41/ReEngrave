"""DOES `probe_corpus.py` SEE ANYTHING? — the positive control for its zero.

`probe_corpus.py` reports gained 0 / LOST 0 / CHANGED 0 over 1,719 distinct
strings. The LOST and CHANGED zeros are the result; the GAINED zero says the
committed corpora contain none of the strings these repairs fix, which is a
fact about the corpora and not about the repairs.

⚠️⚠️ A ZERO FROM AN INSTRUMENT THAT HAS NEVER REPORTED ANYTHING IS NOT A
RESULT. This injects the widening `instruments.py` REFUSES BY NAME — the `c/e`
fold, priced there at `Fug.`->`Fag.`, `Oh.`->`Ob.` and Mahler's `Veelle.` —
and requires the same comparison to go non-zero. If it does not, the zero
above is measuring the harness.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SRC = ROOT / "tools/omr/instruments.py"
CORPUS = ROOT / "benchmarks/omr-lexicon-2026-09/labels.json"

FIND = '''    "0": "o",
    "y": "v",
})'''
REPL = '''    "0": "o",
    "y": "v",
    "e": "c",
})'''


def resolve() -> dict:
    out = {}
    sys.path.insert(0, str(ROOT))
    for mod in [m for m in list(sys.modules) if m.startswith("tools.omr")]:
        del sys.modules[mod]
    from tools.omr.instruments import lookup
    for row in json.loads(CORPUS.read_text()):
        t = row["text"] if isinstance(row, dict) else str(row)
        if not t or t in out:
            continue
        h = lookup(t)
        out[t] = None if h is None else [h.instrument.name, h.instrument.family]
    return out


def main() -> int:
    snap = SRC.read_bytes()
    try:
        before = resolve()
        assert SRC.read_text(encoding="utf8").count(FIND) == 1, "BAD ANCHOR"
        SRC.write_text(snap.decode().replace(FIND, REPL), encoding="utf8")
        after = resolve()
    finally:
        SRC.write_bytes(snap)
    assert SRC.read_bytes() == snap, "restore failed"

    gained = [t for t in before if before[t] is None and after[t] is not None]
    lost = [t for t in before if before[t] is not None and after[t] is None]
    changed = [t for t in before if before[t] and after[t]
               and before[t] != after[t]]
    print("POSITIVE CONTROL — the refused `c/e` fold, injected")
    print("  strings           %d" % len(before))
    print("  gained            %d  %s" % (len(gained), gained[:6]))
    print("  LOST              %d  %s" % (len(lost), lost[:6]))
    print("  CHANGED           %d  %s"
          % (len(changed), [(t, before[t][0], after[t][0]) for t in changed[:6]]))
    moved = len(gained) + len(lost) + len(changed)
    print()
    if moved == 0:
        print("FAILED: the comparison cannot see a widening this file refuses "
              "BY NAME. Every zero it reports is a measurement of the harness.")
        return 2
    print("OK: the comparison moves on %d strings, so its zero is a result." % moved)
    (HERE / "out" / "positive-control.json").write_text(json.dumps(
        {"gained": gained, "lost": lost,
         "changed": {t: [before[t], after[t]] for t in changed}}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
