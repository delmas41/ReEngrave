import sys, json, re
import numpy as np

REPO = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a3ef66441824adfff"
sys.path.insert(0, REPO)
from tools.omr.preprocessing import render_page, deskew
from tools.omr import measure_extractor as me

LINE_RE = re.compile(r"(glyph/\d+/\d+/\d+/\d+/\d+)")

RECORDS = {
    "base_litolff": json.loads(open("/tmp/aa-base-1/benchmarks/acceptance/quick/out/beethoven5-litolff/beethoven5-litolff-p3.record.json").read())["record"],
    "arm_litolff": json.loads(open(REPO + "/benchmarks/acceptance/quick/out/beethoven5-litolff/beethoven5-litolff-p3.record.json").read())["record"],
    "base_brahms": json.loads(open("/tmp/aa-base-1/benchmarks/acceptance/quick/out/brahms1-breitkopf/brahms1-breitkopf-p1.record.json").read())["record"],
    "arm_brahms": json.loads(open(REPO + "/benchmarks/acceptance/quick/out/brahms1-breitkopf/brahms1-breitkopf-p1.record.json").read())["record"],
}
PDFS = {
    "litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
    "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
}

_page_cache = {}


def get_page(doc, page_idx):
    key = (doc, page_idx)
    if key not in _page_cache:
        page = render_page(PDFS[doc], page_idx, dpi=600)
        rgb, binary, skew = deskew(page.rgb, page.binary)
        page.rgb, page.binary, page.skew_correction_deg = rgb, binary, skew
        _page_cache[key] = page
    return _page_cache[key]


def box_of(rec, sub):
    for o in rec["observations"]:
        if o["subject"] == sub and o["quantity"] == "glyph_box":
            return o["detail"].get("bbox_page_px")
    return None


def staff_lines(rec, page_idx, system, staff):
    key = f"staff/{page_idx}/{system}/{staff}"
    for o in rec["observations"]:
        if o["subject"] == key and o["quantity"] == "staff_lines":
            return [float(y) for y in o["value"]]
    return None


def which_doc(sub):
    if box_of(RECORDS["base_litolff"], sub) is not None:
        return "litolff"
    if box_of(RECORDS["base_brahms"], sub) is not None:
        return "brahms"
    return None


subs = []
with open(REPO + "/benchmarks/omr-local-staff-2026-09/out/score_2_48_fix12.txt") as fh:
    for line in fh:
        if "right  ->wrong" in line or "right ->wrong" in line:
            m = LINE_RE.search(line)
            if m:
                subs.append(m.group(1))
print(f"parsed {len(subs)} right->wrong subjects")

rows = []
for sub in subs:
    doc = which_doc(sub)
    if doc is None:
        print(f"{sub}: not found in either record, skipped")
        continue
    base_rec, arm_rec = RECORDS[f"base_{doc}"], RECORDS[f"arm_{doc}"]
    base_box = box_of(base_rec, sub)
    arm_box = box_of(arm_rec, sub)
    box_same = (base_box == arm_box)
    parts = sub.split("/")
    page_idx, system, staff, cell, glyph_i = (int(x) for x in parts[1:6])
    lines = staff_lines(base_rec, page_idx, system, staff)
    if lines is None or base_box is None:
        rows.append(dict(sub=sub, doc=doc, box_same=box_same, shift_px=None,
                         shift_steps=None))
        continue
    spacing = (max(lines) - min(lines)) / 4.0
    half_step = spacing / 2.0
    cx = (base_box[0] + base_box[2]) / 2.0
    page = get_page(doc, page_idx)
    win = 150
    wx0, wx1 = max(0, int(cx - win)), min(page.binary.shape[1], int(cx + win))
    thickness = None
    shift = me._walk_comb_shift(page.binary, lines, wx0, wx1, spacing,
                                line_thickness_px=thickness)
    shift_px = None
    if shift is not None:
        idx = min(len(shift) - 1, max(0, int(cx) - wx0))
        shift_px = float(shift[idx])
    rows.append(dict(sub=sub, doc=doc, box_same=box_same,
                     shift_px=shift_px,
                     shift_steps=(shift_px / half_step if shift_px is not None else None)))

n_box_diff = sum(1 for r in rows if not r["box_same"])
n_small_shift = sum(1 for r in rows if r["shift_steps"] is not None and abs(r["shift_steps"]) < 0.1)
attributable = [r for r in rows
               if r["box_same"] and r["shift_steps"] is not None and abs(r["shift_steps"]) >= 0.1]
print(f"n={len(rows)}  box differs: {n_box_diff}  |shift|<0.1 step: {n_small_shift}  "
     f"attributable to the comb (box same AND |shift|>=0.1 step): {len(attributable)}")
for r in rows:
    print(r)
