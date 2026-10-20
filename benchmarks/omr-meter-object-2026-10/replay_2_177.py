"""ROADMAP 2.177 -- replay a 20261018-night record (per-page jsonl slices from slice_record.py) through GATHER(meter object only) ->
ADJUDICATE..INFER..second EVALUATE -> EXPORT, flag OFF vs ON. Measures the EXPORTED FILE.

  off -- OMR_METER_OBJECT=0 (no claim rows; today's 2.173 `on_a_read_meter`, `rest_is_a_meter_digit` 18-space column)
  on  -- OMR_METER_OBJECT=1: `gather.gather_meter_object` is run on the page raster (rendered from the library PDF at 600 dpi, the frame
         of `bbox_page_px`), fed by SHIM staves/cells/detections rebuilt from the record's own rows (the real function, not a copy), and
         its `Q.CLAIMED_AREA` rows join the rebuilt log before ADJUDICATE.

usage: replay_2_177.py DOC SLICEDIR OUTDIR ARM[,ARM...]
Writes OUTDIR/DOC.ARM.json {glyphs, refusals{glyph:[value, reason, margin]}, rest_refusals, claims, coverage, notes_in_xml, held_bars}."""
import collections
import glob
import json
import os
import sys
import time

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staged import export as E  # noqa: E402
from tools.omr.staged import gather as G  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

