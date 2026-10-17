"""ROADMAP 2.161 -- replay the 20261016-night records page by page (the per-page slices: common rows + one page) with the
fixed harness (`review.rerun.rebuild_gather` + `run_stages`, 2.157), flag `OMR_HEAD_STEM_BRIDGE` OFF vs ON, every other
flag as shipped (2.159 `OMR_HEAD_FILL_LOCATED_BOX` ON). The night records predate both GATHER rows, so 2.159's
`interior_white_located` is INJECTED from `located_<doc>.json` (2.159's probe) and this lane's `stem_bridge` from
`bridge_<doc>.json` (bridge_2_161.py: the production `gather.head_stem_bridge` on cells re-cut as production cuts them).
Only pages holding a bridged head can change (the flag reads nothing else); usage takes them from BRIDGE.json unless
PAGES are given. A per-page replay is faithful for ADJUDICATE (no meter carried in from earlier pages, so the
later stages are compared OFF vs ON only, never against the stored record).
CONTROL: the OFF arm's first ADJUDICATE duration verdict vs the stored one, every glyph (differences may only be 2.159's).
usage: replay_pages_2_161.py SLICEDIR DOC LOCATED.json BRIDGE.json OUT.json [PAGES...]"""
import collections
import glob
import json
import os
import sys
import time

sys.path.insert(0, ".")
from tools.omr.staged.review import rerun as RR  # noqa: E402

SD, DOC, LOC, BRG, OUT = sys.argv[1:6]
FLAG = "OMR_HEAD_STEM_BRIDGE"
BRIDGE = json.load(open(BRG))
ONLY = {int(p) for p in sys.argv[6:]} or {int(s.split("/")[1]) for s in BRIDGE}
D = os.path.join(SD, DOC)
LOCATED = json.load(open(LOC))


def rows(path):
    return [json.loads(line) for line in open(path)] if os.path.exists(path) else []


def inject(obs):
    boxes = {o["subject"]: o for o in obs if o["quantity"] == "glyph_box"}
    n = 0
    for o in obs:
        if o["quantity"] != "notehead_ink" or o["subject"] not in LOCATED or o["subject"] not in boxes:
            continue
        L = LOCATED[o["subject"]]
        b = boxes[o["subject"]]
        _, x, y, w, h = b["value"]
        bb = b["detail"]["bbox_page_px"]
        k = (bb[2] - bb[0]) / float(w)
        px, py, pw, ph = L["box_page"]
        cell_box = [round(x + (px - bb[0]) / k, 2), round(y + (py - bb[1]) / k, 2), round(pw / k, 2), round(ph / k, 2)]
        src = {"recentre": "notehead_recentre"}.get(L["src"], L["src"])
        o["detail"] = dict(o.get("detail") or {})
        o["detail"]["interior_white_located"] = {**L["iw"], "frame": "page", "box_cell": cell_box, "located_by": src}
        n += 1
    for o in obs:
        if o["quantity"] == "notehead_ink" and o["subject"] in BRIDGE:
            b = {k: v for k, v in BRIDGE[o["subject"]].items() if k not in ("name", "sp", "head_box")}
            o["detail"] = dict(o.get("detail") or {})
            o["detail"]["stem_bridge"] = b
            n += 1000
    return n


def first_adj(verdicts):
    out = {}
    for v in verdicts:
        if v["quantity"] == "duration" and v["subject"].startswith("glyph/") \
                and str(v.get("decider", "")).endswith("adjudicate_duration") and v["subject"] not in out:
            out[v["subject"]] = v
    return out


def live(verdicts):
    chains = collections.defaultdict(list)
    for v in verdicts:
        if v["quantity"] == "duration" and v["subject"].startswith("glyph/"):
            chains[v["subject"]].append(v)
    out = {}
    for g, ch in chains.items():
        sup = {x.get("supersedes") for x in ch if x.get("supersedes")}
        out[g] = ([x for x in ch if x["id"] not in sup] or ch)[-1]
    return out


def brief(v):
    if v is None:
        return None
    val = v["value"] if isinstance(v["value"], dict) else {}
    return dict(outcome=v["outcome"], written=val.get("written"), dots=val.get("dots"), beats=val.get("beats"),
                reason=v.get("reason"), decider=v.get("decider"),
                cands=sorted({(c.get("value") or {}).get("written") for c in (v.get("candidates") or [])
                              if isinstance(c.get("value"), dict)} - {None}) or None,
                hff=((v.get("detail") or {}).get("head_fill_first") or {}).get("located_by"),
                bridged=bool(((v.get("detail") or {}).get("head_fill_first") or {}).get("stem_bridge")))


def key(b):
    return None if b is None else (b["outcome"], b["written"], b["dots"], b["beats"], tuple(b["cands"] or ()))


common_o, common_a = rows(os.path.join(D, "common.observations.jsonl")), rows(os.path.join(D, "common.abstentions.jsonl"))
res = {"doc": DOC, "pages": {}, "changed": {}, "control_rows": []}
t0 = time.time()
for p in sorted(glob.glob(os.path.join(D, "p*.observations.jsonl"))):
    pg = int(os.path.basename(p)[1:3])
    if ONLY and pg not in ONLY:
        continue
    obs = common_o + rows(p)
    rec = {"observations": obs, "abstentions": common_a + rows(p.replace("observations", "abstentions")),
           "verdicts": []}
    n_inj = inject(rec["observations"])
    stored = {g: brief(v) for g, v in first_adj(rows(p.replace("observations", "verdicts"))).items()}
    arms = {}
    for arm, val in (("off", None), ("on", "1")):
        if val is None:
            os.environ.pop(FLAG, None)
        else:
            os.environ[FLAG] = val
        log, _ = RR.rebuild_gather(rec)
        RR.run_stages(log)
        vs = log.to_json()["verdicts"]
        arms[arm] = ({g: brief(v) for g, v in first_adj(vs).items()}, {g: brief(v) for g, v in live(vs).items()})
        del log, vs
    os.environ.pop(FLAG, None)
    ctl = collections.Counter("agree" if key(arms["off"][0].get(g)) == key(b) else "differ" for g, b in stored.items())
    res["control_rows"] += [dict(glyph=g, stored=b, off=arms["off"][0].get(g)) for g, b in stored.items()
                            if key(arms["off"][0].get(g)) != key(b)][:20]
    ch = 0
    for g in sorted(set(arms["off"][0]) | set(arms["on"][0])):
        a0, a1 = arms["off"][0].get(g), arms["on"][0].get(g)
        l0, l1 = arms["off"][1].get(g), arms["on"][1].get(g)
        if key(a0) != key(a1) or key(l0) != key(l1):
            res["changed"][g] = dict(adj_off=a0, adj_on=a1, live_off=l0, live_on=l1)
            ch += 1
    res["pages"][pg] = dict(injected=n_inj, glyphs=len(arms["off"][0]), control=dict(ctl), changed=ch)
    print(DOC, "p%02d" % pg, "injected", n_inj, "control", dict(ctl), "changed", ch, "%.0fs" % (time.time() - t0),
          flush=True)
    json.dump(res, open(OUT, "w"), indent=0)
print(DOC, "done", sum(x["changed"] for x in res["pages"].values()), "changed", "%.0fs" % (time.time() - t0))
