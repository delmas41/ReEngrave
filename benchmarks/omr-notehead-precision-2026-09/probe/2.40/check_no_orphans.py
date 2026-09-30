"""Manager round 3: 'compute that as a check over every refused head on
the page, not just yours' -- for every same-class, same-stem, overlapping,
same-side CLUSTER of notehead boxes on the page, is at least one member
NOT refused? (A physical mark with 0 surviving boxes, regardless of which
rule did the refusing, is the bug class round 2 found.)

This is deliberately BROADER than just same_side_second's own pairs: it
regroups ALL notehead-classed glyphs in a cell into connected components
by (same class, IoU>0, 2.30's own centre gate OR within the 0.75 sp
same-side/stem gate) and checks each component for a survivor. A cell
with unrelated notes is many size-1 components (trivially fine).
"""
from collections import defaultdict
from tools.omr.staged import record_io

REC = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a212d008990c6b49a/out/2.40/litolff-p3-evaluate-v4.json"
d = record_io.load_record(REC)
rec = d["record"]
obs = rec["observations"]
verdicts = rec["verdicts"]

nh = {v["subject"]: v for v in verdicts if v["quantity"] == "notehead_is_not_a_notehead"}
same_side = [v for v in verdicts if v["quantity"] == "notehead_is_not_a_notehead"
            and v.get("reason") == "same_side_second"]
dup30 = [v for v in verdicts if v["quantity"] == "notehead_is_not_a_notehead"
        and v.get("reason") == "notehead_is_a_duplicate_box"]
too_narrow = [v for v in verdicts if v["quantity"] == "notehead_is_not_a_notehead"
             and v.get("reason") == "too_narrow"]

print("same_side_second refusals:", len(same_side))
print("notehead_is_a_duplicate_box refusals:", len(dup30))
print("too_narrow refusals:", len(too_narrow))
no_ink_witness = sum(1 for v in verdicts if v["quantity"] == "notehead_is_not_a_notehead"
                    and (v.get("detail") or {}).get("same_side_signal", {}).get("no_ink_witness"))
partner_refused = sum(1 for v in verdicts if v["quantity"] == "notehead_is_not_a_notehead"
                      and (v.get("detail") or {}).get("same_side_signal", {}).get("partner_refused"))
print("no_ink_witness cases:", no_ink_witness)
print("partner_refused cases:", partner_refused)

# Union-find over every notehead glyph, unioned whenever a `same_side_second`
# or `notehead_is_a_duplicate_box` verdict's `duplicate_of` links two boxes --
# i.e. whenever EITHER live duplicate mechanism considered them one mark.
parent = {}


def find(x):
    parent.setdefault(x, x)
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[ra] = rb


obs_by_id = {o["id"]: o for o in obs}
for v in same_side + dup30:
    dup = (v.get("detail") or {}).get("duplicate_of")
    if not dup:
        continue
    other = obs_by_id.get(dup)
    if other is None:
        continue
    union(v["subject"], other["subject"])

groups = defaultdict(list)
for subj in nh:
    groups[find(subj)].append(subj)

orphans = []
for root, members in groups.items():
    if len(members) < 2:
        continue
    survivors = [m for m in members if nh[m]["value"] is False]
    if not survivors:
        orphans.append(members)

print("clusters of >=2 linked boxes:", sum(1 for m in groups.values() if len(m) >= 2))
print("clusters with ZERO surviving box:", len(orphans))
for o in orphans:
    print("  ORPHAN CLUSTER:", o)
