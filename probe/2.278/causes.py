"""2.278: cause buckets from the verdict's own detail. usage: causes.py DIAG.jsonl"""
import json, sys, collections
R = [json.loads(l) for l in open(sys.argv[1])]
N = [r for r in R if r["fate"] == "duration_narrowed"]


def cause(r):
    reason = r["reason"]; d = r.get("d", {})
    if reason in ("beams_ambiguous", "beam_discounted_uncertain", "beam_certain_not_joined"):
        if not d.get("stems_attached"):
            return "A beam family: head has NO own stem found (stems_attached=0)"
        if reason == "beam_certain_not_joined":
            return "B beam family: stroke counted certain but join reader says not joined"
        if reason == "beams_ambiguous":
            return "C beam family: stroke over the stem possible, not certain (certain<possible)"
        if (d.get("beams_not_by_ink") or 0) > 0:
            return "D beam family: every stroke refused by the ink test (thin/through heads), none certain"
        if (d.get("beams_far_side") or 0) + (d.get("beams_neighbour_staff") or 0) + (d.get("beams_decided_arc") or 0) + (d.get("beams_beyond_stem") or 0) + (d.get("beams_ledger_line") or 0) > 0:
            return "E beam family: strokes discounted (far side / neighbour staff / arc / beyond / ledger)"
        return "F beam family: detector box only (no CV beam stroke), tip not read clean"
    if reason in ("flags_disagree", "flag_ink_unread", "tip_readers_disagree"):
        return "G flag family: " + reason
    if reason == "head_fill_from_ink":
        return "H head fill (hollow/filled) from ink"
    if reason in ("open_head_flag_contradiction", "whole_class_filled_on_a_stem"):
        return "I head class vs stem/flag: " + reason
    return "J other: " + reason


c = collections.Counter(cause(r) for r in N)
for k in sorted(c): print(c[k], k)
print(len(N))
