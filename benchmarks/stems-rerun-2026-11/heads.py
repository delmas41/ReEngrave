"""2.280 r3 (STAGED ADJUDICATE..EXPORT replay, read-only; nothing in tools/ changed): one row per KEPT notehead-classed box
(NOTEHEAD_IS_NOT_A_NOTEHEAD decided 'notehead', the 2.280 p1 definition) with its stem row(s), its export fate and the
verdicts that decide its value. Same shipped functions as 2.280 p1/p8 and 2.278 diag.

usage:
  heads.py slice PLATE TAG PAGES OUT.jsonl     rows = the saved GATHER slice lane-report-slices-TAG (gather of that night), re-adjudicated on THIS tree
  heads.py rec PATH PAGES OUT.jsonl            rows = a fresh small gather record (gather.sh), re-adjudicated on THIS tree
PAGES: comma list or 'all'.
"""
import collections
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
from tools.omr.staged import export as EXPORT                     # noqa: E402
from tools.omr.staged import lane_report as LR                    # noqa: E402
from tools.omr.staged.review import rerun as RR                   # noqa: E402
from tools.omr.staged.record import Q                             # noqa: E402
from tools.omr.staged.geometry import stem_touches_head           # noqa: E402
from tools.omr.staged.adjudicators.stem_value import _head_xywh   # noqa: E402

CAP = {}
_orig = EXPORT._place_notes


def _place(rec, runs, **kw):
    CAP["rec"], CAP["fates"] = rec, kw.get("fates")
    return _orig(rec, runs, **kw)


EXPORT._place_notes = _place

mode = sys.argv[1]
if mode == "slice":
    plate, tag, pages_s, out = sys.argv[2:6]
else:
    path, pages_s, out = sys.argv[2:5]
    plate = None
pages = None if pages_s == "all" else {int(p) for p in pages_s.split(",")}
t0 = time.time()
if mode == "slice":
    from tools.omr.staged import conservation as CONS
    rows_in = CONS.load_pages(plate, sorted(pages), tag)
else:
    from tools.omr.staged.record_io import load_record
    d = load_record(path)
    r0 = d.get("record", d)
    rows_in = {"observations": [o for o in r0["observations"] if pages is None or LR.page_of(o.get("subject")) in pages or LR.page_of(o.get("subject")) is None],
               "abstentions": r0.get("abstentions", []), "verdicts": []}
    del d, r0
log, _ = RR.rebuild_gather(rows_in)
del rows_in
RR.run_stages(log)
result = {"record": log.to_json(), "summary": log.summary()}
del log
xml, report = EXPORT.to_musicxml(result)
rec, fates = CAP["rec"], CAP["fates"]
print("stages+export %.0fs" % (time.time() - t0), "written", report["written"].get("notes"), "not_written", report["notes_not_written_total"],
      "conservation", {k: report["conservation"][k] for k in ("read_by_adjudicate", "written", "written_guessed", "not_written_total")}, flush=True)

RED = {}
for pl in report["conservation"]["in_red_bars"]["places"]:
    for gl in pl.get("glyphs") or ():
        RED[gl] = [pl["page"], pl["system"], pl["staff"], pl["cell"]]
json.dump(report["conservation"]["in_red_bars"], open(out + ".red.json", "w"))
print("red-bar glyph ids", len(RED), list(RED)[:3])
stems = collections.defaultdict(list)
for o in rec.obs_of(Q.STEM):
    stems[o["subject"]].append((o["id"], tuple(o["value"])))
KEEP = ["stems_attached", "beams_by_stem", "flags_attached", "flag_levels", "levels_certain", "levels_possible", "cv_beams", "yolo_beams",
        "yolo_kept", "beams_not_by_ink", "beams_far_side", "beams_neighbour_staff", "beams_decided_arc", "beams_beyond_stem", "beams_ledger_line",
        "beam_evidence", "page_beam", "bare_stem_likelihood", "bare_stem_evidence_holds", "bare_stem_tip_window_clean", "head_fill_first",
        "head_is_open"]


def vd(q, sub):
    v = rec.verdict(q, sub)
    if v is None:
        return None
    val = v.get("value")
    if isinstance(val, (list, dict)):
        val = json.dumps(val, default=str)[:200]
    return [v["outcome"], v.get("reason"), val]


n = 0
with open(out, "w") as f:
    for o in rec.obs_of(Q.GLYPH_BOX):
        sub = o["subject"]
        pg = LR.page_of(sub)
        if pages is not None and pg not in pages:
            continue
        k = rec.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, sub)
        if not rec.obs(Q.NOTEHEAD_CLASS, sub):
            continue
        cell = "cell/" + sub[6:].rsplit("/", 1)[0]
        head = _head_xywh(o["value"])
        touching = [(i, b) for i, b in stems.get(cell, []) if stem_touches_head(b, head)]
        dv = rec.verdict(Q.DURATION, sub)
        det = (dv.get("detail") or {}) if dv else {}
        try:
            g = EXPORT.guess_of(rec, sub) if fates.get(sub) in ("written", "written_relocated") else None
        except RuntimeError as e:
            g = {"stage": "ERR", "rule": str(e)[:60], "quantity": None}
        row = dict(sub=sub, red=RED.get(sub), guess=[g["stage"], g["rule"], g["quantity"]] if g else None, page=pg, cls=o["value"][0], conf=o["score"], box=list(o["value"]), page_box=(o.get("detail") or {}).get("bbox_page_px"),
                   kept=bool(k and k["outcome"] == "decided" and k["reason"] == "notehead"), not_a_head=[k["outcome"], k["reason"]] if k else None,
                   fate=fates.get(sub, "NO_FATE"), n_stem=len(touching), stem_boxes=[list(b) for _, b in touching][:3],
                   head_stem=vd(Q.HEAD_STEM, sub), duration=vd(Q.DURATION, sub), stem_dir=vd(Q.STEM_DIRECTION, sub),
                   whole_rest=vd(Q.NOTEHEAD_IS_A_WHOLE_REST, sub), head_ink_rest=vd(Q.HEAD_INK_IS_A_REST, sub),
                   cands=[[(c["value"] or {}).get("written"), (c["value"] or {}).get("beam_levels"), (c["value"] or {}).get("dots")]
                          for c in ((dv or {}).get("candidates") or []) if isinstance(c.get("value"), dict)],
                   d={kk: det[kk] for kk in KEEP if kk in det}, bfs=det.get("beams_from_strokes"))
        f.write(json.dumps(row, default=str) + "\n")
        n += 1
print(n, "rows ->", out, "%.0fs" % (time.time() - t0))
print(collections.Counter(json.loads(l)["fate"] for l in open(out)).most_common(14))
