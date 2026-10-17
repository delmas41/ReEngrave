"""ROADMAP 2.160 (from replay_2_158.py; the flag below is 2.160's guard, 2.158 at its default ON in both arms) -- replay a night record (whole, or a slice file) through INFER with review.rerun (2.157-fixed), flag
`OMR_LONE_EVENT_FILLS_BAR` OFF vs ON; every other flag as shipped. STAGED ADJUDICATE..INFER (+ the second EVALUATE).
CONTROL: the OFF arm's live duration verdict vs the stored live one, every glyph (tools at HEAD == the records' commit
1d42c4aa outside acceptance.py, so a faithful replay differs on 0; it can fail).
Writes OUT.json {doc, glyphs, control, changed{glyph:{off,on}}} and OUTPREFIX.<arm>.record.json mini records (observations +
the replay's verdicts) for `python3 -m tools.omr.staged.judged score`.
usage: replay_2_160.py RECORD_OR_SLICE.json OUT.json OUTPREFIX   (OUTPREFIX '-' writes no mini records)"""
import collections
import json
import os
import sys
import time

sys.path.insert(0, ".")
from tools.omr.staged.review import rerun as RR  # noqa: E402

SRC, OUT, PREFIX = sys.argv[1:4]
FLAG = "OMR_LONE_EVENT_HEAD_INK_GUARD"


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
                decider=v.get("decider"), reason=v.get("reason"),
                cands=sorted({(c.get("value") or {}).get("beats") for c in (v.get("candidates") or [])
                              if isinstance(c.get("value"), dict)} - {None}) or None)


def key(b):
    return None if b is None else (b["outcome"], b["written"], b["dots"], b["beats"], tuple(b["cands"] or ()), b["reason"])


t0 = time.time()
raw = json.load(open(SRC))
rec = raw.get("record", raw)
stored = {g: brief(v) for g, v in live(rec.get("verdicts") or ()).items()}
print("rows", len(rec["observations"]), len(rec.get("abstentions") or ()), "stored glyphs", len(stored), flush=True)
arms = {}
for arm, val in (("off", None), ("on", "1")):
    os.environ.pop("OMR_LONE_EVENT_FILLS_BAR", None)
    if val is None:
        os.environ.pop(FLAG, None)
    else:
        os.environ[FLAG] = val
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    vs = log.to_json()["verdicts"]
    del log
    arms[arm] = {g: brief(v) for g, v in live(vs).items()}
    if PREFIX != "-":
        json.dump({"record": {"observations": rec["observations"], "abstentions": [], "verdicts": vs}},
                  open("%s.%s.record.json" % (PREFIX, arm), "w"), default=str)
    del vs
    print(arm, len(arms[arm]), "%.0fs" % (time.time() - t0), flush=True)
os.environ.pop(FLAG, None)
ctl = collections.Counter("agree" if key(arms["off"].get(g)) == key(b) else "differ" for g, b in stored.items())
ctl_rows = [dict(glyph=g, stored=b, off=arms["off"].get(g)) for g, b in stored.items() if key(arms["off"].get(g)) != key(b)]
changed = {g: dict(off=arms["off"].get(g), on=arms["on"].get(g))
           for g in sorted(set(arms["off"]) | set(arms["on"])) if key(arms["off"].get(g)) != key(arms["on"].get(g))}
json.dump(dict(src=SRC, glyphs=len(arms["off"]), control=dict(ctl), control_rows=ctl_rows[:200], changed=changed,
               seconds=round(time.time() - t0)), open(OUT, "w"), indent=0)
print("glyphs", len(arms["off"]), "control", dict(ctl), "changed", len(changed), "%.0fs" % (time.time() - t0), flush=True)
