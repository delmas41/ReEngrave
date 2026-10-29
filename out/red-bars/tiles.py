"""tiles.py: 12 blind tiles via lane_report.cut_tiles (10 red bars across the classes + 2 controls that add up). Writes out/red-bars/tiles-1029/{tiles/,key.json}."""
import json, pathlib, random, collections, sys
from tools.omr.staged import lane_report as L
from tools.omr.staged.record_io import load_record

R = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/lane-2.222-one-head/out/lane-report/2.222-gather/%s.record.json"
PAGES = {"litolff": {1, 2, 4, 6, 8, 9, 10, 11, 16}, "brahms": {0, 4, 5, 8, 12, 14, 19, 25}}
RED = [  # (plate, cell key, our class label (key only), what I think the print shows (key only))
 ("litolff", "9/1/9/5", "cut/shifted bar", "cell reaches past the barline: next bar's first note counted"),
 ("litolff", "1/0/0/3", "extra: tempo-mark note", "metronome half note above the staff counted as a head; whole rest then 4 beats"),
 ("litolff", "10/0/7/2", "value: flag missed", "first note an eighth with a flag, written as a quarter"),
 ("litolff", "4/0/8/6", "missing: quarter rest", "quarter rest on the print, nothing written"),
 ("litolff", "16/0/7/12", "missing: heads in a beamed group", "beamed sixteenths merged with the beam; heads not written"),
 ("litolff", "16/1/4/3", "voices: one beam group split in two voices", "one beamed run written as two voices"),
 ("brahms", "4/1/1/2", "value: flag missed", "middle note an eighth with a flag, written as a quarter"),
 ("brahms", "8/0/3/3", "voices: two voices read as one", "two voices each fill the bar"),
 ("brahms", "14/1/4/3", "extra: neighbour staff rest", "rest of the staff above counted in this bar"),
 ("brahms", "8/0/8/12", "value: dot missed", "first note a dotted quarter, written as a quarter"),
]
res = {p: load_record(R % p) for p in PAGES}
cb, ev, redkeys, partial, unread = {}, {}, {}, {}, {}
for p, rs in res.items():
    r = rs["record"] if "record" in rs else rs
    for o in r["observations"]:
        if o["quantity"] == "cell_box" and L.page_of(o["subject"]) in PAGES[p]:
            cb[p + ":" + o["subject"][5:]] = o["value"]
    for v in r["verdicts"]:
        if v["quantity"] == "event" and v["outcome"] == "decided" and L.page_of(v["subject"]) in PAGES[p]:
            ev[p + ":" + v["subject"][5:]] = len(v["value"]["events"])
for p in PAGES:
    rep = json.load(open("out/red-bars/work/%s.new.report.json" % p))
    for b in rep["bars_written_red"]["bars_list"]:
        redkeys[p + ":%d/%d/%d/%d" % (b["page"], b["system"], b["staff"], b["cell"])] = 1
    for b in rep["partial_bars"]["bars"]:
        partial[p + ":%d/%d/%d/%d" % (b["page"], b["system"], b["staff"], b["cell"])] = 1
    for b in rep["unread_empty_bars"]["list"]:
        unread[p + ":%d/%d/%d/%d" % (b["page"], b["system"], b["staff"], b["cell"])] = 1
    held = rep.get("bars_held_out_sum")
rng = random.Random(1029)
ctrl = []
for p, nmin in (("litolff", 3), ("brahms", 3)):
    pool = [k for k, n in ev.items() if k.startswith(p + ":") and n >= nmin and k not in redkeys and k not in partial and k not in unread and k in cb
            and int(k.split(":")[1].split("/")[3]) > 0]
    rng.shuffle(pool)
    ctrl.append((p, pool[0].split(":")[1], "control: adds up", "the exporter's own sum fills the bar (not red, not partial, not unread)"))
items = []
for p, k, cls, note in RED + ctrl:
    x0, y0, x1, y1 = cb[p + ":" + k]
    u = L.PLATES[p]["unit"]
    cy = (y0 + y1) / 2
    pg = int(k.split("/")[0])
    items.append(dict(role=("control" if cls == "control: adds up" else "case"), plate=p, page=pg, box=[x0, cy - 2 * u, x1, cy + 2 * u], cell=k, ours=cls, note=note, red=(cls != "control: adds up"),
                      width_sp=round((x1 - x0) / u, 1)))
rng.shuffle(items)
out = pathlib.Path("out/red-bars/tiles-1029")
out.mkdir(parents=True, exist_ok=True)
L.cut_tiles(items, out)
print(json.dumps([(i["cell"], i["plate"], i["ours"], i["width_sp"]) for i in items], indent=0))
