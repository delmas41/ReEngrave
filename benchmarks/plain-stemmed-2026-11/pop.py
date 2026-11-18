import json, collections
S = "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad"
D = json.load(open(S + "/p314/tally1.json"))
FLAG_REASONS = {"flag_ink_unread", "flags_disagree", "hooks_counted", "open_head_flag_contradiction", "tip_readers_disagree"}


def has_ink(it, r):
    lv = [x for x in (it.get("levels") or []) if x]
    if lv:
        return "levels"
    if it.get("beams_by_stem"):
        return "beams_by_stem"
    if it["reason"] in FLAG_REASONS:
        return "flag_reason"
    if it["mechanism"].startswith(("beam_ink_over", "beam_stroke_seen", "beam_joined", "stroke_at_stem_tip")):
        return "beam_mechanism"
    if (it.get("cv_beams") or it.get("yolo_beams")) and it["mechanism"].startswith("stroke_refused"):
        return "beam_box_seen"
    return None


POP = {}
for plate, rows in D.items():
    c = collections.Counter()
    pop = []
    for r in rows:
        h = has_ink(r["it"], r)
        c[h] += 1
        if h is None:
            pop.append(r)
    POP[plate] = pop
    print(plate, len(rows), dict(c), "no-ink population", len(pop))
    print("   by mech", collections.Counter(r["it"]["mechanism"] for r in pop).most_common())
json.dump(POP, open(S + "/p314/pop.json", "w"))
