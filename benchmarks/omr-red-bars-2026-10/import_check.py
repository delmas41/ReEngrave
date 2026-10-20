"""usage: import_check.py FILE.musicxml -- MusicXML import with music21 (MuseScore is not installed on this box): parts, measures,
notes, rests, irregular measures (music21 `paddingLeft/Right` or a bar whose duration differs from its time signature),
warnings raised. A parse error is printed and the exit code is 1."""
import sys
import time
import warnings

import music21

path = sys.argv[1]
t0 = time.time()
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    try:
        sc = music21.converter.parse(path, forceSource=True)
    except Exception as e:  # noqa: BLE001
        print("IMPORT ERROR", type(e).__name__, str(e)[:300])
        sys.exit(1)
parts = list(sc.parts)
nm = sum(len(p.getElementsByClass("Measure")) for p in parts)
notes = len(sc.recurse().notes)
rests = len(sc.recurse().getElementsByClass("Rest"))
irregular = 0
for p in parts:
    for m in p.getElementsByClass("Measure"):
        ts = m.timeSignature or m.getContextByClass("TimeSignature")
        if ts is not None and abs(float(m.duration.quarterLength) - float(ts.barDuration.quarterLength)) > 1e-6:
            irregular += 1
print("imported ok: parts=%d measures=%d notes=%d rests=%d irregular_measures=%d warnings=%d secs=%.0f"
      % (len(parts), nm, notes, rests, irregular, len(w), time.time() - t0))
for x in w[:5]:
    print("  warn:", str(x.message)[:160])
