"""2.90: what the arm does with Sean's 11 answered 2.89 tiles.

    python3 .../2.90_tile_status.py DOC RECORD.json

For each of the document's tiles: is there a divisi pair in the bar, was it kept
apart (`_settle_divisi_pairs`) or left fused, why, and what the exporter writes.
"""
import sys

sys.path.insert(0, ".")
from tools.omr.staged import export as E  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.voicing import group_chords_in_measure, split_events_into_voices  # noqa: E402

TILES = {  # tile -> (doc, page, system, staff, cell, Sean's answer)
    1: ("litolff", 2, 0, 7, 4, "one voice"), 2: ("litolff", 4, 0, 5, 12, "two voices (unison)"),
    3: ("litolff", 6, 0, 5, 9, "one voice"), 4: ("litolff", 7, 1, 2, 13, "one voice"),
    5: ("litolff", 12, 0, 2, 5, "one voice"), 6: ("litolff", 13, 1, 9, 13, "one voice"),
    7: ("brahms", 0, 0, 11, 5, "two voices"), 8: ("brahms", 0, 0, 13, 1, "one voice"),
    9: ("brahms", 1, 0, 0, 3, "two voices"), 10: ("brahms", 1, 0, 2, 5, "two voices"),
    11: ("brahms", 1, 0, 3, 2, "two voices")}
doc = sys.argv[1]
want = {(p, s, st, c): (n, a) for n, (d, p, s, st, c, a) in TILES.items() if d == doc}
res = load_record(sys.argv[2])
seen = {}
real = E._settle_divisi_pairs


def spy(runs, divisi=None):
    pre = {}
    for run in runs.values():
        for ci, cell in run.cells.items():
            k = (run.page, run.system, run.staff, ci)
            if k in want:
                evs = group_chords_in_measure(cell.detections)
                chords = [e for e in evs if e.get("kind") == "chord"]
                pre[k] = (E._divisi_pairs(evs), len(chords),
                          [e.get("stem_direction") for e in chords],
                          [[(h.get("pitch"), h["duration_beats"], h.get("stem_direction")) for h in e["noteheads"]]
                           for e in chords])
    real(runs, divisi)
    for run in runs.values():
        for ci, cell in run.cells.items():
            k = (run.page, run.system, run.staff, ci)
            if k in pre:
                seen[k] = (pre[k], any(d.get("stem_direction") for d in cell.detections))


E._settle_divisi_pairs = spy
xml, rep = E.to_musicxml(res)
for k, (n, ans) in sorted(want.items(), key=lambda kv: kv[1][0]):
    if k not in seen:
        print(f"tile {n} (Sean: {ans}): bar not in the export's cells")
        continue
    (pairs, nch, dirs, heads), kept = seen[k]
    print(f"tile {n} (Sean: {ans}): pair={bool(pairs)} chords={nch} dirs={dirs} "
          f"-> {('KEPT AS TWO VOICES' if kept else 'left fused') if pairs else 'no divisi pair (stays as 2.89 left it)'}")
    print("     heads:", heads)
