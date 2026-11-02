"""2.248 r2: for Sean's 7 moved-note tiles, the ledger count's verdict (`notehead_position`, 2.56) beside the box-centre and
ink-centre positions, and his line/space answer.  usage: far_check.py ON_L ON_B KEY.json ANSWERS.json"""
import json
import sys


def load(p):
    r = json.load(open(p))
    return r.get("record", r)


def main(on_l, on_b, key, answers):
    recs = {"litolff": load(on_l), "brahms": load(on_b)}
    ans = json.load(open(answers))["line_or_space"]
    for t in json.load(open(key)):
        if t["kind"] != "position_moved":
            continue
        r = recs[t["plate"]]
        g = t["glyph"]
        far = [(v["outcome"], v.get("value"), v.get("reason")) for v in r["verdicts"]
               if v["subject"] == g and v["quantity"] == "notehead_position"]
        far_abs = [a.get("reason") for a in r.get("abstentions", ()) if a["subject"] == g and a["quantity"] == "far_head_ledger_position"]
        pitch = [(v.get("value"), v.get("decider"), v.get("reason")) for v in r["verdicts"] if v["subject"] == g and v["quantity"] == "pitch"]
        off, on = t["off_position"], t["on_position"]
        kind = lambda p: "line" if round(p) % 2 == 0 else "space"
        print("tile %s %s %s box %.2f(%s) ink %.2f(%s) Sean %s | ledger count %s %s | pitch %s" % (
            t["tile"], t["plate"], g, off, kind(off), on, kind(on), ans.get(str(t["tile"])), far, far_abs, pitch))


if __name__ == "__main__":
    main(*sys.argv[1:])
