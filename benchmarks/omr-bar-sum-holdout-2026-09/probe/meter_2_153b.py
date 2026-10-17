"""ROADMAP 2.153b -- why does `OMR_BEAM_LEVEL_NEEDS_A_JOINED_STEM` move the meter in force on Brahms? Replays pages
0..LAST (every page before the target, so the meter carry is the whole record's) OFF vs ON and dumps, for the systems of
the named pages: every `meter` verdict (id, outcome, decider, reason, value, detail support/bars_agree/bars_disagree) and
the live duration of every whole rest the whole replay saw change. CONTROL: those whole rests' values must equal the whole
replay's (out/2.153b/whole_brahms.json).
usage: meter_2_153b.py LAST PAGE [PAGE ...] -> out/2.153b/meter_p<LAST>.json"""
import collections
import json
import os
import sys

sys.path.insert(0, ".")
from tools.omr.staged.review import rerun as RR  # noqa: E402

SD = ("/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-start-here-go-cbd2bc/"
      "97504ff3-7ad5-4ac2-8be1-95887e8a9382/scratchpad/slices/brahms")
LAST = int(sys.argv[1])
PAGES = {int(x) for x in sys.argv[2:]}
FLAG = "OMR_BEAM_LEVEL_NEEDS_A_JOINED_STEM"


def rows(tag, kind):
    p = os.path.join(SD, "%s.%s.jsonl" % (tag, kind))
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []


tags = ["common"] + ["p%02d" % p for p in range(0, LAST + 1)]
rec = {k: [r for t in tags for r in rows(t, k)] for k in ("observations", "abstentions")}
rec["verdicts"] = []
W = json.load(open("out/2.153b/whole_brahms.json"))["changed"]
rests = {g: d for g, d in W.items() if int(g.split("/")[1]) in PAGES
         and "whole_rest_means_the_bar" in (d["off"]["reason"], d["on"]["reason"])}
out = {"pages": sorted(PAGES), "arms": {}}
for arm, val in (("off", None), ("on", "1")):
    if val is None:
        os.environ.pop(FLAG, None)
    else:
        os.environ[FLAG] = val
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    vs = log.to_json()["verdicts"]
    met = []
    for v in vs:
        p = v["subject"].split("/")
        if v["quantity"] == "meter" and len(p) >= 3 and p[1].isdigit() and int(p[1]) in PAGES:
            d = v.get("detail") or {}
            met.append(dict(id=v["id"], subject=v["subject"], outcome=v["outcome"], decider=v.get("decider"),
                            reason=v.get("reason"), value=v.get("value"), supersedes=v.get("supersedes"),
                            margin=v.get("margin"), basis_n=len(v.get("basis") or v.get("used") or ()),
                            detail={k: d.get(k) for k in ("carried_from", "pages_since_read", "support", "floor",
                                                         "bars_agree", "bars_disagree", "bar_lengths_seen",
                                                         "instead_of", "skipped_uncorroborated")}))
    chains = collections.defaultdict(list)
    for v in vs:
        if v["subject"] in rests and v["quantity"] == "duration":
            chains[v["subject"]].append(v)
    rv = {}
    for g, ch in chains.items():
        sup = {x.get("supersedes") for x in ch if x.get("supersedes")}
        x = ([y for y in ch if y["id"] not in sup] or ch)[-1]
        rv[g] = dict(id=x["id"], beats=(x["value"] or {}).get("beats") if isinstance(x["value"], dict) else None,
                     reason=x.get("reason"))
    ctl = collections.Counter("agree" if rv.get(g, {}).get("beats") == rests[g][arm]["beats"] else "differ"
                              for g in rests)
    out["arms"][arm] = dict(meter=met, rests=rv, control=dict(ctl))
    print(arm, "meter verdicts", len(met), "rests", len(rv), "control vs whole replay", dict(ctl), flush=True)
    del log
os.environ.pop(FLAG, None)
json.dump(out, open("out/2.153b/meter_p%02d.json" % LAST, "w"), indent=1, default=str)
