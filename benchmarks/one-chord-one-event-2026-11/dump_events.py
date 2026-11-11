"""2.300 step 1: dump EVERY bar's exporter events (compact) with the meter it is judged against, for the count.
    PYTHONPATH=. python3 benchmarks/one-chord-one-event-2026-11/dump_events.py PLATE PAGES OUT.json
MEASURE ONLY: hooks `_voice_split` / `_bar_holds_out` (wrappers, nothing changes). Flag state is whatever the environment says.
"""
import json
import os
import pathlib
import sys

os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.omr.staged import conservation as C, export as E  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

BARS = {}
LAST = {}
_vs0 = E._voice_split
_bh0 = E._bar_holds_out


PB = {}


def _page_box(rec, glyph):
    if not PB:
        from tools.omr.staged.record import Q
        for o in rec.obs_of(Q.GLYPH_BOX):
            PB[o["subject"]] = [round(v) for v in E._page_box_of(o)]
    return PB.get(glyph)


def _slim_head(n, rec=None):
    return {"glyph": n.get("glyph"), "stem_id": n.get("stem_id"), "page_box": _page_box(rec, n.get("glyph")) if rec else None, "pitch": n.get("pitch"), "bbox": n.get("bbox"), "stem": n.get("stem_direction"),
            "beats": n.get("duration_beats"), "type": n.get("duration_type"), "dots": n.get("dots"),
            "status": n.get("status")}


def _slim(e, rec=None):
    return {"kind": e["kind"], "x": e["x_position"], "beats": e["duration_beats"], "type": e["duration_type"],
            "heads": [_slim_head(n, rec) for n in e.get("noteheads", [])],
            "rest": (e.get("rest") or {}).get("glyph")}


def _vs(rec, run, ci, events, why=None):
    r = _vs0(rec, run, ci, events, why)
    key = (run.page, run.system, run.staff, ci)
    LAST["key"] = key
    BARS[key] = {"events": [_slim(e, rec) for e in events],
                 "streams": None if r is None else [[events.index(e) for e in s] for s in r],
                 "why": list(why or [])}
    return r


def _bh(events, split, divisions, judged, *a, **k):
    out = _bh0(events, split, divisions, judged, *a, **k)
    key = LAST.get("key")
    if key in BARS:
        BARS[key]["judged"] = str(judged)
        BARS[key]["divisions"] = divisions
        BARS[key]["held"] = out is not None
    return out


E._voice_split = _vs
E._bar_holds_out = _bh
plate, pages, out = sys.argv[1], [int(x) for x in sys.argv[2].split(",")], sys.argv[3]
rows = C.load_pages(plate, pages, C.DEFAULT_TAG)
log, _ = RR.rebuild_gather(rows)
RR.run_stages(log)
result = {"record": log.to_json(), "summary": log.summary()}
xml, report = E.to_musicxml(result)
red = {tuple(b[k] for k in ("page", "system", "staff", "cell")) for b in report["bars_written_red"]["bars_list"]}
part = {tuple(b[k] for k in ("page", "system", "staff", "cell")): b for b in report["partial_bars"]["bars"]}
rows_out = []
for k, v in BARS.items():
    v["key"] = list(k)
    v["red"] = k in red
    v["partial"] = k in part
    rows_out.append(v)
json.dump({"plate": plate, "pages": pages, "bars": rows_out,
           "red_bars": report["bars_written_red"]["bars_list"], "partial": list(part.values())},
          open(out, "w"), default=str)
print(plate, pages, "bars", len(rows_out), "red", len(red), "partial", len(part))
