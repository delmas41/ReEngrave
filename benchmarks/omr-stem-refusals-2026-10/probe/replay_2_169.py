"""ROADMAP 2.169 -- page replay of `OMR_STEM_PAIR_AT_HEAD=1`, GATHER+ADJUDICATE, on the SYSTEMS that hold a changed cell. No page gather by
the detector: the record's own `glyph_box` rows are the detections.

For every cell where reach_2_169.py's NEW arm adds a stem: the cell is prepared as the gather prepares it (`prepare_pages`), the
gather's own `gather_cv_lines` + `gather_beam_stroke_ink` run on it into a scratch log with the flag ON, and those rows REPLACE the
record's cv_lines rows of that cell (and every row keyed to one of them by `beam_row_id`/`stem_row_id`; ids re-pointed). The slice (all
systems holding a changed cell; rows whose subject has no page/system are global and stay) is rebuilt (replay_util_2_153.rebuild: the
2.157 id remap) and re-decided (`review.rerun.run_stages`) twice: CONTROL (the record's rows untouched) and ARM (changed cells replaced).
CONTROL must give the record's stored first `adjudicate_duration` verdict on every glyph of the slice up to the known restricted-re-decide
noise (counted and printed); every figure is ARM vs CONTROL, never vs the record.
Outputs: OUT.json = per-glyph control/arm readings (duration + head_stem), plus overlay records OUT.control.verdicts.json / OUT.arm.verdicts.json
for `tools.omr.staged.judged.score`.
usage: replay_2_169.py DOC ROWS.json REACH.json OUT   (DOC litolff|brahms)
"""
import copy
import json
import os
import sys
from collections import Counter, defaultdict
from types import SimpleNamespace

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/gather-zoom-layers-2026-10/probe")
sys.path.insert(0, "benchmarks/omr-bar-sum-holdout-2026-09/probe")
import rec as RC  # noqa: E402
from replay_util_2_153 import rebuild  # noqa: E402
from tools.omr.staged import gather as G  # noqa: E402
from tools.omr.staged import record as R  # noqa: E402
from tools.omr.staged.pipeline import prepare_pages  # noqa: E402
from tools.omr.staged.review import rerun as RR  # noqa: E402

