"""2.114 round 2, step 3/4 (2026-10-14): Sean's round-2 blind-tile answers scored against the hidden manifest, then the 90%-interior measurement
(`interior_variants.json`, written by `interior_variants.py`, NOT re-gathered) re-done with the Litolff "black" set CLEANED.
  cleaned by Sean's answers only : drop the 7 production black boxes he called not-a-note, move tile 2's box (a hollow half) to the hollow side
  cleaned by the record's own verdicts too : also drop every remaining black box the OFF record itself reads as a non-note mark, by
      R1 `notehead_is_not_a_notehead` decided True (except belongs_to_a_nearer_staff / notehead_is_a_duplicate_box / stacked_head_duplicate: real heads),
      R2 `notehead_is_a_whole_rest` decided True,
      R3 >= 50% of the box lies inside a detector box of a non-note class (rest*, fermata*, dynamic*, key*, accidental*, clef*, timeSig*, brace),
      R4 the box centre is within 1 staff space of the staff's left/right extent (bracket / barline column).
  Item 4: all production noteheadBlack* boxes of the idx 1 page, the same flags, and their EXPORT fate (`export.build`, `fates`).
usage: cleaned_interior.py   (run from the repo root; writes cleaned_interior.json, prints the tables)"""
import collections, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, ".")
from tools.omr.staged import readout as RO
from tools.omr.staged import record_io, export as EX
HERE = Path("benchmarks/omr-second-detector-2026-10"); sys.path.insert(0, str(HERE))
from interior_variants import stats, best_cut
R2 = Path("out/print/2.114-round2")
OFF = "runs/2.114/ab/rec-lit-off.json"

# ---- 1. Sean's answers (verbatim: "1. Part of a bracket 2.2 3.f dyn 4.bracket 5. Key flat 6.2 7.4 8. Time signature number 4 9. Whole rest 10.2 11. Fermata 12.2 13. Dot 2")
SEAN = {1: ("not_a_note", "Part of a bracket"), 2: ("hollow", "2"), 3: ("not_a_note", "f dyn"), 4: ("not_a_note", "bracket"), 5: ("not_a_note", "Key flat"),
        6: ("hollow", "2"), 7: ("black", "4"), 8: ("not_a_note", "Time signature number 4"), 9: ("not_a_note", "Whole rest"), 10: ("hollow", "2"),
        11: ("not_a_note", "Fermata"), 12: ("hollow", "2"), 13: ("hollow", "Dot 2 (dotted half)")}
man = json.loads((R2 / "manifest.json").read_text())["tiles"]
ans = {f"tile_{n:02d}": {"answer": a, "sean": w} for n, (a, w) in SEAN.items()}
(R2 / "answers.json").write_text(json.dumps(ans, indent=1))

# ---- 2. score against the hidden manifest
def expected(h):
    if h["group"].startswith("CONTROL"): return h["expected"]
    if h["group"].startswith("THRESHOLD truth hollow"): return "hollow"
    return None      # threshold black-labelled: production said black, truth unknown (the question)
score = {"controls": {}, "truth_hollow": {}, "threshold_black": {}}
for t in man:
    n, h = t["n"], t["hidden"]; a = SEAN[n][0]
    if h["group"].startswith("CONTROL"): score["controls"][n] = (h["expected"], a, h["expected"] == a)
    elif h["group"].startswith("THRESHOLD truth hollow"): score["truth_hollow"][n] = ("hollow", a, a == "hollow")
    else: score["threshold_black"][n] = (h["key"], a, SEAN[n][1])
tb = collections.Counter(v[1] for v in score["threshold_black"].values())
print("controls", score["controls"]); print("truth hollow", score["truth_hollow"]); print("threshold black-labelled:", dict(tb), score["threshold_black"])

# ---- 3. the cleaned measurement
d = json.loads((HERE / "interior_variants.json").read_text()); items = d["items"]
sean_nn = {h["key"] for t in man for h in [t["hidden"]] if h["group"].startswith("THRESHOLD black") and SEAN[t["n"]][0] == "not_a_note"}
sean_hollow = {h["key"] for t in man for h in [t["hidden"]] if h["group"].startswith("THRESHOLD black") and SEAN[t["n"]][0] == "hollow"}
assert len(sean_nn) == 7 and len(sean_hollow) == 1
rec = EX.Record(record_io.load_record(OFF))
run = RO.load_run(OFF)
sp = float(np.median([float(o["value"]) for o in run.observations if o["quantity"] == "staff_spacing"]))
ext = {o["subject"]: o["value"] for o in run.observations if o["quantity"] == "staff_extent"}
NONNOTE = ("rest", "fermata", "dynamic", "key", "accidental", "clef", "timeSig", "brace")
others = [g for g in run.glyphs.values() if g.page == 1 and g.box_page and g.cls and g.cls.startswith(NONNOTE) and not g.cls.startswith("noteheadH")]
def inter(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0]); h = min(a[3], b[3]) - max(a[1], b[1])
    return max(w, 0) * max(h, 0)
