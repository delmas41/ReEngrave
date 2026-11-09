"""2.279 probe A: for every dropped REAL-note head (the representative of each distinct-ink cluster in the 2.275 buckets
duration_narrowed / chord_value_undecided / no_pitch / duration_abstained) dump what is left to decide it, and whether the
loss is VISIBLE in the exported file (its bar is red / partial-with-gap / held). READ-ONLY; re-exports the saved record with
the CURRENT tree; nothing is re-decided.

usage: python3 probe/2.279/probe_a.py RECORD INK.json OUT.jsonl [slim]
"""
import collections
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import export as EXPORT          # noqa: E402
from tools.omr.staged.record_io import load_record, expand_result  # noqa: E402
from tools.omr.staged.record import Q                   # noqa: E402

rec_path, ink_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
t = time.time()
if len(sys.argv) > 4 and sys.argv[4] == "slim":
    def _hook(o):
        if "quantity" in o and "outcome" in o:
            o.pop("considered", None)
            o.pop("correlated", None)
        return o
    d = expand_result(json.loads(Path(rec_path).read_text(), object_hook=_hook))
else:
    d = load_record(rec_path)
print("loaded", round(time.time() - t), flush=True)
CAP = {}
orig = EXPORT._place_notes


def place(rec, runs, **kw):
    CAP["rec"] = rec
    CAP["fates"] = kw.get("fates")
    return orig(rec, runs, **kw)


EXPORT._place_notes = place
xml, report = EXPORT.to_musicxml(d)
rec, fates = CAP["rec"], CAP["fates"]
print("exported", round(time.time() - t), report["notes_not_written_total"], flush=True)

ink = json.load(open(ink_path))
BUCKETS = ("refused:duration_narrowed", "refused:chord_value_undecided", "refused:no_pitch", "refused:duration_abstained")

# bar status by (page, system, staff, cell)
bar_status = {}
for b in report["partial_bars"]["bars"]:
    bar_status[(b["page"], b["system"], b["staff"], b["cell"])] = ("partial:" + b["status"], b)
for b in (report.get("bars_written_red") or {}).get("bars_list", []):
    bar_status.setdefault((b["page"], b["system"], b["staff"], b["cell"]), ("red", b))
for b in report["bars_held_out_sum"]["held"]:
    bar_status.setdefault((b["page"], b["system"], b["staff"], b["cell"]), ("held", b))

for b in report["unread_empty_bars"]["list"]:
    pg, sy, ce = [int(x) for x in b["bar_key"].split("/")]
    bar_status.setdefault((pg, sy, b["staff"], ce), ("unread_empty", b))

# every glyph subject of each cell, with its fate (for the bar context)
cell_members = collections.defaultdict(list)
for sub, fate in fates.items():
    p = sub.split("/")
    cell_members[(int(p[1]), int(p[2]), int(p[3]), int(p[4]))].append((sub, fate))


def cands(v):
    out = []
    for c in (v or {}).get("candidates") or ():
        val = c.get("value")
        if isinstance(val, dict):
            out.append({"beats": val.get("beats"), "written": val.get("written"), "dots": val.get("dots"),
                        "levels": val.get("beam_levels"), "support": c.get("support")})
        else:
            out.append({"value": val, "support": c.get("support")})
    return out


def brief(v, with_cands=True):
    if v is None:
        return None
    r = {"outcome": v["outcome"], "reason": v.get("reason"), "decider": v.get("decider"), "margin": v.get("margin")}
    val = v.get("value")
    if isinstance(val, dict) and "beats" in val:
        r["beats"] = val["beats"]
        r["levels"] = val.get("beam_levels")
        r["dots"] = val.get("dots")
    elif val is not None and not isinstance(val, (dict, list)):
        r["value"] = val
    if with_cands:
        r["cands"] = cands(v)
    return r


rows = []
for bucket in BUCKETS:
    for sub in ink["members"].get(bucket, []):
        p = sub.split("/")
        cellk = (int(p[1]), int(p[2]), int(p[3]), int(p[4]))
        staff = "staff/%s/%s/%s" % (p[1], p[2], p[3])
        dur = rec.verdict(Q.DURATION, sub)
        det = (dur or {}).get("detail") or {}
        st = bar_status.get(cellk)
        # chord siblings: the other heads on the same decided stem
        hs = rec.verdict(Q.HEAD_STEM, sub)
        sv = rec.verdict(Q.STEM_VALUE, sub)
        mem = ((sv or {}).get("detail") or {}).get("members") or []
        sib = []
        for m in mem:
            if m == sub:
                continue
            md = rec.verdict(Q.DURATION, m)
            sib.append({"sub": m, "fate": fates.get(m), "dur": brief(md, False), "pitch": (rec.verdict(Q.PITCH, m) or {}).get("value")})
        clef = rec.verdict(Q.CLEF, staff)
        row = {
            "bucket": bucket, "sub": sub, "cell": list(cellk),
            "fate": fates.get(sub),
            "dur": brief(dur),
            "dur_detail": {k: det.get(k) for k in ("bare_stem_likelihood", "bare_stem_evidence_holds", "bare_stem_tip_window_clean",
                                                   "bare_stem_refused_stroke_at_tip", "flag_level_votes", "certain_conflicts",
                                                   "certain", "possible", "beam_evidence", "refused_strokes") if k in det},
            "stem_value": brief(sv),
            "stem_dir": (rec.verdict(Q.STEM_DIRECTION, sub) or {}).get("value"),
            "head_stem": (hs or {}).get("reason"),
            "pitch": brief(rec.verdict(Q.PITCH, sub), False),
            "clef": brief(clef),
            "sibs": sib,
            "meter": brief(rec.verdict(Q.METER, "system/%s/%s" % (p[1], p[2])), False),
            "bar_status": st[0] if st else "silent",
            "bar": ({k: st[1].get(k) for k in ("status", "why", "unread_glyphs", "gap_quarters", "events", "rows", "rows_written",
                                               "rows_in_gap", "want_quarters", "counted_quarters", "two_voice")} if st else None),
            "cell_members": [(s, f) for s, f in cell_members.get(cellk, [])],
            "cell_detail": [(s.split("/")[-1], f, ((rec.verdict(Q.DURATION, s) or {}).get("value") or {}).get("beats") if isinstance((rec.verdict(Q.DURATION, s) or {}).get("value"), dict) else None, (rec.verdict(Q.PITCH, s) or {}).get("value"), (rec.verdict(Q.STEM_DIRECTION, s) or {}).get("value")) for s, f in cell_members.get(cellk, []) if f.startswith("written") or f in ("duration_narrowed", "chord_value_undecided", "no_pitch")],
        }
        rows.append(row)
with open(out_path, "w") as f:
    for r in rows:
        f.write(json.dumps(r, default=str) + "\n")
c = collections.Counter((r["bucket"], r["bar_status"]) for r in rows)
for k, n in sorted(c.items()):
    print(k, n)
print("rows", len(rows), "done", round(time.time() - t))
