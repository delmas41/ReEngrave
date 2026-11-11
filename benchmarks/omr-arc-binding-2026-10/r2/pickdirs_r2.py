"""arcs-r2: arrange a replay (`replay.sh`: run-LABEL-{hold,dev}/work) so `holdout_runs.py` reads it: per (set, plate) a directory holding the replay's `<plate>.{on,off}.musicxml` and
`<plate>.on.extra.json` and links to the SAVED real gathers' `<plate>.{on,off}.gathered.record.json` (their rows are the boxes / runs; the replay re-adjudicated them).

    python3 pickdirs_r2.py LABEL                  -> prints the PLATE:WORKDIR:pages specs for holdout_runs.py
"""
import os
import pathlib
import sys

O = pathlib.Path("/private/tmp/claude-501/scr-arcs-r2")
S = pathlib.Path("/private/tmp/claude-501/scr-arcs")
PAGES = {("hold", "litolff"): "5,13,15", ("hold", "brahms"): "11,18,20", ("dev", "litolff"): "4", ("dev", "brahms"): "0,4,5"}
label = sys.argv[1]
for (st, plate), pages in PAGES.items():
    d = O / ("pick-%s-%s-%s" % (label, st, plate))
    d.mkdir(exist_ok=True)
    src = O / ("run-%s-%s" % (label, st)) / "work"
    for arm in ("on", "off"):
        for name, base in (("%s.%s.gathered.record.json" % (plate, arm), S / ("run-%s-%s" % (st, plate)) / "work"), ("%s.%s.musicxml" % (plate, arm), src)):
            t = d / name
            if t.is_symlink() or t.exists():
                t.unlink()
            os.symlink(base / name, t)
    t = d / ("%s.on.extra.json" % plate)
    if t.is_symlink() or t.exists():
        t.unlink()
    os.symlink(src / ("%s.on.extra.json" % plate), t)
    print("%s:%s:%s" % (plate, d, pages))
