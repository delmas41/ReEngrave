"""2.90: the bars the exporter NEWLY writes as two voices (a divisi pair kept
apart by `_settle_divisi_pairs`, the bar adding up so it is not held out), with
every head's page box and our value. Feeds `2.90_tiles.py`.

    python3 .../2.90_newly_two_voice.py RECORD.json OUT.json

A bar counts as "newly" if the arm writes it as two voices from the exporter's
own split AND the base (no carried stems) did not write it as two voices.
"""
import json
import sys

sys.path.insert(0, ".")
from tools.omr.staged import export as E  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402

res = load_record(sys.argv[1])
seen = {}
held = {}
real_split = E._voice_split
real_hold = E._bar_holds_out


def split_spy(rec, run, ci, events, why=None):
    w = [] if why is None else why
    out = real_split(rec, run, ci, events, w)
    if out is not None and E._divisi_pairs(events):
        seen[id(events)] = (run, ci, events, out,
                            "exporter_split" if E.DIVISI_FROM_EXPORTER_STEMS in w else "q_voices_split")
    if why is not None and why is not w:
        why[:] = w
    return out


def hold_spy(events, streams, divisions, meter):
    r = real_hold(events, streams, divisions, meter)
    held[id(events)] = r
    return r


E._voice_split = split_spy
E._bar_holds_out = hold_spy
xml, rep = E.to_musicxml(res)

rows = []
for key, (run, ci, events, streams, path) in seen.items():
    is_held = held.get(key) is not None   # held out by the bar sum: not written
    heads = []
    for si, st in enumerate(streams):
        for ev in st:
            for h in ev.get("noteheads") or ():
                heads.append({"voice": si + 1, "pitch": h.get("pitch"),
                              "beats": h["duration_beats"], "type": h["duration_type"],
                              "dots": h["dots"], "dir": h.get("stem_direction"),
                              "bbox_page": h.get("bbox_page"), "glyph": h.get("glyph")})
    rows.append({"page": run.page, "system": run.system, "staff": run.staff,
                 "cell": ci, "heads": heads, "held_out_by_sum": is_held, "path": path})
seen_cells = {}
for r in rows:
    seen_cells[(r["page"], r["system"], r["staff"], r["cell"])] = r
rows = list(seen_cells.values())
print(json.dumps({"bars_kept_as_two_voices": len(rows),
                  "written": sum(1 for r in rows if not r["held_out_by_sum"]),
                  "held_out_by_sum": sum(1 for r in rows if r["held_out_by_sum"]),
                  "by_path": {p: sum(1 for r in rows if r["path"] == p) for p in ("q_voices_split", "exporter_split")}}))
json.dump(rows, open(sys.argv[2], "w"), indent=1, default=str)
