"""Size of the clean-tip question (not a change): heads whose duration the clean-tip rule DECIDES (`stem_tip_reads_no_beam`) and whose stem's tip
has a thick horizontal page stroke (>= 0.4 sp, the beam family) whose near end lies within DX_SP of the tip, horizontally, and within DY_SP of it
vertically -- beam ink the level reader may have missed. Also: stems whose Q.BEAM_STEM_LEVELS reads 0 with such ink at the tip (whatever the duration
did). Usage: cleantip_count.py REC.json [--pages ...]"""
import sys, os, collections
sys.path.insert(0, os.getcwd())
sys.path.insert(0, "benchmarks/page-ledger-2026-11")
import m4a_controls as M
from tools.omr.staged.record_io import load_record

DX_SP, DY_SP = 1.0, 0.75
rec = load_record(sys.argv[1])
pages = {int(x) for x in sys.argv[sys.argv.index("--pages") + 1].split(",")} if "--pages" in sys.argv else None
Q = M.rows_by_quantity(rec)
geo = M.cell_geometry(Q)
V = rec["record"]["verdicts"]
hs = {v["subject"]: v for v in V if v["quantity"] == "head_stem" and v["outcome"] == "decided"}
du = {v["subject"]: v for v in V if v["quantity"] == "duration"}
sd = {v["subject"]: v for v in V if v["quantity"] == "stem_direction" and v["outcome"] == "decided"}
stem = {o["id"]: o for o in Q["stem"]}
lev = {}
for o in Q["beam_stem_levels"]:
    lev[(o.get("detail") or {}).get("stem_row_id")] = o["value"]
hor = collections.defaultdict(list)
for o in Q["page_stroke"]:
    d = o["detail"]
    if o["value"] in ("horizontal", "curve") and (d.get("thickness_spaces") or 0) >= 0.4:
        hor[M.page_of(o["subject"])].append((d["bbox_page_px"], d.get("staff_space_local_px") or 30.0))


def page_box(sid):
    o = stem.get(sid)
    if not o or o["subject"] not in geo:
        return None
    (rx0, ry0, _a, _b), up = geo[o["subject"]]
    x, y, w, h = o["value"][:4]
    return [rx0 + x / up, ry0 + y / up, rx0 + (x + w) / up, ry0 + (y + h) / up]


def ink_at_tip(p, sb, direction):
    tip_y = sb[1] if direction == "up" else sb[3]
    xc = (sb[0] + sb[2]) / 2.0
    for b, sp in hor[p]:
        dx = 0.0 if b[0] <= xc <= b[2] else min(abs(b[0] - xc), abs(b[2] - xc))
        dy = 0.0 if b[1] <= tip_y <= b[3] else min(abs(b[1] - tip_y), abs(b[3] - tip_y))
        if dx <= DX_SP * sp and dy <= DY_SP * sp:
            return True
    return False


n_heads = n_hit = 0
stems_hit = set()
for s, d in du.items():
    p = M.page_of(s)
    if pages and p not in pages:
        continue
    if d["outcome"] != "decided" or d["reason"] != "stem_tip_reads_no_beam":
        continue
    n_heads += 1
    h = hs.get(s)
    dr = sd.get(s)
    sb = page_box(h["value"]) if h else None
    if sb and dr and ink_at_tip(p, sb, dr["value"]):
        n_hit += 1
        stems_hit.add(h["value"])
z = zh = 0
for sid, v in lev.items():
    o = stem.get(sid)
    if not o or v != 0:
        continue
    p = M.page_of(o["subject"])
    if pages and p not in pages:
        continue
    sb = page_box(sid)
    if not sb:
        continue
    z += 1
    if ink_at_tip(p, sb, "up") or ink_at_tip(p, sb, "down"):
        zh += 1
print("heads decided by the clean tip: %d; with beam-family ink within %.1f sp of the tip: %d heads on %d stems" % (n_heads, DX_SP, n_hit, len(stems_hit)))
print("stems whose level reader reads 0: %d; with such ink at either end: %d" % (z, zh))
