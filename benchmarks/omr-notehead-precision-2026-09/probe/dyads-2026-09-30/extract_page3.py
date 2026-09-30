import json, pickle, time
from pathlib import Path
from collections import defaultdict

REC = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/beethoven5-litolff-mvt1-whole-20260930b.record.json"
OUT = "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-acceptance-measure-notehead-box-e75821/2c34bf69-0e00-4748-a821-6f4862e751be/scratchpad/page3.pkl"

t0 = time.time()
d = json.loads(Path(REC).read_text())
print("loaded", time.time() - t0)
rec = d["record"]
obs = rec["observations"]
abst = rec["abstentions"]
verdicts = rec["verdicts"]

PAGE = 3

def subj_page(s):
    parts = s.split("/")
    if parts[0] == "document":
        return None
    return int(parts[1])

quantities_needed = {
    "glyph_box", "notehead_class", "notehead_staff_position",
    "notehead_is_not_a_notehead", "notehead_is_a_whole_rest",
    "cell_box", "cell_staff_space", "staff_lines", "staff_spacing",
    "stem", "stem_direction", "event", "duration", "onset_column",
    "voices", "pitch", "tie_pair", "arc_box", "arc_kind", "arc_owner",
    "glyph_conf", "rest", "rest_is_not_a_rest", "measure_partition",
    "printed_bar_number", "part_name", "system_membership",
}

by_q_page = defaultdict(list)
for o in obs:
    if o["quantity"] in quantities_needed:
        pg = subj_page(o["subject"])
        if pg == PAGE:
            by_q_page[o["quantity"]].append(o)

abst_by_q_page = defaultdict(list)
for a in abst:
    if a["quantity"] in quantities_needed:
        pg = subj_page(a["subject"])
        if pg == PAGE:
            abst_by_q_page[a["quantity"]].append(a)

verd_by_q_page = defaultdict(list)
for v in verdicts:
    if v["quantity"] in quantities_needed:
        pg = subj_page(v["subject"])
        if pg == PAGE:
            verd_by_q_page[v["quantity"]].append(v)

for q in sorted(quantities_needed):
    print(q, "obs", len(by_q_page.get(q, [])), "abst", len(abst_by_q_page.get(q, [])), "verd", len(verd_by_q_page.get(q, [])))

with open(OUT, "wb") as f:
    pickle.dump({
        "by_q_page": dict(by_q_page),
        "abst_by_q_page": dict(abst_by_q_page),
        "verd_by_q_page": dict(verd_by_q_page),
    }, f)
print("saved", OUT)
