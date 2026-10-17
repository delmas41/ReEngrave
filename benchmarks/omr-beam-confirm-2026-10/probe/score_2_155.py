"""ROADMAP 2.155 -- score Sean's 20 tile answers (out/print/2.155-review/answers.json) against base and arm.

Arms: A = the tile pages re-gathered `--through adjudicate` with shipped defaults, base vs `OMR_STEM_AT_BAR_EDGE=1`
(out/2.155/tiles_{litolff,brahms}_{base,edge}.record.json); B (changed + control tiles only) = Litolff p1/p2/p10 with the 2.153
rule ON in both arms (out/2.155/litolff_p1_2_10_{base,edge}.record.json).
Per tile: right (decided = Sean), wrong, narrowed_right (a narrowing holding Sean's value), narrowed_wrong, refused (no duration:
right only for a non-note), and for grace notes the value written (no reader marks a grace note). Writes the verdicts into
answers.json (base/arm/verdict per tile, per arm set) and prints the counts.
usage: score_2_155.py"""
import json

SEAN = {"16": 0.25, "8": 0.5, "4": 1.0, "16th grace note": 0.25}


def load(p):
    r = json.load(open(p))
    return r.get("record", r)


def cand_written(c):
    if not isinstance(c, dict):
        return None
    if "written" in c:
        return c["written"]
    v = c.get("value")
    return v.get("written") if isinstance(v, dict) else None


def reading(r, g):
    """The STANDING duration verdict of `g` (last in its supersession chain) + the head's class and notehead refusal."""
    ch = [v for v in r["verdicts"] if v["subject"] == g and v["quantity"] == "duration"]
    sup = {v.get("supersedes") for v in ch if v.get("supersedes")}
    live = [v for v in ch if v["id"] not in sup]
    out = {"cls": next((o["value"][0] for o in r["observations"] if o["subject"] == g and o["quantity"] == "glyph_box"), None)}
    nn = next((v for v in r["verdicts"] if v["subject"] == g and v["quantity"] == "notehead_is_not_a_notehead"), None)
    out["not_a_head"] = None if nn is None else (nn["outcome"], nn["value"])
    if not live:
        out.update(outcome="absent")
        return out
    v = live[-1]
    val = v["value"] if isinstance(v["value"], dict) else {}
    out.update(outcome=v["outcome"], reason=v.get("reason"), decider=v.get("decider"), written=val.get("written"),
               cands=sorted({c for c in (cand_written(c) for c in (v.get("candidates") or [])) if c is not None}))
    return out


def verdict(sean, rd):
    if sean == "flat accidental":
        return "right" if rd["outcome"] in ("abstained", "absent") or (rd.get("not_a_head") or (None, None))[1] is True else "wrong"
    want = SEAN[sean]
    if rd["outcome"] == "decided":
        return "right" if rd["written"] == want else "wrong"
    if rd["outcome"] == "narrowed":
        return "narrowed_right" if want in rd["cands"] else "narrowed_wrong"
    return "refused"


if __name__ == "__main__":
    ans = json.load(open("out/print/2.155-review/answers.json"))
    sets = {"defaults": {d: (load("out/2.155/tiles_%s_base.record.json" % d), load("out/2.155/tiles_%s_edge.record.json" % d))
                         for d in ("litolff", "brahms")},
            "rule_2153_on": {"litolff": (load("out/2.155/litolff_p1_2_10_base.record.json"),
                                         load("out/2.155/litolff_p1_2_10_edge.record.json"))}}
    counts = {}
    for t in ans["tiles"]:
        for name, recs in sets.items():
            if t["doc"] not in recs:
                continue
            b, e = recs[t["doc"]]
            if not any(o["subject"] == t["glyph"] for o in b["observations"] if o["quantity"] == "glyph_box"):
                continue
            rb, re_ = reading(b, t["glyph"]), reading(e, t["glyph"])
            vb, ve = verdict(t["sean"], rb), verdict(t["sean"], re_)
            t.setdefault("scored", {})[name] = dict(base=rb, arm=re_, base_verdict=vb, arm_verdict=ve)
            for arm, v in (("base", vb), ("arm", ve)):
                counts.setdefault(name, {}).setdefault(arm, {}).setdefault(v, 0)
                counts[name][arm][v] += 1
            print("%-12s %2d %-7s %-16s sean %-16s | base %-9s %-28s %-5s -> %-14s | arm %-9s %-28s %-5s -> %s" % (
                name, t["n"], t["doc"], t["role"], t["sean"], rb["outcome"], rb.get("reason"), rb.get("written"), vb,
                re_["outcome"], re_.get("reason"), re_.get("written"), ve))
    ans["scoring"] = ("score_2_155.py: decided = Sean -> right; narrowing holding Sean's value -> narrowed_right; no duration -> "
                      "refused (right only for the flat); grace notes scored by written value (no reader marks a grace note)")
    ans["counts"] = counts
    json.dump(ans, open("out/print/2.155-review/answers.json", "w"), indent=1)
    print(json.dumps(counts, indent=1))
