"""2.187b: how many staves does the fixed-order marker filter free from `mixed_marker_kinds` (lane 2.197's census: 13 of 131 Brahms staves on pages 0-3)?
Real gather rows (the 20261020-night slices) -> markers gathered again with / without the measured step -> ADJUDICATE; counts the staff key readings by reason.
usage: marker_order_count_2_187b.py SLICEDIR DOC PAGES"""
import collections, json, os, sys
sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page
from tools.omr.staged import gather as G
from tools.omr.staged.review import rerun as RR
from tools.omr.staged.record import Q

SD, DOC, PAGES = sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3].split(",")]
PDFS = {"litolff": "library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        "brahms": "library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
import collections
class _Det:
    def __init__(s, name, x, y, w, h):
        s.smufl_name, s.x_canonical, s.y_canonical, s.width_canonical, s.height_canonical = name, x, y, w, h
        s.confidence, s.category = 1.0, ""; s.y_center = y + h / 2.0


class _Cell:
    def __init__(s, si, k, pg, bbox, up):
        s.staff_index, s.measure_index, s.page_index, s.bbox_page_px, s.upscale_factor = si, k, pg, bbox, up


class _Staff:
    def __init__(s, si, sy, ly):
        s.staff_index, s.system_index, s.line_ys = si, sy, ly


class _Page:
    def __init__(s, pg, b):
        s.page_index, s.binary = pg, b


class _PWS:
    def __init__(s, page, staves):
        s.page, s.staves = page, staves


def inject(log, obs, binary, pg, dossier, key_object):
    lines, cellbox, boxes = {}, {}, collections.defaultdict(dict)
    for o in obs:
        q, s = o["quantity"], o["subject"].split("/")
        if q == "staff_lines" and s[0] == "staff": lines[(int(s[2]), int(s[3]))] = o["value"]
        elif q == "cell_box" and s[0] == "cell" and len(s) == 5: cellbox[(int(s[2]), int(s[3]), int(s[4]))] = o["value"]
        elif q == "glyph_box" and s[0] == "glyph" and len(s) == 6:
            pb = (o.get("detail") or {}).get("bbox_page_px")
            if isinstance(pb, list) and len(pb) == 4:
                boxes[(int(s[2]), int(s[3]), int(s[4]))][int(s[5])] = (str(o["value"][0]), pb, o["value"])
    staves, local, cells, dets = [], {}, [], {}
    for (sy, li), ly in sorted(lines.items()):
        si = sy * 1000 + li; staves.append(_Staff(si, sy, ly)); local[si] = (sy, li)
    for (sy, li, k), cb in sorted(cellbox.items()):
        si = sy * 1000 + li; b = boxes.get((sy, li, k), {})
        ups = [v[3] / (pb[2] - pb[0]) for _n, pb, v in b.values() if pb[2] > pb[0] and v[3]]
        up = sorted(ups)[len(ups) // 2] if ups else 1.0
        cells.append(_Cell(si, k, pg, cb, up)); lst = []
        for gi in range((max(b) + 1) if b else 0):
            if gi in b:
                nm, pbx, v = b[gi]
                lst.append(_Det(nm, (pbx[0] - cb[0]) * up, (pbx[1] - cb[1]) * up, (pbx[2] - pbx[0]) * up, (pbx[3] - pbx[1]) * up))
            else:
                lst.append(_Det("", -1e9, -1e9, 0, 0))
        dets["cell/%d/%d/%d/%d" % (pg, sy, li, k)] = lst
    pws = _PWS(_Page(pg, binary), staves)
    return log, pws, cells, local, dets




res = {}
for pg in PAGES:
    P = os.path.join(SD, DOC)
    ld = lambda kind: [json.loads(l) for f in (os.path.join(P, "g.%s.jsonl" % kind), os.path.join(P, "p%02d.%s.jsonl" % (pg, kind))) if os.path.exists(f) for l in open(f)]
    obs, ab = ld("observations"), ld("abstentions")
    binary = render_page(PDFS[DOC], pg, dpi=600).binary
    for arm in ("off", "on"):
        os.environ["OMR_KEY_PER_SYSTEM"] = "1" if arm == "on" else "0"
        keep = [o for o in obs if not (arm == "on" and o["quantity"] == "keysig_marker")]
        keepab = [a for a in ab if not (arm == "on" and a["quantity"] == "keysig_marker")]
        rec = {"observations": keep, "abstentions": keepab, "verdicts": []}
        log, _ = RR.rebuild_gather(rec)
        log, pws, cells, local, dets = inject(log, [o for o in obs if (o["subject"] or "").split("/")[1:2] == [str(pg)]], binary, pg, None, False)
        if arm == "on":
            for si, key in sorted(local.items()):
                G._gather_keysig_markers(log, G.R.staff(pg, key[0], key[1]), dets, pg, key, geometry=G._marker_geometry(pws, cells, si))
        RR.run_stages(log)
        vs = log.to_json()["verdicts"]
        last = {}
        for v in vs:
            if v["quantity"] == "key_signature" and v["subject"].startswith("staff/%d/" % pg):
                last[v["subject"]] = v
        for subj, v in last.items():
            res.setdefault(arm, collections.Counter())[(v.get("outcome"), v.get("reason"))] += 1
            res.setdefault(arm + "_staff", {})[subj] = (v.get("outcome"), v.get("reason"), v.get("value"))
        print(DOC, pg, arm, flush=True)
for arm in ("off", "on"):
    print(arm, dict(res.get(arm, {})))
off, on = res.get("off_staff", {}), res.get("on_staff", {})
mixed_off = [s for s, v in off.items() if v[1] and "mixed_marker" in str(v[1])]
print("staves with mixed_marker_kinds OFF:", len(mixed_off), "-> of them now not mixed:", sum(1 for s in mixed_off if not (on.get(s) and "mixed_marker" in str(on[s][1]))))
json.dump({"off": off, "on": on}, open(sys.argv[4] if len(sys.argv) > 4 else "/dev/null", "w"))
