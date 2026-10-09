"""Re-score Sean's 12 judged tiles on the FRESH merged-tree records (match by box IoU)."""
import json

from tools.omr.staged import record_io

SP = "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-session-checkin-roadmap-ed72e9/8e902872-6f18-47fb-8e95-ff88adede5e7/scratchpad/t275/"
WT = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a44a0b3bce3ed7a64/out/print/2.75-review/"
man = json.load(open(WT + "manifest.json"))
ans = json.load(open(WT + "answers.json"))


def iou(a, b):
    ix = min(a[2], b[2]) - max(a[0], b[0])
    iy = min(a[3], b[3]) - max(a[1], b[1])
    if ix <= 0 or iy <= 0:
        return 0.0
    i = ix * iy
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


def load(path):
    r = record_io.load_record(path)["record"]
    ver = {}
    for v in r["verdicts"]:
        if v["quantity"] in ("arc_kind", "arc_is_not_an_arc"):
            ver[(v["quantity"], v["subject"])] = v
    out = []
    for o in r["observations"]:
        if o["quantity"] == "arc_box" and (o["detail"] or {}).get("bbox_page_px"):
            kv = ver.get(("arc_kind", o["subject"]))
            out.append((o["subject"], o["detail"]["bbox_page_px"],
                        kv["value"] if kv and kv["outcome"] == "decided" else None))
    return out


arcs = {"litolff": load(SP + "m_litolff.record.json"), "brahms": load(SP + "m_brahms.record.json")}


def best(doc, box, page):
    c = [a for a in arcs[doc] if int(a[0].split("/")[1]) == page]
    b = max(c, key=lambda a: iou(a[1], box))
    return b, iou(b[1], box)


right = 0
for a in man["arcs"]:
    n = a["tile"].replace(".png", "")
    sean = ans[n].split()[0].lower()
    (sub, box, kind), i = best(a["doc"], a["arc_box_page_px"], a["pdf_page_index"])
    ok = kind == sean
    right += ok
    print(n, "sean", sean, "ours", kind, "iou %.2f" % i, "OK" if ok else "WRONG")
print("single arcs right", right, "of", len(man["arcs"]))
for p in man["stacked_below"]:
    ka = best("brahms", p["A_box_page_px"], p["pdf_page_index"])
    kb = best("brahms", p["B_box_page_px"], p["pdf_page_index"])
    print(p["tile"], "A", ka[0][2], "B", kb[0][2])
