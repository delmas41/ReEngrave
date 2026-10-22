"""2.167c probe 1: run the shipped export on a record and capture, for every held-by-sum bar, the exporter's own events
(what it summed) plus the voice split it tried. READ-ONLY; no product code changed.
usage: c1_capture.py RECORD OUT.json [slim]"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import export as EX              # noqa: E402
from tools.omr.staged.record_io import load_record, expand_result   # noqa: E402

CAP = {}
o_split, o_hold = EX._voice_split, EX._bar_holds_out
LAST = {}


def split(rec, run, i, events, why=None):
    r = o_split(rec, run, i, events, why)
    LAST.update(run=run, i=i, events=events, split=r, why=list(why or []))
    return r


def hold(events, streams, divisions, meter):
    r = o_hold(events, streams, divisions, meter)
    if r is not None and LAST.get("events") is events:
        run, i = LAST["run"], LAST["i"]
        CAP[(run.page, run.system, run.staff, i)] = dict(
            held=r, why=LAST["why"], events=events, streams=streams,
            condensed=bool(run.condensed_from),
            box=run.cell_boxes.get(i), spacing=run.spacing, top=run.top_line, name=run.name, clef=run.clef)
    return r


o_place = EX._place_notes
PL = {}


def place(rec, runs, **kw):
    PL["rec"] = rec
    PL["fates"] = kw.get("fates")
    return o_place(rec, runs, **kw)


EX._place_notes = place
EX._voice_split, EX._bar_holds_out = split, hold
path, out = sys.argv[1], sys.argv[2]
t = time.time()
if len(sys.argv) > 3 and sys.argv[3] == "slim":
    def _hook(o):
        if "quantity" in o and "outcome" in o:
            o.pop("considered", None)
            o.pop("correlated", None)
        return o
    d = expand_result(json.loads(Path(path).read_text(), object_hook=_hook))
else:
    d = load_record(path)
print("loaded", round(time.time() - t), flush=True)
xml, report = EX.to_musicxml(d)
print("exported", round(time.time() - t), "held", report["bars_held_out_sum"]["bars"], "captured", len(CAP), flush=True)


def slim_head(h):
    keep = {}
    for k, v in h.items():
        try:
            json.dumps(v)
        except Exception:
            v = str(v)
        if k not in ("considered", "correlated"):
            keep[k] = v
    return keep


from tools.omr.staged.record import Q   # noqa: E402
rec, fates = PL["rec"], PL["fates"]
held_cells = set(CAP)
BOXES = {}


def vd(q, sub):
    v = rec.verdict(q, sub)
    if v is None:
        return None
    val = v.get("value")
    if isinstance(val, (list, dict)):
        val = "..."
    return [v["outcome"], v.get("reason"), val]


for o in rec.obs_of(Q.GLYPH_BOX):
    sub = o["subject"]
    p = sub.split("/")
    ck = (int(p[1]), int(p[2]), int(p[3]), int(p[4]))
    if ck not in held_cells:
        continue
    if not rec.obs(Q.NOTEHEAD_CLASS, sub):
        continue
    BOXES.setdefault(ck, []).append({
        "sub": sub, "cls": o["value"][0], "bbox": (o.get("detail") or {}).get("bbox_page_px"),
        "fate": fates.get(sub, "NO_FATE"), "duration": vd(Q.DURATION, sub), "stem_dir": vd(Q.STEM_DIRECTION, sub),
        "owner": vd(Q.GLYPH_OWNER, sub), "not_a_head": vd(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, sub),
        "head_stem": vd(Q.HEAD_STEM, sub), "pitch": vd(Q.PITCH, sub)})
rows = []
for k, c in sorted(CAP.items()):
    sid = {}
    for si, s in enumerate(c["streams"] or []):
        for e in s:
            sid.setdefault(id(e), []).append(si)
    evs = []
    for e in c["events"]:
        row = json.loads(json.dumps({kk: e[kk] for kk in e if kk not in ("noteheads", "rest")}, default=str))
        row["heads"] = [slim_head(h) for h in (e.get("noteheads") or [])]
        row["rest"] = json.loads(json.dumps(e.get("rest"), default=str)) if e.get("rest") else None
        row["units"] = EX._event_units(e, c["held"]["divisions"])
        row["streams"] = sid.get(id(e), [])
        evs.append(row)
    rows.append(dict(page=k[0], system=k[1], staff=k[2], cell=k[3], condensed=c["condensed"], box=c["box"], spacing=c["spacing"], top=c["top"], name=c["name"], clef=c["clef"], held=c["held"],
                     why=c["why"], events=evs, boxes=BOXES.get(k, [])))
json.dump(rows, open(out, "w"))
print("wrote", out, len(rows))