DOC, SD, OUTDIR, ARMS = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(",")
D = os.path.join(SD, DOC)
PDFS = {
    "litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
               "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
    "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
FLAG = "OMR_METER_OBJECT"
os.makedirs(OUTDIR, exist_ok=True)
JUDGED_Q = {"duration", "notehead_is_not_a_notehead", "unboxed_ink_is_a_rest", "notehead_is_an_eighth_rest", "arc_kind",
            "rest_is_not_a_rest"}


def rows(kind):
    out = []
    for p in sorted(glob.glob(os.path.join(D, "*.%s.jsonl" % kind))):
        out += [json.loads(l) for l in open(p)]
    return out


def live(verdicts, quantity, prefix):
    chains = collections.defaultdict(list)
    for v in verdicts:
        if v["quantity"] == quantity and v["subject"].startswith(prefix):
            chains[v["subject"]].append(v)
    out = {}
    for g, ch in chains.items():
        sup = {x.get("supersedes") for x in ch if x.get("supersedes")}
        out[g] = ([x for x in ch if x["id"] not in sup] or ch)[-1]
    return out


def brief(v):
    val = v["value"] if isinstance(v["value"], dict) else {}
    return dict(outcome=v["outcome"], written=val.get("written"), dots=val.get("dots"), beats=val.get("beats"),
                rest=bool(val.get("is_rest")), measure_rest=bool(val.get("measure_rest")), decider=v.get("decider"), reason=v.get("reason"))


class _Det:
    def __init__(self, name, x, y, w, h):
        self.smufl_name, self.x_canonical, self.y_canonical, self.width_canonical, self.height_canonical = name, x, y, w, h
        self.confidence = 1.0


class _Cell:
    def __init__(self, staff_index, measure_index, page_index, bbox):
        self.staff_index, self.measure_index, self.page_index = staff_index, measure_index, page_index
        self.bbox_page_px, self.upscale_factor = bbox, 1.0


class _Staff:
    def __init__(self, staff_index, system_index, line_ys):
        self.staff_index, self.system_index, self.line_ys = staff_index, system_index, line_ys


class _Page:
    def __init__(self, page_index, binary):
        self.page_index, self.binary = page_index, binary


class _PWS:
    def __init__(self, page, staves):
        self.page, self.staves = page, staves


def inject_claims(log, rec_obs_by_page, binary_of):
    """Run the REAL `gather.gather_meter_object` per page on shim inputs rebuilt from the record's rows."""
    n0 = len(log.all_rows())
    for pg, obs in sorted(rec_obs_by_page.items()):
        lines, cellbox, boxes = {}, {}, collections.defaultdict(dict)
        for o in obs:
            q = o["quantity"]
            s = o["subject"].split("/")
            if q == "staff_lines" and s[0] == "staff":
                lines[(int(s[2]), int(s[3]))] = o["value"]
            elif q == "cell_box" and s[0] == "cell" and len(s) == 5:
                cellbox[(int(s[2]), int(s[3]), int(s[4]))] = o["value"]
            elif q == "glyph_box" and s[0] == "glyph" and len(s) == 6:
                pb = (o.get("detail") or {}).get("bbox_page_px")
                if isinstance(pb, list) and len(pb) == 4:
                    boxes[(int(s[2]), int(s[3]), int(s[4]))][int(s[5])] = (str(o["value"][0]), pb)
        if not lines or not cellbox:
            continue
        binary = binary_of(pg)
        staves, local, cells, dets = [], {}, [], {}
        for (sy, li), ly in sorted(lines.items()):
            si = sy * 1000 + li
            staves.append(_Staff(si, sy, ly))
            local[si] = (sy, li)
        for (sy, li, k), cb in sorted(cellbox.items()):
            si = sy * 1000 + li
            cells.append(_Cell(si, k, pg, cb))
            b = boxes.get((sy, li, k), {})
            lst = []
            top = max(b) + 1 if b else 0
            for gi in range(top):
                if gi in b:
                    nm, pbx = b[gi]
                    lst.append(_Det(nm, pbx[0] - cb[0], pbx[1] - cb[1], pbx[2] - pbx[0], pbx[3] - pbx[1]))
                else:
                    lst.append(_Det("", -1e9, -1e9, 0, 0))
            dets["cell/%d/%d/%d/%d" % (pg, sy, li, k)] = lst
        G.gather_meter_object(log, _PWS(_Page(pg, binary), staves), cells, local, dets)
    return len(log.all_rows()) - n0


t0 = time.time()
rec = {"observations": rows("observations"), "abstentions": rows("abstentions"), "verdicts": []}
print(DOC, "rows", len(rec["observations"]), len(rec["abstentions"]), "%.0fs" % (time.time() - t0), flush=True)
by_page = collections.defaultdict(list)
for o in rec["observations"]:
    if o["quantity"] in ("staff_lines", "cell_box", "glyph_box"):
        p = (o["subject"] or "").split("/")
        if len(p) >= 2 and p[1].isdigit():
            by_page[int(p[1])].append(o)
_rast = {}


def binary_of(pg):
    if pg not in _rast:
        _rast.clear()
        _rast[pg] = render_page(PDFS[DOC], pg, dpi=600).binary
    return _rast[pg]


KEEP = ("bars_held_out_sum", "partial_bars", "guessed", "written", "notes_not_written_total", "balance")
for arm in ARMS:
    os.environ[FLAG] = "1" if arm == "on" else "0"
    log, _ = RR.rebuild_gather(rec)
    nclaim = 0
    if arm == "on":
        nclaim = inject_claims(log, by_page, binary_of)
        print(DOC, "claim rows+abstentions", nclaim, "%.0fs" % (time.time() - t0), flush=True)
    RR.run_stages(log)
    result = {"record": log.to_json(), "summary": log.summary()}
    del log
    vs = result["record"]["verdicts"]
    glyph_live = live(vs, "duration", "glyph/")
    glyphs = {g: brief(v) for g, v in glyph_live.items()}
    refusals = {g: [v["value"], v.get("reason"), v.get("margin")] for g, v in live(vs, "notehead_is_not_a_notehead", "glyph/").items()
                if v["value"] is True}
    rest_ref = {g: [v["value"], v.get("reason"), v.get("margin")] for g, v in live(vs, "rest_is_not_a_rest", "glyph/").items()
                if v["value"] is True}
    claims = [dict(subject=o["subject"], value=o["value"], cell=(o.get("detail") or {}).get("cell"),
                   numbers=(o.get("detail") or {}).get("numbers"), n_in_column=(o.get("detail") or {}).get("n_in_column"),
                   n_staves=(o.get("detail") or {}).get("n_staves"), form=(o.get("detail") or {}).get("form"),
                   inside={k: v for k, v in ((o.get("detail") or {}).get("boxes_inside") or {}).items()})
              for o in result["record"]["observations"] if o["quantity"] == "claimed_area"]
    claim_abst = [dict(subject=a["subject"], cell=(a.get("detail") or {}).get("cell"), why=(a.get("detail") or {}).get("why"))
                  for a in result["record"]["abstentions"] if a["quantity"] == "claimed_area"]
    t1 = time.time()
    xml, report = E.to_musicxml(result)
    print(DOC, arm, "export %.0fs" % (time.time() - t1), flush=True)
    cov = {k: report.get(k) for k in KEEP}
    cov["bars_held_out_sum"] = {k: v for k, v in (report.get("bars_held_out_sum") or {}).items() if k != "held"}
    cov["partial_bars"] = {k: v for k, v in (report.get("partial_bars") or {}).items() if not isinstance(v, list) or k == "stay_held_by_reason"}
    held_bars = (report.get("bars_held_out_sum") or {}).get("held", [])
    nfile = {k: v for k, v in (report.get("written") or {}).items()}
    out = dict(doc=DOC, arm=arm, glyphs=glyphs, refusals=refusals, rest_refusals=rest_ref, claims=claims, claim_abstentions=claim_abst,
               coverage=cov, notes_in_xml=xml.count("<note"),
               held_bars=[(h["page"], h["system"], h["staff"], h["cell"]) for h in held_bars],
               not_a_notehead={k: v for k, v in report.items() if "not_a_notehead" in str(k)})
    json.dump(out, open(os.path.join(OUTDIR, "%s.%s.json" % (DOC, arm)), "w"), default=str)
    json.dump({"observations": [], "abstentions": [], "verdicts": [v for v in vs if v["quantity"] in JUDGED_Q]},
              open(os.path.join(OUTDIR, "%s.%s.record.json" % (DOC, arm)), "w"), default=str)
    open(os.path.join(OUTDIR, "%s.%s.musicxml" % (DOC, arm)), "w").write(xml)
    del vs, result, xml
    print(DOC, arm, "notes", nfile.get("notes"), "held", cov["bars_held_out_sum"].get("bars"), "refused", len(refusals),
          "rest_refused", len(rest_ref), "claims", len(claims), "%.0fs" % (time.time() - t0), flush=True)
