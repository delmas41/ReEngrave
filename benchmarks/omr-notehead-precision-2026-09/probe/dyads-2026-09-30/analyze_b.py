"""Population B: single notehead boxes whose OWN box height is already
about two heads tall (>=1.85 staff spaces, vs a ~1.2-1.5 sp single-head
norm measured above) -- candidates for 'one box hides two merged heads'.
"""
import pickle, json
from collections import defaultdict

PKL = "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-acceptance-measure-notehead-box-e75821/2c34bf69-0e00-4748-a821-6f4862e751be/scratchpad/page3.pkl"
d = pickle.load(open(PKL, "rb"))
gbox = {o["subject"]: o for o in d["by_q_page"]["glyph_box"]}
nclass = {o["subject"]: o["value"] for o in d["by_q_page"]["notehead_class"]}
cell_ss = {o["subject"]: o["value"] for o in d["by_q_page"]["cell_staff_space"]}
notehead_verdict = {v["subject"]: v for v in d["verd_by_q_page"]["notehead_is_not_a_notehead"]}
event_verdict = {v["subject"]: v for v in d["verd_by_q_page"]["event"]}
duration_verdict = {v["subject"]: v for v in d["verd_by_q_page"]["duration"]}
stems_by_cell = defaultdict(list)
for o in d["by_q_page"]["stem"]:
    stems_by_cell[o["subject"]].append(o["value"])

THRESH = 1.65

cands = []
for s, cls in nclass.items():
    _, x, y, w, h = gbox[s]["value"]
    cellkey = "/".join(["cell"] + s.split("/")[1:5])
    ss = cell_ss.get(cellkey, 100.0)
    h_sp = h / ss
    if h_sp < THRESH:
        continue
    refused = notehead_verdict.get(s, {}).get("value")
    reason = notehead_verdict.get(s, {}).get("reason")
    dur = duration_verdict.get(s, {})
    cands.append(dict(subject=s, cls=cls, height_sp=h_sp, cell=cellkey,
                       refused=refused, reason=reason,
                       n_stems_in_cell=len(stems_by_cell.get(cellkey, [])),
                       duration=dur.get("value"), duration_reason=dur.get("reason")))

cands.sort(key=lambda c: -c["height_sp"])
print("population B candidates (box height >= 1.85 staff spaces):", len(cands))
for c in cands:
    print(round(c["height_sp"], 2), c["subject"], c["cls"], "refused" if c["refused"] else "stands", c["reason"], c["duration"])

json.dump(cands, open("/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-acceptance-measure-notehead-box-e75821/2c34bf69-0e00-4748-a821-6f4862e751be/scratchpad/pop_b.json", "w"), indent=1, default=str)
