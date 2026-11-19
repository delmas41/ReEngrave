"""ROADMAP 2.322 small test, READ-ONLY. Per page: (2) what the NO-OWNER ink is, by the stroke map's beam roles;
(3) every head box's share of ink held by another kind of claim. Uses claim_readout's own page ledger (build_page, ledger=True) unchanged;
nothing under tools/ is edited. Hooks are monkeypatches in THIS process only.

    OMR_SURYA_KEEP_ALIVE=0 python3 benchmarks/claim-once-gaps-2026-11/gaps_page.py litolff 2,4,6,8,9,10,11,16 OUTDIR [SLICE_TAG]
"""
import collections
import json
import pathlib
import sys

import numpy as np

from tools.omr.staged import beam_strokes as BS
from tools.omr.staged import claim_readout as CR
from tools.omr.staged import cell_map as CM
from tools.omr.staged import gather as G

plate, pages_s, outdir = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3])
tag = sys.argv[4] if len(sys.argv) > 4 else "20261117-night"
pages = [int(p) for p in pages_s.split(",")]
outdir.mkdir(parents=True, exist_ok=True)
SLICES = CR.RECORDS / ("lane-report-slices-%s" % tag) / plate
SYMS = CR.RECORDS / "overnight-20261117-night" / "compare" / "rank" / ("%s.tag-all.symbols.json" % plate)

# ---- hooks: remember each cell's key, rect, label image and meta as build_page feeds the canvas
CAP = []
_state = {"local": None, "last_ck": None}
_orig_local = G._system_local
_orig_grid = G._cell_grid


def _local(staves):
    r = _orig_local(staves)
    _state["local"] = r
    return r


def _grid(c):
    key = _state["local"].get(c.staff_index)
    _state["last_ck"] = (c.page_index, key[0], key[1], c.measure_index) if key is not None else None
    return _orig_grid(c)


G._system_local = _local
G._cell_grid = _grid
_orig_add = CR.LedgerInk.add_cell


def _add(self, rect, labels, claims, erased_staff=None, lines_page=(), meta=None):
    CAP.append({"ck": _state["last_ck"], "rect": [int(v) for v in rect], "lab": labels.copy(), "meta": meta})
    return _orig_add(self, rect, labels, claims, erased_staff, lines_page, meta)


CR.LedgerInk.add_cell = _add

rows_all = CR.read_rows(SLICES, pages)
ed = CR.edition_info(rows_all)
pdf = CR.LIB / ed["edition_path"]
cm_root = CM.ROOT_DEFAULT

written = {}
sym = json.load(open(SYMS))
for h in sym["hosts"]:
    if h.get("kind") == "note" and h.get("rg"):
        written.setdefault(h["rg"], []).append({"type": h.get("type"), "blue": h.get("blue"), "pitch": h.get("pitch")})

LATER = {"accidental", "arc", "hairpin", "dynamic", "mark", "dot", "rest"}     # tiers AFTER heads in stroke_owner.TIERS (rest: whole rests are before)
EARLIER = {"barline", "bracket", "clef", "key", "meter", "word", "tremolo"}      # tiers before heads (word: TIERS[0]; tremolo: a page-wide claim)
KINDS = sorted(LATER | EARLIER)
NAMES = CR.FINE_KINDS


def masknames(m):
    return [k for k in NAMES if int(m) & int(CR.FINE_BIT[k])]


all_none_by_role = collections.Counter()
all_state_by_role = collections.Counter()         # (role, state name) -> px
all_one_owner_by_role = collections.Counter()     # (role, owner kind) -> px, for ST_ONE
none_by_class_role = collections.Counter()
heads = []
comps_all = []

