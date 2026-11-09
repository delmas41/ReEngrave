"""2.278 diag: one row per narrowed / chord-undecided head of a record: the duration verdict's reason, candidates and the
detail the ADJUDICATE rule recorded about the beam/flag evidence at that stem. READ-ONLY (instrumented export, as 2.275 p1).

usage: python3 probe/2.278/diag.py RECORD OUT.jsonl [slim]
"""
import sys, json, collections, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
from tools.omr.staged import export as EXPORT
from tools.omr.staged.record_io import load_record, expand_result
from tools.omr.staged.record import Q

CAP = {}
orig = EXPORT._place_notes
def place(rec, runs, **kw):
    CAP["rec"] = rec; CAP["fates"] = kw.get("fates"); return orig(rec, runs, **kw)
EXPORT._place_notes = place

path, out = sys.argv[1], sys.argv[2]
t = time.time()
if len(sys.argv) > 3 and sys.argv[3] == "slim":
    def _hook(o):
        if "quantity" in o and "outcome" in o:
            o.pop("considered", None); o.pop("correlated", None)
        return o
    d = expand_result(json.loads(Path(path).read_text(), object_hook=_hook))
else:
    d = load_record(path)
print("loaded", round(time.time() - t), flush=True)
xml, report = EXPORT.to_musicxml(d)
rec, fates = CAP["rec"], CAP["fates"]
print("exported", round(time.time() - t), report["notes_not_written_total"], flush=True)

KEEP = ["head", "head_is_open", "beam_evidence", "cv_beams", "yolo_beams", "yolo_kept", "beams_ledger_line", "beams_slash",
        "beams_neighbour_staff", "beams_decided_arc", "beams_double_thick", "beams_not_by_ink", "beams_not_by_ink_why",
        "beam_side", "beams_far_side", "beams_beyond_stem", "stems_attached", "beams_by_stem", "flags_attached",
        "flag_levels", "levels_certain", "levels_possible", "bare_stem_likelihood", "bare_stem_evidence_holds",
        "bare_stem_tip_window_clean", "bare_stem_refused_stroke_at_tip", "refused_strokes", "certain_conflicts",
        "head_fill_first", "tips_honour_claims", "beam_refused_off_the_tip", "page_beam"]
rows = []
for sub, fate in fates.items():
    if fate not in ("duration_narrowed", "chord_value_undecided"):
        continue
    v = rec.verdict(Q.DURATION, sub)
    r = {"sub": sub, "fate": fate}
    o = rec.obs(Q.GLYPH_BOX, sub)
    if o:
        r["bbox"] = (o[-1].get("detail") or {}).get("bbox_page_px")
    if v:
        r["outcome"] = v["outcome"]; r["reason"] = v["reason"]
        r["cands"] = [(c["value"].get("written"), c["value"].get("beam_levels"), c["value"].get("dots"), c.get("support"))
                      for c in (v.get("candidates") or []) if isinstance(c.get("value"), dict)]
        dt = v.get("detail") or {}
        r["d"] = {k: dt[k] for k in KEEP if k in dt}
        bfs = dt.get("beams_from_strokes")
        if bfs: r["bfs"] = bfs
        r["detail_keys"] = sorted(dt.keys())
    hs = rec.verdict(Q.HEAD_STEM, sub)
    if hs: r["head_stem"] = [hs["outcome"], hs["reason"], str(hs.get("value"))[:200]]
    sv = rec.verdict(Q.STEM_VALUE, sub)
    if sv: r["stem_value"] = [sv["outcome"], sv["reason"], str(sv.get("value"))[:200]]
    ev = rec.verdict(Q.EVENT_DURATION, sub) if hasattr(Q, "EVENT_DURATION") else None
    rows.append(r)
with open(out, "w") as f:
    for r in rows:
        f.write(json.dumps(r, default=str) + "\n")
print(len(rows), collections.Counter((r["fate"], r.get("reason")) for r in rows))
