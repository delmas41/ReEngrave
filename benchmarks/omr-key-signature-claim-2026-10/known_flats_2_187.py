"""2.187 -- the 24 KNOWN key flats written as rests (20 Litolff: key_flats_written_as_rests_litolff.json; 4 Brahms: FINDINGS 2.183 §1),
page by page, three arms, through the REAL gather (key claim, key object) -> ADJUDICATE -> INFER -> EXPORT of each page's slice of the
20261020-night record. Prints, per flat, whether the box is still written as a rest. Not a whole-movement replay.
  base  OMR_KEY_SIGNATURE_CLAIM=0                     (main as recorded)
  c183  OMR_KEY_SIGNATURE_CLAIM=1  OMR_KEY_PER_SYSTEM=0
  c187  OMR_KEY_SIGNATURE_CLAIM=1  OMR_KEY_PER_SYSTEM=1   (dossier admitted: data/dossiers, as the confirmed sheet would)  |  c187nd: dossier silent
usage: known_flats_2_187.py SLICEDIR OUTJSON"""
import collections, glob, json, os, sys
sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page
from tools.omr.staged import gather as G
from tools.omr.staged.record import Q as _Q
from tools.omr.staged.review import rerun as RR

SD, OUT = sys.argv[1], sys.argv[2]
ONLY = {int(x) for x in sys.argv[3].split(',')} if len(sys.argv) > 3 else None
PDFS = {"litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
DOSS = {"litolff": "data/dossiers/beethoven-sym5-mvt1.json", "brahms": "data/dossiers/brahms-sym1-mvt1.json"}
KNOWN = {"litolff": [f["g"] for f in json.load(open("benchmarks/omr-key-signature-claim-2026-10/key_flats_written_as_rests_litolff.json"))],
         "brahms": ["glyph/5/0/1/0/7", "glyph/15/0/0/0/11", "glyph/21/0/9/0/3", "glyph/24/1/4/0/16"]}


class _Det:
    def __init__(s, name, x, y, w, h):
        s.smufl_name, s.x_canonical, s.y_canonical, s.width_canonical, s.height_canonical = name, x, y, w, h
        s.confidence, s.category = 1.0, ""


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
    G.gather_key_signature_claim(log, pws, cells, local, dets)
    if key_object:
        G.gather_key_object(log, pws, cells, local, dets, dossier=dossier)


def live_all(vs, quantity):
    ch = collections.defaultdict(list)
    for v in vs:
        if v["quantity"] == quantity: ch[v["subject"]].append(v)
    return [([x for x in c if x["id"] not in {y.get("supersedes") for y in c}] or c)[-1] for c in ch.values()]


def live(vs, quantity):
    ch = collections.defaultdict(list)
    for v in vs:
        if v["quantity"] == quantity and v["subject"].startswith("glyph/"): ch[v["subject"]].append(v)
    out = {}
    for g, c in ch.items():
        sup = {x.get("supersedes") for x in c if x.get("supersedes")}
        out[g] = ([x for x in c if x["id"] not in sup] or c)[-1]
    return out


res = {}
TAIL = []
for doc in ("litolff", "brahms"):
    dossier = json.load(open(DOSS[doc]))
    pages = sorted({int(g.split("/")[1]) for g in KNOWN[doc]})
    for ex in os.environ.get('EXTRA_PAGES', '').split(';'):
        if ex.startswith(doc + ':'):
            pages = sorted(set(pages) | {int(x) for x in ex.split(':')[1].split(',') if x})
    for pg in pages:
        if ONLY and pg not in ONLY:
            continue
        P = os.path.join(SD, doc)
        ld = lambda kind: [json.loads(l) for f in (os.path.join(P, "g.%s.jsonl" % kind), os.path.join(P, "common.%s.jsonl" % kind), os.path.join(P, "p%02d.%s.jsonl" % (pg, kind))) if os.path.exists(f) for l in open(f)]
        obs, ab = ld("observations"), ld("abstentions")
        binary = render_page(PDFS[doc], pg, dpi=600).binary
        for arm, env in (("base", dict(OMR_KEY_SIGNATURE_CLAIM="0", OMR_KEY_PER_SYSTEM="0")),
                         ("c183", dict(OMR_KEY_SIGNATURE_CLAIM="1", OMR_KEY_PER_SYSTEM="0")),
                         ("c187", dict(OMR_KEY_SIGNATURE_CLAIM="1", OMR_KEY_PER_SYSTEM="1")),
                         ("c187nd", dict(OMR_KEY_SIGNATURE_CLAIM="1", OMR_KEY_PER_SYSTEM="1"))):
            if os.environ.get("ARMS") and arm not in os.environ["ARMS"].split(","):
                continue
            os.environ.update(env)
            os.environ.pop("OMR_METER_OBJECT", None); os.environ.pop("OMR_CLAIMED_REGISTER", None)
            rec = {"observations": obs, "abstentions": ab, "verdicts": []}
            log, _ = RR.rebuild_gather(rec)
            inject(log, [o for o in obs if (o["subject"] or "").split("/")[1:2] == [str(pg)]], binary, pg, dossier if arm != "c187nd" else None,
                   arm.startswith("c187"))
            if os.environ.get("DEBUG_KEY") and arm == "c187":
                from tools.omr.staged.record import Q as _Q, Subject as _S
                for g in KNOWN[doc]:
                    if int(g.split("/")[1]) != pg: continue
                    pp = g.split("/")
                    from tools.omr.staged import record as _R
                    for r in log.rows(_Q.CLAIMED_AREA, _R.staff(int(pp[1]), int(pp[2]), int(pp[3]))):
                        if (r.detail or {}).get("owner") == "key_signature":
                            d = dict(r.detail); d.pop("boxes_inside", None); print("   ", g, r.value, json.dumps(d, default=str)[:400])
                    for a in log._abs.values():
                        if a.quantity == _Q.CLAIMED_AREA and a.subject.to_key().startswith("staff/%s/%s/" % (pp[1], pp[2])) and (a.detail or {}).get("owner") == "key_signature":
                            print("    ABST", a.subject.to_key(), a.reason, json.dumps(a.detail, default=str)[:300])
            RR.run_stages(log)
            LJ = log.to_json()
            vs = LJ["verdicts"]
            if os.environ.get("SIZE"):
                print("SIZE", doc, pg, arm, "verdict basis bytes", sum(len(json.dumps(v.get("basis"))) for v in vs), "verdicts", len(vs), flush=True)
            if arm == "c187" and os.environ.get("DUMP_TAIL"):
                clefs = {v["subject"]: v["value"] for v in live_all(vs, "clef")}
                glyph_v = {}
                for qn in ("rest_is_not_a_rest", "notehead_is_not_a_notehead"):
                    for g, v in live(vs, qn).items():
                        glyph_v.setdefault(g, {})[qn] = {"outcome": v.get("outcome"), "reason": v.get("reason"), "value": v.get("value")}
                from tools.omr.staged import adjudicate as _A
                from tools.omr.staged.adjudicators import header as _H
                from tools.omr.staged.record import Subject as _S
                _spec = _A.REGISTRY[_Q.REST_IS_NOT_A_REST]
                _ctx = {}
                for o in LJ["observations"]:
                    dd = o.get("detail") or {}
                    if o["quantity"] == "claimed_area" and dd.get("source") == "system_key_object":
                        if o["subject"] not in _ctx:
                            try:
                                _ko = dd.get("key_object") or {}
                                _ctx[o["subject"]] = _H.key_tail_context(_A.Evidence(log, _S.from_key(o["subject"]), _spec), system_count=_ko.get("system_count"),
                                                                          read_shapes=[(q or {}).get("shape") for q in _ko.get("read_pieces") or ()])
                            except Exception as ex:   # a context that cannot be read is a finding, not a crash
                                _ctx[o["subject"]] = {"error": repr(ex)}
                for o in LJ["observations"]:
                    dd = o.get("detail") or {}
                    if o["quantity"] == "claimed_area" and dd.get("source") == "system_key_object":
                        bi = dd.get("boxes_inside") or {}
                        TAIL.append({"doc": doc, "page": pg, "staff": o["subject"], "part": dd.get("part"), "standing": dd.get("standing"),
                                     "clef": clefs.get(o["subject"]), "ctx": _ctx.get(o["subject"]), "ko": dd.get("key_object"), "tail_info": dd.get("tail_info"),
                                     "area": o["value"], "boxes": {g: dict(e, verdicts=glyph_v.get(g)) for g, e in bi.items()}})
            rn, dur = live(vs, "rest_is_not_a_rest"), live(vs, "duration")
            for g in KNOWN[doc]:
                if int(g.split("/")[1]) != pg: continue
                r, d = rn.get(g), dur.get(g)
                dv = (d["value"] if d and isinstance(d["value"], dict) else {}) if d else {}
                res.setdefault(g, {})[arm] = dict(refused=bool(r and r["value"] is True), reason=(r or {}).get("reason"),
                                                  outcome=(r or {}).get("outcome"), written_as_rest=bool(dv.get("is_rest")),
                                                  dur_outcome=(d or {}).get("outcome"),
                                                  claimed=((r or {}).get("detail") or {}).get("claimed_by"))
            print(doc, pg, arm, flush=True)
json.dump(res, open(OUT, "w"), indent=1)
if TAIL: json.dump(TAIL, open(OUT.replace('.json', '.tail.json'), 'w'), default=str)
for arm in ("base", "c183", "c187", "c187nd"):
    n = collections.Counter()
    for g, a in res.items():
        x = a.get(arm)
        if x: n["refused" if x["refused"] else ("narrowed" if x["outcome"] == "narrowed" else "still_rest" if x["written_as_rest"] else "other")] += 1
    print(arm, dict(n))