for pg in pages:
    CAP.clear()
    canvas, ver, pws, cells = CR.build_page(rows_all, pdf, pg, cm_root, None, ledger=True)
    ink, state = canvas.ink, canvas.state
    H, W = ink.shape
    prows = {k: [r for r in v if CR.page_of_subject(r.get("subject", "")) in (None, pg)] for k, v in rows_all.items()}
    # --- stroke views per cell -> beam roles
    views = collections.defaultdict(list)
    for o in prows["observations"]:
        if o.get("quantity") != "stroke":
            continue
        p = o["subject"].split("/")
        g = int(p[5])
        if g < CR.STROKE_BASE:
            continue
        d = o.get("detail") or {}
        box = d.get("stroke_box")
        if not box or len(box) < 4:
            continue
        views[CR.cell_key(o["subject"])].append(BS.StrokeView(
            ordinal=g - CR.STROKE_BASE, kind=str(o.get("value")), box=tuple(float(v) for v in box[:4]),
            length=float(d.get("length_spaces") or 0.0), thickness=float(d.get("thickness_spaces") or 0.0),
            sagitta=d.get("sagitta_spaces"), angle=float(d.get("angle_deg") or 0.0),
            touches=tuple((int(a), float(b)) for a, b in (d.get("touches") or ())),
            space_px=float(d.get("staff_space_local_px") or 0.0), row_id=o["id"],
            profile=tuple(int(v) for v in (d.get("profile_sixteenths") or ())),
            ends=tuple(float(v) for v in (d.get("ends") or ())[:4]),
            end_steps=tuple(float(v) for v in (d.get("end_steps_from_top") or ())[:2])))
    roles = {ck: BS.roles(vs, face_join=True, trough=True, one_count=True) for ck, vs in views.items()}
    kinds_of = {ck: {v.ordinal: v.kind for v in vs} for ck, vs in views.items()}

    # --- attribute every ink pixel once to (cell, stroke) in capture order
    attributed = np.zeros((H, W), bool)
    rolemap = np.zeros((H, W), np.uint8)       # 0 no stroke, then ROLE codes
    ROLE_CODES = ["none"] + ["beam", "beam_stub", "beam_doubt", "span_thin", "hook", "hook_or_stub"] + ["other:vertical", "other:horizontal", "other:curve", "other:blob", "other:?"]
    for cap in CAP:
        ck = cap["ck"]
        x0, y0, x1, y1 = cap["rect"]
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        w, h = x1 - x0, y1 - y0
        if w <= 0 or h <= 0 or cap["lab"].max() == 0:
            continue
        lab = CR.sample_to_rect(CR.fill_labels(cap["lab"]), w, h)
        sl = (slice(y0, y1), slice(x0, x1))
        m = ink[sl] & ~attributed[sl] & (lab > 0)
        if not m.any():
            continue
        rl = np.zeros(int(lab.max()) + 1, np.uint8)
        for i in range(1, len(rl)):
            r = roles.get(ck, {}).get(i - 1)
            role = r["role"] if r else "other:?"
            if role == "other":
                role = "other:" + kinds_of.get(ck, {}).get(i - 1, "?")
            rl[i] = ROLE_CODES.index(role) if role in ROLE_CODES else ROLE_CODES.index("other:?")
        sub = rolemap[sl]
        sub[m] = rl[lab[m]]
        attributed[sl][m] = True
    # --- tallies by role
    st_names = CR.ST_NAMES
    for ri, rn in enumerate(ROLE_CODES):
        sel = ink & (rolemap == ri) if ri else ink & ~attributed
        if not sel.any():
            continue
        vals, cnt = np.unique(state[sel], return_counts=True)
        for v, c in zip(vals, cnt):
            all_state_by_role[(rn if ri else "no_stroke_here", st_names[v] if v < len(st_names) else str(v))] += int(c)
        one = sel & (state == CR.ST_ONE)
        if one.any():
            vals, cnt = np.unique(canvas.fam_eff[one], return_counts=True)
            for v, c in zip(vals, cnt):
                k = masknames(v)
                all_one_owner_by_role[(rn if ri else "no_stroke_here", "+".join(k) if k else "?")] += int(c)
        nn = sel & (state == CR.ST_NONE)
        if nn.any():
            vals, cnt = np.unique(canvas.none_class[nn], return_counts=True)
            for v, c in zip(vals, cnt):
                none_by_class_role[(rn if ri else "no_stroke_here", CR.NONE_CLASSES[v - 1] if v else "?")] += int(c)
    none = ink & (state == CR.ST_NONE)
    # --- no-owner components (not beam-role) for crops
    import cv2
    nb = none & ~np.isin(rolemap, [1, 2, 3])
    n, labc, stats, _c = cv2.connectedComponentsWithStats(cv2.dilate(nb.astype(np.uint8), np.ones((3, 3), np.uint8)), connectivity=8)
    for j in range(1, n):
        x, y, w_, h_, a = stats[j]
        px = int((nb & (labc == j)).sum()) if a < 200000 else int(a)
        if px < 60:
            continue
        sel = (labc == j) & nb
        cls = np.bincount(canvas.none_class[sel]).argmax()
        rr = np.bincount(rolemap[sel]).argmax()
        comps_all.append({"page": pg, "box": [int(x), int(y), int(x + w_), int(y + h_)], "px": px,
                          "class": CR.NONE_CLASSES[cls - 1] if cls else "?", "role": ROLE_CODES[rr]})
    np.savez_compressed(outdir / ("%s_p%d.npz" % (plate, pg)), ink=ink, none=none, rolemap=rolemap, state=state)

    # --- head boxes
    verd = collections.defaultdict(list)
    for v in prows["verdicts"] if prows.get("verdicts") else []:
        verd[v["subject"]].append(v)
    notenotes = {}
    for o in prows["observations"]:
        if o.get("quantity") != "glyph_box":
            continue
        cls = str(o["value"][0])
        if not cls.lower().startswith("notehead"):
            continue
        bb = (o.get("detail") or {}).get("bbox_page_px")
        if not bb:
            continue
        sub = o["subject"]
        x0, y0, x1, y1 = (int(round(v)) for v in bb)
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        if x1 <= x0 or y1 <= y0:
            continue
        inb = ink[y0:y1, x0:x1] & (state[y0:y1, x0:x1] != CR.ST_STAFF)
        n_ink = int(inb.sum())
        if n_ink == 0:
            continue
        fe = canvas.fam_eff[y0:y1, x0:x1]
        row = {"page": pg, "subject": sub, "class": cls, "box": [x0, y0, x1, y1], "ink": n_ink, "written": sub in written,
               "written_as": written.get(sub), "score": o.get("score"), "share": {}}
        for k in KINDS:
            s = int((inb & ((fe & CR.FINE_BIT[k]) != 0)).sum())
            if s:
                row["share"][k] = round(s / n_ink, 3)
        row["head_only_px"] = int((inb & (fe == CR.FINE_BIT["notehead"])).sum())
        row["head_any_px"] = int((inb & ((fe & CR.FINE_BIT["notehead"]) != 0)).sum())
        row["none_share"] = round(int((inb & (state[y0:y1, x0:x1] == CR.ST_NONE)).sum()) / n_ink, 3)
        row["stem_beam_share"] = round(int((inb & ((fe & (CR.FINE_BIT["stem"] | CR.FINE_BIT["beam"] | CR.FINE_BIT["flag"])) != 0)).sum()) / n_ink, 3)
        heads.append(row)
    print("page", pg, "done; heads so far", len(heads), flush=True)
    del canvas, pws, cells

json.dump({"plate": plate, "pages": pages, "ROLE_CODES": ROLE_CODES,
           "state_by_role": {"%s|%s" % k: v for k, v in all_state_by_role.items()},
           "one_owner_by_role": {"%s|%s" % k: v for k, v in all_one_owner_by_role.items()},
           "none_by_class_role": {"%s|%s" % k: v for k, v in none_by_class_role.items()}},
          open(outdir / ("%s_roles.json" % plate), "w"), indent=1)
json.dump(heads, open(outdir / ("%s_heads.json" % plate), "w"))
json.dump(comps_all, open(outdir / ("%s_nonebeam_components.json" % plate), "w"))
print("wrote", outdir)
