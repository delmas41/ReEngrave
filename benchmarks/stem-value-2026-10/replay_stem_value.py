"""ROADMAP 2.209 probe. Replays a plate's saved GATHER rows (lane-report slices of a night record) through
ADJUDICATE..EVALUATE with the current tree (no gather, no detector) and writes, per plate, every head whose
standing duration `share_stem_value` rewrote, with the stem-value verdict's evidence and the tip member's box.

    python3 benchmarks/stem-value-2026-10/replay_stem_value.py PLATE TAG OUT.json [PAGES comma]
Env flags (OMR_STEM_...) are whatever the shell has: run once OFF, once ON.
"""
import json, os, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.omr.staged import lane_report as LR
from tools.omr.staged.review import rerun as RR

plate, tag, out = sys.argv[1], sys.argv[2], sys.argv[3]
pages = [int(p) for p in sys.argv[4].split(",")] if len(sys.argv) > 4 else None
rec = LR.load_slices(LR.slice_dir(plate, tag))
if pages is not None:
    keep = set(pages)
    for k in ("observations", "abstentions"):
        rec[k] = [r for r in rec[k] if LR.page_of(r.get("subject")) is None or LR.page_of(r.get("subject")) in keep]
rec["verdicts"] = []
log, _ = RR.rebuild_gather(rec)
RR.run_stages(log)
j = log.to_json()
V = j["verdicts"]; O = j["observations"]
box = {}
for o in O:
    if o["quantity"] == "glyph_box":
        box[o["subject"]] = o
live = {}
gs = {o["subject"]: o for o in O if o["quantity"] == "glyph_strokes"}
so = {v["subject"]: v for v in V if v["quantity"] == "stroke_owner"}
def cell_of(sub):
    return "cell/" + "/".join(sub.split("/")[1:5])
def own_state(sub):
    g = gs.get(sub)
    if g is None:
        return None
    ords = g["value"]
    c = so.get(cell_of(sub))
    st = ((c or {}).get("detail") or {}).get("strokes") or {}
    return [dict(ord=o, raw=(st.get(str(o)) or st.get(o))) for o in ords]
for v in V:
    live.setdefault((v["subject"], v["quantity"]), []).append(v)
res = []
def mem(k):
    dv = [x for x in live.get((k, "duration"), []) if not x.get("supersedes_of")]
    # the duration verdict BEFORE share_stem_value: the one that was superseded
    chain = live.get((k, "duration"), [])
    first = chain[0] if chain else None
    return dict(key=k, score=box.get(k, {}).get("score"), cls=(box.get(k, {}).get("value") or [None])[0],
                first=(None if first is None else dict(decider=first.get("decider"), reason=first.get("reason"), outcome=first.get("outcome"),
                       value=({x: (first.get("value") or {}).get(x) for x in ("written", "dots", "beam_levels")} if isinstance(first.get("value"), dict) else None))),
                strokes=own_state(k))
for v in V:
    if v["quantity"] == "duration" and v.get("decider") == "share_stem_value" and v.get("reason") == "stem_value_follows":
        sv = [x for x in live.get((v["subject"], "stem_value"), [])][-1]
        d = sv.get("detail") or {}
        ev = d.get("evidence") or {}
        tip = ev.get("tip_member")
        res.append(dict(head=v["subject"], evidence=ev, member_info=[mem(k) for k in (d.get("members") or [])], was=(v.get("detail") or {}).get("was"),
                        now={k: v["value"].get(k) for k in ("written", "dots", "beam_levels", "beats")},
                        sv_reason=sv.get("reason"), members=d.get("members"), tip=tip,
                        levels_from=ev.get("levels_from"), base_from=ev.get("base_from"),
                        head_box=box.get(v["subject"], {}).get("value"),
                        tip_box=(box.get(tip, {}).get("value") if tip else None),
                        tip_score=(box.get(tip, {}).get("score") if tip else None),
                        head_score=box.get(v["subject"], {}).get("score"),
                        tip_strokes=(own_state(tip) if tip else None),
                        tip_refusal=[(x.get("outcome"), x.get("value")) for x in live.get((tip, "notehead_is_not_a_notehead"), [])][-1:] if tip else None))
# ── every multi-head stem: how far is the tip-most member's centre from the stem's tip, in staff spaces?
space = {}
for o in O:
    if o["quantity"] == "cell_staff_space":
        space[o["subject"]] = o["value"]
dirv = {}
for v in V:
    if v["quantity"] == "stem_direction" and v.get("outcome") == "decided":
        dirv[v["subject"]] = v["value"]
hs = {}
for v in V:
    if v["quantity"] == "head_stem" and v.get("outcome") == "decided":
        hs[v["subject"]] = v
stems = {}
for sub, v in hs.items():
    stems.setdefault(v["value"], []).append(sub)
tipdist = []
for sid, subs in stems.items():
    if len(subs) < 2:
        continue
    v0 = hs[subs[0]]
    sb = (v0.get("detail") or {}).get("stem_box")
    if not sb:
        continue
    cellkey = "/".join(subs[0].split("/")[:5])
    sp = space.get("cell/" + "/".join(subs[0].split("/")[1:5])) or space.get(cellkey)
    ds = {dirv.get(x) for x in subs} - {None}
    if len(ds) != 1 or not sp:
        continue
    dr = next(iter(ds))
    tip_y = sb[1] if dr == "up" else sb[1] + sb[3]
    ms = []
    for x in subs:
        b = box.get(x, {}).get("value")
        if b:
            ms.append((abs((b[2] + b[4] / 2.0) - tip_y) / float(sp), x, box[x].get("score")))
    ms.sort()
    tipdist.append(dict(stem=sid, dir=dr, stem_len_sp=sb[3] / float(sp), members=ms))
json.dump(tipdist, open(out.replace(".off.json", ".tipdist.json"), "w"))
excluded = [dict(head=v["subject"], score=box.get(v["subject"], {}).get("score"), cls=(box.get(v["subject"], {}).get("value") or [None])[0],
                dur=[(x.get("outcome"), (x.get("value") or {}).get("written") if isinstance(x.get("value"), dict) else None) for x in live.get((v["subject"], "duration"), [])][-1:])
            for v in V if v["quantity"] == "stem_value" and v.get("reason") == "not_a_member"]
json.dump(dict(plate=plate, excluded_not_a_member=excluded, tag=tag, pages=pages, n_stem_value_rewrites=len(res), rewrites=res), open(out, "w"), default=str)
print(plate, "rewrites", len(res), "decided-moved", sum(1 for r in res if (r["was"] or {}).get("outcome") == "decided"))
