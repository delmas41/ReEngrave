"""Fate of the chord flips made by a0d77e6a under the top/bottom rule, + the 12 tiles.
usage: analyze3.py  (reads t275/m_*.record.json and v3_*.rows.json)"""
import collections
import json

from tools.omr.staged import record_io

SP = "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-session-checkin-roadmap-ed72e9/8e902872-6f18-47fb-8e95-ff88adede5e7/scratchpad/t275/"
WT = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a44a0b3bce3ed7a64/out/print/2.75-review/"


def prev_verdicts(path):
    r = record_io.load_record(path)["record"]
    out = {}
    for v in r["verdicts"]:
        if v["quantity"] == "arc_kind":
            g = ((v.get("detail") or {}).get("grammar") or {}).get("tie_slur_rule") or {}
            out[v["subject"]] = (v["outcome"], v["value"], (g.get("two_note") or {}), g.get("detector_class"))
    return out


tot = collections.Counter()
detail = {}
for doc in ("litolff", "brahms"):
    prev = prev_verdicts(SP + f"m_{doc}.record.json")
    rows = {r["sub"]: r for r in json.load(open(SP + f"v3_{doc}.rows.json"))}
    flips = []
    for sub, (outc, val, tn, det) in prev.items():
        r = rows[sub]
        if r["refused"]:
            continue
        if det == "slur" and val == "tie" and tn.get("chord"):
            flips.append(sub)
    c = collections.Counter()
    for sub in flips:
        r = rows[sub]
        tn = (r.get("rule") or {}).get("two_note") or {}
        fate = ("tie (kept)" if r["kind"] == "tie" else
                "slur (class stands)" if r["kind"] == "slur" else "abstain")
        why = tn.get("relation") or tn.get("why")
        c[(fate, why)] += 1
    detail[doc] = (len(flips), c)
    print(doc, "chord slur->tie flips of the previous rule:", len(flips))
    for k, v in sorted(c.items(), key=lambda kv: -kv[1]):
        print("   ", v, k)
    # all arcs: new vs detector
    ch = collections.Counter()
    for sub, r in rows.items():
        if r["refused"] or not r["box"]:
            continue
        k = r["kind"] or "ABSTAIN"
        if k != r["det"]:
            ch[(r["det"], k)] += 1
    print("   all changes vs detector:", dict(ch))
    # previous tie->slur chord flips
    bad = [s for s, (o, v, tn, d) in prev.items() if not rows[s]["refused"] and d == "tie" and v == "slur" and tn.get("chord")]
    print("   previous-rule chord tie->slur flips:", len(bad), "->", collections.Counter((rows[s]["kind"] or "ABSTAIN") for s in bad))

man = json.load(open(WT + "manifest.json"))
ans = json.load(open(WT + "answers.json"))


def iou(a, b):
    ix = min(a[2], b[2]) - max(a[0], b[0])
    iy = min(a[3], b[3]) - max(a[1], b[1])
    if ix <= 0 or iy <= 0:
        return 0.0
    i = ix * iy
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


R = {d: [r for r in json.load(open(SP + f"v3_{d}.rows.json")) if r["box"]] for d in ("litolff", "brahms")}


def best(doc, box, page):
    c = [r for r in R[doc] if int(r["sub"].split("/")[1]) == page]
    return max(c, key=lambda r: iou(r["box"], box))


right = 0
for a in man["arcs"]:
    n = a["tile"].replace(".png", "")
    sean = ans[n].split()[0].lower()
    r = best(a["doc"], a["arc_box_page_px"], a["pdf_page_index"])
    ok = r["kind"] == sean
    right += ok
    tn = (r.get("rule") or {}).get("two_note") or {}
    print(n, "sean", sean, "ours", r["kind"], "det", r["det"], "OK" if ok else "NOT-RIGHT",
          "| relation", tn.get("relation"), "side", tn.get("arc_side"), "steps", tn.get("start_step"), tn.get("stop_step"),
          tn.get("start_candidate"), tn.get("stop_candidate"), tn.get("start_step_source"), tn.get("stop_step_source"))
print("single arcs right:", right, "of", len(man["arcs"]))
for p in man["stacked_below"]:
    ra = best("brahms", p["A_box_page_px"], p["pdf_page_index"])
    rb = best("brahms", p["B_box_page_px"], p["pdf_page_index"])
    print(p["tile"], "A", ra["kind"], "B", rb["kind"])
