"""2.280 r3 step 2, first half: of READ heads that HAVE a stem row, how many have a beam or flag read at that stem, and how was their value decided.
usage: stemchain.py HEADS.jsonl [--pages 1,2]   (population as chain.py: kept, no copies, no whole-rest ink, twins folded)"""
import collections
import json
import sys

rows = [json.loads(l) for l in open(sys.argv[1])]
if "--pages" in sys.argv:
    pg = {int(p) for p in sys.argv[sys.argv.index("--pages") + 1].split(",")}
    rows = [r for r in rows if r["page"] in pg]
sys.argv = [sys.argv[0]]
COPY = ("owned_by_another_staff", "mark_group_duplicate")


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u else 0


def is_wr(r):
    w = r["whole_rest"]
    return r["fate"] == "ink_is_a_whole_rest" or (w and w[0] == "decided" and w[2] == "True")


real = []
for r in sorted([r for r in rows if r["kept"] and r["fate"] not in COPY and not is_wr(r)], key=lambda r: -(r["conf"] or 0)):
    if r["page_box"] and any(o["page"] == r["page"] and iou(o["page_box"], r["page_box"]) >= 0.5 for o in real if o["page_box"]):
        continue
    real.append(r)
withstem = [r for r in real if r["n_stem"] > 0]
print("READ heads %d; with a stem row %d (%.1f%%); no stem row %d" % (len(real), len(withstem), 100.0 * len(withstem) / len(real), len(real) - len(withstem)))


def beamflag(r):
    d = r["d"] or {}
    bfs = r["bfs"] or {}
    tip = (bfs.get("tip") or {}) if isinstance(bfs, dict) else {}
    return ((d.get("beams_by_stem") or 0) > 0 or (d.get("levels_certain") or 0) > 0 or (d.get("flags_attached") or 0) > 0
            or bool(tip.get("stem_beamed")) or (bfs.get("tip_levels") or 0) > 0)


c = collections.Counter()
for r in withstem:
    dv = r["duration"] or [None, None]
    kind = ("beam/flag read at the stem" if beamflag(r) else "no beam/flag read")
    c[(kind, dv[0], dv[1] if dv[0] != "decided" else ("tip clean (no beam)" if dv[1] == "stem_tip_reads_no_beam" else "decided:" + str(dv[1])))] += 1
for k, v in sorted(c.items(), key=lambda kv: -kv[1]):
    print("  %5d  %s | %s | %s" % (v, *k))