REAL_HEAD_REASONS = ('belongs_to_a_nearer_staff', 'notehead_is_a_duplicate_box', 'stacked_head_duplicate')   # a real head boxed twice / on another staff: not a non-note mark
def flags(key):
    g = run.glyphs[key]; b = g.box_page; f = []
    v = rec.verdict("notehead_is_not_a_notehead", key)
    if v and v["outcome"] == "decided" and v["value"] is True and v.get("reason") not in REAL_HEAD_REASONS: f.append("R1:" + v["reason"])
    v = rec.verdict("notehead_is_a_whole_rest", key)
    if v and v["outcome"] == "decided" and v["value"] is True: f.append("R2:whole_rest")
    ar = (b[2] - b[0]) * (b[3] - b[1])
    for o in others:
        if o.system == g.system and o.staff == g.staff and ar > 0 and inter(b, o.box_page) / ar >= 0.5:
            f.append("R3:" + o.cls); break
    e = ext.get(f"staff/{g.page}/{g.system}/{g.staff}")
    if e:
        cx = (b[0] + b[2]) / 2
        if min(abs(cx - e[0]), abs(cx - e[1])) <= sp: f.append("R4:edge_column")
    return f
blk = [i for i in items if i["page"] == "litolff" and i["label"] == "black"]
rflag = {i["key"]: flags(i["key"]) for i in blk}
print("Sean's 7 under the record's own flags:", {k: rflag.get(k) for k in sorted(sean_nn)}); print("tile 2 hollow:", rflag.get(next(iter(sean_hollow))))
extra = {k: f for k, f in rflag.items() if f and k not in sean_nn and k not in sean_hollow}
print("record-flagged beyond Sean's:", len(extra)); [print("  ", k, f) for k, f in extra.items()]
sets = {}
sets["original"] = (blk, [i for i in items if i["page"] == "litolff" and i["label"] == "hollow"])
hol = sets["original"][1]
moved = [dict(i, label="hollow") for i in blk if i["key"] in sean_hollow]
sets["sean"] = ([i for i in blk if i["key"] not in sean_nn and i["key"] not in sean_hollow], hol + moved)
sets["sean+record"] = ([i for i in sets["sean"][0] if i["key"] not in extra], sets["sean"][1])
out = {"extra": extra, "rows": {}}
def errs(bl, ho, c): return sum(1 for x in bl if x < c), sum(1 for x in ho if x >= c)
for name, (B, H) in sets.items():
    for var in ("a", "b", "c"):
        bl = [i[var] for i in B if i[var] is not None]; ho = [i[var] for i in H if i[var] is not None]
        r = dict(nb=len(bl), nh=len(ho), black=stats(bl), hollow=stats(ho), best=best_cut(bl, ho), cuts={str(c): errs(bl, ho, c) for c in (0.85, 0.90, 0.95)})
        out["rows"][f"{name}/{var}"] = r
        print(name, var, json.dumps(r))
# Brahms unchanged: straight from the stored summary
out["brahms"] = {v: d["summary"][f"brahms/{v}"] for v in "abc"}
# the Brahms per-cut numbers too (not in the summary)
for v in "abc":
    bl = [i[v] for i in items if i["page"] == "brahms" and i["label"] == "black" and i[v] is not None]; ho = [i[v] for i in items if i["page"] == "brahms" and i["label"] == "hollow" and i[v] is not None]
    out["brahms"][v]["cuts"] = {str(c): errs(bl, ho, c) for c in (0.85, 0.90, 0.95)}; print("brahms", v, out["brahms"][v]["cuts"], out["brahms"][v]["best"])

# ---- 4. every production black head box on the page, the flags, the export fate
cap = {}
_orig = EX._place_notes
def _spy(*a, **k):
    cap["fates"] = k.get("fates"); return _orig(*a, **k)
EX._place_notes = _spy
EX.build(rec)
fates = cap["fates"]
allb = [g for g in run.glyphs.values() if g.page == 1 and (g.cls or "").startswith("noteheadBlack")]
fl = {g.key: flags(g.key) for g in allb}
on = [g.key for g in allb if fl[g.key] or g.key in sean_nn]
rows = []
for k in on:
    g = run.glyphs[k]; nn = rec.verdict("notehead_is_not_a_notehead", k)
    rows.append(dict(key=k, sean=k in sean_nn, flags=fl[k], not_a_notehead=(nn["value"], nn.get("reason")) if nn else None, fate=fates.get(k)))
out["item4"] = dict(n_black_boxes=len(allb), n_on_nonnote=len(on), n_sean=len(sean_nn),
    fates=dict(collections.Counter(r["fate"] for r in rows)), rows=rows)
print("item4", json.dumps({k: v for k, v in out["item4"].items() if k != "rows"}))
for r in rows: print("  ", r)
(HERE / "cleaned_interior.json").write_text(json.dumps(out, indent=1, default=str))
