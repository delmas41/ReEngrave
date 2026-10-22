"""(helper copy of known_flats shims) 2.187 -- the 24 KNOWN key flats written as rests (20 Litolff: key_flats_written_as_rests_litolff.json; 4 Brahms: FINDINGS 2.183 §1),
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
from tools.omr.staged.review import rerun as RR

SD = sys.argv[4] if len(sys.argv) > 4 else None
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


def live(vs, quantity):
    ch = collections.defaultdict(list)
    for v in vs:
        if v["quantity"] == quantity and v["subject"].startswith("glyph/"): ch[v["subject"]].append(v)
    out = {}
    for g, c in ch.items():
        sup = {x.get("supersedes") for x in c if x.get("supersedes")}
        out[g] = ([x for x in c if x["id"] not in sup] or c)[-1]
    return out



import hashlib
from tools.omr.staged import export as E
PLATE, ARM, OUTD = sys.argv[1], sys.argv[2], sys.argv[3]       # PLATE litolff|brahms ; ARM base|c183|c187|c187nd
SAMPLE = {"litolff": [1, 2, 4, 6, 8, 9, 10, 11, 16], "brahms": [0, 4, 5, 8, 12, 14, 19, 25]}
if os.environ.get("PAGES"):
    SAMPLE[PLATE] = [int(x) for x in os.environ["PAGES"].split(",")]
TAG = os.environ.get("TAG", "")
os.makedirs(OUTD, exist_ok=True)
env = {"base": dict(OMR_KEY_SIGNATURE_CLAIM="0", OMR_KEY_PER_SYSTEM="0"), "c183": dict(OMR_KEY_SIGNATURE_CLAIM="1", OMR_KEY_PER_SYSTEM="0"),
       "c187": dict(OMR_KEY_SIGNATURE_CLAIM="1", OMR_KEY_PER_SYSTEM="1"), "c187nd": dict(OMR_KEY_SIGNATURE_CLAIM="1", OMR_KEY_PER_SYSTEM="1")}[ARM]
os.environ.update(env)
dossier = json.load(open(DOSS[PLATE])) if ARM != "c187nd" else None
P = os.path.join(SD, PLATE)
def ld(kind):
    out = []
    for f in [os.path.join(P, n) for n in ["g.%s.jsonl" % kind, "common.%s.jsonl" % kind] + ["p%02d.%s.jsonl" % (p, kind) for p in SAMPLE[PLATE]]]:
        if os.path.exists(f): out += [json.loads(l) for l in open(f)]
    return out
obs, ab = ld("observations"), ld("abstentions")
rec = {"observations": obs, "abstentions": ab, "verdicts": []}
log, _ = RR.rebuild_gather(rec)
if ARM != "base":
    for pg in SAMPLE[PLATE]:
        binary = render_page(PDFS[PLATE], pg, dpi=600).binary
        inject(log, [o for o in obs if (o["subject"] or "").split("/")[1:2] == [str(pg)]], binary, pg, dossier, ARM.startswith("c187"))
RR.run_stages(log)
result = {"record": log.to_json(), "summary": log.summary()}
xml, report = E.to_musicxml(result)
open(os.path.join(OUTD, "%s.%s%s.musicxml" % (PLATE, ARM, TAG)), "w").write(xml)
vs = [v for v in result["record"]["verdicts"] if v["quantity"] in ("duration", "notehead_is_not_a_notehead", "rest_is_not_a_rest", "unboxed_ink_is_a_rest", "notehead_is_an_eighth_rest", "arc_kind")]
json.dump({"verdicts": vs, "claims": [dict(subject=o["subject"], value=o["value"], detail={k: v for k, v in (o.get("detail") or {}).items() if k != "boxes_inside"})
                                      for o in result["record"]["observations"] if o["quantity"] == "claimed_area" and (o.get("detail") or {}).get("owner") == "key_signature"],
           "red": (report.get("red_bars") or {}).get("n") if isinstance(report.get("red_bars"), dict) else None},
          open(os.path.join(OUTD, "%s.%s%s.json" % (PLATE, ARM, TAG)), "w"), default=str)
print(PLATE, ARM, "xml", hashlib.sha1(xml.encode()).hexdigest()[:10], "notes", xml.count("<note"), "blue", xml.count('color="%s"' % E.GUESS_COLOR), flush=True)
