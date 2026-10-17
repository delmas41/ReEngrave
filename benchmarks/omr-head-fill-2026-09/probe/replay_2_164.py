"""ROADMAP 2.164 -- replay a night record (whole, or a slice file) through every stage with review.rerun (2.157-fixed),
flag `OMR_ARC_TAIL_NOT_A_HEAD` OFF vs ON, every other flag as shipped (2.158 ON). The night records predate this lane's
GATHER row, so `Q.HEAD_OVAL` is INJECTED in the ON arm from `scan_2_164.py` (the same `head_oval.oval_width` on the same
600-dpi page raster `pws.page.binary` holds) for every left-edge head the scan found -- exactly the rows GATHER would file
that the rule can read (a left-edge head with no previous-bar arc is never refused, row or not).
CONTROL: the OFF arm's live duration verdict vs the stored one, every glyph (the stored record predates 2.158 ON, so its
lone-event guesses differ; counted, not hidden).
Writes OUT.json {doc, control, changed{glyph:{off,on}}, refused[...]} and OUTPREFIX.<arm>.record.json mini records.
usage: replay_2_164.py RECORD_OR_SLICE.json SCAN.json OUT.json OUTPREFIX   (OUTPREFIX '-' writes no mini records)"""
import collections
import json
import os
import sys
import time

sys.path.insert(0, ".")
from tools.omr.staged.review import rerun as RR  # noqa: E402

SRC, SCAN, OUT, PREFIX = sys.argv[1:5]
FLAG = "OMR_ARC_TAIL_NOT_A_HEAD"


def live(verdicts, q):
    chains = collections.defaultdict(list)
    for v in verdicts:
        if v["quantity"] == q and v["subject"].startswith("glyph/"):
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
                reason=v.get("reason"),
                cands=sorted({(c.get("value") or {}).get("beats") for c in (v.get("candidates") or [])
                              if isinstance(c.get("value"), dict)} - {None}) or None)


def key(b):
    return None if b is None else (b["outcome"], b["written"], b["dots"], b["beats"], tuple(b["cands"] or ()), b["reason"])


def summary(vs):
    nn = {g: (v.get("value"), v.get("reason")) for g, v in live(vs, "notehead_is_not_a_notehead").items()}
    du = {g: brief(v) for g, v in live(vs, "duration").items()}
    pi = {g: v.get("value") for g, v in live(vs, "pitch").items()}
    return nn, du, pi


def inject(obs, hits):
    have = {o["subject"] for o in obs if o["quantity"] == "glyph_box"}
    frame = {o["subject"]: o.get("frame") for o in obs if o["quantity"] == "glyph_box"}
    n = 0
    for h in hits:
        if h["glyph"] not in have or not h.get("oval"):
            continue
        d = dict(h["oval"])
        d.update(left_gap_sp=h["left_gap_sp"], space_page_px=round(h["sp"], 3))
        obs.append({"id": "obs:h164%05d" % n, "subject": h["glyph"], "quantity": "head_oval",
                    "value": h["oval"]["oval_width_sp"], "reader": "cv_head_oval", "frame": frame[h["glyph"]],
                    "score": None, "detail": d, "basis": []})
        n += 1
    return n


t0 = time.time()
raw = json.load(open(SRC))
rec = raw.get("record", raw)
hits = json.load(open(SCAN))["hits"]
stored_du = {g: brief(v) for g, v in live(rec.get("verdicts") or (), "duration").items()}
base_obs = rec["observations"]
print("rows", len(base_obs), "stored glyphs", len(stored_du), flush=True)
arms = {}
for arm in ("off", "on"):
    os.environ.pop(FLAG, None)
    obs = list(base_obs)
    if arm == "on":
        os.environ[FLAG] = "1"
        print("injected", inject(obs, hits), flush=True)
    r = {"observations": obs, "abstentions": rec.get("abstentions") or [], "verdicts": []}
    log, _ = RR.rebuild_gather(r)
    RR.run_stages(log)
    vs = log.to_json()["verdicts"]
    del log
    arms[arm] = summary(vs)
    if PREFIX != "-":
        json.dump({"record": {"observations": obs, "abstentions": [], "verdicts": vs}},
                  open("%s.%s.record.json" % (PREFIX, arm), "w"), default=str)
    del vs, r, obs
    print(arm, "%.0fs" % (time.time() - t0), flush=True)
os.environ.pop(FLAG, None)
ctl = collections.Counter("agree" if key(arms["off"][1].get(g)) == key(b) else "differ" for g, b in stored_du.items())
ctl_reasons = collections.Counter((arms["off"][1].get(g) or {}).get("reason") for g, b in stored_du.items()
                                  if key(arms["off"][1].get(g)) != key(b))
changed = {}
for g in sorted(set(arms["off"][0]) | set(arms["on"][0]) | set(arms["off"][1]) | set(arms["on"][1])):
    o = (arms["off"][0].get(g), arms["off"][1].get(g), arms["off"][2].get(g))
    n = (arms["on"][0].get(g), arms["on"][1].get(g), arms["on"][2].get(g))
    if o[0] != n[0] or key(o[1]) != key(n[1]) or o[2] != n[2]:
        changed[g] = dict(off=dict(nn=o[0], dur=o[1], pitch=o[2]), on=dict(nn=n[0], dur=n[1], pitch=n[2]))
refused = [g for g, c in changed.items() if (c["on"]["nn"] or (None, None))[1] == "is_an_arc_tail"]
json.dump(dict(src=SRC, control=dict(ctl), control_reasons=dict(ctl_reasons), changed=changed, refused=refused,
               seconds=round(time.time() - t0)), open(OUT, "w"), indent=0, default=str)
print("control", dict(ctl), dict(ctl_reasons), "| changed", len(changed), "| refused is_an_arc_tail", len(refused),
      "%.0fs" % (time.time() - t0), flush=True)