PDFS = {"litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
                   "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
                  "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
PATH = {"litolff": RC.LIB + "beethoven5-litolff-mvt1-whole-20261016-night.record.json",
        "brahms": RC.LIB + "brahms1-breitkopf-mvt1-whole-20261016-night.record.json"}
DOC, ROWS, REACH, OUT = sys.argv[1:5]
ONLY_SYS = None
if len(sys.argv) > 5:
    ONLY_SYS = {tuple(int(v) for v in s.split(",")) for s in sys.argv[5].split(";")}

rows = json.load(open(ROWS))
reach = json.load(open(REACH))
changed = sorted({a["cell"] for a in reach["added"] if a["arm"] == "NEW"})
SYS = sorted({(int(c.split("/")[1]), int(c.split("/")[2])) for c in changed})
if ONLY_SYS is not None:
    SYS = [s for s in SYS if s in ONLY_SYS]
    changed = [c for c in changed if (int(c.split("/")[1]), int(c.split("/")[2])) in ONLY_SYS]
SYSSET = set(SYS)
print("changed cells", len(changed), "systems", len(SYS), flush=True)


def keep(subject):
    p = subject.split("/")
    if len(p) >= 3 and p[1].lstrip("-").isdigit() and p[2].lstrip("-").isdigit():
        return (int(p[1]), int(p[2])) in SYSSET
    return True


# ---- slice of the record (streamed: Brahms is 7 GB) ----
sl = {"observations": [], "abstentions": [], "verdicts": []}
with RC.lock():
    for k in sl:
        for o in RC.items(PATH[DOC], k):
            if keep(o["subject"]):
                sl[k].append(o)
print("slice rows", {k: len(v) for k, v in sl.items()}, flush=True)


def idnum(i):
    return int(i.split(":")[1])


top = max(idnum(x["id"]) for k in ("observations", "abstentions") for x in sl[k])

# ---- the gather's own rows for each changed cell, flag ON ----
os.environ["OMR_STEM_PAIR_AT_HEAD"] = "1"
glyphs = defaultdict(list)
for sub, v in rows["glyph"].items():
    p = sub.split("/")
    glyphs["cell/" + "/".join(p[1:5])].append((int(p[5]), v))
cell_box = {k: tuple(v) for k, v in rows["cell_box"].items()}

new_rows = {}                       # cell key -> (obs list, abs list) from the scratch log
by_page = defaultdict(list)
for c in changed:
    by_page[int(c.split("/")[1])].append(c)
for pg in sorted(by_page):
    (pws, cells), = prepare_pages(PDFS[DOC], [pg])
    by_bb = {tuple(float(v) for v in c.bbox_page_px): c for c in cells}
    for key in by_page[pg]:
        c = by_bb.get(tuple(float(v) for v in cell_box[key]))
        if c is None:
            print("cell not matched", key)
            continue
        _, p, s, st, m = key.split("/")
        sub = R.cell(int(p), int(s), int(st), int(m))
        dets = [SimpleNamespace(smufl_name=v[0], x_canonical=v[1], y_canonical=v[2], width_canonical=v[3], height_canonical=v[4],
                                x_center=v[1] + v[3] / 2.0, y_center=v[2] + v[4] / 2.0) for _g, v in sorted(glyphs[key])]
        scratch = R.Log()
        local = {c.staff_index: (int(s), int(st))}
        G.gather_cv_lines(scratch, [c], local, detections={sub.to_key(): dets})
        G.gather_beam_stroke_ink(scratch, [c], local)
        sj = scratch.to_json()
        new_rows[key] = (sj["observations"], sj["abstentions"])
    print("gathered page", pg, flush=True)
del os.environ["OMR_STEM_PAIR_AT_HEAD"]

# ---- inject (ADD-ONLY: every old row keeps its id, so no row of another reader can dangle) ----
# A new stem (box not among the cell's old cv stems) is added with the rows keyed to it (stem_tip_ink, stem_slash, beam_stem_join);
# a beam stroke the arm's stems make that the record lacks is added with its ink rows; a join to an OLD stroke is re-pointed at the
# old stroke's row id by box. LIMIT (printed, not hidden): rows other gather functions derive FROM stems (notehead_stem_cross_ink,
# stacked_head_fit, beam_stem_levels) are not re-derived, so they keep the old stems' reading.
arm = copy.deepcopy(sl)
n_added = n_skipped = n_new_stems = 0
k = top + 1
for key, (nobs, nabs) in new_rows.items():
    old = {kind: [o for o in arm[kind] if o["subject"] == key and o.get("reader") == "cv_lines"] for kind in ("observations", "abstentions")}
    old_stem = {tuple(o["value"]): o["id"] for o in old["observations"] if o["quantity"] == "stem"}
    old_beam = {tuple(o["value"]): o["id"] for o in old["observations"] if o["quantity"] == "beam_stroke"}
    smap, bmap, add_ids = {}, {}, set()
    for o in nobs:
        if o["quantity"] == "stem":
            if tuple(o["value"]) in old_stem:
                smap[o["id"]] = old_stem[tuple(o["value"])]
            else:
                add_ids.add(o["id"])
                n_new_stems += 1
        elif o["quantity"] == "beam_stroke" and o.get("reader") == "cv_lines":
            if tuple(o["value"]) in old_beam:
                bmap[o["id"]] = old_beam[tuple(o["value"])]
            else:
                add_ids.add(o["id"])
    new_stem_ids = {o["id"] for o in nobs if o["id"] in add_ids and o["quantity"] == "stem"}
    new_beam_ids = {o["id"] for o in nobs if o["id"] in add_ids and o["quantity"] == "beam_stroke"}
    idmap = {}
    for o in nobs + nabs:
        d = o.get("detail") or {}
        if o["id"] in add_ids or d.get("stem_row_id") in new_stem_ids or d.get("beam_row_id") in new_beam_ids:
            idmap[o["id"]] = "%s:%06d" % (o["id"].split(":")[0], k)
            k += 1
    allmap = {**smap, **bmap, **idmap}
    for kind, lst in (("observations", nobs), ("abstentions", nabs)):
        for o in lst:
            if o["id"] not in idmap:
                continue
            o = copy.deepcopy(o)
            o["id"] = idmap[o["id"]]
            d = o.get("detail") or {}
            ok = True
            for f in ("stem_row_id", "beam_row_id"):
                if f in d:
                    if d[f] in allmap:
                        d[f] = allmap[d[f]]
                    else:
                        ok = False
            if not ok:
                n_skipped += 1
                continue
            o["detail"] = d
            o["basis"] = []
            arm[kind].append(o)
            n_added += 1
    # the cell's "no stem found" abstention is no longer true once a stem is filed
    if new_stem_ids:
        gone = {o["id"] for o in old["abstentions"] if o["quantity"] == "stem"}
        arm["abstentions"] = [o for o in arm["abstentions"] if o["id"] not in gone]
print("injected: new stems", n_new_stems, "rows added", n_added, "skipped (dangling)", n_skipped, flush=True)


def run(rec, label):
    log, _ = rebuild(rec)
    RR.run_stages(log)
    out = log.to_json()
    print("stages done", label, flush=True)
    return out


ctl_out = run(sl, "control")
arm_out = run(arm, "arm")


def readings(r):
    dur, hs = {}, {}
    chain = defaultdict(list)
    for v in r["verdicts"]:
        if v["quantity"] == "duration":
            chain[v["subject"]].append(v)
        elif v["quantity"] == "head_stem" and v["subject"] not in hs:
            hs[v["subject"]] = [v["outcome"], v.get("reason")]
    for g, ch in chain.items():
        sup = {v.get("supersedes") for v in ch if v.get("supersedes")}
        live = [v for v in ch if v["id"] not in sup] or ch
        v = live[-1]
        val = v["value"] if isinstance(v["value"], dict) else {}
        cands = sorted({(c.get("written") if "written" in c else (c.get("value") or {}).get("written"))
                        for c in (v.get("candidates") or []) if isinstance(c, dict)} - {None})
        dur[g] = dict(outcome=v["outcome"], reason=v.get("reason"), written=val.get("written"), cands=cands,
                      decider=v.get("decider"))
    return dur, hs


stored_dur, stored_hs = readings(sl)
cd, ch = readings(ctl_out)
ad, ah = readings(arm_out)
noise = sum(1 for g in stored_dur if g in cd and (stored_dur[g]["outcome"], stored_dur[g]["written"]) != (cd[g]["outcome"], cd[g]["written"]))
print("CONTROL vs stored: durations differing", noise, "of", len(stored_dur), flush=True)
chg_cells = set(changed)
res = {}
for g in sorted(set(cd) | set(ad)):
    cellk = "cell/" + "/".join(g.split("/")[1:5])
    res[g] = dict(stored=stored_dur.get(g), control=cd.get(g), arm=ad.get(g), hs_control=ch.get(g), hs_arm=ah.get(g),
                  in_changed_cell=cellk in chg_cells)
json.dump(dict(changed_cells=changed, systems=[list(s) for s in SYS], control_vs_stored_differ=noise, n_stored=len(stored_dur),
               readings=res), open(OUT + ".json", "w"), indent=0)
json.dump({"verdicts": ctl_out["verdicts"]}, open(OUT + ".control.verdicts.json", "w"))
json.dump({"verdicts": arm_out["verdicts"]}, open(OUT + ".arm.verdicts.json", "w"))
t = Counter()
for g, r in res.items():
    c, a = r["control"], r["arm"]
    if c is None or a is None:
        t["missing"] += 1
        continue
    t["glyphs"] += 1
    if r["in_changed_cell"]:
        t["glyphs_in_changed_cells"] += 1
    kc, ka = (c["outcome"], c["written"]), (a["outcome"], a["written"])
    if kc != ka:
        t["duration_changed"] += 1
        t["dur:%s>%s" % (c["outcome"], a["outcome"])] += 1
    if r["hs_control"] != r["hs_arm"]:
        t["head_stem_changed"] += 1
        t["hs:%s>%s" % (r["hs_control"], r["hs_arm"])] += 1
print("SUMMARY", dict(t))
