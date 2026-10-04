import sys, json, re
REPO = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a3ef66441824adfff"
sys.path.insert(0, REPO)

LINE_RE = re.compile(r"(glyph/\d+/\d+/\d+/\d+/\d+)")

RECORDS = {}


def load(path):
    return json.loads(open(path).read())["record"]


RECORDS["base_litolff"] = load("/tmp/check-base/benchmarks/acceptance/quick/out/beethoven5-litolff/beethoven5-litolff-p3.record.json")
RECORDS["arm_litolff"] = load(REPO + "/benchmarks/acceptance/quick/out/beethoven5-litolff/beethoven5-litolff-p3.record.json")
try:
    RECORDS["base_brahms"] = load("/tmp/check-base/benchmarks/acceptance/quick/out/brahms1-breitkopf/brahms1-breitkopf-p1.record.json")
    RECORDS["arm_brahms"] = load(REPO + "/benchmarks/acceptance/quick/out/brahms1-breitkopf/brahms1-breitkopf-p1.record.json")
    HAVE_BRAHMS = True
except FileNotFoundError:
    HAVE_BRAHMS = False
    print("brahms base not ready yet -- litolff only")


def pos_of(rec, sub):
    rows = [o for o in rec["observations"]
           if o["subject"] == sub and o["quantity"] == "notehead_staff_position"]
    return float(rows[-1]["value"]) if rows else None


def box_of(rec, sub):
    for o in rec["observations"]:
        if o["subject"] == sub and o["quantity"] == "glyph_box":
            return o["detail"].get("bbox_page_px")
    return None


def which_doc(sub):
    if box_of(RECORDS["base_litolff"], sub) is not None:
        return "litolff"
    if HAVE_BRAHMS and box_of(RECORDS["base_brahms"], sub) is not None:
        return "brahms"
    return None


def load_subs(fname, pattern):
    subs = []
    with open(fname) as fh:
        for line in fh:
            if pattern in line:
                m = LINE_RE.search(line)
                if m:
                    subs.append(m.group(1))
    return subs


rtw = load_subs(REPO + "/benchmarks/omr-local-staff-2026-09/out/score_2_48_fix12.txt", "right  ->wrong")
wtr_all = []
with open(REPO + "/benchmarks/omr-local-staff-2026-09/out/score_2_48_fix12.txt") as fh:
    for line in fh:
        if "wrong  ->right" in line or "->right" in line and "right  ->wrong" not in line and "right ->wrong" not in line:
            if "wrong" in line.split("->")[0]:
                m = LINE_RE.search(line)
                if m:
                    wtr_all.append(m.group(1))

print(f"rtw={len(rtw)} wtr={len(wtr_all)}")

rows = []
for sub, kind in [(s, "rtw") for s in rtw] + [(s, "wtr") for s in wtr_all]:
    doc = which_doc(sub)
    if doc is None:
        continue
    base_rec, arm_rec = RECORDS[f"base_{doc}"], RECORDS[f"arm_{doc}"]
    base_box, arm_box = box_of(base_rec, sub), box_of(arm_rec, sub)
    base_pos, arm_pos = pos_of(base_rec, sub), pos_of(arm_rec, sub)
    if base_pos is None or arm_pos is None:
        continue
    base_round, arm_round = round(base_pos), round(arm_pos)
    rows.append(dict(sub=sub, doc=doc, kind=kind, box_same=(base_box == arm_box),
                     base_pos=round(base_pos, 3), arm_pos=round(arm_pos, 3),
                     base_round=base_round, arm_round=arm_round,
                     rounding_changed=(base_round != arm_round)))

changed = [r for r in rows if r["rounding_changed"]]
unchanged = [r for r in rows if not r["rounding_changed"]]
print(f"n={len(rows)}  rounding CHANGED (comb's real effect on THIS head): {len(changed)}  "
     f"rounding UNCHANGED (cascade/judge, not this head's geometry): {len(unchanged)}")
rtw_changed = [r for r in changed if r["kind"] == "rtw"]
wtr_changed = [r for r in changed if r["kind"] == "wtr"]
print(f"of rounding-CHANGED: right->wrong={len(rtw_changed)}  wrong->right={len(wtr_changed)}")
for r in rows:
    print(r)
